# GeoIP Database Directory

This directory stores the MaxMind GeoLite2-City database for IP geolocation.

## Important: DO NOT COMMIT THE .mmdb FILE TO GIT

The database file is large (~70MB) and should not be in version control.

## Download Instructions

### Method 1: Manual Download (Recommended)

1. **Sign up for a free MaxMind account:**
   - Go to: https://www.maxmind.com/en/geolite2/signup
   - Create a free account

2. **Get your license key:**
   - Log in to your MaxMind account
   - Go to: https://www.maxmind.com/en/accounts/current/license-key
   - Generate a new license key (save it securely!)

3. **Download the database:**
   - Go to: https://www.maxmind.com/en/accounts/current/geoip/downloads
   - Find "GeoLite2 City" in the list
   - Click "Download GZIP" (the .tar.gz file)
   - Or use this direct link (requires login): https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz

4. **Extract the database:**
   ```bash
   # Move the downloaded file here
   mv ~/Downloads/GeoLite2-City*.tar.gz .
   
   # Extract it
   tar -xzf GeoLite2-City*.tar.gz
   
   # Copy the .mmdb file to this directory
   cp GeoLite2-City_*/GeoLite2-City.mmdb .
   
   # Clean up
   rm -rf GeoLite2-City_* GeoLite2-City*.tar.gz
   ```

### Method 2: Using curl with License Key

If you have a MaxMind license key:

```bash
# Replace YOUR_LICENSE_KEY with your actual license key
curl -o GeoLite2-City.tar.gz \
  "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz"

# Extract
tar -xzf GeoLite2-City.tar.gz

# Move the .mmdb file
mv GeoLite2-City_*/GeoLite2-City.mmdb .

# Clean up
rm -rf GeoLite2-City_* GeoLite2-City.tar.gz
```

### Method 3: One-Line Script (macOS/Linux)

Save this as `download_geoip.sh`:

```bash
#!/bin/bash
# Usage: ./download_geoip.sh YOUR_LICENSE_KEY

LICENSE_KEY=$1

if [ -z "$LICENSE_KEY" ]; then
    echo "Usage: ./download_geoip.sh YOUR_LICENSE_KEY"
    echo "Get your license key from: https://www.maxmind.com/en/accounts/current/license-key"
    exit 1
fi

cd "$(dirname "$0")"

echo "Downloading GeoLite2-City database..."
curl -o GeoLite2-City.tar.gz \
  "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=$LICENSE_KEY&suffix=tar.gz"

if [ $? -ne 0 ]; then
    echo "Download failed!"
    exit 1
fi

echo "Extracting..."
tar -xzf GeoLite2-City.tar.gz

echo "Moving database file..."
mv GeoLite2-City_*/GeoLite2-City.mmdb .

echo "Cleaning up..."
rm -rf GeoLite2-City_* GeoLite2-City.tar.gz

echo "✅ Done! GeoLite2-City.mmdb is ready to use."
ls -lh GeoLite2-City.mmdb
```

Make it executable and run:
```bash
chmod +x download_geoip.sh
./download_geoip.sh YOUR_LICENSE_KEY
```

## Verify Installation

After downloading, verify the file exists:

```bash
ls -lh GeoLite2-City.mmdb
# Should show: GeoLite2-City.mmdb (~70MB)
```

Test in Django:

```python
python manage.py shell

from tracker.visitor_tracking import get_geolocation_from_ip
print(get_geolocation_from_ip('8.8.8.8'))
# Should return: {'country': 'United States', 'city': '', ...}
```

## File Structure

After setup, this directory should contain:
```
geoip/
├── README.md (this file)
├── .gitignore (excludes .mmdb files)
└── GeoLite2-City.mmdb (the database - DO NOT COMMIT)
```

## Automatic Updates

The GeoLite2 database is updated regularly. To keep it fresh:

### Using geoipupdate (Recommended for Production)

1. Install geoipupdate:
   ```bash
   # macOS
   brew install geoipupdate
   
   # Ubuntu/Debian
   sudo apt-get install geoipupdate
   ```

2. Configure `~/.geoipupdate/GeoIP.conf`:
   ```ini
   AccountID YOUR_ACCOUNT_ID
   LicenseKey YOUR_LICENSE_KEY
   EditionIDs GeoLite2-City
   DatabaseDirectory /path/to/vismatrix/progress_tracker/geoip
   ```

3. Run updates:
   ```bash
   geoipupdate -v
   ```

4. Set up cron for weekly updates:
   ```bash
   crontab -e
   # Add: 0 2 * * 0 geoipupdate  # Every Sunday at 2 AM
   ```

## Troubleshooting

**File not found error?**
- Make sure `GeoLite2-City.mmdb` exists in this directory
- Check Django settings.py has: `GEOIP_PATH = os.path.join(BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')`

**Permission denied?**
- Make sure the file is readable: `chmod 644 GeoLite2-City.mmdb`

**Database too old?**
- Re-download using the steps above
- MaxMind updates the database weekly

## Privacy & Licensing

- GeoLite2 is free for both personal and commercial use
- Attribution to MaxMind is appreciated but not required
- Database is provided "as is" without warranty
- See MaxMind's terms: https://www.maxmind.com/en/geolite2/eula

## Support

For issues with the database:
- MaxMind Support: https://support.maxmind.com/
- GeoLite2 Documentation: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data

For issues with the Django integration:
- See: ../user_manuals/GEOLOCATION_SETUP.md
