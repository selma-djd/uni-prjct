"""University of Boumerdes - information and announcement management website.

Stack: Python + Flask, Flask-SQLAlchemy, PostgreSQL, Jinja2 templates.
All configuration comes from environment variables (see .env.example), so the
same code runs in Docker (VirtualBox VM) and on Render.
"""
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import click
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def get_database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. See .env.example.")
    # Render gives "postgres://" or "postgresql://". We name the driver (psycopg2)
    # explicitly so the result does not depend on the SQLAlchemy version.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
            break
    return url


def get_secret_key():
    key = os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError("SECRET_KEY is not set. See .env.example.")
    return key


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = get_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)


# --------------------------------------------------------------------------
# Models (database tables)
# --------------------------------------------------------------------------
def now_utc():
    return datetime.now(timezone.utc)


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # never the plain password


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)  # short text for cards
    head = db.Column(db.String(100), nullable=False, default="")  # head of department
    email = db.Column(db.String(120), nullable=False, default="")  # contact email
    programs = db.Column(db.Text, nullable=False, default="")  # one programme per line

    @property
    def program_list(self):
        return [line.strip() for line in self.programs.splitlines() if line.strip()]

class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


# --------------------------------------------------------------------------
# Sample data (fictional)
# --------------------------------------------------------------------------
# (name, short description, head, email, programmes)
SAMPLE_DEPARTMENTS = [
    ("Mathematics",
     "Algebra, analysis, probability and statistics, from first-year courses to research.",
     "Prof. Samir Haddad",
     "mathematics@boumerdes-university.example",
     "Bachelor in Mathematics\nBachelor in Applied Mathematics\n"
     "Master in Probability and Statistics\nMaster in Numerical Analysis"),
    ("Physics",
     "Mechanics, electromagnetism, quantum physics and experimental laboratories.",
     "Prof. Leila Mansouri",
     "physics@boumerdes-university.example",
     "Bachelor in Physics\nMaster in Condensed Matter Physics\nMaster in Renewable Energy"),
    ("Chemistry",
     "General, organic and analytical chemistry with practical laboratory training.",
     "Prof. Yacine Boudiaf",
     "chemistry@boumerdes-university.example",
     "Bachelor in Chemistry\nMaster in Analytical Chemistry\nMaster in Organic Chemistry"),
    ("Biology",
     "Cell biology, genetics, microbiology and ecology, with field and lab work.",
     "Prof. Nadia Cherif",
     "biology@boumerdes-university.example",
     "Bachelor in Biology\nMaster in Microbiology\nMaster in Genetics\nMaster in Ecology"),
    ("Agronomy",
     "Plant production, soil science and sustainable farming in semi-arid regions.",
     "Prof. Omar Belkacem",
     "agronomy@boumerdes-university.example",
     "Bachelor in Agronomy\nMaster in Plant Production\nMaster in Soil Science and Irrigation"),
    ("Computer Science",
     "",
     "Prof. Rania Slimani",
     "computer-science@boumerdes-university.example",
     "Bachelor in Computer Science\nMaster in Software Engineering\n"
     "Master in Artificial Intelligence\nMaster in Networks and Cloud Computing"),
]

SAMPLE_ANNOUNCEMENTS = [
    ("Registration for the spring semester is open",
     "Registration for the spring semester is open until the end of the month. "
     "Students must confirm their courses at the administration office or on the "
     "registration desk of their department. Bring your student card and the "
     "payment receipt.", 2),
    ("Mathematics seminar: introduction to probability",
     "The Department of Mathematics invites all students to an open seminar on "
     "probability, held in Lecture Hall B on Thursday at 14:00. Entry is free and "
     "no registration is required.", 5),
    ("Chemistry laboratory safety session",
     "All second-year chemistry students must attend a laboratory safety session "
     "before their first practical work. Sessions are held on Monday and Wednesday "
     "morning in Laboratory 2.", 9),
    ("Agronomy field trip to the experimental farm",
     "A field trip to the experimental farm is organised for first-year agronomy "
     "students. Transport leaves from the main gate at 8:00. Wear suitable "
     "clothing and bring water.", 14),
    ("Library extended opening hours during exams",
     "During the examination period the library will stay open until 20:00 from "
     "Sunday to Thursday. Silent study rooms can be used without reservation.", 20),
    ("Biology department open day",
     "Future students and their families are welcome to visit the Biology "
     "department. Laboratories will be open and teachers will present the "
     "programme and answer questions.", 27),
]


def seed_sample_data():
    """Insert sample data only the first time (when both tables are empty)."""
    if Department.query.count() == 0 and Announcement.query.count() == 0:
        for name, description, head, email, programs in SAMPLE_DEPARTMENTS:
            db.session.add(Department(name=name, description=description, head=head,
                                      email=email, programs=programs))
        for title, content, days_ago in SAMPLE_ANNOUNCEMENTS:
            db.session.add(Announcement(title=title, content=content,
                                        created_at=now_utc() - timedelta(days=days_ago)))
        db.session.commit()


def seed_admin():
    """Create the first administrator. The password is stored only as a hash."""
    if Admin.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            print("WARNING: ADMIN_PASSWORD is not set - no administrator created.")
            return
        db.session.add(Admin(username=username,
                             password_hash=generate_password_hash(password)))
        db.session.commit()


def init_db():
    # The database container may need a few seconds to accept connections.
    for attempt in range(15):
        try:
            db.create_all()
            break
        except OperationalError:
            if attempt == 14:
                raise
            time.sleep(2)
    seed_sample_data()
    seed_admin()


with app.app_context():
    init_db()

# --------------------------------------------------------------------------
# Security helpers: CSRF token + login_required
# --------------------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            abort(400)


@app.context_processor
def inject_user():
    return {"is_admin": "admin_id" in session, "admin_name": session.get("admin_name")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in as administrator.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
@app.route("/")
def index():
    # The home page only shows 3 departments and the 3 latest announcements.
    # The pages /departments and /announcements show everything.
    departments = Department.query.order_by(Department.id).limit(3).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    return render_template("index.html", departments=departments,
                           announcements=announcements)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/departments")
def departments():
    items = Department.query.order_by(Department.id).all()
    return render_template("departments.html", departments=items)


@app.route("/departments/<int:dept_id>")
def department_detail(dept_id):
    dept = db.get_or_404(Department, dept_id)
    return render_template("department_detail.html", department=dept)


@app.route("/announcements")
def announcements():
    items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("announcements.html", announcements=items)


@app.route("/announcements/<int:ann_id>")
def announcement_detail(ann_id):
    ann = db.get_or_404(Announcement, ann_id)
    return render_template("announcement_detail.html", announcement=ann)


# --------------------------------------------------------------------------
# Login / logout
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session.clear()  # new session after login
            session["admin_id"] = admin.id
            session["admin_name"] = admin.username
            flash("You are now logged in as administrator.", "success")
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Administration: departments
# --------------------------------------------------------------------------
DEPARTMENT_FIELDS = ("name", "description", "head", "email", "programs")


def read_department_form():
    return {key: request.form.get(key, "").strip() for key in DEPARTMENT_FIELDS}


def validate_department(form):
    if not form["name"]:
        return "Name is required."
    if len(form["name"]) > 100:
        return "Name must be at most 100 characters."
    if len(form["description"]) > 300:
        return "Short description must be at most 300 characters."
    if len(form["head"]) > 100:
        return "Head of department must be at most 100 characters."
    if len(form["email"]) > 120 or (form["email"] and "@" not in form["email"]):
        return "Contact email is not valid."
    return None


@app.route("/departments/new", methods=["GET", "POST"])
@login_required
def department_new():
    form = {key: "" for key in DEPARTMENT_FIELDS}
    if request.method == "POST":
        form = read_department_form()
        error = validate_department(form)
        if error:
            flash(error, "error")
        else:
            dept = Department(**form)
            db.session.add(dept)
            db.session.commit()
            flash("Department added.", "success")
            return redirect(url_for("department_detail", dept_id=dept.id))
    return render_template("department_form.html", form=form, mode="new")


@app.route("/departments/<int:dept_id>/edit", methods=["GET", "POST"])
@login_required
def department_edit(dept_id):
    dept = db.get_or_404(Department, dept_id)
    form = {key: getattr(dept, key) for key in DEPARTMENT_FIELDS}
    if request.method == "POST":
        form = read_department_form()
        error = validate_department(form)
        if error:
            flash(error, "error")
        else:
            for key in DEPARTMENT_FIELDS:
                setattr(dept, key, form[key])
            db.session.commit()
            flash("Department updated.", "success")
            return redirect(url_for("department_detail", dept_id=dept.id))
    return render_template("department_form.html", form=form, mode="edit", department=dept)


@app.route("/departments/<int:dept_id>/delete", methods=["POST"])
@login_required
def department_delete(dept_id):
    dept = db.get_or_404(Department, dept_id)
    db.session.delete(dept)
    db.session.commit()
    flash("Department deleted.", "success")
    return redirect(url_for("departments"))

# --------------------------------------------------------------------------
# Administration: announcements
# --------------------------------------------------------------------------
def read_announcement_form():
    return {key: request.form.get(key, "").strip() for key in ("title", "content")}


def validate_announcement(form):
    if not form["title"] or not form["content"]:
        return "Title and content are required."
    if len(form["title"]) > 200:
        return "Title must be at most 200 characters."
    return None


@app.route("/announcements/new", methods=["GET", "POST"])
@login_required
def announcement_new():
    form = {"title": "", "content": ""}
    if request.method == "POST":
        form = read_announcement_form()
        error = validate_announcement(form)
        if error:
            flash(error, "error")
        else:
            ann = Announcement(**form)
            db.session.add(ann)
            db.session.commit()
            flash("Announcement added.", "success")
            return redirect(url_for("announcement_detail", ann_id=ann.id))
    return render_template("announcement_form.html", form=form, mode="new")


@app.route("/announcements/<int:ann_id>/edit", methods=["GET", "POST"])
@login_required
def announcement_edit(ann_id):
    ann = db.get_or_404(Announcement, ann_id)
    form = {"title": ann.title, "content": ann.content}
    if request.method == "POST":
        form = read_announcement_form()
        error = validate_announcement(form)
        if error:
            flash(error, "error")
        else:
            ann.title, ann.content = form["title"], form["content"]
            db.session.commit()
            flash("Announcement updated.", "success")
            return redirect(url_for("announcement_detail", ann_id=ann.id))
    return render_template("announcement_form.html", form=form, mode="edit", announcement=ann)


@app.route("/announcements/<int:ann_id>/delete", methods=["POST"])
@login_required
def announcement_delete(ann_id):
    ann = db.get_or_404(Announcement, ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash("Announcement deleted.", "success")
    return redirect(url_for("announcements"))

# --------------------------------------------------------------------------
# Errors and command line
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(400)
def bad_request(_error):
    return render_template("error.html", code=400,
                           message="Invalid request. Go back, reload the page and try again."), 400


@app.cli.command("create-admin")
@click.argument("username")
@click.password_option()
def create_admin(username, password):
    """Create an administrator or reset its password (stored hashed)."""
    admin = Admin.query.filter_by(username=username).first()
    if admin:
        admin.password_hash = generate_password_hash(password)
        click.echo(f"Password updated for '{username}'.")
    else:
        db.session.add(Admin(username=username, password_hash=generate_password_hash(password)))
        click.echo(f"Administrator '{username}' created.")
    db.session.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)