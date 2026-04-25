"""Support for Easun Inverter select entities."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from . import DOMAIN
from .sensor import DataCollector

_LOGGER = logging.getLogger(__name__)

class EasunSelect(SelectEntity):
    """Representation of an Easun Inverter select entity."""

    def __init__(self, data_collector, id, name, data_type, data_attr, options_map, entry_id=None):
        """Initialize the select entity."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._data_type = data_type
        self._data_attr = data_attr
        self._options_map = options_map  # Dictionary of {value: label}
        self._reverse_options_map = {v: k for k, v in options_map.items()}
        self._current_option = None
        self._available = True
        self._entry_id = entry_id
        
        # Register with data collector to update state when data is fetched
        self._data_collector.register_sensor(self)

    def update_from_collector(self) -> None:
        """Update select state from data collector."""
        try:
            data = self._data_collector.get_data(self._data_type)
            if data:
                # We need to make sure the data model has these attributes
                # For now, we might need to read them separately if they aren't in the bulk read
                # But for this implementation, we assume they are available or will be added
                value = getattr(data, self._data_attr, None)
                if value in self._options_map:
                    self._current_option = self._options_map[value]
                self._available = True
            else:
                self._available = False
        except Exception as e:
            _LOGGER.error(f"Error updating select {self._name}: {str(e)}")
            self._available = False
        
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the select entity."""
        return f"Easun {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"easun_inverter_{self._id}"

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return list(self._options_map.values())

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._current_option

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def should_poll(self) -> bool:
        """Return False as entity is updated by the data collector."""
        return False

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self._reverse_options_map:
            _LOGGER.error(f"Invalid option selected: {option}")
            return

        value = self._reverse_options_map[option]
        _LOGGER.info(f"Setting {self._name} to {option} (value: {value})")
        
        # Call the library to write the value
        success = await self._data_collector._isolar.write_register(self._data_attr, value)
        
        if success:
            self._current_option = option
            self.async_write_ha_state()
            # Trigger a data refresh to confirm the change
            await self._data_collector.update_data()
        else:
            _LOGGER.error(f"Failed to set {self._name} to {option}")

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Easun Inverter select entities."""
    _LOGGER.debug("Setting up Easun Inverter select entities")
    
    data_collector = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    # Define options for priorities
    # SMG II 11kW registers:
    # 601: Output Source Priority (1: SUB, 2: SBU, 3: USB/Solar First)
    # 632: Charger Source Priority (1: Solar First, 2: Solar & Utility, 3: Only Solar)
    
    output_priority_options = {
        1: "Solar-Utility-Battery (SUB)",
        2: "Solar-Battery-Utility (SBU)",
        3: "Utility-Solar-Battery (USB)",
    }
    
    charger_priority_options = {
        1: "Solar First",
        2: "Solar and Utility",
        3: "Only Solar",
    }

    entities = [
        EasunSelect(
            data_collector, 
            "output_source_priority", 
            "Output Source Priority", 
            "system", 
            "output_source_priority", 
            output_priority_options,
            config_entry.entry_id
        ),
        EasunSelect(
            data_collector, 
            "charger_source_priority", 
            "Charger Source Priority", 
            "system", 
            "charger_source_priority", 
            charger_priority_options,
            config_entry.entry_id
        ),
    ]
    
    add_entities(entities)
