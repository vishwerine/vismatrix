# Quick GeoIP Database Setup

## 🚀 Quick Start (3 Steps)

### Step 1: Get MaxMind License Key

1. Sign up (free): https://www.maxmind.com/en/geolite2/signup
2. Generate license key: https://www.maxmind.com/en/accounts/current/license-key
3. Save the license key somewhere secure

### Step 2: Download Database

Navigate to the geoip directory and run the download script:

```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/geoip

# Make script executable (if not already)
chmod +x download_geoip.sh

# Run with your license key
./download_geoip.sh YOUR_LICENSE_KEY_HERE
```

**Expected Output:**
```
🌍 GeoLite2-City Database Downloader
====================================

⬇️  Downloading GeoLite2-City database...
✅ Downloaded 71M
📦 Extracting...
📁 Moving database file...
🧹 Cleaning up...

✅ Success! Database installed:
-rw-r--r--  1 user  staff   71M Jan 18 20:45 GeoLite2-City.mmdb
```

### Step 3: Test It

```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker

python manage.py shell
```

Then in the Python shell:

```python
from tracker.visitor_tracking import get_geolocation_from_ip

# Test with Google's DNS server IP
result = get_geolocation_from_ip('8.8.8.8')
print(result)
# Expected: {'country': 'United States', 'city': '', ...}

# Test with Cloudflare DNS
result = get_geolocation_from_ip('1.1.1.1')
print(result)
# Expected: {'country': 'Australia', 'city': '', ...}
```

If you see country names, it's working! 🎉

## ✅ Verification Checklist

- [ ] GeoLite2-City.mmdb file exists in `geoip/` directory (~70MB)
- [ ] Django settings has GEOIP_PATH configured
- [ ] Test in shell returns country data
- [ ] Visit landing page and check /landing-analytics/ shows location data

## 📁 File Structure

Your project should now have:

```
progress_tracker/
├── geoip/
│   ├── .gitignore              ✅ (prevents committing .mmdb to git)
│   ├── README.md               ✅ (detailed instructions)
│   ├── download_geoip.sh       ✅ (automated download script)
│   └── GeoLite2-City.mmdb      ⬅️ (you need to download this)
├── progress_tracker/
│   └── settings.py             ✅ (GEOIP_PATH configured)
└── tracker/
    ├── visitor_tracking.py     ✅ (geolocation code)
    └── views.py                ✅ (analytics with location)
```

## 🔧 Troubleshooting

### "Database not found" error

Check the file exists:
```bash
ls -lh /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/geoip/GeoLite2-City.mmdb
```

If not, re-run the download script.

### "Invalid license key" error

- Make sure you copied the entire license key
- Try regenerating a new license key on MaxMind website
- Check you're logged into MaxMind when using the web interface

### Getting empty location data

- Private IPs (127.x, 192.168.x) won't have location data - this is normal
- Test with a public IP address
- Some IP ranges (VPNs, data centers) may only show country, not city

### Download script permission denied

```bash
chmod +x geoip/download_geoip.sh
```

## 📦 Alternative: Manual Download

If the script doesn't work, download manually:

1. Login to MaxMind: https://www.maxmind.com/en/accounts/current/geoip/downloads
2. Find "GeoLite2 City" and click "Download GZIP"
3. Extract the downloaded tar.gz file
4. Copy the .mmdb file to the geoip/ directory:

```bash
# From your Downloads folder
cd ~/Downloads
tar -xzf GeoLite2-City_*.tar.gz
cp GeoLite2-City_*/GeoLite2-City.mmdb \
   /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/geoip/
```

## 🔄 Keeping Database Updated

MaxMind updates the database weekly. To stay current:

### Option 1: Re-run download script monthly

```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/geoip
./download_geoip.sh YOUR_LICENSE_KEY
```

### Option 2: Install geoipupdate

```bash
# macOS
brew install geoipupdate

# Configure it
mkdir -p ~/.geoipupdate
cat > ~/.geoipupdate/GeoIP.conf <<EOF
AccountID YOUR_ACCOUNT_ID
LicenseKey YOUR_LICENSE_KEY
EditionIDs GeoLite2-City
DatabaseDirectory /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/geoip
EOF

# Run update
geoipupdate -v

# Set up automatic monthly updates
crontab -e
# Add: 0 2 1 * * geoipupdate
```

## 🎯 Next Steps

Once the database is working:

1. Visit your landing page to generate some visitor data
2. Check analytics at: http://localhost:8000/landing-analytics/
3. Look for the "🌍 Visitors by Country" and "🏙️ Visitors by City" sections
4. See the Location column in the Recent Visitors table

For production deployment, see [GEOLOCATION_SETUP.md](../../user_manuals/GEOLOCATION_SETUP.md)
