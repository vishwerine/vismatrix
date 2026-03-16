# Backfill Visitor Locations Script

## Overview
This management command backfills geolocation data (latitude, longitude, country, city) for all landing page visitors using the GeoIP2 database.

## Prerequisites

1. **Install GeoIP2 library**:
   ```bash
   pip install geoip2
   ```

2. **Download GeoLite2 Database**:
   - Download from MaxMind: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
   - Place `GeoLite2-City.mmdb` in your project's `geoip/` directory
   - Configure `GEOIP_PATH` in Django settings if using a different location

3. **Ensure latitude/longitude fields exist**:
   - Already added to `LandingPageVisitor` model
   - Run migrations if needed: `python manage.py migrate`

## Usage

### Basic Usage (Default)
Updates visitors missing latitude/longitude coordinates:
```bash
python manage.py backfill_visitor_locations
```

### Update Only Missing Country/City Data
Updates visitors that are missing country or city information:
```bash
python manage.py backfill_visitor_locations --missing-only
```

### Force Update All Visitors
Updates ALL visitors, even those with existing location data:
```bash
python manage.py backfill_visitor_locations --force
```

### Limit Number of Records
Process only the first N visitors:
```bash
python manage.py backfill_visitor_locations --limit 100
```

### Combined Options
```bash
python manage.py backfill_visitor_locations --missing-only --limit 500
```

## Output
The command provides:
- Progress updates every 100 records
- Summary with counts of updated, skipped, and error records
- Helpful error messages if GeoIP2 is not configured

## Example Output
```
Processing visitors missing lat/lng coordinates
Found 245 visitors to process...

Progress: 100/245 (85 updated, 15 skipped, 0 errors)
Progress: 200/245 (168 updated, 32 skipped, 0 errors)

============================================================
✓ Processing complete!
  Total processed: 245
  Successfully updated: 208
  Skipped (private IPs/no data): 37
  Errors: 0
============================================================
```

## Notes

- **Private IPs** (127.x.x.x, 192.168.x.x, 10.x.x.x, 172.x.x.x) are automatically skipped
- The script is idempotent - safe to run multiple times
- Location data is cached in the database for performance
- Use `--force` sparingly as it updates all records

## Troubleshooting

### "geoip2 library not installed"
```bash
pip install geoip2
```

### "GeoIP database not found"
1. Download GeoLite2-City.mmdb from MaxMind
2. Place in `geoip/` directory
3. Update `GEOIP_PATH` in settings.py if needed

### "latitude and longitude fields not found"
The fields should already exist. If not, they were added in the model but migrations weren't run:
```bash
python manage.py makemigrations tracker
python manage.py migrate
```

## See Also
- `user_manuals/GEOLOCATION_SETUP.md` - Full GeoIP setup instructions
- `tracker/visitor_tracking.py` - Geolocation utility functions
