# Google AdSense Integration Guide

## Overview
This guide walks you through setting up Google AdSense to monetize your VisMatrix application.

## Step 1: Create Google AdSense Account

1. **Sign up for Google AdSense**
   - Go to [Google AdSense](https://www.google.com/adsense/)
   - Click "Get Started" and sign in with your Google account
   - Fill in your website URL: `vismatrix.space` (or your actual domain)
   - Select your country and accept the terms

2. **Connect Your Site**
   - AdSense will provide you with a verification code snippet that looks like:
   ```html
   <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
        crossorigin="anonymous"></script>
   ```
   - This code is already integrated in your `base.html` template (see Implementation section)
   - Add the snippet between the `<head>` tags of your site

3. **Verify Your Site**
   - After adding the code, go back to AdSense and click "Verify"
   - Verification typically takes 24-48 hours

## Step 2: Configure Ad Settings

Once your site is approved:

1. **Create Ad Units**
   - Go to AdSense Dashboard → Ads → By ad unit
   - Click "New ad unit"
   - Choose ad type:
     - **Display ads** (recommended for web app)
     - **In-feed ads** (for social feed)
     - **In-article ads** (for blog content)

2. **Recommended Ad Placements for VisMatrix**:
   - **Header Banner**: 728x90 (Leaderboard) - Desktop
   - **Sidebar**: 300x250 (Medium Rectangle) - Desktop
   - **Mobile Banner**: 320x50 or 320x100
   - **In-content**: 336x280 (Large Rectangle)

3. **Get Ad Code**
   - For each ad unit, Google will provide HTML code like:
   ```html
   <ins class="adsbygoogle"
        style="display:block"
        data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
        data-ad-slot="YYYYYYYYYY"
        data-ad-format="auto"
        data-full-width-responsive="true"></ins>
   <script>
        (adsbygoogle = window.adsbygoogle || []).push({});
   </script>
   ```

## Step 3: Implementation in VisMatrix

### Update Django Settings

Add your AdSense publisher ID to `progress_tracker/settings.py`:

```python
# Google AdSense Configuration
GOOGLE_ADSENSE_ENABLED = True  # Set to False to disable ads
GOOGLE_ADSENSE_CLIENT_ID = 'ca-pub-XXXXXXXXXXXXXXXX'  # Replace with your actual ID

# Ad unit slots (get these from AdSense dashboard)
GOOGLE_ADS_SLOTS = {
    'header_banner': 'YYYYYYYYYY',      # Header leaderboard
    'sidebar': 'ZZZZZZZZZZ',            # Sidebar ad
    'in_content': 'AAAAAAAAAA',         # In-content ad
    'mobile_banner': 'BBBBBBBBBB',      # Mobile banner
}
```

### The Template Tag System

The app includes a custom template tag `{% google_ad %}` that you can use anywhere:

```django
{% load ad_tags %}

<!-- Display a header banner ad -->
{% google_ad 'header_banner' %}

<!-- Display a sidebar ad -->
{% google_ad 'sidebar' %}
```

### Where Ads Are Placed

1. **Dashboard**: 
   - Header banner (between welcome section and main content)
   - Sidebar ad (on desktop view)

2. **Base Template**: 
   - AdSense verification script in `<head>`

3. **Future Placements** (you can add):
   - Analytics page
   - Task list page
   - Social feed
   - Between habit cards

## Step 4: Testing

1. **Enable Test Mode**
   - AdSense automatically serves test ads to the account owner
   - You'll see gray placeholder ads initially

2. **Testing Checklist**:
   - ✅ Verify AdSense script loads (check browser DevTools → Network)
   - ✅ Check for console errors
   - ✅ Test on mobile and desktop
   - ✅ Verify ads don't break layout
   - ✅ Ensure ads are responsive

3. **Important**: Never click your own ads! This violates AdSense policies.

## Step 5: Optimize for Revenue

### Best Practices

1. **Ad Placement Strategy**:
   - Place ads above the fold (visible without scrolling)
   - Use native/responsive ad units
   - Don't overwhelm users with too many ads
   - Balance user experience with monetization

2. **Performance Optimization**:
   - Ads are loaded asynchronously (won't block page load)
   - Use lazy loading for below-the-fold ads
   - Monitor Core Web Vitals in Google Search Console

3. **Compliance**:
   - Add Privacy Policy (you already have this!)
   - Mention ads in your Terms of Service
   - Comply with GDPR/CCPA if you have EU/CA users

### Revenue Expectations

- **Early Stage**: $0.25 - $2 per 1000 pageviews (RPM)
- **Growing Site**: $2 - $10 RPM
- **Established Site**: $10+ RPM

Actual revenue depends on:
- Traffic volume
- User location (US/UK traffic pays more)
- Niche (tech/finance pays more than entertainment)
- Ad placement optimization
- User engagement

## Step 6: Monitoring & Analytics

### AdSense Dashboard
- Monitor daily earnings
- Track RPM (Revenue Per Mille)
- View top performing ad units
- Check policy violations

### Google Analytics Integration
- Link AdSense to Google Analytics
- Track which pages generate most ad revenue
- Analyze user behavior around ads

## Troubleshooting

### Ads Not Showing

1. **Site Not Approved Yet**: Wait 24-48 hours after verification
2. **Ad Blocker**: Disable ad blockers when testing
3. **Invalid Code**: Double-check your publisher ID
4. **Policy Violation**: Check AdSense dashboard for warnings
5. **Low Traffic**: AdSense may not serve ads to very low traffic sites initially

### Common Errors

```
AdSense script not loading → Check network tab for blocked requests
Empty ad slots → Normal for new accounts, wait for approval
Console errors → Check syntax in ad code
```

## Configuration Reference

### Environment Variables (Optional)

For added security, use environment variables:

```bash
# In your .env file
GOOGLE_ADSENSE_CLIENT_ID=ca-pub-XXXXXXXXXXXXXXXX
GOOGLE_ADS_HEADER_SLOT=YYYYYYYYYY
GOOGLE_ADS_SIDEBAR_SLOT=ZZZZZZZZZZ
```

Then in settings.py:
```python
import os
GOOGLE_ADSENSE_CLIENT_ID = os.getenv('GOOGLE_ADSENSE_CLIENT_ID', '')
```

## Quick Commands

```bash
# Collect static files if you make changes
python manage.py collectstatic --noinput

# Restart your Django app
# (specific command depends on your hosting setup)
```

## Additional Resources

- [Google AdSense Help Center](https://support.google.com/adsense/)
- [AdSense Program Policies](https://support.google.com/adsense/answer/48182)
- [AdSense Optimization Tips](https://support.google.com/adsense/answer/9274019)

## Support

If you encounter issues:
1. Check the AdSense dashboard for notifications
2. Review Policy Center for violations
3. Contact AdSense support through the dashboard

---

**Note**: It typically takes 1-2 weeks for new AdSense accounts to be fully approved and start serving real ads. Be patient and focus on creating quality content while waiting!
