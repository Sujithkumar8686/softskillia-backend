from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "softskilia_secret_key"
CORS(app, supports_credentials=True)

def get_user_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_progress_db():
    conn = sqlite3.connect('progress.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    with get_user_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

    with get_progress_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                simulation_name TEXT,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required."}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_user_db() as conn:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists."}), 409

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    with get_user_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            session["user_id"] = user["id"]
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/session", methods=["GET"])
def get_session():
    if "username" in session:
        return jsonify({"loggedIn": True, "username": session["username"]})
    return jsonify({"loggedIn": False})

@app.route("/api/progress", methods=["GET"])
def get_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    user_id = session["user_id"]
    with get_progress_db() as conn:
        rows = conn.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,)).fetchall()
        data = [dict(row) for row in rows]
    return jsonify({"success": True, "progress": data})

@app.route("/api/progress", methods=["POST"])
def save_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.json
    simulation = data.get("simulation_name")
    completed = int(data.get("completed", 0))

    with get_progress_db() as conn:
        existing = conn.execute(
            "SELECT * FROM progress WHERE user_id = ? AND simulation_name = ?",
            (session["user_id"], simulation)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE progress SET completed = ? WHERE user_id = ? AND simulation_name = ?",
                (completed, session["user_id"], simulation)
            )
        else:
            conn.execute(
                "INSERT INTO progress (user_id, simulation_name, completed) VALUES (?, ?, ?)",
                (session["user_id"], simulation, completed)
            )

    return jsonify({"success": True})

@app.route("/api/jobs")
def get_jobs():
    jobs = [
        {
            "title": "Frontend Developer",
            "company": "Infosys",
            "location": "Remote",
            "link": "https://www.linkedin.com/jobs/view/000"
        },
        {
            "title": "Python Intern",
            "company": "Zoho",
            "location": "Chennai",
            "link": "https://www.naukri.com/job-listings-python"
        },
        {
            "title": "Business Analyst",
            "company": "Wipro",
            "location": "Bangalore",
            "link": "https://www.linkedin.com/jobs/view/001"
        }
    ]
    return jsonify(jobs)

if __name__ == "__main__":
    import os
    create_tables()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

