"""Support for Hubitat thermostats."""

from typing import Any

from custom_components.hubitat.const import TEMP_C, TEMP_F
from homeassistant.backports.enum import StrEnum
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_ON,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from .device import HubitatEntity
from .entities import create_and_add_entities
from .hubitatmaker import Device, DeviceCapability, DeviceCommand
from .types import EntityAdder


class ClimateAttr(StrEnum):
    COOLING_SETPOINT = "coolingSetpoint"
    FAN_MODE = "thermostatFanMode"
    HEATING_SETPOINT = "heatingSetpoint"
    HUMIDITY = "humidity"
    MODE = "thermostatMode"
    NEST_MODE = "nestThermostatMode"
    NEST_SUPPORTED_MODES = "supportedNestThermostatModes"
    OPERATING_STATE = "thermostatOperatingState"
    PRESENCE = "presence"
    SUPPORTED_FAN_MODES = "supportedThermostatFanModes"
    SUPPORTED_MODES = "supportedThermostatModes"
    TEMP = "temperature"
    TEMP_UNIT = "temperatureUnit"


class ClimateMode(StrEnum):
    AUTO = "auto"
    COOL = "cool"
    EMERGENCY_HEAT = "emergency heat"
    HEAT = "heat"
    NEST_ECO = "eco"
    OFF = "off"


class ClimateOpState(StrEnum):
    HEATING = "heating"
    PENDING_COOL = "pending cool"
    PENDING_HEAT = "pending heat"
    VENT_ECONOMIZER = "vent economizer"
    IDLE = "idle"
    COOLING = "cooling"
    FAN_ONLY = "fan only"


class ClimatePresence(StrEnum):
    PRESENT = "present"
    AWAY = "not present"


PRESET_AWAY_AND_ECO = "Away and Eco"
HASS_PRESET_MODES = [PRESET_HOME, PRESET_AWAY]
HASS_NEST_PRESET_MODES = [PRESET_HOME, PRESET_AWAY, PRESET_ECO, PRESET_AWAY_AND_ECO]


class ClimateFanMode(StrEnum):
    ON = "on"
    AUTO = "auto"
    CIRCULATE = "circulate"


HASS_FAN_MODES = [FAN_ON, FAN_AUTO]

_device_attrs = (
    ClimateAttr.COOLING_SETPOINT,
    ClimateAttr.FAN_MODE,
    ClimateAttr.HEATING_SETPOINT,
    ClimateAttr.HUMIDITY,
    ClimateAttr.MODE,
    ClimateAttr.NEST_MODE,
    ClimateAttr.OPERATING_STATE,
    ClimateAttr.PRESENCE,
    ClimateAttr.TEMP,
    ClimateAttr.TEMP_UNIT,
)


class HubitatThermostat(HubitatEntity, ClimateEntity):
    """Representation of a Hubitat switch."""

    @property
    def device_attrs(self) -> tuple[str, ...] | None:
        """Return this entity's associated attributes"""
        return _device_attrs

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self.get_int_attr(ClimateAttr.HUMIDITY)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.get_float_attr(ClimateAttr.TEMP)

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        mode = self.get_str_attr(ClimateAttr.FAN_MODE)
        if mode == ClimateFanMode.CIRCULATE or mode == ClimateFanMode.ON:
            return FAN_ON
        if mode == ClimateFanMode.AUTO:
            return FAN_AUTO
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return HASS_FAN_MODES

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self.get_str_attr(ClimateAttr.MODE)
        if mode == ClimateMode.OFF:
            return HVACMode.OFF
        if mode == ClimateMode.HEAT or mode == ClimateMode.EMERGENCY_HEAT:
            return HVACMode.HEAT
        if mode == ClimateMode.COOL:
            return HVACMode.COOL
        return HVACMode.AUTO

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac operation modes."""
        return [
            HVACMode.AUTO,
            HVACMode.HEAT,
            HVACMode.HEAT_COOL,
            HVACMode.COOL,
            HVACMode.OFF,
        ]

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported."""
        opstate = self.get_str_attr(ClimateAttr.OPERATING_STATE)
        if opstate == ClimateOpState.PENDING_HEAT or opstate == ClimateOpState.HEATING:
            return HVACAction.HEATING
        if opstate == ClimateOpState.PENDING_COOL or opstate == ClimateOpState.COOLING:
            return HVACAction.COOLING
        if opstate == ClimateOpState.FAN_ONLY:
            return HVACAction.FAN
        if opstate == ClimateOpState.IDLE:
            return HVACAction.IDLE
        return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        nest_mode = self.get_str_attr(ClimateAttr.NEST_MODE)
        presence = self.get_str_attr(ClimateAttr.PRESENCE)
        if nest_mode == ClimateMode.NEST_ECO:
            if presence == ClimatePresence.AWAY:
                return PRESET_AWAY_AND_ECO
            return PRESET_ECO
        if presence == ClimatePresence.AWAY:
            return PRESET_AWAY
        return PRESET_HOME

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        nest_mode = self.get_str_attr(ClimateAttr.NEST_MODE)
        if nest_mode is not None:
            return HASS_NEST_PRESET_MODES
        return HASS_PRESET_MODES

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.FAN_MODE
        )

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT:
            return self.get_float_attr(ClimateAttr.HEATING_SETPOINT)
        if self.hvac_mode == HVACMode.COOL:
            return self.get_float_attr(ClimateAttr.COOLING_SETPOINT)
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            return self.get_float_attr(ClimateAttr.COOLING_SETPOINT)
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            return self.get_float_attr(ClimateAttr.HEATING_SETPOINT)
        return None

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        unit = self.get_str_attr(ClimateAttr.TEMP_UNIT)
        if unit == TEMP_F:
            return UnitOfTemperature.FAHRENHEIT
        if unit == TEMP_C:
            return UnitOfTemperature.CELSIUS
        return (
            UnitOfTemperature.FAHRENHEIT
            if self._hub.temperature_unit == TEMP_F
            else UnitOfTemperature.CELSIUS
        )

    @property
    def precision(self) -> float:
        """Return current temperature precision in tenths."""
        return PRECISION_TENTHS

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this climate."""
        return f"{super().unique_id}::climate"

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode == FAN_ON:
            await self.send_command(DeviceCommand.FAN_ON)
        elif fan_mode == FAN_AUTO:
            await self.send_command(DeviceCommand.FAN_AUTO)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.COOL:
            await self.send_command(DeviceCommand.COOL)
        elif hvac_mode == HVACMode.HEAT:
            await self.send_command(DeviceCommand.HEAT)
        elif hvac_mode == HVACMode.HEAT_COOL or hvac_mode == HVACMode.AUTO:
            await self.send_command(DeviceCommand.AUTO)
        elif hvac_mode == HVACMode.OFF:
            await self.send_command(DeviceCommand.OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.send_command(DeviceCommand.AWAY)
        if preset_mode == PRESET_HOME:
            await self.send_command(DeviceCommand.PRESENT)
        if preset_mode == PRESET_ECO:
            await self.send_command(DeviceCommand.ECO)
        if preset_mode == PRESET_AWAY_AND_ECO:
            await self.send_command(DeviceCommand.AWAY)
            await self.send_command(DeviceCommand.ECO)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if self.hvac_mode == HVACMode.HEAT_COOL or self.hvac_mode == HVACMode.AUTO:
            temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
            temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
            if temp_low is not None:
                await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp_low)
            if temp_high is not None:
                await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp_high)
        else:
            temp = kwargs.get(ATTR_TEMPERATURE)
            if temp is not None:
                if self.hvac_mode == HVACMode.COOL:
                    await self.send_command(DeviceCommand.SET_COOLING_SETPOINT, temp)
                elif self.hvac_mode == HVACMode.HEAT:
                    await self.send_command(DeviceCommand.SET_HEATING_SETPOINT, temp)


def is_thermostat(device: Device, overrides: dict[str, str] | None = None) -> bool:
    """Return True if device looks like a thermostat."""
    return DeviceCapability.THERMOSTAT in device.capabilities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: EntityAdder,
) -> None:
    """Initialize thermostat devices."""
    create_and_add_entities(
        hass, entry, async_add_entities, "climate", HubitatThermostat, is_thermostat
    )
