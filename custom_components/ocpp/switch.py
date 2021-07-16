"""Switch platform for ocpp."""
from typing import Any

from homeassistant.components.switch import SwitchEntity

from ocpp.v16.enums import ChargePointStatus

from .api import CentralSystem
from .const import CONF_CPID, DOMAIN, ICON
from .enums import HAChargerServices, HAChargerStatuses

# At a minimum define switch name and on service call, pulse used to call a service once such as reset
# metric and condition combination can be used to drive switch state, use default to set initial state to True
SWITCH_CHARGE = {
    "name": "Charge_Control",
    "on": HAChargerServices.service_charge_start.name,
    "off": HAChargerServices.service_charge_stop.name,
    "metric": HAChargerStatuses.status.value,
    "condition": ChargePointStatus.charging.value,
}
SWITCH_AVAILABILITY = {
    "name": "Availability",
    "on": HAChargerServices.service_availability.name,
    "off": HAChargerServices.service_availability.name,
    "default": True,
    "metric": HAChargerStatuses.status.value,
    "condition": ChargePointStatus.available.value,
}
SWITCH_RESET = {
    "name": "Reset",
    "on": HAChargerServices.service_reset.name,
    "pulse": True,
}
SWITCH_UNLOCK = {
    "name": "Unlock",
    "on": HAChargerServices.service_unlock.name,
    "pulse": True,
}


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the sensor platform."""
    central_system = hass.data[DOMAIN][entry.entry_id]
    cp_id = entry.data[CONF_CPID]

    entities = []

    for ent in [SWITCH_CHARGE, SWITCH_AVAILABILITY, SWITCH_RESET, SWITCH_UNLOCK]:
        entities.append(ChargePointSwitch(central_system, cp_id, ent))

    async_add_devices(entities, False)


class ChargePointSwitch(SwitchEntity):
    """Individual switch for charge point."""

    def __init__(self, central_system: CentralSystem, cp_id: str, serv_desc):
        """Instantiate instance of a ChargePointSwitch."""
        self.cp_id = cp_id
        self._state = False
        self.central_system = central_system
        self._purpose = serv_desc
        if self._purpose.get("default") is not None:
            self._state = bool(self._purpose["default"])
        else:
            self._state = False
        self._id = ".".join(["switch", DOMAIN, self.cp_id, self._purpose["name"]])
        self._name = ".".join([self.cp_id, self._purpose["name"]])
        self.entity_id = "switch." + "_".join([self.cp_id, self._purpose["name"]])

    @property
    def unique_id(self):
        """Return the unique id of this entity."""
        return self._id

    @property
    def available(self) -> bool:
        """Return if switch is available."""
        return True  # type: ignore [no-any-return]

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        if self._purpose.get("metric") is not None:
            resp = self.central_system.get_metric(self.cp_id, self._purpose["metric"])
            if resp == self._purpose["condition"]:
                self._state = True
            else:
                self._state = False
        return self._state  # type: ignore [no-any-return]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """For a pulse switch, reset to off afterwards."""
        if self._purpose.get("pulse", False) is True:
            resp = await self.central_system.set_charger_state(
                self.cp_id, self._purpose["on"]
            )
            self._state = not resp
        else:
            self._state = await self.central_system.set_charger_state(
                self.cp_id, self._purpose["on"]
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        """Response is True if successful but State is False"""
        if self._purpose.get("off") is None:
            resp = True
        elif self._purpose["off"] == self._purpose["on"]:
            resp = await self.central_system.set_charger_state(
                self.cp_id, self._purpose["off"], False
            )
        else:
            resp = await self.central_system.set_charger_state(
                self.cp_id, self._purpose["off"]
            )
        self._state = not resp

    @property
    def current_power_w(self) -> float:
        """Return the current power usage in W."""
        return self.central_system.get_metric(self.cp_id, "Power.Active.Import")

    @property
    def name(self):
        """Return the name of this entity."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.cp_id)},
            "via_device": (DOMAIN, self.central_system.id),
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "unique_id": self.unique_id,
            "integration": DOMAIN,
        }

    def update(self):
        """Get the latest data and update the states."""
        pass
