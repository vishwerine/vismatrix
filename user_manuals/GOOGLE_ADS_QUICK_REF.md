# Google AdSense Quick Reference

## Quick Start Checklist

- [ ] Sign up for Google AdSense account
- [ ] Get your Publisher ID (ca-pub-XXXXXXXXXXXXXXXX)
- [ ] Add Publisher ID to environment variables
- [ ] Create ad units in AdSense dashboard
- [ ] Add ad slot IDs to environment variables
- [ ] Enable ads in production
- [ ] Test ad display
- [ ] Wait for approval (24-48 hours)

## Environment Variables Setup

Add these to your `.env` file or production environment:

```bash
# Google AdSense Configuration
GOOGLE_ADSENSE_ENABLED=False  # Set to True in production
GOOGLE_ADSENSE_CLIENT_ID=ca-pub-XXXXXXXXXXXXXXXX

# Ad Unit Slots (get from AdSense dashboard)
GOOGLE_ADS_HEADER_SLOT=1234567890
GOOGLE_ADS_SIDEBAR_SLOT=0987654321
GOOGLE_ADS_CONTENT_SLOT=1122334455
GOOGLE_ADS_MOBILE_SLOT=5544332211
```

## Where Ads Are Displayed

### Dashboard Page
1. **Header Banner** - Below welcome section (responsive, 728x90 desktop)
2. **Sidebar Ad** - Right column top (300x250)
3. **In-Content Ad** - Bottom of left column (336x280)

### How Ads Work
- Ads only show when `GOOGLE_ADSENSE_ENABLED=True`
- Ads are responsive and mobile-friendly
- Ads load asynchronously (won't slow down your site)
- AdSense script is loaded once in the base template

## Using the Template Tag

Add ads to any template:

```django
{% load ad_tags %}

<!-- Simple ad placement -->
{% google_ad 'header_banner' %}

<!-- Ad with container and styling -->
{% ad_container 'sidebar' 'my-6 max-w-md mx-auto' %}

<!-- Custom ad format -->
{% google_ad 'in_content' ad_format='rectangle' %}
```

## Testing

1. **Local Development**:
   - Set `GOOGLE_ADSENSE_ENABLED=False`
   - Or use test mode with valid credentials

2. **Production Testing**:
   - Set `GOOGLE_ADSENSE_ENABLED=True`
   - You'll see gray placeholder ads initially
   - Don't click your own ads!

3. **Verify Script Loads**:
   ```bash
   # Check in browser DevTools → Network tab
   # Look for: pagead2.googlesyndication.com
   ```

## Revenue Optimization Tips

### Best Practices
1. Place ads above the fold (visible without scrolling)
2. Use responsive ad units
3. Don't overwhelm users with too many ads
4. Monitor ad performance in AdSense dashboard
5. Test different placements for better RPM

### Common Mistakes to Avoid
❌ Clicking your own ads (policy violation)
❌ Too many ads per page (poor UX)
❌ Hiding ad labels ("Advertisement" text)
❌ Encouraging clicks ("Click here", etc.)
❌ Placing ads on error pages

### Performance Monitoring
- **Daily**: Check AdSense dashboard for earnings
- **Weekly**: Review RPM and CTR trends
- **Monthly**: Analyze top performing pages
- **Quarterly**: Optimize ad placements

## Troubleshooting

### Ads Not Showing
1. Check `GOOGLE_ADSENSE_ENABLED=True`
2. Verify Publisher ID is correct
3. Ensure ad slots are configured
4. Check browser console for errors
5. Disable ad blocker
6. Wait for AdSense approval (24-48 hours)

### Console Errors
```
"adsbygoogle.push() error"
→ Check if ad slot ID exists in AdSense

"Ad request is blocked"
→ Check Privacy settings, ensure HTTPS

"Cannot read property 'push'"
→ AdSense script not loaded, check base.html
```

### Low Revenue
- Increase traffic (more pageviews)
- Improve ad placement (above the fold)
- Target high-paying keywords
- Optimize for US/UK traffic
- Improve user engagement

## Commands

```bash
# Restart Django after changing settings
python manage.py runserver

# Collect static files (if needed)
python manage.py collectstatic --noinput

# Check template syntax
python manage.py check

# View current environment variables
echo $GOOGLE_ADSENSE_CLIENT_ID
```

## Support Resources

- [AdSense Dashboard](https://www.google.com/adsense/)
- [AdSense Help Center](https://support.google.com/adsense/)
- [Policy Center](https://www.google.com/adsense/policies/)
- [Optimization Tips](https://support.google.com/adsense/answer/9274019)

## Ad Placement Examples

### Adding Ads to Other Pages

**Analytics Page**:
```django
{% extends 'tracker/base.html' %}
{% load ad_tags %}

{% block content %}
  <h1>Analytics</h1>
  
  <!-- Ad between sections -->
  {% ad_container 'in_content' 'my-8' %}
  
  <!-- Your analytics content -->
{% endblock %}
```

**Task List Page**:
```django
{% extends 'tracker/base.html' %}
{% load ad_tags %}

{% block content %}
  <div class="grid grid-cols-12 gap-6">
    <div class="col-span-8">
      <!-- Task list -->
    </div>
    <div class="col-span-4">
      <!-- Sidebar ad -->
      {% ad_container 'sidebar' %}
    </div>
  </div>
{% endblock %}
```

## Revenue Calculator

Estimate your potential earnings:

```
Daily Earnings = (Pageviews / 1000) × RPM
Monthly Earnings = Daily Earnings × 30

Example:
- 1,000 pageviews/day
- $5 RPM (average)
- Daily: $5
- Monthly: $150
```

## Next Steps

1. ✅ Complete AdSense signup
2. ✅ Get publisher ID
3. ✅ Configure environment variables
4. ✅ Create ad units
5. ✅ Enable ads in production
6. ⏳ Wait for approval
7. 📊 Monitor performance
8. 💰 Get paid!

---

**Pro Tip**: Start with fewer ads and optimize placement based on user behavior. Quality user experience → Better engagement → Higher revenue.
