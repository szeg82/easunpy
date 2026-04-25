"""Support for Easun Inverter number entities."""
import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfElectricCurrent

from . import DOMAIN
from .sensor import DataCollector

_LOGGER = logging.getLogger(__name__)

class EasunNumber(NumberEntity):
    """Representation of an Easun Inverter number entity."""

    def __init__(self, data_collector, id, name, unit, data_type, data_attr, min_value, max_value, step, scale=1.0, entry_id=None):
        """Initialize the number entity."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._scale = scale  # Scale factor (e.g. 0.1 for voltages)
        self._value = None
        self._available = True
        self._entry_id = entry_id
        
        # Register with data collector to update state when data is fetched
        self._data_collector.register_sensor(self)

    def update_from_collector(self) -> None:
        """Update number state from data collector."""
        try:
            data = self._data_collector.get_data(self._data_type)
            if data:
                raw_value = getattr(data, self._data_attr, None)
                if raw_value is not None:
                    self._value = raw_value * self._scale
                self._available = True
            else:
                self._available = False
        except Exception as e:
            _LOGGER.error(f"Error updating number {self._name}: {str(e)}")
            self._available = False
        
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the number entity."""
        return f"Easun {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"easun_inverter_{self._id}"

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return self._value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._unit

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def native_step(self) -> float:
        """Return the increment step."""
        return self._step

    @property
    def mode(self) -> NumberMode:
        """Return the mode of the entity."""
        return NumberMode.BOX

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def should_poll(self) -> bool:
        """Return False as entity is updated by the data collector."""
        return False

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(f"Setting {self._name} to {value}")
        
        # Convert back to raw integer value for Modbus
        raw_value = int(value / self._scale)
        
        # Call the library to write the value
        success = await self._data_collector._isolar.write_register(self._data_attr, raw_value)
        
        if success:
            self._value = value
            self.async_write_ha_state()
            # Trigger a data refresh to confirm the change
            await self._data_collector.update_data()
        else:
            _LOGGER.error(f"Failed to set {self._name} to {value}")

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Easun Inverter number entities."""
    _LOGGER.debug("Setting up Easun Inverter number entities")
    
    data_collector = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    # SMG II 11kW registers:
    # 637: Bulk Charging Voltage (48.0 - 60.0, step 0.1)
    # 638: Floating Charging Voltage (48.0 - 60.0, step 0.1)
    # 640: Max Charging Current (0 - 150, step 1) -> Actually scale might be 1.0 or 0.1, check.
    # 641: Max Mains Charging Current (0 - 150, step 1)

    entities = [
        EasunNumber(
            data_collector, 
            "bulk_charging_voltage", 
            "Bulk Charging Voltage", 
            UnitOfElectricPotential.VOLT, 
            "system", 
            "bulk_charging_voltage", 
            48.0, 64.0, 0.1, 0.1,
            config_entry.entry_id
        ),
        EasunNumber(
            data_collector, 
            "floating_charging_voltage", 
            "Floating Charging Voltage", 
            UnitOfElectricPotential.VOLT, 
            "system", 
            "floating_charging_voltage", 
            48.0, 64.0, 0.1, 0.1,
            config_entry.entry_id
        ),
        EasunNumber(
            data_collector, 
            "max_charging_current", 
            "Max Charging Current", 
            UnitOfElectricCurrent.AMPERE, 
            "system", 
            "max_charging_current", 
            0, 150, 1, 1.0,
            config_entry.entry_id
        ),
        EasunNumber(
            data_collector, 
            "max_mains_charging_current", 
            "Max Utility Charging Current", 
            UnitOfElectricCurrent.AMPERE, 
            "system", 
            "max_mains_charging_current", 
            0, 150, 1, 1.0,
            config_entry.entry_id
        ),
    ]
    
    add_entities(entities)
