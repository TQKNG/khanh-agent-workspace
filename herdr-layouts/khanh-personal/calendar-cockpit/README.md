# Local Google Calendar Cockpit

This is the first local Cockpit vertical slice for the Herdr `personal` layout.

It implements a read-only `meetings` view backed by Google Calendar.

## Setup

1. Enable the Google Calendar API in a Google Cloud project.
2. Create OAuth credentials with application type `Desktop app`.
3. Save the downloaded OAuth client JSON as `credentials.json` beside `calendar_cockpit.py`.
4. Create `cockpit.json` in the Herdr app home with paths for this service.
5. Run `calendar-cockpit.cmd auth` once to authorize the local account.
6. Reopen or reload Herdr.

The local `cockpit.json` should use this shape, with absolute paths for the user's machine:

```json
{
  "bin": "C:\\path\\to\\calendar-cockpit.cmd",
  "home": "C:\\path\\to\\calendar-cockpit",
  "cache": "C:\\path\\to\\calendar-cockpit\\cache",
  "version": "0.1.0"
}
```

The service stores the refresh token under `data/token.json`.

Do not commit `credentials.json` or `data/token.json`.

The first version requests only `https://www.googleapis.com/auth/calendar.events.readonly`.

It reads the primary calendar for the previous hour and the next seven days.

It supports list, day, and week views plus opening calendar and meeting links.

Create and edit actions are intentionally disabled.
