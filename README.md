# NSW Fuel API Workspace

This is a minimal scaffold to test a Home Assistant command that retrieves and parses NSW fuel pricing data.

## What you get
- `src/main.py`: entry point for manual testing.
- `src/nsw_fuel_client.py`: thin client with placeholder endpoints.
- `src/parser.py`: parsing helpers with TODOs.
- `.env.example`: environment variable template.

## Quick start
1. Create a virtual environment and install deps.
2. Copy `.env.example` to `.env` and fill in values.
3. Run `python src/main.py`.

## Notes
The workspace includes OAuth client-credential token handling against
`/oauth/client_credential/accesstoken` with `grant_type=client_credentials`,
and it now targets the documented v1/v2 endpoints for prices and reference data.

## Home Assistant (HACS)
This repo now includes a custom integration at `custom_components/nsw_fuel`.
You can add it as a HACS custom repository (type: Integration), then install it.

After install:
1. Restart Home Assistant.
2. Add the integration via Settings -> Devices & Services -> Add Integration -> "NSW Fuel Prices".
3. Fill in API credentials, home location, and your location entities (person, device_tracker, or sensor).
4. Use the `nsw_fuel.refresh` service to refresh on demand or from automations.

Nearby and favourite fuel sensors are not refreshed automatically. They update only when you call `nsw_fuel.refresh` (manually or via your own automation), and their last known values are restored after Home Assistant restarts.

## Example automations
Refresh at 4pm on weekdays:
```yaml
alias: Fuel Prices - 4pm Refresh
trigger:
  - platform: time
    at: "16:00:00"
condition:
  - condition: time
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: nsw_fuel.refresh
mode: single
```

Refresh favourite station 4x daily (6am/12pm/6pm/12am):
```yaml
alias: Favourite Station Fuel - 4x Daily Refresh
trigger:
  - platform: time
    at: "00:00:00"
  - platform: time
    at: "06:00:00"
  - platform: time
    at: "12:00:00"
  - platform: time
    at: "18:00:00"
action:
  - service: nsw_fuel.refresh
mode: single
```
