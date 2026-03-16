# Landing Page Analytics - Quick Reference

## What's New
✅ Automatic visitor tracking on landing page  
✅ Comprehensive analytics dashboard for admins  
✅ Conversion tracking from visitor to user  
✅ UTM campaign parameter support  
✅ Device, browser, and OS detection  

## Quick Access
- **Analytics Dashboard**: `/admin-analytics/landing/`
- **Django Admin**: `/admin/tracker/landingpagevisitor/`

## Key Metrics Tracked
- Total visitors & unique visitors
- Returning visitors
- Conversion rate (signups)
- Device type (mobile/desktop/tablet)
- Browser & OS breakdown
- Referrer sources
- UTM campaign parameters

## Using UTM Parameters
Track your marketing campaigns by adding UTM parameters to your landing page URL:

```
https://yoursite.com/?utm_source=google&utm_medium=cpc&utm_campaign=spring_sale
```

**Parameters:**
- `utm_source`: Where traffic came from (google, facebook, newsletter)
- `utm_medium`: Marketing medium (cpc, email, social)
- `utm_campaign`: Campaign name
- `utm_term`: Keywords (for paid search)
- `utm_content`: Content variation (for A/B testing)

## Privacy Note
⚠️ This feature collects IP addresses and browser information. Ensure you:
- Have a privacy policy mentioning analytics
- Consider cookie consent for GDPR compliance
- Review data retention requirements

## Files Changed/Added

### New Files
- `tracker/models.py` - Added `LandingPageVisitor` model
- `tracker/visitor_tracking.py` - Tracking utilities
- `tracker/templates/tracker/landing_analytics.html` - Analytics dashboard
- `tracker/migrations/0022_landingpagevisitor.py` - Database migration

### Modified Files
- `tracker/views.py` - Updated `landing_page()`, added `landing_analytics()`
- `tracker/admin.py` - Registered `LandingPageVisitor` in admin
- `tracker/signals.py` - Added conversion tracking on signup
- `tracker/urls.py` - Added `/admin-analytics/landing/` route

## Next Steps

1. **Run migration:**
   ```bash
   python manage.py migrate tracker
   ```

2. **Access analytics:**
   - Log in as admin/staff user
   - Visit `/admin-analytics/landing/`

3. **Test tracking:**
   - Visit landing page in incognito mode
   - Check admin to verify visitor was tracked
   - Sign up to test conversion tracking

4. **Set up campaigns:**
   - Create UTM-tagged URLs for your marketing campaigns
   - Monitor which campaigns drive the most conversions

## Troubleshooting

**Visitors not tracked?**
- Check Django sessions are enabled
- Verify no errors in logs

**Conversions not tracked?**
- Ensure signals are working (`tracker/signals.py`)
- Check that session persists during signup

**Behind proxy/load balancer?**
- Ensure `X-Forwarded-For` header is passed correctly

## Support
See full documentation: `user_manuals/LANDING_PAGE_ANALYTICS.md`
