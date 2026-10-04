# Vienna Tennis Court Finder — Project Specification

## Version 1 (build this first): on-demand check in Claude Code

This is the simplified first version. Everything in it should be built and working before any of the "Later" features (Section 7) are even attempted.

**How it works:** there is no app, no server, no WhatsApp. You open a Claude Code session and type a request directly, in plain language, using a **day plus a time-of-day word** rather than an exact clock time — for example:

> "Give me the availabilities for tennis courts tomorrow afternoon or on Wednesday evening."

The program checks each club **in your priority order**, and reports back **immediately, in the same chat** — no retrying, no waiting, no notifications — showing **all free time slots it finds within that window**, not just a single yes/no answer. If nothing is free in that window, it tells you that; you ask again later yourself if you want to check again.

This removes, for now:
- Any always-on server or hosting cost
- WhatsApp entirely (no Twilio account needed)
- Background retrying and the "STOP" command (nothing to stop — each check is a single, immediate action)
- Automatic weather lookup — you simply state indoor/outdoor yourself as part of your request (or ask it to show both, if you don't specify)

---

## 1. Your tennis clubs (v1 scope: 2 clubs, confirmed)

Try in this order, stopping at the first one with a free slot:

1. **Europahalle** (1230 Wien) — confirmed public booking calendar, no login needed to view. Platform: **eTennis.at** (reservierung.europahalle.at).
2. **La Ville Tennis Club** (Alterlaa, "Union Tennis Sport Center La Ville") — confirmed public booking calendar, no login needed to view. Same platform: **eTennis.at** (reservierung.laville.at).

Both clubs were directly verified by browsing their real booking pages — not assumed. Both run the exact same underlying booking platform, so the checking logic for each club can likely share the same code, just pointed at a different club ID.

**Why this scope is simpler than originally planned:** no login, no credentials, no browser automation needed — just reading a public calendar page for each club. This was the single biggest source of complexity in the original 4-club plan, and it's now removed entirely for v1.

### Deferred for later (not dropped — see Section 7)

- **Wienerberg** ("City & Country Club Wienerberg") — confirmed **login-required** (platform: Nexxchange), needs your membership credentials. Revisit once v1 works and you're ready to handle credentials.
- **Südstadt** — could not be confirmed; exact club/website still unclear. Revisit once you can share the specific name or link.

---

## 2. Time-of-day definitions

Since requests use a time-of-day word instead of an exact clock time, these are the fixed meanings the program uses:

| Word | Time range |
|---|---|
| **Morning** | 6:00 – 11:00 |
| **Noon** | 10:00 – 14:00 |
| **Afternoon** | 13:00 – 18:00 |
| **Evening** | 17:00 – 23:00 |

**Note:** these ranges deliberately overlap by an hour at each boundary (e.g. 10–11am counts as both "morning" and "noon"), exactly as you defined them — this isn't a bug, just worth knowing since it means a court at, say, 10:30am will show up under either word.

A request can include **more than one day/window combination at once** (as in the example above — "tomorrow afternoon or Wednesday evening"); the program checks each combination separately and reports on all of them.

---

## 3. Indoor / outdoor (v1: manual, no weather check)

You say which you want as part of your request ("...outdoor" / "...indoor"). If you don't specify, the program should **show both** (clearly labeled) rather than silently guessing — same "don't guess, ask or show clearly" principle as before, just without the weather automation behind it.

---

## 4. What a result looks like

Since a request can cover a multi-hour window (and possibly several day/window combinations at once), the result is a **list of available slots**, grouped by the window you asked about — not a single yes/no answer. Suggested format to keep it consistent (and reusable later for WhatsApp):

**Slots found:**
> **Tomorrow afternoon:**
> - Europahalle — 14:00, 15:30, 17:00 (outdoor, sand)
> - La Ville — 13:00, 16:00 (outdoor, sand)
>
> **Wednesday evening:**
> - No free slots found at either club.

**Nothing found for a window:**
> No free slots at Europahalle or La Ville for **[day] [time-of-day]**.

Each listed slot should show enough to actually act on it: club, start time, and surface — indoor/outdoor only needs stating if you didn't specify it in your request (see Section 3).

---

## 5. Status: v1 built and verified

Everything below is written, tested against real captured pages from both clubs, and working correctly:

- [x] Visit each club's real website and confirm booking system type (see Section 1).
- [x] Inspected the actual eTennis.at page structure — the availability data is embedded directly in the page's HTML (not a separate API call), as `<div class="slot">` elements per court with `av`/`res` (available/reserved) classes, a start timestamp, and a price tier. See `src/etennis_parser.py`.
- [x] Shared parsing logic works for both clubs from one function, verified against real saved pages (`fixtures/europahalle_sample.html`, `fixtures/laville_sample.html`).
- [x] Confirmed real court IDs for both clubs (Europahalle: 4927–4938; La Ville: 14651–14660).
- [x] Day/time-of-day phrase resolution ("tomorrow afternoon", "wednesday evening") implemented and tested — see `src/time_windows.py`. Currently handles "today"/"tomorrow"/weekday names directly; looser phrasing would need passing the raw text to Claude for extraction instead (not yet built).
- [x] Surface handling: Europahalle is hardcoded "carpet" (not in the page data); La Ville is read live from each court's own label text (e.g. "Platz 5 Rebound Ace"), confirmed correct against your stated facts.
- [x] Full pipeline (`src/check_courts.py`) ties it together and produces output in the Section 4 format, verified end-to-end against real data.

**Known limitation, not yet resolved:** the actual *live* internet request (fetching a fresh page for "today," not a saved sample) hasn't been tested, because this development sandbox can't reach the internet directly (see earlier conversation notes). The live-request code is written (`fetch_club_page` in `check_courts.py`) and should work as-is, but needs a real test once there's genuine internet access — e.g. the rented cloud server from Section 7, or any other machine with normal internet.

---

## 6. Suggested rough architecture (v1) — as built

- **Language:** Python. Three files: `etennis_parser.py` (parses one club's page into Slot objects), `time_windows.py` (turns a day+time-of-day phrase into an actual date/time range), `check_courts.py` (ties them together: fetch → filter → format).
- **No server, no scheduling, no webhook.** The script just runs once per request, when you ask for it.
- **No login, no credentials.** Both clubs' calendars are publicly viewable.
- **Output:** printed back to you, using the format in Section 4 — confirmed working.

---

## 7. Later (not part of v1 — revisit once v1 works)

These were part of the original fuller plan. Nothing here is lost, just deliberately deferred so v1 stays simple:

- **Wienerberg and Südstadt as additional clubs** — Wienerberg needs login handling worked out; Südstadt needs its actual website confirmed first.
- **WhatsApp as the interface** (both sending requests and receiving results), instead of typing into Claude Code directly.
- **Always-on cloud server hosting** (~€4–6/month, e.g. Hetzner or DigitalOcean) — only needed once WhatsApp messages must be receivable at any time.
- **Background retry/polling** — keep checking periodically until a slot opens up, rather than a single on-demand check.
- **"STOP" command** — cancel an active background search, only relevant once retrying exists.
- **Automatic weather-based indoor/outdoor decision** — using a free forecast API (Open-Meteo suggested), with a rule to ask you directly when the forecast is borderline/uncertain.
- **Natural-language date/time parsing via the Claude API** — needed once requests arrive as free-text WhatsApp messages instead of typed directly into Claude Code.

When you're ready to build any of these, we can expand this document again — the earlier version already worked out the design decisions for each (message formats, retry/stop logic, weather thresholds, hosting comparison), so it won't need to be re-derived from scratch.
