"""Sensor platform for Nixle integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ALERT_TYPES, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nixle sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Extract agency name from URL
    agency_url = entry.data["agency_url"]
    agency_id = agency_url.split("/")[-2] if agency_url.endswith("/") else agency_url.split("/")[-1]
    agency_name = agency_id.replace("-", " ").title()
    
    alert_types_filter = entry.data.get(CONF_ALERT_TYPES, [])
    
    sensors = [
        NixleTotalAlertsSensor(coordinator, entry, agency_name, agency_id),
        NixleAlertCountSensor(coordinator, entry, agency_name, agency_id, "alert"),
        NixleAlertCountSensor(coordinator, entry, agency_name, agency_id, "advisory"),
        NixleAlertCountSensor(coordinator, entry, agency_name, agency_id, "community"),
        NixleLatestAlertSensor(coordinator, entry, agency_name, agency_id, alert_types_filter),
    ]
    
    async_add_entities(sensors)


class NixleBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Nixle."""

    def __init__(self, coordinator, entry, agency_name, agency_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._agency_name = agency_name
        self._agency_id = agency_id
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._agency_id)},
            name=f"Nixle - {self._agency_name}",
            manufacturer="Nixle",
            model="Alert Service",
            configuration_url=self._entry.data["agency_url"],
        )


class NixleTotalAlertsSensor(NixleBaseSensor):
    """Sensor for total alert count."""

    def __init__(self, coordinator, entry, agency_name, agency_id):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, agency_name, agency_id)
        self._attr_name = f"{agency_name} Total Alerts"
        self._attr_unique_id = f"{agency_id}_total_alerts"
        self._attr_icon = "mdi:bell"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data["counts"]["total"]
        return 0

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "last_updated": self.coordinator.data.get("last_updated"),
            "alert_count": self.coordinator.data["counts"]["alert"],
            "advisory_count": self.coordinator.data["counts"]["advisory"],
            "community_count": self.coordinator.data["counts"]["community"],
        }


class NixleAlertCountSensor(NixleBaseSensor):
    """Sensor for specific alert type count."""

    def __init__(self, coordinator, entry, agency_name, agency_id, alert_type):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, agency_name, agency_id)
        self._alert_type = alert_type
        self._attr_name = f"{agency_name} {alert_type.title()} Count"
        self._attr_unique_id = f"{agency_id}_{alert_type}_count"
        self._attr_icon = "mdi:bell-alert" if alert_type == "alert" else "mdi:information"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data["counts"][self._alert_type]
        return 0


class NixleLatestAlertSensor(NixleBaseSensor):
    """Sensor for the latest alert."""

    def __init__(self, coordinator, entry, agency_name, agency_id, alert_types_filter):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, agency_name, agency_id)
        self._alert_types_filter = alert_types_filter
        self._attr_name = f"{agency_name} Latest Alert"
        self._attr_unique_id = f"{agency_id}_latest_alert"
        self._attr_icon = "mdi:bell-ring"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.data["alerts"]:
            return "No alerts"
        
        # Filter by alert types if specified
        alerts = self.coordinator.data["alerts"]
        if self._alert_types_filter:
            alerts = [a for a in alerts if a["type"].lower() in self._alert_types_filter]
        
        if not alerts:
            return "No matching alerts"
        
        latest = alerts[0]
        return latest["text"][:100] + ("..." if len(latest["text"]) > 100 else "")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if not self.coordinator.data or not self.coordinator.data["alerts"]:
            return {}
        
        alerts = self.coordinator.data["alerts"]
        if self._alert_types_filter:
            alerts = [a for a in alerts if a["type"].lower() in self._alert_types_filter]
        
        if not alerts:
            return {}
        
        latest = alerts[0]
        
        # Include last 5 alerts
        recent_alerts = []
        for alert in alerts[:5]:
            recent_alerts.append({
                "type": alert["type"],
                "timestamp": alert["timestamp"],
                "text": alert["text"],
                "link": alert.get("link"),
            })
        
        return {
            "type": latest["type"],
            "timestamp": latest["timestamp"],
            "full_text": latest["text"],
            "link": latest.get("link"),
            "recent_alerts": recent_alerts,
        }
