# Kegel-Club App — Single-file Flask MVP
# -------------------------------------
# Lokale Web-App (kein externer Service noetig). Start: `python app.py`
# Abhängigkeiten: Flask (pip install flask)
#
# Version: 0.0.31
# Changes v030->v031:
# - UI: "Finish Game" confirmation dialog now shows a sorted leaderboard with rank numbers.
# - UX: Aborting a game now ensures the setup screen is completely cleared (no lingering selections).
#
# Features (MVP):
# - Startseite mit großen Touch-Kacheln (Apple-ähnlicher Look)
# - Kegel‑Club: Mitgliederliste, Beitrittsdatum, Schnitt-Anzeige
# - Strichliste (aktuelles Spiel):
#     • Auswahl der Spieler mit visueller Reihenfolge (#1, #2...)
#     • Live‑Summen für den laufenden Durchgang (Turn Stats)
#     • Manual Turn Confirm ("Weiter")
#     • Auto-Sorting Leaderboard with Average calculation
#     • Nickname support
# - Persistenz: members.csv, temp_game.csv

from __future__ import annotations
from flask import Flask, request, jsonify, redirect, url_for, make_response
from flask import render_template_string, send_file
import csv
import os
import json
import re
from datetime import datetime

APP_TITLE = "Durchgekegelt v0.31"
MEMBERS_CSV = "members.csv"
TEMP_GAME_CSV = "temp_game.csv"
PW_TXT = "notsmart.txt"
RULES_FILE = "rules.html"

app = Flask(__name__)

# ---------- Utilities ----------

def ensure_files():
    if not os.path.exists(MEMBERS_CSV):
        with open(MEMBERS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id","name","games","total_points","total_throws","total_cost_eur","joined_at"])
    if not os.path.exists(PW_TXT):
        with open(PW_TXT, "w", encoding="utf-8") as f:
            f.write("admin")
    if not os.path.exists(RULES_FILE):
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            f.write("<h3>Regeln</h3><p>Platzhalter.</p>")

def read_members():
    members = []
    if not os.path.exists(MEMBERS_CSV):
        ensure_files()
    with open(MEMBERS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            row["games"] = int(row.get("games", 0) or 0)
            row["total_points"] = int(row.get("total_points", 0) or 0)
            row["total_throws"] = int(row.get("total_throws", 0) or 0)
            row["total_cost_eur"] = float(row.get("total_cost_eur", 0) or 0)
            if not row.get("joined_at"):
                row["joined_at"] = datetime.now().strftime("%Y-%m-%d")
            members.append(row)
    return members

def write_members(members):
    with open(MEMBERS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","name","games","total_points","total_throws","total_cost_eur","joined_at"])
        w.writeheader()
        for m in members:
            # We must ensure no extra keys (like 'display_name') are passed to DictWriter if extrasaction='raise'
            # Filter the dict to only valid fieldnames
            clean_m = {k: m.get(k) for k in ["id","name","games","total_points","total_throws","total_cost_eur","joined_at"]}
            w.writerow(clean_m)

def new_member_id(members):
    existing = {int(m["id"]) for m in members} if members else set()
    i = 1
    while i in existing:
        i += 1
    return str(i)

def check_pw(pw: str) -> bool:
    try:
        with open(PW_TXT, encoding="utf-8") as f:
            saved = f.read().strip()
        return pw == saved
    except FileNotFoundError:
        return False

def get_display_name(full_name: str) -> str:
    """Extracts nickname from brackets if present, e.g. 'Name [Nick]' -> 'Nick'."""
    match = re.search(r'\[(.*?)\]', full_name)
    if match:
        return match.group(1).strip()
    return full_name

# Lese/Schreibe aktives Spiel
def save_temp_game(players, throwsPerPlayer, priceStanding, priceMiss, mode):
    with open(TEMP_GAME_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["player_id","name","throws","points","cost_eur","remaining","throws_per_player","price_per_standing_pin_eur","price_per_miss_eur","mode","saved_at"])
        ts = datetime.now().isoformat(timespec='seconds')
        for p in players:
            throws_str = " ".join(str(x) for x in p['throws'])
            w.writerow([
                p['id'], 
                p['name'], 
                throws_str, 
                p['points'], 
                f"{p['cost']:.2f}",
                p.get('remaining', 9),
                throwsPerPlayer, 
                priceStanding, 
                priceMiss, 
                mode, 
                ts
            ])

def load_temp_game():
    if not os.path.exists(TEMP_GAME_CSV):
        return None
    try:
        game_data = {"players": [], "throwsPerPlayer": 3, "priceStanding": 0.0, "priceMiss": 0.0, "mode": "VOLLE"}
        with open(TEMP_GAME_CSV, newline='', encoding='utf-8') as f:
            r = csv.DictReader(f)
            rows = list(r)
            if not rows: return None
            first = rows[0]
            game_data["throwsPerPlayer"] = int(first.get("throws_per_player") or 3)
            game_data["priceStanding"] = float(first.get("price_per_standing_pin_eur") or 0.0)
            game_data["priceMiss"] = float(first.get("price_per_miss_eur") or 0.0)
            game_data["mode"] = first.get("mode") or "VOLLE"
            for row in rows:
                throws_str = row.get("throws", "").strip()
                throws = [int(x) for x in throws_str.split(" ")] if throws_str else []
                player = {
                    "id": row["player_id"],
                    "name": row["name"],
                    "throws": throws,
                    "points": int(row.get("points") or 0),
                    "cost": float(row.get("cost_eur") or 0.0),
                    "remaining": int(row.get("remaining") or 9)
                }
                game_data["players"].append(player)
        return game_data
    except Exception as e:
        print(f"Error loading temp game: {e}")
        return None

def clear_temp_game():
    if os.path.exists(TEMP_GAME_CSV):
        os.remove(TEMP_GAME_CSV)

# ---------- Templates ----------

BASE_CSS = r"""
:root {
  --bg: #f5f5f7;
  --card: #ffffff;
  --card-2: #f9f9fb;
  --text: #1c1c1e;
  --muted: #6e6e73;
  --accent: #0071e3;
  --ok: #34c759;
  --warn: #ff9f0a;
  --danger: #ff3b30;
  --radius: 24px;
  --shadow: 0 10px 30px rgba(0,0,0,.08);
  --header-name: #003366;
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin: 0; padding: 0; height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Arial, sans-serif;
  background: radial-gradient(1200px 800px at 50% -10%, #ffffff, var(--bg));
  color: var(--text);
}
.container { max-width: 1100px; margin: 0 auto; padding: 24px; }
.header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin: 8px 0 16px; }
.h1 { font-size: 28px; font-weight: 700; letter-spacing:-.02em; }
.nav a { color: var(--muted); text-decoration:none; margin-left:16px; font-weight:600; }
.nav a.active, .nav a:hover { color: var(--text); }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 20px; margin-top: 22px; }
.card { background: linear-gradient(180deg, var(--card-2), var(--card)); border-radius: var(--radius); box-shadow: var(--shadow); padding: 22px; }
.tile { display:flex; flex-direction:column; justify-content:center; align-items:center; padding:30px; text-align:center; border-radius: var(--radius); background: linear-gradient(180deg,#ffffff,#f2f2f7); box-shadow: var(--shadow); min-height: 160px; text-decoration:none; color: var(--text); border: 1px solid #e6e6ea; }
.tile .icon { font-size: 44px; margin-bottom: 12px; }
.tile .label { font-size: 18px; font-weight: 700; }

.button { display:inline-flex; align-items:center; justify-content:center; gap:10px; padding: 14px 18px; border-radius: 16px; border: 1px solid #e6e6ea; background: var(--accent); color:#fff; font-weight:700; font-size:16px; cursor:pointer; box-shadow: var(--shadow); transition: all 0.2s; }
.button.ghost { background: #f2f2f7; color: var(--text); }
.button.warn { background: var(--warn); color:#1a1a1a; }
.button.danger { background: var(--danger); color:#fff; }
.button.ok { background: var(--ok); color:#fff; }
.button.pulse-green { background: #28a745; animation: pulse 1.5s infinite; border-color: #28a745; }
@keyframes pulse { 0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); } 70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); } 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); } }

.input, select { width:100%; padding:14px 16px; border-radius:14px; border:1px solid #e6e6ea; background:#ffffff; color:var(--text); }
.table { width:100%; border-collapse:separate; border-spacing:0 10px; }
.table th { text-align:left; color: var(--muted); font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
.table td, .table th { padding:10px 12px; }
.table tr { background: #ffffff; border:1px solid #efeff4; }
.table tr td:first-child, .table tr th:first-child { border-top-left-radius:12px; border-bottom-left-radius:12px; }
.table tr td:last-child, .table tr th:last-child { border-top-right-radius:12px; border-bottom-right-radius:12px; }
.row { display:flex; gap:12px; align-items:center; }
.col { flex:1; }
.small { color: var(--muted); font-size: 13px; }

.numpad { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; }
.numpad button { 
    padding: 18px 0; font-size:22px; font-weight:800; border-radius:18px; border:1px solid #e6e6ea; 
    background:#ffffff; color:var(--text); box-shadow: var(--shadow); 
    transition: transform 0.05s, background-color 0.1s; 
}
.numpad button.primary { background: var(--accent); color:#fff; }
.numpad button:disabled { opacity: 0.2; pointer-events: none; background: #e0e0e0; border-color: #d1d1d6; color: #a0a0a5; }

/* Visual Feedback Class for Touch */
.click-feedback {
    transform: scale(0.92) !important;
    background-color: #d1d1d6 !important;
}
.numpad button.primary.click-feedback {
    background-color: #005bb5 !important;
}

/* Touch controls */
.ctrls { display:flex; align-items:center; gap:8px; }
.iconbtn { display:inline-flex; align-items:center; justify-content:center; width:40px; height:40px; border-radius:12px; border:1px solid #e6e6ea; background:#fff; box-shadow: var(--shadow); font-weight:800; }
.iconbtn:active { transform: scale(.98); }
.segment { display:flex; gap:10px; }
.segment .seg { flex:1; text-align:center; padding:12px; border:1px solid #e6e6ea; border-radius:12px; background:#fff; box-shadow: var(--shadow); cursor:pointer; font-weight:700; }
.segment .seg.active { outline:3px solid var(--accent); color:#000; }
.checklist { border:1px solid #e6e6ea; border-radius:14px; background:#fff; padding:8px; max-height:220px; overflow:auto; box-shadow: var(--shadow); }
.checklist label { display:flex; align-items:center; gap:10px; padding:8px 6px; border-bottom:1px solid #f1f1f4; cursor:pointer; }
.checklist label:last-child { border-bottom:none; }
.badge { background:#f2f2f7; color:var(--text); border-radius:999px; padding: 6px 10px; font-size:12px; font-weight:700; border:1px solid #e6e6ea; }

.rank-badge {
    background: var(--accent); color: white;
    font-size: 11px; font-weight: 800;
    min-width: 20px; height: 20px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin-right: 4px; opacity: 0; transition: opacity 0.2s;
}
.rank-badge.visible { opacity: 1; }

@media (hover: hover) { .tile:hover { transform: translateY(-2px); transition: .2s ease; } }
.nav { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.nav a, .nav .navbtn {
  display:inline-flex; align-items:center; gap:8px;
  padding:10px 14px; border-radius:16px;
  background:#fff; border:1px solid #e6e6ea;
  box-shadow: var(--shadow);
  text-decoration:none; color: var(--text); font-weight:700;
}
.nav .i { font-size:18px; line-height:1; }
.nav a.active, .nav .navbtn.active { outline:3px solid var(--accent); color:#000; }

/* Game Header */
.game-header { background: #fff; padding: 16px; border-radius: var(--radius); box-shadow: var(--shadow); display:flex; flex-direction:column; gap:8px; border:1px solid #e6e6ea; margin-bottom:16px; }
.gh-top { display:flex; justify-content:space-between; align-items:center; }
.gh-title { font-size:18px; font-weight:800; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }
.gh-player { font-size:28px; font-weight:900; color:var(--header-name); letter-spacing: -0.5px; } /* Dark Blue Name */
.gh-stats-row { display:flex; flex-direction:column; gap:4px; padding-top:8px; border-top:1px solid #f1f1f4; margin-top:4px; }
.gh-stat { font-size:16px; font-weight:600; color:var(--text); }
.gh-detail { font-size:15px; font-weight:600; color:var(--muted); font-family:monospace; }

.val-curr { color: var(--accent); font-weight: 800; font-size: 18px; }
.val-total { color: #8e8e93; font-weight: 600; font-size: 16px; }

/* Stats Grid Dashboard */
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px; margin-bottom: 12px; }
.stat-card { background: #f2f2f7; padding: 14px 8px; border-radius: 18px; text-align: center; border: 1px solid #e6e6ea; }
.stat-card .label { font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 700; letter-spacing: 0.05em; margin-bottom: 4px; }
.stat-card .val { font-size: 20px; font-weight: 800; color: var(--text); }

/* Player List Cards */
.player-list { display: flex; flex-direction: column; gap: 8px; margin-top: 24px; margin-bottom: 12px; max-height: 280px; overflow-y: auto; padding: 4px; }
.player-card { display: flex; align-items: center; justify-content: space-between; background: #fff; padding: 12px 16px; border-radius: 16px; border: 1px solid #e6e6ea; box-shadow: var(--shadow); transition: .2s; }
.player-card.active { background: #f2f9ff; } /* Subtle active background only */
.pc-name { font-weight: 700; font-size: 16px; color: var(--text); }
.pc-meta { font-size: 13px; color: var(--muted); margin-top: 2px; }
.pc-cost { font-weight: 700; font-size: 15px; color: var(--text); text-align: right; }
"""

BASE_HTML = '''
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
  <title>{{ title }}</title>
  <style>{{ css|safe }}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="h1">{{ app_title }}</div>
      <div class="nav">
        <a href="{{ url_for('home') }}" class="navbtn {% if active=='home' %}active{% endif %}"><span class="i">🏠</span><span>Home</span></a>
        <a href="{{ url_for('club') }}" class="navbtn {% if active=='club' %}active{% endif %}"><span class="i">👥</span><span>Club</span></a>
        <a href="{{ url_for('stats') }}" class="navbtn {% if active=='stats' %}active{% endif %}"><span class="i">📈</span><span>Stats</span></a>
        <a href="{{ url_for('scoreboard') }}" class="navbtn {% if active=='score' %}active{% endif %}"><span class="i">🎯</span><span>Spiel</span></a>
        <a href="{{ url_for('rules') }}" class="navbtn {% if active=='rules' %}active{% endif %}"><span class="i">📜</span><span>Regeln</span></a>
        <a href="{{ url_for('admin') }}" class="navbtn {% if active=='admin' %}active{% endif %}"><span class="i">⚙️</span><span>Einstellungen</span></a>
      </div>
    </div>
    {{ body|safe }}
  </div>
</body>
</html>
'''

HOME_BODY = '''
  <div class="grid">
    <a class="tile" href="{{ url_for('club') }}"><div class="icon">👥</div><div class="label">Kegel‑Club</div><div class="small">Mitglieder verwalten</div></a>
    <a class="tile" href="{{ url_for('stats') }}"><div class="icon">📊</div><div class="label">Statistiken</div><div class="small">All‑Time Übersicht</div></a>
    <a class="tile" href="{{ url_for('scoreboard') }}"><div class="icon">🧮</div><div class="label">Spiel</div><div class="small">Aktuelles Spiel</div></a>
    <a class="tile" href="{{ url_for('rules') }}"><div class="icon">📘</div><div class="label">Kegel‑Regeln</div><div class="small">Begriffe & Regeln</div></a>
    <a class="tile" href="{{ url_for('admin') }}"><div class="icon">🛠️</div><div class="label">Einstellungen</div><div class="small">Passwort & Einstellungen</div></a>
  </div>
  <div class="small" style="margin-top:20px;">© 2026 | Kluge Solutions: Kegel-Club Version 0.0.31 (Pre-Alpha | Touch optimiert)</div>
'''

CLUB_BODY = '''
  <div class="card">
    <h2 style="margin:0 0 12px">Mitglieder</h2>
    <table class="table">
      <thead><tr><th>Name</th><th>Dabei seit</th><th>Ø Treffer Quote</th><th></th></tr></thead>
      <tbody>
        {% for m in members %}
        {% set avg = (m.total_points / m.total_throws) if m.total_throws > 0 else 0 %}
        <tr>
          <td><b>{{m.name}}</b></td>
          <td>{{m.joined_at}}</td>
          <td>{{ "{:.2f}".format(avg) }}</td>
          <td style="text-align:right;"><button class="button danger" onclick="delMember('{{m.id}}')">Löschen</button></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="card" style="margin-top:16px;">
    <h3>Neues Mitglied</h3>
    <div class="row">
      <input class="input col" id="newName" placeholder="Name eingeben" />
      <button class="button ok" onclick="addMember()">Anlegen</button>
    </div>
  </div>
  <script>
    async function addMember(){
      const name = document.getElementById('newName').value.trim();
      if(!name) return alert('Name fehlt');
      const r = await fetch('/api/member', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
      if(r.ok) location.reload(); else alert('Fehler beim Anlegen');
    }
    async function delMember(id){
      const pw = prompt('Admin‑Passwort zum Löschen eingeben:');
      if(!pw) return;
      const r = await fetch('/api/member/'+id+'?pw='+encodeURIComponent(pw), {method:'DELETE'});
      if(r.ok) location.reload(); else alert('Falsches Passwort oder Fehler.');
    }
  </script>
'''

STATS_BODY = '''
  <div class="card">
    <h2 style="margin:0 0 12px">All‑Time Statistiken</h2>
    <table class="table">
      <thead><tr><th>Name</th><th>Spiele</th><th>Würfe</th><th>Kegel</th><th>Treffer Quote</th><th>Strafe (€)</th></tr></thead>
      <tbody>
        {% for m in members %}
        {% set p_per_throw = (m.total_points / m.total_throws if m.total_throws>0 else 0) %}
        <tr>
          <td>{{m.name}}</td><td>{{m.games}}</td><td>{{m.total_throws}}</td><td>{{m.total_points}}</td><td>{{"{:.2f}".format(p_per_throw)}}</td><td>{{"{:.2f}".format(m.total_cost_eur)}}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
'''

SCOREBOARD_BODY = r"""
  <div class="card">
    <h2 style="margin:0 0 10px">Aktuelles Spiel</h2>
    
    <!-- Setup Area -->
    <div id="setupArea">
        <div class="row wrap" style="margin-bottom:12px;align-items:flex-start">
        <div class="col">
            <label class="small">Spieler auswählen (Reihenfolge durch Auswahl)</label>
            <div style="margin-bottom:6px;">
                <input class="input" id="searchMember" oninput="filterMembers()" placeholder="🔍 Spieler suchen..." style="padding:10px 14px; font-size:14px;">
            </div>
            <div class="checklist" id="playerChecklist">
            {% for m in members %}
                <label data-search-name="{{ m.name|lower }}" data-id="{{ m.id }}">
                    <span class="rank-badge" id="badge-{{ m.id }}"></span>
                    <input type="checkbox" value="{{ m.id }}" onclick="togglePlayer('{{ m.id }}', this.checked)" autocomplete="off"/> 
                    <span>{{ m.display_name }}</span>
                </label>
            {% endfor %}
            </div>
            <div class="row" style="margin-top:8px;">
            <button class="button" onclick="selectAll(true)">Alle</button>
            <button class="button" onclick="selectAll(false)">Keine</button>
            </div>
        </div>
        <div class="col">
            <label class="small">Würfe pro Durchgang [max. 10]</label>
            <div class="row">
            <button class="iconbtn" onclick="chgThrows(-1)">−</button>
            <input id="throwsInput" class="input" type="number" min="1" max="10" value="3" style="max-width:120px;text-align:center;font-weight:800;"/>
            <button class="iconbtn" onclick="chgThrows(1)">+</button>
            <span class="badge" id="throwsBadge">3</span>
            </div>
            <div class="row" style="margin-top:12px;">
            <div class="col">
                <label class="small">Strafe - Kegel stehen [€]</label>
                <div class="row">
                <button class="iconbtn" onclick="chgPrice('priceStanding',-0.01)">−</button>
                <input id="priceStanding" class="input" type="number" step="0.01" min="0" value="0.00" style="max-width:120px;text-align:center;"/>
                <button class="iconbtn" onclick="chgPrice('priceStanding',+0.01)">+</button>
                </div>
            </div>
            <div class="col">
                <label class="small">Strafe - Fehlwurf [€]</label>
                <div class="row">
                <button class="iconbtn" onclick="chgPrice('priceMiss',-0.01)">−</button>
                <input id="priceMiss" class="input" type="number" step="0.01" min="0" value="0.00" style="max-width:120px;text-align:center;"/>
                <button class="iconbtn" onclick="chgPrice('priceMiss',+0.01)">+</button>
                </div>
            </div>
            </div>
            <div style="margin-top:12px;">
            <label class="small">Spiel-Modi</label>
            <div class="segment" id="modeSeg">
                <div class="seg active" data-mode="VOLLE" onclick="setMode('VOLLE', this)">In die Vollen</div>
                <div class="seg" data-mode="ABRAEUMEN" onclick="setMode('ABRAEUMEN', this)">Abräumen</div>
            </div>
            </div>
        </div>
        </div>
        <div class="row" style="margin-top:16px;">
            <button class="button ok" onclick="startGame()">Spiel starten</button>
        </div>
    </div>
  </div>

  <div class="card" id="gameArea" style="display:none; margin-top:16px;">
    
    <div class="game-header">
      <div class="gh-top">
          <div class="gh-title">Würfe erfassen für</div>
      </div>
      <div class="gh-player" id="activePlayerName">Spieler</div>
      <div class="gh-stats-row">
          <div class="gh-stat" id="activeThrowInfo"></div>
          <div class="gh-detail" id="activeTurnDetail">Kegel pro Wurf: -</div>
      </div>
    </div>

    <div class="numpad" style="margin-top:12px;">
      <button class="num-btn" id="btn-1" onclick="press(1)">1</button>
      <button class="num-btn" id="btn-2" onclick="press(2)">2</button>
      <button class="num-btn" id="btn-3" onclick="press(3)">3</button>
      <button class="num-btn" id="btn-4" onclick="press(4)">4</button>
      <button class="num-btn" id="btn-5" onclick="press(5)">5</button>
      <button class="num-btn" id="btn-6" onclick="press(6)">6</button>
      <button class="num-btn" id="btn-7" onclick="press(7)">7</button>
      <button class="num-btn" id="btn-8" onclick="press(8)">8</button>
      <button class="num-btn" id="btn-9" onclick="press(9)">9</button>
      <button class="primary num-btn" id="btn-0" onclick="press(0)">0</button>
      <button class="primary num-btn" id="btn-undo" onclick="undo()">⌫</button>
      <button class="primary" id="btnNext" onclick="next()">Weiter</button>
    </div>
    
    <div id="playerSummary" class="player-list"></div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">Würfe Gesamt</div>
        <div class="val" id="totalThrows">0</div>
      </div>
      <div class="stat-card">
        <div class="label">Kegel Gesamt</div>
        <div class="val" id="totalPoints">0</div>
      </div>
      <div class="stat-card">
        <div class="label">Spiel-Kasse</div>
        <div class="val" id="totalCost">0.00 €</div>
      </div>
    </div>
    
    <div class="row" style="margin-top:16px;">
        <button class="button warn" onclick="finishGame()">Spiel beenden</button>
        <button class="button danger" onclick="cancelGame()">Spiel abbrechen</button>
    </div>
  </div>


  <script>
    let throwsPerTurn = 3;  
    let priceStanding = 0.00; 
    let priceMiss = 0.00;     
    let mode = 'VOLLE';       
    let game = [];            
    let iPlayer = 0;
    
    let selectedPlayerIds = [];
    // JS 'allMembers' populated with NICKNAMES
    const allMembers = {
      {% for m in members %}
        "{{m.id}}": "{{m.display_name}}",
      {% endfor %}
    };

    const restoreData = {{ restored_game|tojson }};

    function init(){
        if(restoreData){
            game = restoreData.players;
            throwsPerTurn = restoreData.throwsPerPlayer || 3;
            priceStanding = restoreData.priceStanding;
            priceMiss = restoreData.priceMiss;
            mode = restoreData.mode;
            iPlayer = findActivePlayerRoundRobin();
            
            document.getElementById('throwsInput').value = throwsPerTurn;
            document.getElementById('throwsBadge').innerText = throwsPerTurn;
            document.getElementById('priceStanding').value = priceStanding.toFixed(2);
            document.getElementById('priceMiss').value = priceMiss.toFixed(2);
            document.querySelectorAll('#modeSeg .seg').forEach(s => {
                s.classList.toggle('active', s.dataset.mode === mode);
            });
            
            document.getElementById('setupArea').style.display = 'none';
            document.getElementById('gameArea').style.display = 'block';
            updateInfo();
        } else {
            // UX Fix: Ensure clean slate when not restoring
            // Explicitly uncheck all checkboxes to prevent browser caching ghost selections
            const cbs = document.querySelectorAll('#playerChecklist input[type="checkbox"]');
            cbs.forEach(cb => cb.checked = false);
            selectedPlayerIds = [];
            updateRanks();
        }
    }

    function findActivePlayerRoundRobin(){
        if(game.length === 0) return 0;
        for(let i=0; i<game.length; i++){
            if(game[i].throws.length % throwsPerTurn !== 0) return i;
        }
        let minThrows = -1;
        for(let i=0; i<game.length; i++){
            let c = game[i].throws.length;
            if(minThrows === -1 || c < minThrows) minThrows = c;
        }
        for(let i=0; i<game.length; i++){
            if(game[i].throws.length === minThrows) return i;
        }
        return 0;
    }

    async function saveState(){
        if(game.length === 0) return;
        const payload = { players: game, throwsPerPlayer: throwsPerTurn, priceStanding, priceMiss, mode };
        try {
            await fetch('/api/update_game', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body: JSON.stringify(payload)
            });
        } catch(e) { console.error("Save failed", e); }
    }

    // --- Setup Interaction ---

    function updateRanks() {
        document.querySelectorAll('.rank-badge').forEach(el => {
            el.innerText = '';
            el.classList.remove('visible');
        });
        selectedPlayerIds.forEach((id, index) => {
            const badge = document.getElementById('badge-' + id);
            if(badge) {
                badge.innerText = index + 1;
                badge.classList.add('visible');
            }
        });
    }

    window.togglePlayer = (id, isChecked) => {
        if(isChecked) {
            if(!selectedPlayerIds.includes(id)) selectedPlayerIds.push(id);
        } else {
            selectedPlayerIds = selectedPlayerIds.filter(pid => pid !== id);
        }
        updateRanks();
    };

    window.filterMembers = () => {
        const term = document.getElementById('searchMember').value.toLowerCase();
        document.querySelectorAll('#playerChecklist label').forEach(lbl => {
            const name = lbl.getAttribute('data-search-name');
            lbl.style.display = name.includes(term) ? 'flex' : 'none';
        });
    };

    window.selectAll = (flag)=>{
      const checkboxes = document.querySelectorAll('#playerChecklist input[type="checkbox"]');
      checkboxes.forEach(cb=>{ cb.checked = !!flag; });
      if(flag){
          checkboxes.forEach(cb => {
              if(!selectedPlayerIds.includes(cb.value)) selectedPlayerIds.push(cb.value);
          });
      } else {
          selectedPlayerIds = [];
      }
      updateRanks();
    }
    
    // --- Game Logic ---

    function triggerFeedback(btnId) {
        const btn = document.getElementById(btnId);
        if(!btn) return;
        btn.classList.remove('click-feedback');
        void btn.offsetWidth; // Force reflow
        btn.classList.add('click-feedback');
        setTimeout(() => btn.classList.remove('click-feedback'), 150);
    }

    function updateInfo(){
      if(game.length===0) return;
      if(iPlayer >= game.length) iPlayer=0; 
      
      const g = game[iPlayer];
      const currentThrowsTotal = g.throws.length;
      
      const actualActiveIndex = findActivePlayerRoundRobin();
      const isBatchComplete = (iPlayer !== actualActiveIndex);
      
      // Controls for "Wait/Pulse" state
      const btnNext = document.getElementById('btnNext');
      
      if(isBatchComplete){
          btnNext.classList.add('pulse-green');
          
          // Case: Turn Complete (Waiting for Weiter)
          // DISABLE inputs 0-9 to prevent accidental extra entries
          for(let k=0; k<=9; k++){
              const b = document.getElementById('btn-'+k);
              if(b) b.disabled = true;
          }
          // ENABLE Undo so correction of last throw is possible
          const btnUndo = document.getElementById('btn-undo');
          if(btnUndo) btnUndo.disabled = false;
          
      } else {
          btnNext.classList.remove('pulse-green');
          
          // Re-enable logic:
          // 1. Undo is always available if not complete (logic handled in undo() but let's enable btn)
          document.getElementById('btn-undo').disabled = false;
          
          // 2. Button 0 is always available
          document.getElementById('btn-0').disabled = false;
          
          // 3. Buttons 1-9 depend on mode
          const maxPins = (mode === 'ABRAEUMEN') ? g.remaining : 9;
          
          for(let k=1; k<=9; k++){
              const btn = document.getElementById('btn-'+k);
              if(btn) {
                  btn.disabled = (k > maxPins);
              }
          }
      }

      // Display calculations
      const throwInBatch = isBatchComplete ? throwsPerTurn : (currentThrowsTotal % throwsPerTurn) + 1;
      
      let turnDetailText = "Wurf:Kegel";
      let displayMod = currentThrowsTotal % throwsPerTurn;
      if(displayMod === 0 && currentThrowsTotal > 0) displayMod = throwsPerTurn; 
      
      if (currentThrowsTotal > 0) {
          const currentTurnThrows = g.throws.slice(-displayMod);
          const parts = currentTurnThrows.map((score, idx) => `W${idx+1}:K${score}`);
          const sum = currentTurnThrows.reduce((a,b)=>a+b, 0);
          turnDetailText = `Wurf:Kegel | < ${parts.join(' • ')} > | Total: <K${sum}>`;
      }

      document.getElementById('activePlayerName').innerText = g.name;
      
      // Color coded throw info
      let throwHTML = `Wurf <span class="val-curr">${throwInBatch}</span> von <span class="val-total">${throwsPerTurn}</span>`;
      if(mode==='ABRAEUMEN') throwHTML += ` <span style="color:var(--muted)"> - Kegel über: ${g.remaining}</span>`;
      
      document.getElementById('activeThrowInfo').innerHTML = throwHTML;
      document.getElementById('activeTurnDetail').innerText = turnDetailText;
      
      const sumThrows = game.reduce((s,p)=>s+p.throws.length,0);
      const sumPoints = game.reduce((s,p)=>s+p.points,0);
      const sumCost   = game.reduce((s,p)=>s+p.cost,0);
      
      document.getElementById('totalThrows').innerText = sumThrows;
      document.getElementById('totalPoints').innerText = sumPoints;
      document.getElementById('totalCost').innerText = sumCost.toFixed(2) + ' €';

      // Sort logic for Leaderboard: Points Descending, then Throws Ascending
      // We map to preserve the original index to identify 'iPlayer' correctly
      let displayList = game.map((p, idx) => ({ ...p, origIdx: idx }));
      
      displayList.sort((a, b) => {
          // Sort 1: Points Descending (Higher is better)
          if (b.points !== a.points) return b.points - a.points;
          // Sort 2: Throws Ascending (Efficiency)
          return a.throws.length - b.throws.length;
      });

      const html = displayList.map((p) => {
         const activeClass = (p.origIdx === iPlayer) ? 'active' : '';
         const avg = (p.throws.length > 0) ? (p.points / p.throws.length) : 0.0;
         
         return `
         <div class="player-card ${activeClass}">
            <div>
                <div class="pc-name">${p.name}</div>
                <div class="pc-meta">
                    ${p.points} Kegel • ${p.throws.length} Würfe • Ø ${avg.toFixed(2)}
                </div>
            </div>
            <div class="pc-cost">${p.cost.toFixed(2)} €</div>
         </div>
         `;
      }).join('');
      document.getElementById('playerSummary').innerHTML = html;
    }

    window.startGame = ()=>{
      if(selectedPlayerIds.length===0){ alert('Spieler wählen'); return; }
      game = selectedPlayerIds.map(id => {
          return {
              id: id,
              name: allMembers[id] || 'Unbekannt',
              throws: [],
              points: 0,
              cost: 0,
              remaining: 9
          };
      });
      iPlayer=0;
      document.getElementById('setupArea').style.display='none';
      document.getElementById('gameArea').style.display='block';
      priceStanding = parseFloat(document.getElementById('priceStanding').value||'0')||0;
      priceMiss = parseFloat(document.getElementById('priceMiss').value||'0')||0;
      updateInfo();
      saveState();
    }

    window.press = (n)=>{
      if(n<0||n>9) return;
      
      // UX: Visual Feedback
      triggerFeedback('btn-' + n);
      
      // Safety: check if batch is complete
      const actualActiveIndex = findActivePlayerRoundRobin();
      if(iPlayer !== actualActiveIndex) return; 

      const g = game[iPlayer];

      if(mode==='ABRAEUMEN' && n>g.remaining){ 
          // UI should prevent this, but double check
          return; 
      }
      
      g.throws.push(n);
      g.points += n;
      if(priceStanding>0){ g.cost += (9-n) * priceStanding; }
      if(n===0 && priceMiss>0){ g.cost += priceMiss; }
      if(mode==='ABRAEUMEN'){ g.remaining -= n; if(g.remaining<=0) g.remaining=9; }

      updateInfo();
      saveState();
    }

    window.undo = ()=>{
        const g = game[iPlayer];
        if (!g || g.throws.length === 0) return;

        // Check Logic: Are we "Waiting for Weiter"?
        const actualActiveIndex = findActivePlayerRoundRobin();
        const isWaitingForConfirmation = (iPlayer !== actualActiveIndex); 

        // Ground Truth Logic:
        // We can only undo if we are in the MIDDLE of a turn (mod != 0)
        // OR if we just finished a turn and are waiting for confirmation (isWaitingForConfirmation).
        // If we are at the exact start of a new turn (mod == 0 and NOT waiting), it means the previous batch was committed.
        
        const mod = g.throws.length % throwsPerTurn;
        
        if (mod !== 0 || isWaitingForConfirmation) {
            popThrow(iPlayer);
            updateInfo();
            saveState();
        } 
        // Else: We are at start of a fresh turn/batch. Previous throws are locked. Do nothing.
    }
    
    function popThrow(idx) {
      const g = game[idx];
      const last = g.throws.pop();
      if(last===undefined) return;
      g.points -= last;
      if(priceStanding>0){ g.cost -= (9-last) * priceStanding; }
      if(last===0 && priceMiss>0){ g.cost -= priceMiss; }
      if(mode==='ABRAEUMEN'){ g.remaining += last; if(g.remaining>9) g.remaining=9; }
    }

    window.next = ()=>{
      const g = game[iPlayer];
      
      const actualActiveIndex = findActivePlayerRoundRobin();
      const isActuallyDone = (iPlayer !== actualActiveIndex);

      if(isActuallyDone) {
          if(mode === 'ABRAEUMEN') g.remaining = 9;
          iPlayer = actualActiveIndex;
      } else {
          const remainder = throwsPerTurn - (g.throws.length % throwsPerTurn);
          for(let k=0; k<remainder; k++){
              g.throws.push(0); 
              if(priceStanding>0) g.cost += 9 * priceStanding; 
              if(priceMiss>0) g.cost += priceMiss; 
          }
          if(mode === 'ABRAEUMEN') g.remaining = 9;
          iPlayer = findActivePlayerRoundRobin();
      }
      
      updateInfo();
      saveState();
    }
    
    window.cancelGame = async () => {
        if(!confirm('Spiel wirklich abbrechen? Daten gehen verloren!')) return;
        await fetch('/api/clear_game', {method:'POST'});
        location.reload();
    }

    window.finishGame = async ()=>{
      if(game.length===0){ alert('Kein Spiel aktiv'); return; }
      
      // Sort for confirmation (Points Descending, Throws Ascending)
      let sorted = [...game];
      sorted.sort((a, b) => {
          if (b.points !== a.points) return b.points - a.points;
          return a.throws.length - b.throws.length;
      });

      const lines = sorted.map((p, i) => `#${i+1} ${p.name}: ${p.points} Holz, ${p.throws.length} Wurf, ${p.cost.toFixed(2)} €`).join('\n');
      const total = game.reduce((s,p)=>s+p.cost,0).toFixed(2);
      
      if(!confirm('Ergebnisse speichern?\n\n' + lines + '\n\nGesamtkosten: ' + total + ' €')) return;
      
      const payload = { players: game, throwsPerPlayer: throwsPerTurn, priceStanding, priceMiss, mode };
      const r = await fetch('/api/finish_game', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      const j = await r.json();
      if(r.ok){ alert('Gespeichert. Mitglieder‑Statistiken aktualisiert.'); location.href='/stats'; }
      else alert(j.error||'Fehler beim Speichern');
    }
    
    window.chgThrows = (d)=>{
      const el = document.getElementById('throwsInput');
      let v = parseInt(el.value||'3',10) + d; if(isNaN(v)) v=3; v=Math.min(10,Math.max(1,v));
      el.value = v; throwsPerTurn = v; document.getElementById('throwsBadge').innerText = String(v);
      if(game.length > 0) { iPlayer = findActivePlayerRoundRobin(); updateInfo(); saveState(); }
    }
    window.chgPrice = (id,delta)=>{
      const el = document.getElementById(id);
      let v = parseFloat(el.value||'0'); if(isNaN(v)) v=0; v = Math.max(0, Math.round((v+delta)*100)/100);
      el.value = v.toFixed(2);
      if(id==='priceStanding') priceStanding=v; else priceMiss=v;
      if(game.length > 0) { updateInfo(); saveState(); }
    }
    window.setMode = (m,node)=>{
      mode=m; document.querySelectorAll('#modeSeg .seg').forEach(s=>s.classList.remove('active')); node.classList.add('active');
      if(game.length > 0) { updateInfo(); saveState(); }
    }

    init();
  </script>
"""

RULES_BODY = """
  <div class="card">
    <h2 style="margin:0 0 12px">Kegel‑Regeln & Begriffe</h2>
    <p class="small">Diese Seite ist ein Platzhalter. Hier können alle lokalen Regeln, Strafen und Begriffe dokumentiert werden.</p>
    <ul>
      <li><b>Neun:</b> Alle 9 Kegel fallen.</li>
      <li><b>Rinne:</b> Wurf ohne Treffer (0 Holz).</li>
      <li><b>Räumen:</b> Letzter Rest fällt; Kegel werden neu aufgestellt.</li>
    </ul>
  </div>
"""

ADMIN_BODY = """
  <div class="card">
    <h2 style="margin:0 0 12px">Admin</h2>
    <div class="row">
      <div class="col">
        <label class="small">Aktuelles Passwort</label>
        <input class="input" id="oldPw" type="password" placeholder="Aktuelles Passwort" />
      </div>
      <div class="col">
        <label class="small">Neues Passwort</label>
        <input class="input" id="newPw" type="password" placeholder="Neues Passwort" />
      </div>
    </div>
    <div class="row" style="margin-top:12px;">
      <button class="button" onclick="changePw()">Passwort speichern</button>
    </div>
    <script>
      async function changePw(){
        const oldPw = document.getElementById('oldPw').value;
        const newPw = document.getElementById('newPw').value;
        if(!oldPw || !newPw) return alert('Bitte beide Felder ausfüllen');
        const r = await fetch('/api/password', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({oldPw, newPw})});
        const j = await r.json();
        if(r.ok) alert('Passwort geändert'); else alert(j.error || 'Fehler');
      }
    </script>
  </div>
"""

# ---------- Routes ----------

@app.route("/")
def home():
    ensure_files()
    body = render_template_string(HOME_BODY)
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Start", app_title=APP_TITLE, active='home', body=body)

@app.route("/club")
def club():
    members = read_members()
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Club", app_title=APP_TITLE, active='club', body=render_template_string(CLUB_BODY, members=members))

@app.route("/stats")
def stats():
    members = read_members()
    members.sort(key=lambda m: m["total_points"], reverse=True)
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Statistiken", app_title=APP_TITLE, active='stats', body=render_template_string(STATS_BODY, members=members))

@app.route("/scoreboard")
def scoreboard():
    members = read_members()
    
    # Preprocess members to add display_name (Nickname logic)
    for m in members:
        m['display_name'] = get_display_name(m['name'])

    # Check for active game
    restored_game = load_temp_game()
    
    # Feature v029: Refresh restored game names with current nicknames
    if restored_game:
        # Map ID -> Nickname
        nickname_map = {m['id']: m['display_name'] for m in members}
        for p in restored_game['players']:
            if p['id'] in nickname_map:
                p['name'] = nickname_map[p['id']]
    
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Strichliste", app_title=APP_TITLE, active='score', 
                                  body=render_template_string(SCOREBOARD_BODY, members=members, restored_game=restored_game))

@app.route("/rules")
def rules():
    ensure_files()
    content = None
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, encoding='utf-8') as f:
            content = f.read()
    if content is None:
        body = RULES_BODY
    else:
        body = f"""
        <div class='card'>
          <h2 style='margin:0 0 12px'>Kegel‑Regeln & Begriffe</h2>
          <div class='small'>Aus Datei: <code>{RULES_FILE}</code></div>
          <div style='margin-top:12px;'>
          {content}
          </div>
        </div>
        """
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Regeln", app_title=APP_TITLE, active='rules', body=body)

@app.route("/admin")
def admin():
    body = render_template_string(ADMIN_BODY)
    return render_template_string(BASE_HTML, css=BASE_CSS,
                                  title=APP_TITLE+" — Admin", app_title=APP_TITLE, active='admin', body=body)

# ---------- APIs ----------

@app.post("/api/member")
def api_add_member():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error":"Name fehlt"}), 400
    members = read_members()
    if any(m['name'].lower()==name.lower() for m in members):
        return jsonify({"error":"Name existiert bereits"}), 400
    members.append({"id": new_member_id(members), "name": name, "games":0, "total_points":0, "total_throws":0, "total_cost_eur":0.0})
    write_members(members)
    return jsonify({"ok": True})

@app.delete("/api/member/<id>")
def api_delete_member(id):
    pw = request.args.get('pw','')
    if not check_pw(pw):
        return jsonify({"error":"Passwort falsch"}), 403
    members = read_members()
    new_members = [m for m in members if m['id'] != id]
    if len(new_members) == len(members):
        return jsonify({"error":"Mitglied nicht gefunden"}), 404
    write_members(new_members)
    return jsonify({"ok": True})

@app.post("/api/password")
def api_change_password():
    data = request.get_json(force=True)
    if not check_pw(data.get('oldPw','')):
        return jsonify({"error":"Aktuelles Passwort falsch"}), 403
    newPw = (data.get('newPw') or '').strip()
    if len(newPw) < 4:
        return jsonify({"error":"Neues Passwort zu kurz (min. 4)"}), 400
    with open(PW_TXT, 'w', encoding='utf-8') as f:
        f.write(newPw)
    return jsonify({"ok": True})

@app.post("/api/update_game")
def api_update_game():
    # Persist current state to temp_game.csv
    data = request.get_json(force=True)
    players = data.get('players', [])
    throwsPerPlayer = int(data.get('throwsPerPlayer', 0))
    priceStanding = float(data.get('priceStanding', 0))
    priceMiss = float(data.get('priceMiss', 0))
    mode = data.get('mode', 'VOLLE')
    
    save_temp_game(players, throwsPerPlayer, priceStanding, priceMiss, mode)
    return jsonify({"ok": True})

@app.post("/api/clear_game")
def api_clear_game():
    clear_temp_game()
    return jsonify({"ok": True})

@app.post("/api/finish_game")
def api_finish_game():
    data = request.get_json(force=True)
    players = data.get('players', [])
    throwsPerPlayer = int(data.get('throwsPerPlayer', 0))
    priceStanding = float(data.get('priceStanding', 0))
    priceMiss = float(data.get('priceMiss', 0))
    mode = data.get('mode', 'VOLLE')
    
    if not players:
        return jsonify({"error":"Keine Spieler"}), 400
        
    # Update members.csv
    members = read_members()
    if len(members) > 100:
        members = members[:100]
    m_by_id = {m['id']: m for m in members}
    for p in players:
        m = m_by_id.get(str(p['id']))
        if m is None:
            continue
        m['games'] += 1
        m['total_points'] += int(p['points'])
        m['total_throws'] += int(len(p['throws']))
        m['total_cost_eur'] += float(p['cost'])
    write_members(members)
    
    # Clear the temp game so next game starts fresh
    clear_temp_game()
    
    return jsonify({"ok": True})


@app.route('/favicon.ico')
def favicon():
    return ('', 204)

if __name__ == "__main__":
    ensure_files()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n➡ Starte {APP_TITLE} lokal auf http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=True)