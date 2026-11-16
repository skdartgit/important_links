import os
import secrets
import sqlite3
from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__, instance_path=INSTANCE_DIR)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or
        open(os.path.join(INSTANCE_DIR, "secret_key.txt"), "a+").read().strip()
        or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    MAX_CONTENT_LENGTH=2 * 1024 * 1024
)

# Persist the secret key across application restarts.
secret_file = os.path.join(INSTANCE_DIR, "secret_key.txt")
if not os.path.exists(secret_file) or os.path.getsize(secret_file) == 0:
    with open(secret_file, "w") as f:
        f.write(app.config["SECRET_KEY"])

DATABASE = os.path.join(INSTANCE_DIR, "important_links.db")


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_name TEXT NOT NULL,
                purpose TEXT NOT NULL,
                website_url TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        admin = db.execute(
            "SELECT id FROM admins WHERE id = 1"
        ).fetchone()

        if admin is None:
            db.execute(
                "INSERT INTO admins (id, username, password_hash) VALUES (?, ?, ?)",
                (1, "admin", generate_password_hash("12345"))
            )


init_db()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def inject_globals():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        submitted = (
            request.form.get("csrf_token")
            or (request.get_json(silent=True) or {}).get("csrf_token")
        )
        expected = session.get("csrf_token")
        if not expected or not submitted or not secrets.compare_digest(
            str(expected), str(submitted)
        ):
            abort(400, description="Invalid or expired security token. Refresh the page.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin area.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def valid_url(value):
    try:
        parsed = urlsplit(value.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


@app.route("/")
def home():
    with get_db() as db:
        links = db.execute(
            "SELECT * FROM links ORDER BY position ASC, id ASC"
        ).fetchall()

    return render_template("home.html", links=links)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            admin = db.execute(
                "SELECT * FROM admins WHERE id = 1"
            ).fetchone()

        if admin and secrets.compare_digest(username, admin["username"]) \
                and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_logged_in"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            flash("Welcome! You are successfully logged in.", "success")
            return redirect(url_for("dashboard"))

        flash("Incorrect username or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@admin_required
def dashboard():
    with get_db() as db:
        links = db.execute(
            "SELECT * FROM links ORDER BY position ASC, id ASC"
        ).fetchall()

    return render_template("dashboard.html", links=links)


@app.route("/add", methods=["GET", "POST"])
@admin_required
def add_link():
    if request.method == "POST":
        name = request.form.get("website_name", "").strip()
        purpose = request.form.get("purpose", "").strip()
        website_url = request.form.get("website_url", "").strip()

        if not name or not purpose or not website_url:
            flash("Please fill in all three fields.", "warning")
        elif len(name) > 150 or len(purpose) > 500 or len(website_url) > 2048:
            flash("One or more fields exceed the allowed length.", "warning")
        elif not valid_url(website_url):
            flash("Enter a valid website URL beginning with https:// or http://.", "warning")
        else:
            with get_db() as db:
                position = db.execute(
                    "SELECT COALESCE(MAX(position), -1) + 1 FROM links"
                ).fetchone()[0]

                db.execute("""
                    INSERT INTO links
                    (website_name, purpose, website_url, position)
                    VALUES (?, ?, ?, ?)
                """, (name, purpose, website_url, position))

            flash("Website link added successfully.", "success")
            return redirect(url_for("dashboard"))

    return render_template("link_form.html", link=None, page_title="Add New Link")


@app.route("/edit/<int:link_id>", methods=["GET", "POST"])
@admin_required
def edit_link(link_id):
    with get_db() as db:
        link = db.execute(
            "SELECT * FROM links WHERE id = ?", (link_id,)
        ).fetchone()

    if link is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("website_name", "").strip()
        purpose = request.form.get("purpose", "").strip()
        website_url = request.form.get("website_url", "").strip()

        if not name or not purpose or not website_url:
            flash("Please fill in all three fields.", "warning")
        elif len(name) > 150 or len(purpose) > 500 or len(website_url) > 2048:
            flash("One or more fields exceed the allowed length.", "warning")
        elif not valid_url(website_url):
            flash("Enter a valid URL beginning with https:// or http://.", "warning")
        else:
            with get_db() as db:
                db.execute("""
                    UPDATE links
                    SET website_name = ?, purpose = ?, website_url = ?
                    WHERE id = ?
                """, (name, purpose, website_url, link_id))

            flash("Website link updated successfully.", "success")
            return redirect(url_for("dashboard"))

    return render_template(
        "link_form.html", link=link, page_title="Edit Website Link"
    )


@app.route("/delete/<int:link_id>", methods=["POST"])
@admin_required
def delete_link(link_id):
    with get_db() as db:
        db.execute("DELETE FROM links WHERE id = ?", (link_id,))
        db.execute("""
            UPDATE links SET position = (
                SELECT COUNT(*) FROM links AS other
                WHERE other.position < links.position
            )
        """)

    flash("Website link deleted successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reorder", methods=["POST"])
@admin_required
def reorder_links():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids")

    if not isinstance(ids, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in ids
    ):
        return jsonify(success=False, message="Invalid order data."), 400

    with get_db() as db:
        existing = [
            row["id"] for row in db.execute(
                "SELECT id FROM links ORDER BY id"
            ).fetchall()
        ]

        if len(ids) != len(set(ids)) or set(ids) != set(existing):
            return jsonify(success=False, message="The link list has changed. Refresh and try again."), 400

        db.executemany(
            "UPDATE links SET position = ? WHERE id = ?",
            [(position, link_id) for position, link_id in enumerate(ids)]
        )

    return jsonify(success=True, message="New order saved.")


@app.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or len(username) > 80:
            flash("Enter a valid username (maximum 80 characters).", "warning")
        elif len(new_password) < 5:
            flash("New password must contain at least 5 characters.", "warning")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        else:
            with get_db() as db:
                admin = db.execute(
                    "SELECT * FROM admins WHERE id = 1"
                ).fetchone()

                if not check_password_hash(
                    admin["password_hash"], current_password
                ):
                    flash("Your current password is incorrect.", "danger")
                else:
                    try:
                        db.execute("""
                            UPDATE admins
                            SET username = ?, password_hash = ?
                            WHERE id = 1
                        """, (
                            username,
                            generate_password_hash(new_password)
                        ))
                        flash("Admin credentials updated successfully.", "success")
                        return redirect(url_for("settings"))
                    except sqlite3.IntegrityError:
                        flash("That username is already in use.", "warning")

    with get_db() as db:
        admin = db.execute(
            "SELECT username FROM admins WHERE id = 1"
        ).fetchone()

    return render_template("settings.html", admin=admin)


@app.errorhandler(400)
def bad_request(error):
    return render_template(
        "error.html", code=400,
        message=getattr(error, "description", "Bad request.")
    ), 400


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html", code=404,
        message="The requested page or link was not found."
    ), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
