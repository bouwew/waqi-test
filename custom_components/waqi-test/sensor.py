from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    PRESSURE_HPA,
    TEMP_CELSIUS,
)

from .const import DOMAIN


@dataclass
class EntityDescriptionMixin:
    """Mixin used to handle data for the WAQI sensors."""

    found_fn: Callable[[dict[str, Any]], StateType]
    value_fn: Callable[[dict[str, Any]], StateType]


@dataclass
class WAQISensorEntityDescription(SensorEntityDescription, EntityDescriptionMixin):
    """Class describing WAQI sensor entities."""


SENSOR_DESCRIPTIONS: tuple[WAQISensorEntityDescription, ...] = (
    WAQISensorEntityDescription(
        key="aqi",
        icon="mdi:air-filter",
        name="AQI",
        native_unit_of_measurement="AQI",
        found_fn=lambda data: "aqi" in data,
        value_fn=lambda data: data["aqi"],
    ),
    WAQISensorEntityDescription(
        key="pm25",
        device_class=SensorDeviceClass.PM25,
        name="PM2.5",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "pm25" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["pm25"]["v"],
    ),
    WAQISensorEntityDescription(
        key="pm10",
        device_class=SensorDeviceClass.PM10,
        name="PM10",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "pm10" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["pm10"]["v"],
    ),
    WAQISensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "h" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["h"]["v"],
    ),
    WAQISensorEntityDescription(
        key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        name="Pressure",
        native_unit_of_measurement=PRESSURE_HPA,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "p" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["p"]["v"],
    ),
    WAQISensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "t" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["t"]["v"],
    ),
    WAQISensorEntityDescription(
        key="co",
        name="CO",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "co" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["co"]["v"],
    ),
    WAQISensorEntityDescription(
        key="no2",
        device_class=SensorDeviceClass.NITROGEN_DIOXIDE,
        name="NO2",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "no2" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["no2"]["v"],
    ),
    WAQISensorEntityDescription(
        key="so2",
        device_class=SensorDeviceClass.SULPHUR_DIOXIDE,
        name="SO2",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "so2" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["so2"]["v"],
    ),
    WAQISensorEntityDescription(
        key="o3",
        device_class=SensorDeviceClass.OZONE,
        name="O3",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        found_fn=lambda data: "o3" in data["iaqi"],
        value_fn=lambda data: data["iaqi"]["o3"]["v"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        (
            WAQISensor(coordinator, description, entry.unique_id, entry.title)
            for description in SENSOR_DESCRIPTIONS
            if description.found_fn(coordinator.data)
        ),
    )


class WAQISensor(CoordinatorEntity[DataUpdateCoordinator], SensorEntity):
    """Defines a WAQI sensor entity."""

    _attr_attribution = "Data provided by the World Air Quality Index project."
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entity_description: WAQISensorEntityDescription,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)

        self.entity_description = entity_description

        self._attrs = {}

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            name=name,
        )

        self._attr_unique_id = f"{DOMAIN}-{unique_id}-{entity_description.key}".lower()

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
