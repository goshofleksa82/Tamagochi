from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import random
import sqlite3
import time
from urllib.parse import urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DB_PATH = os.path.join(BASE_DIR, "tamagotchi.db")

MAX_STAT = 100
MIN_STAT = 0
TICK_SECONDS = 30

PET_SPECIES = ("cat", "dog", "bunny", "bear", "fox")
PET_COLORS = ("#f5c46b", "#f08f6f", "#8bc6a8", "#9fb7e8", "#d99adf", "#c49a6c")
PET_ACCENTS = ("#fff3cc", "#f7d7c4", "#d8f0df", "#e1e8ff", "#f4d8f5", "#ead6bc")


def clamp(value):
    return max(MIN_STAT, min(MAX_STAT, int(value)))


def should_end(hunger, happiness, energy, cleanliness):
    return min(hunger, happiness, energy, cleanliness) <= 0


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                hunger INTEGER NOT NULL,
                happiness INTEGER NOT NULL,
                energy INTEGER NOT NULL,
                cleanliness INTEGER NOT NULL,
                age_seconds INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_tick_at INTEGER NOT NULL
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(pets)").fetchall()}
        if "species" not in columns:
            conn.execute("ALTER TABLE pets ADD COLUMN species TEXT NOT NULL DEFAULT 'cat'")
        if "body_color" not in columns:
            conn.execute("ALTER TABLE pets ADD COLUMN body_color TEXT NOT NULL DEFAULT '#f5c46b'")
        if "accent_color" not in columns:
            conn.execute("ALTER TABLE pets ADD COLUMN accent_color TEXT NOT NULL DEFAULT '#fff3cc'")
        if "pattern" not in columns:
            conn.execute("ALTER TABLE pets ADD COLUMN pattern TEXT NOT NULL DEFAULT 'spots'")
        if "ended_at" not in columns:
            conn.execute("ALTER TABLE pets ADD COLUMN ended_at INTEGER")


def random_design(previous=None):
    previous = previous or {}
    for _ in range(20):
        design = {
            "species": random.choice(PET_SPECIES),
            "body_color": random.choice(PET_COLORS),
            "accent_color": random.choice(PET_ACCENTS),
            "pattern": random.choice(("spots", "stripe", "blush", "patch")),
        }
        if design != previous:
            return design

    species_index = PET_SPECIES.index(previous.get("species", PET_SPECIES[0]))
    return {
        **previous,
        "species": PET_SPECIES[(species_index + 1) % len(PET_SPECIES)],
    }


def pet_row_to_dict(row):
    if row is None:
        return None

    is_ended = row["ended_at"] is not None
    status = "great"
    if row["hunger"] <= 20 or row["happiness"] <= 20 or row["energy"] <= 20 or row["cleanliness"] <= 20:
        status = "needs-care"
    if row["hunger"] <= 0 or row["happiness"] <= 0 or row["energy"] <= 0 or row["cleanliness"] <= 0:
        status = "critical"
    if is_ended:
        status = "ended"

    return {
        "id": row["id"],
        "name": row["name"],
        "hunger": row["hunger"],
        "happiness": row["happiness"],
        "energy": row["energy"],
        "cleanliness": row["cleanliness"],
        "ageSeconds": row["age_seconds"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "lastTickAt": row["last_tick_at"],
        "endedAt": row["ended_at"],
        "status": status,
        "isEnded": is_ended,
        "timeFactor": {
            "tickSeconds": TICK_SECONDS,
            "decayPerTick": {
                "hunger": 3,
                "happiness": 2,
                "energy": 2,
                "cleanliness": 2,
            },
        },
        "design": {
            "species": row["species"],
            "bodyColor": row["body_color"],
            "accentColor": row["accent_color"],
            "pattern": row["pattern"],
        },
    }


def tick_pet(conn):
    row = conn.execute("SELECT * FROM pets WHERE id = 1").fetchone()
    if row is None:
        return None
    if row["ended_at"] is not None:
        return row

    now = int(time.time())
    elapsed = max(0, now - row["last_tick_at"])
    tick_count = elapsed // TICK_SECONDS
    if tick_count <= 0:
        return row

    hunger = clamp(row["hunger"] - tick_count * 3)
    happiness = clamp(row["happiness"] - tick_count * 2)
    energy = clamp(row["energy"] - tick_count * 2)
    cleanliness = clamp(row["cleanliness"] - tick_count * 2)
    age_seconds = row["age_seconds"] + elapsed
    ended_at = now if should_end(hunger, happiness, energy, cleanliness) else None

    conn.execute(
        """
        UPDATE pets
        SET hunger = ?, happiness = ?, energy = ?, cleanliness = ?,
            age_seconds = ?, updated_at = ?, last_tick_at = ?, ended_at = ?
        WHERE id = 1
        """,
        (hunger, happiness, energy, cleanliness, age_seconds, now, now, ended_at),
    )
    return conn.execute("SELECT * FROM pets WHERE id = 1").fetchone()


def get_pet():
    with connect_db() as conn:
        return pet_row_to_dict(tick_pet(conn))


def create_pet(name):
    now = int(time.time())
    clean_name = (name or "Pixel").strip()[:24] or "Pixel"
    with connect_db() as conn:
        previous_row = conn.execute("SELECT * FROM pets WHERE id = 1").fetchone()
        previous_design = None
        if previous_row is not None:
            previous_design = {
                "species": previous_row["species"],
                "body_color": previous_row["body_color"],
                "accent_color": previous_row["accent_color"],
                "pattern": previous_row["pattern"],
            }
        design = random_design(previous_design)
        conn.execute("DELETE FROM pets WHERE id = 1")
        conn.execute(
            """
            INSERT INTO pets (
                id, name, hunger, happiness, energy, cleanliness,
                age_seconds, created_at, updated_at, last_tick_at,
                species, body_color, accent_color, pattern, ended_at
            )
            VALUES (1, ?, 80, 80, 80, 80, 0, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                clean_name,
                now,
                now,
                now,
                design["species"],
                design["body_color"],
                design["accent_color"],
                design["pattern"],
            ),
        )
        return pet_row_to_dict(conn.execute("SELECT * FROM pets WHERE id = 1").fetchone())


def update_name(name):
    clean_name = (name or "").strip()[:24]
    if not clean_name:
        raise ValueError("Name is required.")

    with connect_db() as conn:
        tick_pet(conn)
        row = conn.execute("SELECT * FROM pets WHERE id = 1").fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE pets SET name = ?, updated_at = ? WHERE id = 1",
            (clean_name, int(time.time())),
        )
        return pet_row_to_dict(conn.execute("SELECT * FROM pets WHERE id = 1").fetchone())


def apply_action(action):
    effects = {
        "feed": {"hunger": 18, "energy": -4, "cleanliness": -5},
        "play": {"happiness": 18, "energy": -12, "hunger": -6, "cleanliness": -4},
        "sleep": {"energy": 25, "happiness": -3, "hunger": -6},
        "clean": {"cleanliness": 24, "happiness": 4},
    }
    if action not in effects:
        raise ValueError("Unknown action.")

    with connect_db() as conn:
        row = tick_pet(conn)
        if row is None:
            return None
        if row["ended_at"] is not None:
            return pet_row_to_dict(row)

        values = dict(row)
        for stat, delta in effects[action].items():
            values[stat] = clamp(values[stat] + delta)

        now = int(time.time())
        ended_at = now if should_end(
            values["hunger"],
            values["happiness"],
            values["energy"],
            values["cleanliness"],
        ) else None
        conn.execute(
            """
            UPDATE pets
            SET hunger = ?, happiness = ?, energy = ?, cleanliness = ?,
                updated_at = ?, ended_at = ?
            WHERE id = 1
            """,
            (
                values["hunger"],
                values["happiness"],
                values["energy"],
                values["cleanliness"],
                now,
                ended_at,
            ),
        )
        return pet_row_to_dict(conn.execute("SELECT * FROM pets WHERE id = 1").fetchone())


class TamagotchiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self):
        if urlparse(self.path).path == "/api/pet":
            pet = get_pet()
            self.send_json(200, {"pet": pet})
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_json()
            if path == "/api/pet":
                self.send_json(201, {"pet": create_pet(data.get("name"))})
                return
            if path == "/api/pet/name":
                pet = update_name(data.get("name"))
                if pet is None:
                    self.send_json(404, {"error": "Create a pet first."})
                    return
                self.send_json(200, {"pet": pet})
                return
            if path == "/api/action":
                pet = apply_action(data.get("action"))
                if pet is None:
                    self.send_json(404, {"error": "Create a pet first."})
                    return
                self.send_json(200, {"pet": pet})
                return
            self.send_json(404, {"error": "Not found."})
        except (json.JSONDecodeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})


def main():
    init_db()
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), TamagotchiHandler)
    print(f"Tamagotchi running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
