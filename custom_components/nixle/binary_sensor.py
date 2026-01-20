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
        self._attr_name = f"{agency_name} Alert Condition"
        self._attr_unique_id = f"{agency_id}_alert_condition"
        self._attr_icon = "mdi:alert-circle"

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

    def _calculate_alert_posted_time(self, timestamp_text: str) -> datetime:
        """Calculate when the alert was posted based on timestamp."""
        now = dt_util.now()
        
        # Parse "Entered: X year(s), Y month(s), Z day(s), W hour(s) ago"
        years_match = re.search(r"(\d+)\s+years?", timestamp_text)
        months_match = re.search(r"(\d+)\s+months?", timestamp_text)
        days_match = re.search(r"(\d+)\s+days?", timestamp_text)
        hours_match = re.search(r"(\d+)\s+hours?", timestamp_text)
        
        years_ago = int(years_match.group(1)) if years_match else 0
        months_ago = int(months_match.group(1)) if months_match else 0
        days_ago = int(days_match.group(1)) if days_match else 0
        hours_ago = int(hours_match.group(1)) if hours_match else 0
        
        # Calculate when alert was posted
        # Approximate: 1 month = 30 days, 1 year = 365 days
        total_days = (years_ago * 365) + (months_ago * 30) + days_ago
        alert_posted = now - timedelta(days=total_days, hours=hours_ago)
        
        return alert_posted

    def _parse_alert_date(self, text: str, timestamp_text: str) -> datetime | None:
        """Parse date from alert text and timestamp."""
        now = dt_util.now()
        
        # Calculate when the alert was posted
        alert_posted = self._calculate_alert_posted_time(timestamp_text)
        
        # Pattern: "tonight, Day, Month Date, Year" or "tonight, Day, Month Date"
        tonight_pattern = r"tonight,\s+\w+,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s+(\d{4}))?"
        match = re.search(tonight_pattern, text, re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            
            # If year is in the text, use it. Otherwise infer from when alert was posted
            if year:
                year = int(year)
            else:
                # Use the year from when alert was posted
                year = alert_posted.year
                
            month = MONTHS.get(month_name, alert_posted.month)
            day = int(day)
            
            # Create the alert date (the "tonight" mentioned)
            try:
                alert_date = dt_util.as_local(datetime(year, month, day, 0, 0, 0))
                # Expires at 6am the next day
                expiry = alert_date.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
                _LOGGER.debug(f"Parsed 'tonight' alert: posted={alert_posted.date()}, date={alert_date.date()}, expires={expiry}, now={now}")
                return expiry
            except ValueError as e:
                _LOGGER.warning(f"Invalid date parsed: {year}/{month}/{day} - {e}")
                return None
        
        # Pattern: "Day night, Month Date" (with optional year)
        # Example: "Saturday night, February 15th" or "Saturday night, February 15th, 2025"
        night_pattern = r"(?:for|declared)\s+\w+\s+night,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?"
        match = re.search(night_pattern, text, re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            
            # If year is in text, use it. Otherwise use year from when alert was posted
            if year:
                year = int(year)
            else:
                year = alert_posted.year
                
            month = MONTHS.get(month_name, alert_posted.month)
            day = int(day)
            
            try:
                alert_date = dt_util.as_local(datetime(year, month, day, 0, 0, 0))
                expiry = alert_date.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
                _LOGGER.debug(f"Parsed 'night' alert: posted={alert_posted.date()}, date={alert_date.date()}, expires={expiry}, now={now}")
                return expiry
            except ValueError as e:
                _LOGGER.warning(f"Invalid date parsed: {year}/{month}/{day} - {e}")
                return None
        
        # Pattern: "for Day, Month Date" (not tonight)
        day_pattern = r"for\s+\w+,\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s+(\d{4}))?"
        match = re.search(day_pattern, text, re.IGNORECASE)
        if match:
            month_name, day, year = match.groups()
            
            if year:
                year = int(year)
            else:
                year = alert_posted.year
                
            month = MONTHS.get(month_name, alert_posted.month)
            day = int(day)
            
            try:
                alert_date = dt_util.as_local(datetime(year, month, day, 0, 0, 0))
                expiry = alert_date.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
                _LOGGER.debug(f"Parsed specific day alert: posted={alert_posted.date()}, date={alert_date.date()}, expires={expiry}, now={now}")
                return expiry
            except ValueError as e:
                _LOGGER.warning(f"Invalid date parsed: {year}/{month}/{day} - {e}")
                return None
        
        return None

    def _is_alert_active(self, alert: dict) -> bool:
        """Check if an alert is currently active."""
        alert_type = alert.get("type", "")
        text = alert.get("text", "")
        timestamp = alert.get("timestamp", "")
        
        # Only process "Alert" type
        if alert_type != "Alert":
            return False
        
        # Parse the expiry date
        expiry = self._parse_alert_date(text, timestamp)
        
        if not expiry:
            # Couldn't parse date - assume inactive
            _LOGGER.debug(f"Could not parse date from alert: {text}")
            return False
        
        now = dt_util.now()
        is_active = now < expiry
        
        _LOGGER.debug(f"Alert active check: '{text[:50]}...' - expires={expiry}, now={now}, active={is_active}")
        
        return is_active

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
                expiry = self._parse_alert_date(alert["text"], alert.get("timestamp", ""))
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
