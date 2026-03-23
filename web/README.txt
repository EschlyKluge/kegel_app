Durchgekegelt — Kegel-Club App
===============================
Author:  Eschly Jan Kluge <kluge.eschly@gmail.com>
Version: 0.0.32 (Pre-Alpha)
License: Proprietary


Quick Start
-----------
    pip install -r requirements.txt
    python kegel_club.py              # opens on http://127.0.0.1:5000
    PORT=8080 python kegel_club.py    # custom port


Project Structure
-----------------
    web/
    ├── kegel_club.py          Flask app — routes, APIs, data I/O
    ├── src/                   Templates & styles (shipped with the app)
    │   ├── base.html          Jinja2 base layout (nav, head, CSS injection)
    │   ├── base.css           Shared stylesheet (Apple-like design system)
    │   ├── home.html          Home page tiles
    │   ├── club.html          Member list + add form
    │   ├── stats.html         All-time statistics table
    │   ├── game.html          Game setup + numpad scoring + leaderboard (JS)
    │   ├── rules.html         Club rules (user-editable)
    │   └── settings.html      Admin / password change
    └── db/                    Runtime data (gitignored, auto-created)
        ├── members.csv        Member registry
        ├── temp_game.csv      Active game state (survives refresh)
        └── notsmart.txt       Admin password (plaintext — fix pending)


Current Features (MVP)
----------------------
- Touch-optimised tile navigation (Apple-like design)
- Member management (add / delete with admin password)
- Live game scoring via numpad (9-pin skittles)
    - Player selection with visual ordering (#1, #2, …)
    - Round-robin turn flow with "Weiter" confirmation
    - VOLLE and ABRAEUMEN game modes
    - Per-throw penalty tracking (standing pins, misses)
    - Auto-sorting leaderboard with average calculation
    - Nickname support (e.g. "Max Müller [Maxi]")
    - Game state persistence (survives page refresh)
- All-time statistics table (sorted by total points)
- Editable club rules page
- Admin password change


Changelog
---------
v0.32 (2026-03-23):
- Refactor: Extracted inline HTML/CSS/JS to src/ folder
- Refactor: Fixed path resolution via __file__ (works from any CWD)
- Refactor: render_page() helper eliminates per-route boilerplate
- Refactor: ensure_files() runs once via @app.before_request, validates all source files
- Refactor: Consistent 4-space indentation, cleaned unused imports
- Hygiene: Added .gitignore, requirements.txt
- Docs: Module docstring, function docstrings, polished README

v0.31:
- UI: "Finish Game" dialog shows sorted leaderboard with rank numbers
- UX: Aborting a game fully clears the setup screen (no ghost selections)


Roadmap
-------
Development follows an iterative phased approach. Each phase produces a
usable increment. See the earlier architecture conversation for full details.

PHASE 0 — Foundation  [IN PROGRESS]
  Goal: Harden & clean up the existing Flask web app.

  [x] 0.1  Project hygiene — requirements.txt, .gitignore, __file__ paths
  [x] 0.2  Extract inline HTML/CSS/JS to src/ files
  [ ] 0.3  Security: Hash admin password (werkzeug.security)
  [ ] 0.4  Security: Move password from URL query param to POST body
  [ ] 0.5  Security: Turn off debug=True, add SECRET_KEY
  [ ] 0.6  Security: Sanitise rules.html to prevent XSS via |safe

  Backlog — current web app polish:
  [ ] 0.7  Club: Hide money columns; show join date + hit ratio instead
  [ ] 0.8  Club: Show money only in admin view after password entry
  [ ] 0.9  Stats: Make columns sortable, add more statistics
  [ ] 0.10 Game: Rename "Strichliste/Scoreboard" to "Spiel" throughout
  [ ] 0.11 Game: Settings panel left, scoring panel right (layout)
  [ ] 0.12 Game: Clearer active-player indicator + current-throw stats
  [ ] 0.13 Game: Show "Wurf 2 von 3" instead of "2/3"
  [ ] 0.14 Game: Abräumen — reset pins after x throws, not on every clear
  [ ] 0.15 Game: Improve undo ("Löschen") and skip ("Weiter") correctness
  [ ] 0.16 Game: Larger visual feedback on successful/failed pin entry
  [ ] 0.17 Admin: Rename to "Einstellungen", move admin into a sub-section

PHASE 1 — Flutter Client  [PLANNED]
  Goal: Rebuild the POC as a cross-platform Flutter app with local SQLite.

  [ ] 1.1  Data models in Dart (Club, Member, Game, GameSession, Throw)
  [ ] 1.2  Local SQLite via drift (replaces CSV)
  [ ] 1.3  Home screen (tile navigation, matching current design)
  [ ] 1.4  Member management (add, list, delete with PIN)
  [ ] 1.5  9-pin scoring engine (pure Dart library, testable)
  [ ] 1.6  Numpad scoring UI (player select → score → finish)
  [ ] 1.7  Statistics screen
  [ ] 1.8  Rules screen
  [ ] 1.9  Settings / admin screen
  [ ] 1.10 Game history (list of past games with details)
  [ ] 1.11 State management with Riverpod

PHASE 2 — Monetisation  [PLANNED]
  Goal: Ship v1.0 to stores with free/full split and ads.

  [ ] 2.1  Feature flags (is_premium gate)
  [ ] 2.2  Google AdMob integration (banner + interstitial)
  [ ] 2.3  In-App Purchase (Play Store + App Store)
  [ ] 2.4  Gate features: 8 members, 1 club, 5 game history (free tier)
  [ ] 2.5  i18n framework (DE + EN)
  [ ] 2.6  App icons, splash screen, store screenshots
  [ ] 2.7  Publish to Google Play
  [ ] 2.8  Publish to Apple App Store
  [ ] 2.9  Deploy Flutter web version (Vercel/Netlify)

PHASE 3 — Bowling + Cloud  [PLANNED]
  Goal: Add 10-pin bowling, cloud sync, and the FastAPI backend.

  [ ] 3.1  10-pin bowling scoring engine (frames, strikes, spares)
  [ ] 3.2  10-pin UI (frame-based display, ball-by-ball input)
  [ ] 3.3  FastAPI backend (auth, clubs, members, games)
  [ ] 3.4  Supabase setup (PostgreSQL + Auth)
  [ ] 3.5  JWT auth in app (login, register, token refresh)
  [ ] 3.6  Cloud sync (local SQLite ↔ PostgreSQL)
  [ ] 3.7  "Hausnummer" game mode (Kleine/Große Hausnummer, 3 series)
  [ ] 3.8  Desktop builds (macOS + Windows via Flutter)

PHASE 4 — Polish & Growth  [PLANNED]
  Goal: Expand the feature set and grow the user base.

  [ ] 4.1  Advanced statistics with charts (fl_chart)
  [ ] 4.2  Club sharing (invite codes, shared leaderboards)
  [ ] 4.3  Tournament mode (bracket / round-robin)
  [ ] 4.4  Dark mode
  [ ] 4.5  Push notifications (game night reminders)
  [ ] 4.6  CSV/PDF export of stats and game history
  [ ] 4.7  Custom game modes (user-defined rules)
  [ ] 4.8  More languages (FR, NL, PL — big skittles countries)
