#!/bin/bash
# GeoIP Database Download Script
# Usage: ./download_geoip.sh YOUR_LICENSE_KEY

LICENSE_KEY=$1

if [ -z "$LICENSE_KEY" ]; then
    echo "❌ Error: License key required"
    echo ""
    echo "Usage: ./download_geoip.sh YOUR_LICENSE_KEY"
    echo ""
    echo "📝 To get a license key:"
    echo "  1. Sign up at: https://www.maxmind.com/en/geolite2/signup"
    echo "  2. Generate a license key at: https://www.maxmind.com/en/accounts/current/license-key"
    echo ""
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🌍 GeoLite2-City Database Downloader"
echo "===================================="
echo ""

# Clean up any previous attempts
if [ -f "GeoLite2-City.tar.gz" ]; then
    echo "🧹 Cleaning up previous download..."
    rm -f GeoLite2-City.tar.gz
fi

if [ -d "GeoLite2-City_"* ]; then
    rm -rf GeoLite2-City_*
fi

# Download
echo "⬇️  Downloading GeoLite2-City database..."
curl -L -o GeoLite2-City.tar.gz \
  "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=$LICENSE_KEY&suffix=tar.gz"

if [ $? -ne 0 ]; then
    echo "❌ Download failed!"
    exit 1
fi

# Check if download was successful (should be larger than 1KB)
FILE_SIZE=$(stat -f%z GeoLite2-City.tar.gz 2>/dev/null || stat -c%s GeoLite2-City.tar.gz 2>/dev/null)
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "❌ Download failed! File too small (possible authentication error)"
    echo "📝 Check your license key at: https://www.maxmind.com/en/accounts/current/license-key"
    cat GeoLite2-City.tar.gz
    rm GeoLite2-City.tar.gz
    exit 1
fi

echo "✅ Downloaded $(du -h GeoLite2-City.tar.gz | cut -f1)"

# Extract
echo "📦 Extracting..."
tar -xzf GeoLite2-City.tar.gz

if [ $? -ne 0 ]; then
    echo "❌ Extraction failed!"
    exit 1
fi

# Find and move the .mmdb file
echo "📁 Moving database file..."
EXTRACTED_DIR=$(find . -maxdepth 1 -name "GeoLite2-City_*" -type d | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    echo "❌ Could not find extracted directory!"
    exit 1
fi

# Backup old database if exists
if [ -f "GeoLite2-City.mmdb" ]; then
    echo "💾 Backing up old database..."
    mv GeoLite2-City.mmdb "GeoLite2-City.mmdb.backup.$(date +%Y%m%d)"
fi

# Move new database
mv "$EXTRACTED_DIR/GeoLite2-City.mmdb" .

if [ $? -ne 0 ]; then
    echo "❌ Failed to move database file!"
    exit 1
fi

# Clean up
echo "🧹 Cleaning up..."
rm -rf "$EXTRACTED_DIR" GeoLite2-City.tar.gz

# Verify
echo ""
echo "✅ Success! Database installed:"
ls -lh GeoLite2-City.mmdb

echo ""
echo "🔍 Database info:"
file GeoLite2-City.mmdb

echo ""
echo "✨ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Update settings.py with:"
echo "     GEOIP_PATH = os.path.join(BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')"
echo ""
echo "  2. Test it:"
echo "     python manage.py shell"
echo "     >>> from tracker.visitor_tracking import get_geolocation_from_ip"
echo "     >>> print(get_geolocation_from_ip('8.8.8.8'))"
echo ""
