# imports
from __future__ import annotations
from flask import Flask, request, jsonify, render_template_string
import csv
import os
import re
from datetime import datetime

# ---------- Constants ----------
APP_TITLE = "Durchgekegelt v0.32"

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
DATA_DIR = os.path.join(BASE_DIR, "db")

# data files
MEMBERS_DATA = os.path.join(DATA_DIR, "members.csv")
TEMP_GAME_DATA = os.path.join(DATA_DIR, "temp_game.csv")
PW_FILE = os.path.join(DATA_DIR, "notsmart.txt")

# source files
BASE_CSS = os.path.join(SRC_DIR, "base.css")
BASE_HTML = os.path.join(SRC_DIR, "base.html")
HOME_HTML = os.path.join(SRC_DIR, "home.html")
CLUB_HTML = os.path.join(SRC_DIR, "club.html")
STATS_HTML = os.path.join(SRC_DIR, "stats.html")
GAME_HTML = os.path.join(SRC_DIR, "game.html")
RULES_HTML = os.path.join(SRC_DIR, "rules.html")
SETTINGS_HTML = os.path.join(SRC_DIR, "settings.html")


# ---------- Global Variables ----------

_files_ensured = False
REQUIRED_SRC_FILES = [BASE_HTML, BASE_CSS, HOME_HTML, CLUB_HTML, STATS_HTML, GAME_HTML, SETTINGS_HTML]
MEMBER_FIELDS = ["id", "name", "games", "total_points", "total_throws", "total_cost_eur", "joined_at"]


# ---------- Utility Functions ----------

def ensure_files():
    global _files_ensured
    if _files_ensured:
        return

    # Source files — must exist (shipped with the app)
    missing = [f for f in REQUIRED_SRC_FILES if not os.path.exists(f)]
    if missing:
        names = "\n  ".join(missing)
        raise FileNotFoundError(f"Required source files missing:\n  {names}")

    # Data directory + files — created with defaults if absent
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MEMBERS_DATA):
        with open(MEMBERS_DATA, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["id", "name", "games", "total_points", "total_throws", "total_cost_eur", "joined_at"])
    if not os.path.exists(PW_FILE):
        with open(PW_FILE, "w", encoding="utf-8") as f:
            f.write("admin")

    # Rules are user-editable content — create placeholder if missing
    if not os.path.exists(RULES_HTML):
        with open(RULES_HTML, "w", encoding="utf-8") as f:
            f.write("<h3>Regeln</h3><p>Platzhalter.</p>")

    _files_ensured = True


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def render_page(body_template: str, title_suffix: str, active: str, **ctx) -> str:
    """Render a page body into the base layout. Handles CSS/base-HTML loading once."""
    body_html = render_template_string(body_template, **ctx)
    base_html = read_file(BASE_HTML)
    base_css = read_file(BASE_CSS)
    return render_template_string(
        base_html,
        css=base_css,
        title=f"{APP_TITLE} — {title_suffix}",
        app_title=APP_TITLE,
        active=active,
        body=body_html,
    )


def read_members():
    members = []
    with open(MEMBERS_DATA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["games"] = int(row.get("games", 0) or 0)
            row["total_points"] = int(row.get("total_points", 0) or 0)
            row["total_throws"] = int(row.get("total_throws", 0) or 0)
            row["total_cost_eur"] = float(row.get("total_cost_eur", 0) or 0)
            if not row.get("joined_at"):
                row["joined_at"] = datetime.now().strftime("%Y-%m-%d")
            members.append(row)
    return members


def write_members(members: list[dict]):
    with open(MEMBERS_DATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MEMBER_FIELDS)
        writer.writeheader()
        for m in members:
            writer.writerow({k: m.get(k) for k in MEMBER_FIELDS})


def new_member_id(members: list[dict]) -> str:
    existing = {int(m["id"]) for m in members} if members else set()
    i = 1
    while i in existing:
        i += 1
    return str(i)


def check_pw(pw: str) -> bool:
    try:
        with open(PW_FILE, encoding="utf-8") as f:
            return pw == f.read().strip()
    except FileNotFoundError:
        return False


def get_display_name(full_name: str) -> str:
    """'Name [Nick]' -> 'Nick', otherwise full name."""
    match = re.search(r'\[(.*?)\]', full_name)
    return match.group(1).strip() if match else full_name


def save_temp_game(players, throws_per_player, price_standing, price_miss, mode):
    with open(TEMP_GAME_DATA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["player_id", "name", "throws", "points", "cost_eur",
                     "remaining", "throws_per_player", "price_per_standing_pin_eur",
                     "price_per_miss_eur", "mode", "saved_at"])
        ts = datetime.now().isoformat(timespec="seconds")
        for p in players:
            w.writerow([
                p["id"],
                p["name"],
                " ".join(str(x) for x in p["throws"]),
                p["points"],
                f"{p['cost']:.2f}",
                p.get("remaining", 9),
                throws_per_player,
                price_standing,
                price_miss,
                mode,
                ts,
            ])


def load_temp_game():
    if not os.path.exists(TEMP_GAME_DATA):
        return None
    try:
        with open(TEMP_GAME_DATA, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        first = rows[0]
        game_data = {
            "players": [],
            "throwsPerPlayer": int(first.get("throws_per_player") or 3),
            "priceStanding": float(first.get("price_per_standing_pin_eur") or 0.0),
            "priceMiss": float(first.get("price_per_miss_eur") or 0.0),
            "mode": first.get("mode") or "VOLLE",
        }
        for row in rows:
            throws_str = row.get("throws", "").strip()
            game_data["players"].append({
                "id": row["player_id"],
                "name": row["name"],
                "throws": [int(x) for x in throws_str.split()] if throws_str else [],
                "points": int(row.get("points") or 0),
                "cost": float(row.get("cost_eur") or 0.0),
                "remaining": int(row.get("remaining") or 9),
            })
        return game_data
    except Exception as e:
        print(f"Error loading temp game: {e}")
        return None


def clear_temp_game():
    if os.path.exists(TEMP_GAME_DATA):
        os.remove(TEMP_GAME_DATA)


# ---------- App ----------

app = Flask(__name__)


# ---------- Hooks ----------

@app.before_request
def _before_request():
    ensure_files()


# ---------- Routes ----------

@app.route("/")
def home():
    return render_page(read_file(HOME_HTML), "Start", "home")


@app.route("/club")
def club():
    members = read_members()
    return render_page(read_file(CLUB_HTML), "Club", "club", members=members)


@app.route("/stats")
def stats():
    members = read_members()
    members.sort(key=lambda m: m["total_points"], reverse=True)
    return render_page(read_file(STATS_HTML), "Statistiken", "stats", members=members)


@app.route("/scoreboard")
def scoreboard():
    members = read_members()
    for m in members:
        m["display_name"] = get_display_name(m["name"])

    restored_game = load_temp_game()
    if restored_game:
        nickname_map = {m["id"]: m["display_name"] for m in members}
        for p in restored_game["players"]:
            if p["id"] in nickname_map:
                p["name"] = nickname_map[p["id"]]

    return render_page(
        read_file(GAME_HTML), "Strichliste", "score",
        members=members, restored_game=restored_game,
    )


@app.route("/rules")
def rules():
    return render_page(read_file(RULES_HTML), "Regeln", "rules")


@app.route("/admin")
def admin():
    return render_page(read_file(SETTINGS_HTML), "Admin", "admin")


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# ---------- Request Handlers ----------

@app.post("/api/member")
def api_add_member():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name fehlt"}), 400
    members = read_members()
    if any(m["name"].lower() == name.lower() for m in members):
        return jsonify({"error": "Name existiert bereits"}), 400
    members.append({
        "id": new_member_id(members), "name": name,
        "games": 0, "total_points": 0, "total_throws": 0, "total_cost_eur": 0.0,
    })
    write_members(members)
    return jsonify({"ok": True})


@app.delete("/api/member/<id>")
def api_delete_member(id):
    pw = request.args.get("pw", "")
    if not check_pw(pw):
        return jsonify({"error": "Passwort falsch"}), 403
    members = read_members()
    new_members = [m for m in members if m["id"] != id]
    if len(new_members) == len(members):
        return jsonify({"error": "Mitglied nicht gefunden"}), 404
    write_members(new_members)
    return jsonify({"ok": True})


@app.post("/api/password")
def api_change_password():
    data = request.get_json(force=True)
    if not check_pw(data.get("oldPw", "")):
        return jsonify({"error": "Aktuelles Passwort falsch"}), 403
    new_pw = (data.get("newPw") or "").strip()
    if len(new_pw) < 4:
        return jsonify({"error": "Neues Passwort zu kurz (min. 4)"}), 400
    with open(PW_FILE, "w", encoding="utf-8") as f:
        f.write(new_pw)
    return jsonify({"ok": True})


@app.post("/api/update_game")
def api_update_game():
    data = request.get_json(force=True)
    save_temp_game(
        data.get("players", []),
        int(data.get("throwsPerPlayer", 0)),
        float(data.get("priceStanding", 0)),
        float(data.get("priceMiss", 0)),
        data.get("mode", "VOLLE"),
    )
    return jsonify({"ok": True})


@app.post("/api/clear_game")
def api_clear_game():
    clear_temp_game()
    return jsonify({"ok": True})


@app.post("/api/finish_game")
def api_finish_game():
    data = request.get_json(force=True)
    players = data.get("players", [])
    if not players:
        return jsonify({"error": "Keine Spieler"}), 400

    members = read_members()
    if len(members) > 100:
        members = members[:100]
    m_by_id = {m["id"]: m for m in members}
    for p in players:
        m = m_by_id.get(str(p["id"]))
        if m is None:
            continue
        m["games"] += 1
        m["total_points"] += int(p["points"])
        m["total_throws"] += len(p["throws"])
        m["total_cost_eur"] += float(p["cost"])
    write_members(members)
    clear_temp_game()
    return jsonify({"ok": True})


# ---------- Main ----------

if __name__ == "__main__":
    ensure_files()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n➡ Starte {APP_TITLE} lokal auf http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=True)