# Landing Page Visitor Tracking & Analytics

## Overview

This feature tracks visitors to the landing page and provides comprehensive analytics for understanding user acquisition and conversion.

## Features

### 1. Visitor Tracking
The system automatically tracks the following information for each landing page visitor:

#### Technical Information
- **IP Address**: Visitor's IP address (respects proxies)
- **Session Key**: Django session key for tracking across visits
- **User Agent**: Full browser user agent string
- **Browser**: Detected browser name and version (Chrome, Firefox, Safari, Edge, Opera)
- **Operating System**: Detected OS (Windows, macOS, Linux, iOS, Android)
- **Device Type**: Desktop, Mobile, or Tablet

#### Traffic Source
- **Referrer**: The URL that referred the visitor
- **UTM Parameters**: Tracks all UTM campaign parameters
  - `utm_source`: Traffic source (e.g., google, facebook, email)
  - `utm_medium`: Marketing medium (e.g., cpc, banner, email)
  - `utm_campaign`: Campaign name
  - `utm_term`: Paid keywords
  - `utm_content`: Content variation (for A/B testing)

#### Visit Details
- **Landing Page URL**: Full URL visited (including query parameters)
- **Language**: Browser language preference
- **Visit Count**: Number of times the visitor has returned
- **First Visit**: Timestamp of first visit
- **Last Visit**: Timestamp of most recent visit

#### Conversion Tracking
- **Converted to User**: Whether the visitor signed up
- **User**: Link to User model if converted

## Usage

### Accessing Analytics

Analytics are available to staff members at:
```
/admin-analytics/landing/
```

You can filter by time period:
- Last 7 days: `/admin-analytics/landing/?days=7`
- Last 30 days: `/admin-analytics/landing/?days=30`
- Last 90 days: `/admin-analytics/landing/?days=90`

### Metrics Available

1. **Total Visitors**: All landing page visits
2. **Unique Visitors**: Unique IP addresses
3. **Returning Visitors**: Visitors who came back
4. **Conversions**: Visitors who signed up
5. **Conversion Rate**: Percentage of visitors who signed up

### Breakdowns

- Device breakdown (Desktop, Mobile, Tablet)
- Browser breakdown (Chrome, Firefox, Safari, etc.)
- Operating System breakdown
- Top referrers
- UTM source breakdown
- UTM campaign breakdown
- Daily visitor trends

## Implementation Details

### Models

#### LandingPageVisitor
Located in `tracker/models.py`, this model stores all visitor information.

Key fields:
- `ip_address`: GenericIPAddressField
- `session_key`: CharField(max_length=40)
- `user_agent`: TextField
- `browser`, `os`, `device`: Parsed from user agent
- `referrer`: URLField
- UTM fields: CharField fields
- `converted_to_user`: BooleanField
- `user`: ForeignKey to User

### Utilities

#### visitor_tracking.py
Contains utility functions for tracking:

- `get_client_ip(request)`: Extracts IP address, handling proxies
- `parse_user_agent(user_agent_string)`: Parses user agent to extract browser, OS, device
- `track_landing_page_visitor(request)`: Main tracking function called on landing page
- `mark_visitor_converted(request, user)`: Marks visitor as converted after signup

### Views

#### landing_page (views.py)
Updated to automatically track all visitors using `track_landing_page_visitor()`.

#### landing_analytics (views.py)
Admin-only view that displays comprehensive analytics dashboard.
- Requires staff permissions (`@staff_member_required`)
- Provides filterable analytics by date range
- Includes all metrics and breakdowns

### Signals

#### signals.py
Updated to track conversions:
- `handle_user_signup`: Tracks conversion for email/password signup
- `handle_social_signup`: Tracks conversion for social auth signup

### Admin

The `LandingPageVisitor` model is registered in Django admin with:
- List display showing key fields
- Filters by conversion status, device, browser, OS, UTM parameters
- Search by IP, session key, referrer, user agent
- Date hierarchy by first visit

## UTM Parameter Usage

### Example URLs

Track different marketing campaigns:

```
# Google Ads campaign
https://yoursite.com/?utm_source=google&utm_medium=cpc&utm_campaign=spring_sale&utm_term=productivity_app

# Facebook post
https://yoursite.com/?utm_source=facebook&utm_medium=social&utm_campaign=product_launch

# Email newsletter
https://yoursite.com/?utm_source=newsletter&utm_medium=email&utm_campaign=weekly_digest&utm_content=button_cta

# Affiliate link
https://yoursite.com/?utm_source=affiliate&utm_medium=referral&utm_campaign=partner_promo
```

### Best Practices

1. **Always use lowercase**: UTM parameters are case-sensitive
2. **Be consistent**: Use the same naming conventions
3. **Use underscores**: For multi-word parameters (e.g., `spring_sale`)
4. **Document campaigns**: Keep a spreadsheet of your UTM codes
5. **Test links**: Verify tracking is working before launching campaigns

## Privacy Considerations

### Data Collected
- IP addresses are collected for analytics purposes
- No personally identifiable information beyond IP is stored
- User agent strings contain device/browser info but not personal data

### Compliance
- Ensure you have a privacy policy mentioning analytics tracking
- Consider adding a cookie consent banner for GDPR compliance
- IP addresses may be considered PII in some jurisdictions

### Recommendations
1. Add a privacy policy page explaining data collection
2. Consider implementing cookie consent (especially for EU visitors)
3. Provide opt-out mechanism if required by your jurisdiction
4. Regularly clean old visitor data (consider retention policy)

## Database Migrations

Run migrations to create the `LandingPageVisitor` table:

```bash
python manage.py migrate tracker
```

## Future Enhancements

Potential improvements:

1. **IP Geolocation**: Add country/city detection using IP geolocation service
2. **Advanced User Agent Parsing**: Use `user-agents` library for more accurate parsing
3. **Heatmaps**: Track click patterns and scroll depth
4. **A/B Testing**: Track which content variations perform best
5. **Funnel Analysis**: Track user journey from landing to conversion
6. **Data Export**: Export analytics data to CSV/Excel
7. **Real-time Dashboard**: WebSocket-based live visitor tracking
8. **Retention Analysis**: Track how many visitors return over time
9. **Cookie Consent Integration**: GDPR-compliant cookie banner
10. **API Endpoint**: REST API for external analytics tools

## Troubleshooting

### Visitors Not Being Tracked

1. Check that sessions are working:
   ```python
   # In Django shell
   from django.conf import settings
   print(settings.SESSION_ENGINE)
   ```

2. Verify the view is being called:
   ```python
   # Add logging in landing_page view
   logger.info(f"Landing page accessed from {get_client_ip(request)}")
   ```

3. Check for errors in logs:
   ```bash
   tail -f /path/to/django/logs
   ```

### Conversions Not Being Tracked

1. Verify signals are connected:
   ```python
   # In Django shell
   from tracker.signals import handle_user_signup
   print(handle_user_signup)
   ```

2. Test manually:
   ```python
   from tracker.visitor_tracking import mark_visitor_converted
   from django.contrib.auth.models import User
   
   user = User.objects.first()
   mark_visitor_converted(request, user)
   ```

### Proxy/Load Balancer Issues

If using a proxy or load balancer, ensure the correct header is forwarded:

1. Nginx config:
   ```nginx
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   ```

2. Apache config:
   ```apache
   RequestHeader set X-Forwarded-For %{REMOTE_ADDR}s
   ```

## Testing

### Manual Testing

1. Visit landing page in incognito mode
2. Check admin to verify visitor was tracked
3. Sign up with a new account
4. Verify conversion was tracked in admin

### Test UTM Tracking

Visit with UTM parameters:
```
http://localhost:8000/?utm_source=test&utm_medium=manual&utm_campaign=dev_test
```

Check in admin that UTM parameters were captured.

## Performance Considerations

- **Indexes**: Model includes indexes on frequently queried fields
- **Async Tracking**: Consider moving tracking to background task for high-traffic sites
- **Data Retention**: Implement periodic cleanup of old visitor data
- **Caching**: Analytics dashboard could benefit from caching for large datasets

## Support

For issues or questions:
1. Check Django logs for errors
2. Verify database migrations are applied
3. Test in Django shell for debugging
4. Review privacy/compliance requirements for your region
