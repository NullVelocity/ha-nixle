# Nixle Alerts Integration for Home Assistant

Monitor local Nixle alerts from your public safety agencies directly in Home Assistant.

## Features

- **Real-time Monitoring**: Automatically checks for new alerts every 15 minutes
- **Multiple Sensors**: 
  - Total alert count
  - Individual counts for Alerts, Advisories, and Community messages
  - Latest alert with full text and recent history
- **Customizable Filtering**: Choose which alert types to monitor
- **Rich Attributes**: Access full alert text, timestamps, and direct links

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/philbert2k/ha-nixle`
5. Category: Integration
6. Click "Add"
7. Search for "Nixle Alerts" in HACS and install
8. Restart Home Assistant

### Manual Installation

1. Download the `nixle` folder from this repository
2. Copy it to your `custom_components` directory in your Home Assistant config folder
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Nixle Alerts"
4. Enter your configuration:
   - **Integration Name**: A friendly name (e.g., "Manchester Highway Alerts")
   - **Agency URL**: Your Nixle agency page URL (e.g., `https://local.nixle.com/manchester-nh-highway-department/`)
   - **Alert Types**: Select which types to monitor (Alert, Advisory, Community)

### Finding Your Agency URL

1. Go to [local.nixle.com](https://local.nixle.com)
2. Search for your city or agency
3. Click on the agency you want to monitor
4. Copy the URL from your browser's address bar

Example URLs:
- `https://local.nixle.com/manchester-nh-highway-department/`
- `https://local.nixle.com/city/ca/san-francisco/`

## Sensors Created

After setup, the following sensors will be created:

### Total Alerts Sensor
`sensor.[agency_name]_total_alerts`
- Shows the total count of all alerts on the first page
- Attributes include individual counts by type

### Alert Type Count Sensors
- `sensor.[agency_name]_alert_count` - Count of "Alert" type messages
- `sensor.[agency_name]_advisory_count` - Count of "Advisory" type messages
- `sensor.[agency_name]_community_count` - Count of "Community" type messages

### Latest Alert Sensor
`sensor.[agency_name]_latest_alert`
- Shows the text of the most recent alert (matching your filter)
- Attributes include:
  - `type`: Alert type (Alert/Advisory/Community)
  - `timestamp`: When the alert was posted
  - `full_text`: Complete alert text
  - `link`: Direct link to the alert details
  - `recent_alerts`: List of the 5 most recent alerts

## Usage Examples

### Automation Example
```yaml
automation:
  - alias: "Notify on Snow Emergency"
    trigger:
      - platform: state
        entity_id: sensor.manchester_highway_department_latest_alert
    condition:
      - condition: template
        value_template: "{{ 'Snow Emergency' in trigger.to_state.state }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Snow Emergency Declared"
          message: "{{ states('sensor.manchester_highway_department_latest_alert') }}"
```

### Lovelace Card Example
```yaml
type: entities
title: Nixle Alerts
entities:
  - entity: sensor.manchester_highway_department_total_alerts
    name: Total Alerts
  - entity: sensor.manchester_highway_department_alert_count
    name: Urgent Alerts
  - entity: sensor.manchester_highway_department_latest_alert
    name: Latest Alert
```

### Dashboard with Alert Details
```yaml
type: markdown
title: Latest Alert
content: >
  **Type:** {{ state_attr('sensor.manchester_highway_department_latest_alert', 'type') }}
  
  **Posted:** {{ state_attr('sensor.manchester_highway_department_latest_alert', 'timestamp') }}
  
  **Message:** {{ state_attr('sensor.manchester_highway_department_latest_alert', 'full_text') }}
  
  {% if state_attr('sensor.manchester_highway_department_latest_alert', 'link') %}
  [View Full Alert]({{ state_attr('sensor.manchester_highway_department_latest_alert', 'link') }})
  {% endif %}
```

## Options

You can modify the alert types to monitor after initial setup:
1. Go to Settings → Devices & Services
2. Find your Nixle integration
3. Click "Configure"
4. Update the alert types selection

## Troubleshooting

### No Data Showing
- Verify your agency URL is correct and accessible
- Check that the agency has posted alerts on their Nixle page
- Check Home Assistant logs for any error messages

### Alerts Not Updating
- The integration checks for updates every 15 minutes
- You can force an update by reloading the integration
- Check your internet connection

### Invalid URL Error
- Ensure you're using a valid `local.nixle.com` URL
- The URL should point to a specific agency page, not the main Nixle site
- Format: `https://local.nixle.com/[agency-name]/`

## Support

For issues, feature requests, or questions:
- Open an issue on [GitHub](https://github.com/philbert2k/ha-nixle/issues)
- Check existing issues for solutions

## License

This project is licensed under the MIT License.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Nixle or Everbridge. The integration uses publicly available data from Nixle's local agency pages.
