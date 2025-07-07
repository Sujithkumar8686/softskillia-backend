from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.secret_key = "softskilia_secret_key"
CORS(app, supports_credentials=True)

DATABASE_URL = os.environ.get("DATABASE_URL")  # Render injects this

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def create_tables():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                simulation_name TEXT,
                completed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required."}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
            conn.commit()
        return jsonify({"success": True})
    except psycopg2.errors.UniqueViolation:
        return jsonify({"success": False, "message": "Username already exists."}), 409
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
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
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM progress WHERE user_id = %s", (user_id,))
        data = cur.fetchall()
    return jsonify({"success": True, "progress": data})

@app.route("/api/progress", methods=["POST"])
def save_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.json
    simulation = data.get("simulation_name")
    completed = int(data.get("completed", 0))

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM progress WHERE user_id = %s AND simulation_name = %s",
            (session["user_id"], simulation)
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                "UPDATE progress SET completed = %s WHERE user_id = %s AND simulation_name = %s",
                (completed, session["user_id"], simulation)
            )
        else:
            cur.execute(
                "INSERT INTO progress (user_id, simulation_name, completed) VALUES (%s, %s, %s)",
                (session["user_id"], simulation, completed)
            )
        conn.commit()

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
    create_tables()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
