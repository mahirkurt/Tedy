# English Central Scraper Design

## Goal

Scrape English Central homework completion status and create direct video links. Post to Google Classroom (İngilizce course) as an announcement.

## Site Details

- URL: https://tr.englishcentral.com
- Credentials: isik.kurt26@globed.co / 3624
- Class: 6C (ID: 204944), Org: TED Ronesans 25-26
- Account ID: 14041005
- Teacher: Miss Gözde

## Data Model

29 assigned videos, each with 6-8 activities (Watch, Learn, Speak, Quiz, etc.). Per-activity `started`/`completed` boolean flags. Video completion = all core activities completed.

### Key APIs (intercepted from SPA)

| Endpoint | Returns |
|----------|---------|
| `commerce/my/english/video?progress=All&pageSize=100&classID=204944` | List of dialog IDs (paginated) |
| `content/dialog?dialogIDs=...&fields=dialogID,title,difficulty,duration,dialogURL` | Video metadata |
| `report/activity/dialog?dialogIDs=...` | Per-video activity completion status |

Auth: JWT (from login) + session cookies. APIs on `bridge.englishcentral.com` and `reportcard.englishcentral.com`.

## Approach: Selenium + Fetch Interception

1. **Login** via Selenium (email/password modal)
2. **Navigate** to `myclass/{CLASS_ID}/0/videos` — inject fetch/XHR interceptor before page load
3. **Paginate** through all videos (pageSize=15, fetch page 0 and 1)
4. **Collect** intercepted API responses: video list + dialog details + activity report
5. **Save** to `output/englishcentral_progress.json`

## Output Format

```json
{
  "scraped_at": "2026-03-06T14:00:00",
  "class_name": "6C",
  "class_id": 204944,
  "total_videos": 29,
  "completed_videos": 12,
  "videos": [
    {
      "dialog_id": 35801,
      "title": "I Am the Soil",
      "url": "https://www.englishcentral.com/video/35801",
      "difficulty": 4,
      "duration": "00:01:19",
      "completed": false,
      "started": false,
      "activities": {
        "watch": {"started": false, "completed": false},
        "learn": {"started": false, "completed": false},
        "speak": {"started": false, "completed": false}
      }
    }
  ]
}
```

## Classroom Integration

Single announcement in İngilizce course, updated each sync:

```
🎬 English Central Ödev Durumu (6 Mart 2026)

✅ 12/29 video tamamlandı

Tamamlanmamış videolar:
• I Am the Soil → https://www.englishcentral.com/video/35801
• Wow Them With Your Presentation → https://www.englishcentral.com/video/18519
...

Tamamlanan videolar:
• Taylor Swift Inspires Women → https://www.englishcentral.com/video/25820
...
```

Dedup key: `ec:{course_id}:progress`. Updated on each run (not idempotent — always updates text with latest status).

## Files

- `src/scrape_englishcentral.py` — Scraper (login + intercept + save)
- `src/sync_to_classroom.py` — Add `sync_englishcentral()` function
- `tests/test_classroom_sync.py` — Add test for new sync function

## Integration

Called from `run_sync.py` after other scrapers, before Classroom sync. `sync_to_classroom.py:main()` calls `sync_englishcentral()` which reads `output/englishcentral_progress.json`.
