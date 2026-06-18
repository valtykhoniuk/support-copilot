# Video Playback Issues

If lessons won't play or buffer constantly, follow these troubleshooting steps.

## Quick fixes

| Step | Action |
|------|--------|
| 1 | Refresh the page (Ctrl+R / Cmd+R) |
| 2 | Try a different browser (Chrome recommended) |
| 3 | Disable VPN or proxy |
| 4 | Lower video quality: player gear icon → 480p |
| 5 | Check [status.foxschool.app](https://status.foxschool.app) for outages |

## Common symptoms

### Black screen, audio works

- Cause: hardware acceleration conflict
- Fix: Chrome → Settings → System → turn off "Use hardware acceleration" → restart browser

### Endless buffering

| Connection speed | Expected behavior |
|------------------|-------------------|
| Below 2 Mbps | Auto quality drops to 360p; may buffer |
| 2–5 Mbps | 480p stable |
| 5+ Mbps | 1080p available |

Run a speed test. If speed is fine, clear browser cache for foxschool.app.

### "Video unavailable" error

| Cause | Fix |
|-------|-----|
| Email not verified | Verify email (see [Login Problems](login-problems.md)) |
| Subscription expired | Update payment at Settings → Billing |
| Lesson not unlocked | Complete previous lessons in sequence |
| Content maintenance | Retry in 30 minutes; check status page |

### Subtitles not showing

Click the **CC** button in the video player. Subtitles are available in English and the target language for all A1–B2 lessons. C1–C2 lessons have English subtitles only.

## Speaking exercises fail

Speaking exercises need microphone permission:

1. Browser address bar → allow microphone for foxschool.app
2. macOS: System Settings → Privacy → Microphone → enable browser
3. Use Chrome or Firefox (Safari has known issues with WebRTC on older versions)

You can skip speaking exercises; they are optional and do not block progress.

## Report a persistent issue

Email support@foxschool.app with:

- Lesson name and module ID (shown below video title)
- Browser and OS version
- Screenshot or screen recording
- Results from [status.foxschool.app](https://status.foxschool.app)

Last updated: 2026-03-15
