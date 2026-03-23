Durchgekegelt — Kegel-Club App
===============================
Author: Eschly Jan Kluge <kluge.eschly@gmail.com>
Version: 0.0.32 (Pre-Alpha)

Lokale Web-App (kein externer Service noetig).
Abhängigkeiten: see requirements.txt
Start: python kegel_club.py

Features (MVP):
- Startseite mit großen Touch-Kacheln
- Kegel-Club: Mitgliederliste, Beitrittsdatum, Schnitt-Anzeige
- Strichliste (aktuelles Spiel):
    - Auswahl der Spieler mit visueller Reihenfolge (#1, #2...)
    - Live-Summen für den laufenden Durchgang (Turn Stats)
    - Manual Turn Confirm ("Weiter")
    - Auto-Sorting Leaderboard with Average calculation
    - Nickname support
- Persistenz: members.csv, temp_game.csv


Changelog:
----------
v0.32 (2026-03-23):
- Refactor: Extracted inline HTML/CSS/JS to src/ folder
- Refactor: Fixed path resolution to use __file__ (works from any CWD)
- Refactor: render_page() helper eliminates per-route boilerplate
- Refactor: ensure_files() runs once via @app.before_request, not per-route
- Refactor: Consistent 4-space indentation throughout
- Refactor: Cleaned up unused imports
- Hygiene: Added .gitignore, requirements.txt
- Hygiene: ensure_files() now validates all required source files on startup

v0.31:
- UI: "Finish Game" confirmation dialog now shows a sorted leaderboard with rank numbers.
- UX: Aborting a game now ensures the setup screen is completely cleared (no lingering selections).


TODO:
-----
1. Club: Weniger Stats und keine Geldbeträge in Club-Mitglieder anzeigen, dafür aber Beitrittsdatum und durchschnittliche Trefferquote (Anzal_Kegel/Anzahl_Würfe) und Änderung der Trefferquote über Zeit, 
1.1 Geldbeträge, nur unter admin settings nach eingäbe des admin PW anzeigen
2. Stats: In stats die stats nach columns sortierbar machen und mehr stats anzeigen
3. Scoreboard: Statt Strichliste/Scoreboard eher 'Spiel'
4. Admin: Statt 'Admin' eher 'Settings', in 'Setting' eine unter Sektion 'Admin'
5. Scoreboard: die Settings linkt und punkte-eingabe rechts
6. Scoreboard: Spieler nicht nur wählen, sondern auch Spieler reihenfolge
7. Scoreboard: Sichtbarer machen wer gerade Spielt und seine aktuellen Würfe Stats
8. Scoreboard: Bei Würfen statt 2/3 lieber oder auch '2. Wurf im Gange' oder '1. Wurf übrig'
9. Scoreboard: Bei Abräumen kein hardcore Abräumen, sondern #Kegel Reset nach den x Würfen
10. Spiel Modi: 'Hausnummer' - Es wird bestimmt, ob man 'Kleine' oder 'Grosse' Hausnummer spielen will. Es gibt standardmässig eine 3-stellige Hausnummer zu erspielen -> 3 Wurf-Serien mit jeweils nur 1 Wurf pro Serie. Es muss am Anfang jeder Wurf-Serie bestimmt werden, welchen Teil der 3-Stelligen Hausnummer man Nummerien will.
11. Scoreboard: 'Löschen' und 'Weiter' müssen besser und korrekt Würfe korrigiern können.
12. Scoreboard: Die funktionierte oder nicht funktionierte Punkte Eingabe muss ein größeres Feedback geben. 
