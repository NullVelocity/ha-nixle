"""API client for Nixle."""
import logging
import re
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

# Lazy import to avoid issues during config flow loading
BeautifulSoup = None


class NixleAPI:
    """API client for Nixle local pages."""

    def __init__(self, agency_url: str, hass):
        """Initialize the API client."""
        global BeautifulSoup
        if BeautifulSoup is None:
            from bs4 import BeautifulSoup as BS
            BeautifulSoup = BS
            
        self.agency_url = agency_url.rstrip("/")
        self.hass = hass
        
    def _get_session(self):
        """Get aiohttp session."""
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        return async_get_clientsession(self.hass)

    async def async_get_alerts(self) -> dict:
        """Get alerts from Nixle."""
        try:
            session = self._get_session()
            url = f"{self.agency_url}/?page=1"
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                html = await response.text()
                
            # Use html.parser instead of lxml - it's built into Python
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all alert items
            alerts = []
            alert_items = soup.find_all("li")
            
            for item in alert_items:
                # Look for alert type indicator
                alert_type_elem = item.find(string=lambda text: text and text.strip() in ["Alert", "Advisory", "Community"])
                
                if not alert_type_elem:
                    continue
                
                alert_type = alert_type_elem.strip()
                
                # Get the timestamp
                time_elem = item.find("h2")
                time_text = time_elem.get_text(strip=True) if time_elem else "Unknown"
                
                # Get the alert text/summary
                # The text is typically in a paragraph after the heading
                text_elem = None
                for sibling in item.find_all(string=True):
                    text = sibling.strip()
                    if text and text not in [alert_type, time_text, "More »"]:
                        if len(text) > 20:  # Likely the actual alert content
                            text_elem = text
                            break
                
                alert_text = text_elem if text_elem else "No description available"
                
                # Get the detail link if available
                link_elem = item.find("a", href=re.compile(r"nixle\.us/"))
                link = link_elem["href"] if link_elem else None
                
                alerts.append({
                    "type": alert_type,
                    "timestamp": time_text,
                    "text": alert_text,
                    "link": link,
                })
            
            # Count alerts by type
            alert_counts = {
                "total": len(alerts),
                "alert": sum(1 for a in alerts if a["type"] == "Alert"),
                "advisory": sum(1 for a in alerts if a["type"] == "Advisory"),
                "community": sum(1 for a in alerts if a["type"] == "Community"),
            }
            
            return {
                "alerts": alerts,
                "counts": alert_counts,
                "last_updated": datetime.now().isoformat(),
            }
            
        except Exception as err:
            _LOGGER.error("Error fetching Nixle alerts: %s", err)
            raise
