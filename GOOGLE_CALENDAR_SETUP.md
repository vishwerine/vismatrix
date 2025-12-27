# Google Calendar Integration Setup Guide

## Overview

The Google Calendar integration allows users to automatically sync their calendar events as log activities in VisMatrix. This feature uses OAuth2 to securely connect to a user's Google Calendar with read-only access.

## Features

- ✅ **Automatic Sync**: Calendar events are automatically imported at configurable intervals (1-24 hours)
- ✅ **Smart Filtering**: Configure minimum event duration and exclude all-day events
- ✅ **Default Categories**: Assign synced events to specific categories
- ✅ **Manual Sync**: Trigger sync on-demand via the UI
- ✅ **No Duplicates**: Events are tracked to prevent duplicate imports
- ✅ **Secure**: Read-only access to calendar, OAuth2 authentication

## Setup Instructions

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Calendar API**:
   - Navigate to **APIs & Services** > **Library**
   - Search for "Google Calendar API"
   - Click **Enable**

### 2. Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** (or Internal if using Google Workspace)
3. Fill in the required fields:
   - **App name**: VisMatrix
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **Save and Continue**
5. Add the following scope:
   - `https://www.googleapis.com/auth/calendar.readonly`
6. Add test users (required for External apps in testing mode)
7. Complete the consent screen setup

### 3. Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Choose **Web application**
4. Configure:
   - **Name**: VisMatrix Calendar Integration
   - **Authorized JavaScript origins**: 
     - `http://127.0.0.1:8000` (development)
     - `https://vismatrix.space` (production)
   - **Authorized redirect URIs**: 
     - `http://127.0.0.1:8000/calendar/oauth2callback/` (development)
     - `https://vismatrix.space/calendar/oauth2callback/` (production)
5. Click **Create**
6. Download the JSON file with your credentials

### 4. Configure Environment Variables

Add the following environment variables to your system or `.env` file:

```bash
# Google Calendar OAuth2 Credentials
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/calendar/oauth2callback/"
```

For production:
```bash
export GOOGLE_REDIRECT_URI="https://vismatrix.space/calendar/oauth2callback/"
```

### 5. Install Dependencies

The required packages are already included in `requirements.txt`:
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 6. Run Migrations

```bash
cd progress_tracker
python manage.py migrate
```

## User Guide

### Connecting Google Calendar

1. Log in to VisMatrix
2. Click on your profile menu (top right)
3. Select **Google Calendar**
4. Click **Connect Google Calendar**
5. Authorize VisMatrix to read your calendar events
6. Configure your sync preferences

### Sync Settings

- **Automatic Sync**: Enable/disable automatic background sync
- **Sync Interval**: Choose how often to sync (1-24 hours)
- **Default Category**: Assign a category to all synced events
- **Minimum Event Duration**: Skip events shorter than X minutes
- **Exclude All-Day Events**: Skip all-day calendar events

### Manual Sync

Click the **Sync Now** button to immediately import recent calendar events (last 7 days).

### Disconnecting

Click **Disconnect** in the calendar settings to remove the integration. Your existing log activities will not be deleted.

## How It Works

1. **OAuth Flow**: Users authenticate via Google's OAuth2 consent screen
2. **Token Storage**: Access and refresh tokens are securely stored in the database
3. **Event Fetching**: The system queries the Google Calendar API for events
4. **Log Creation**: Qualifying events are automatically converted to DailyLog entries
5. **Duplicate Prevention**: Each event is tagged with its Google Calendar ID to prevent duplicate imports
6. **Auto Refresh**: Access tokens are automatically refreshed when they expire

## Technical Details

### Models

- `GoogleCalendarIntegration`: Stores OAuth tokens and sync preferences per user

### Views

- `calendar_settings`: Display calendar integration settings
- `calendar_connect`: Initiate OAuth2 flow
- `calendar_oauth_callback`: Handle OAuth2 callback
- `calendar_disconnect`: Remove integration
- `calendar_sync_now`: Trigger manual sync
- `calendar_update_settings`: Update sync preferences

### Service

- `calendar_service.py`: Contains `GoogleCalendarService` class for API interactions

### Sync Logic

Events are synced with the following logic:
- Event title becomes the activity name
- Event description becomes the log description
- Event duration is calculated and stored
- Events are tagged with `[gcal:event_id]` to track syncing
- Only timed events (not all-day) are synced by default
- Minimum duration filter prevents short events from being synced

## Troubleshooting

### "Google Calendar integration is not configured"

Ensure all environment variables are set correctly:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

### "Failed to connect Google Calendar"

- Check that the redirect URI matches exactly in Google Cloud Console
- Ensure the Calendar API is enabled
- Verify test users are added (for External apps in testing mode)

### "Sync completed with errors"

- Check the error message in the calendar settings page
- Verify OAuth tokens are valid (try disconnecting and reconnecting)
- Check server logs for detailed error messages

### No events being synced

- Verify events meet the minimum duration requirement
- Check if all-day events are excluded in settings
- Confirm the sync interval has elapsed
- Try manual sync to test immediately

## Security Considerations

- ✅ **Read-only access**: The integration only requests calendar.readonly scope
- ✅ **Encrypted storage**: Tokens are stored in the database (consider encrypting at rest for production)
- ✅ **User control**: Users can disconnect at any time
- ✅ **No data modification**: Calendar events are never modified or deleted
- ✅ **Secure OAuth2**: Uses industry-standard OAuth2 flow

## Future Enhancements

Potential improvements for future versions:
- [ ] Support for multiple calendar selection
- [ ] Two-way sync (create calendar events from tasks)
- [ ] Category mapping based on calendar colors
- [ ] Webhook support for real-time sync
- [ ] Batch processing for large calendars
- [ ] Support for recurring events
- [ ] Calendar event editing from VisMatrix
- [ ] Analytics on calendar time vs. logged time

## API Rate Limits

Google Calendar API has the following quotas:
- **Queries per day**: 1,000,000
- **Queries per 100 seconds per user**: 1,000

The integration respects these limits by:
- Limiting sync frequency (minimum 1 hour)
- Using incremental sync when possible
- Implementing exponential backoff on errors

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review server logs for detailed error messages
3. Contact support with your error details
4. Check Google Cloud Console for API status

---

**Note**: This integration requires a Google account and calendar access. Users maintain full control over their calendar data and can revoke access at any time through their Google account settings.
