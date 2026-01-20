"""Binary sensor platform for Nixle integration."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Month name to number mapping
MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nixle binary sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Extract agency info
    agency_url = entry.data["agency_url"]
    agency_id = agency_url.split("/")[-2] if agency_url.endswith("/") else agency_url.split("/")[-1]
    agency_name = agency_id.replace("-", " ").title()
    
    sensors = [
        NixleActiveAlertSensor(coordinator, entry, agency_name, agency_id),
    ]
    
    async_add_entities(sensors)


class NixleActiveAlertSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for active Nixle alerts."""

    def __init__(self, coordinator, entry, agency_name, agency_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._agency_name = agency_name
        self._agency_id = agency_id
        self._attr_name = f"{agency_name} Active Alert"
        self._attr_unique_id = f"{agency_id}_active_alert"
        self._attr_icon = "mdi:alert"
        self._attr_device_class = "safety"

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

    def _parse_alert_date(self, text: str) -> datetime | None:
        """Parse date from alert text."""
        now = dt_util.now()
        
        # Pattern: "tonight, Day, Month Date, Year" or "tonight, Day, Month Date"
        # Example: "tonight, Sunday, January 18, 2026" or "tonight, Sunday, January 18th"
        tonight_pattern = r"tonight,\s+\w+,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s+(\d{4}))?"
        match = re.search(tonight_pattern, text, re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            year = int(year) if year else now.year
            month = MONTHS.get(month_name, now.month)
            day = int(day)
            # "tonight" means the alert date, expires 6am next day
            alert_date = datetime(year, month, day, 6, 0, 0)
            return dt_util.as_local(alert_date) + timedelta(days=1)
        
        # Pattern: "for Day night, Month Date" or "may be declared Day night, Month Date"
        # Example: "Sunday night, January 18th"
        night_pattern = r"(?:for|declared)\s+\w+\s+night,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?"
        match = re.search(night_pattern, text, re.IGNORECASE)
        if match:
            month_name, day = match.groups()
            month = MONTHS.get(month_name, now.month)
            day = int(day)
            # Night declaration expires 6am next day
            alert_date = datetime(now.year, month, day, 6, 0, 0)
            return dt_util.as_local(alert_date) + timedelta(days=1)
        
        # Pattern: "for Day, Month Date" (not tonight)
        # Example: "for Tuesday, March 14"
        day_pattern = r"for\s+\w+,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s+(\d{4}))?"
        match = re.search(day_pattern, text, re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            year = int(year) if year else now.year
            month = MONTHS.get(month_name, now.month)
            day = int(day)
            # Specific day expires 6am next day
            alert_date = datetime(year, month, day, 6, 0, 0)
            return dt_util.as_local(alert_date) + timedelta(days=1)
        
        return None

    def _is_alert_active(self, alert: dict) -> bool:
        """Check if an alert is currently active."""
        alert_type = alert.get("type", "")
        text = alert.get("text", "")
        
        # Only process "Alert" type
        if alert_type != "Alert":
            return False
        
        # Check if it's a "may be declared" alert
        if "may be declared" in text.lower():
            # Active only for today until 6am tomorrow
            expiry = self._parse_alert_date(text)
            if expiry:
                now = dt_util.now()
                # If no specific date, expires 6am tomorrow
                if expiry < now:
                    return False
                return True
            # Default: active until 6am tomorrow
            tomorrow_6am = dt_util.now().replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return dt_util.now() < tomorrow_6am
        
        # Check if alert has expired
        expiry = self._parse_alert_date(text)
        if expiry:
            return dt_util.now() < expiry
        
        # If we can't parse a date, not active
        return False

    @property
    def is_on(self) -> bool:
        """Return true if there's an active alert."""
        if not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return False
        
        alerts = self.coordinator.data["alerts"]
        
        # Check if any alert is currently active
        for alert in alerts:
            if self._is_alert_active(alert):
                return True
        
        return False

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return {}
        
        alerts = self.coordinator.data["alerts"]
        active_alerts = []
        
        for alert in alerts:
            if self._is_alert_active(alert):
                expiry = self._parse_alert_date(alert["text"])
                active_alerts.append({
                    "type": alert["type"],
                    "text": alert["text"],
                    "link": alert.get("link"),
                    "expires": expiry.isoformat() if expiry else None,
                })
        
        return {
            "active_alerts": active_alerts,
            "active_count": len(active_alerts),
        }
