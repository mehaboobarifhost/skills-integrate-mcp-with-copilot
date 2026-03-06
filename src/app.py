"""High School Management System API with SQLite persistence."""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "school.sqlite"

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'student_viewer',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants > 0),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                UNIQUE(user_id, activity_id)
            );
            """
        )

        existing_activity_count = conn.execute(
            "SELECT COUNT(*) AS count FROM activities"
        ).fetchone()["count"]

        if existing_activity_count > 0:
            return

        conn.execute(
            "INSERT INTO clubs(name, description) VALUES (?, ?)",
            ("General Activities", "Default club for school-wide activities"),
        )
        club_id = conn.execute(
            "SELECT id FROM clubs WHERE name = ?",
            ("General Activities",),
        ).fetchone()["id"]

        for activity_name, activity in SEED_ACTIVITIES.items():
            conn.execute(
                """
                INSERT INTO activities(club_id, name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    club_id,
                    activity_name,
                    activity["description"],
                    activity["schedule"],
                    activity["max_participants"],
                ),
            )
            activity_id = conn.execute(
                "SELECT id FROM activities WHERE name = ?",
                (activity_name,),
            ).fetchone()["id"]

            for email in activity["participants"]:
                conn.execute(
                    "INSERT OR IGNORE INTO users(email, role) VALUES (?, 'student_viewer')",
                    (email,),
                )
                user_id = conn.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()["id"]
                conn.execute(
                    "INSERT OR IGNORE INTO enrollments(user_id, activity_id) VALUES (?, ?)",
                    (user_id, activity_id),
                )


def fetch_activities() -> dict[str, dict[str, object]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                u.email AS participant_email
            FROM activities AS a
            LEFT JOIN enrollments AS e ON e.activity_id = a.id
            LEFT JOIN users AS u ON u.id = e.user_id
            ORDER BY a.name, u.email
            """
        ).fetchall()

    activities: dict[str, dict[str, object]] = {}
    for row in rows:
        name = row["name"]
        if name not in activities:
            activities[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["participant_email"]:
            activities[name]["participants"].append(row["participant_email"])

    return activities


def get_activity_capacity(activity_name: str) -> tuple[int, int]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                a.id AS activity_id,
                a.max_participants,
                COUNT(e.id) AS current_participants
            FROM activities AS a
            LEFT JOIN enrollments AS e ON e.activity_id = a.id
            WHERE a.name = ?
            GROUP BY a.id, a.max_participants
            """,
            (activity_name,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    return row["activity_id"], row["max_participants"] - row["current_participants"]


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return fetch_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    activity_id, slots_remaining = get_activity_capacity(activity_name)
    if slots_remaining <= 0:
        raise HTTPException(status_code=400, detail="Activity is full")

    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(email, role) VALUES (?, 'student_viewer')",
            (email,),
        )
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        try:
            conn.execute(
                "INSERT INTO enrollments(user_id, activity_id) VALUES (?, ?)",
                (user_row["id"], activity_id),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Student is already signed up") from exc

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    activity_id, _ = get_activity_capacity(activity_name)

    with get_connection() as conn:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if user_row is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )

        result = conn.execute(
            "DELETE FROM enrollments WHERE user_id = ? AND activity_id = ?",
            (user_row["id"], activity_id),
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )

    return {"message": f"Unregistered {email} from {activity_name}"}
