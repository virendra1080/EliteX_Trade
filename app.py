from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from werkzeug.security import check_password_hash, generate_password_hash
import json, os, functools
from datetime import datetime

app = Flask(__name__)
app.secret_key = "elitex_trade_2025_secret"
app.jinja_env.globals.update(enumerate=enumerate, zip=zip, len=len, range=range)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "data.json")

def load():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def safe_user(u):
    return {k: v for k, v in u.items() if k not in ("password_hash",)}

# ── Auth decorators ──────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    d = load()
    for u in d.get("users", []):
        if u["id"] == session["user_id"]:
            return safe_user(u)
    return None

def _set_session(user):
    session["user_id"]  = user["id"]
    session["username"] = user.get("username", "")
    session["role"]     = user["role"]
    session["name"]     = user["name"]

# ── Public pages ─────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", d=load(), current_user=get_current_user())

@app.route("/about")
def about():
    return render_template("about.html", d=load(), current_user=get_current_user())

@app.route("/pricing")
def pricing():
    return render_template("pricing.html", d=load(), current_user=get_current_user())

@app.route("/contact", methods=["GET","POST"])
def contact():
    d = load()
    if request.method == "POST":
        name    = request.form.get("name","").strip()
        email   = request.form.get("email","").strip()
        message = request.form.get("message","").strip()
        if not all([name, email, message]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("contact"))
        d["contact_submissions"].append({
            "id": len(d["contact_submissions"])+1,
            "name": name, "email": email, "message": message,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        save(d)
        flash("Message sent! We'll reply within 24 hours.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html", d=d, current_user=get_current_user())

@app.route("/apply", methods=["GET","POST"])
def apply():
    d = load()
    if request.method == "POST":
        name  = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        if not all([name, email, phone]):
            flash("Please fill in Name, Email and Phone.", "danger")
            return redirect(url_for("apply"))
        d["applications"].append({
            "id": len(d["applications"])+1,
            "name": name, "email": email, "phone": phone,
            "plan": request.form.get("plan","").strip(),
            "experience": request.form.get("experience","").strip(),
            "capital": request.form.get("capital","").strip(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "pending",
        })
        save(d)
        flash("Application received! Our team will contact you within 24 hours.", "success")
        return redirect(url_for("apply"))
    return render_template("apply.html", d=d, current_user=get_current_user())

@app.route("/free-trial", methods=["POST"])
def free_trial():
    d = load()
    email = request.form.get("email","").strip()
    phone = request.form.get("phone","").strip()
    if not email or not phone:
        flash("Please enter your email and phone number.", "danger")
        return redirect(url_for("index")+"#trial")
    d["trial_submissions"].append({
        "id": len(d["trial_submissions"])+1,
        "name":  request.form.get("name","").strip(),
        "email": email, "phone": phone,
        "date":  datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save(d)
    flash("14-day trial activated! Check your email for setup instructions.", "success")
    return redirect(url_for("index")+"#trial")

# ── Auth routes ──────────────────────────────────────────────────

@app.route("/login", methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("admin_dashboard") if session.get("role")=="admin" else url_for("user_dashboard"))
    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","").strip()
        d = load()
        # Match by email (case-insensitive)
        user = next((u for u in d.get("users",[]) if u.get("email","").lower()==email), None)
        if user and user.get("password_hash") and check_password_hash(user["password_hash"], password) and user.get("active",True):
            _set_session(user)
            flash(f"Welcome back, {user['name']}!", "success")
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("admin_dashboard") if user["role"]=="admin" else url_for("user_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", d=load(), current_user=None)

@app.route("/logout")
def logout():
    name = session.get("name","")
    session.clear()
    flash(f"You've been logged out. See you soon{', '+name if name else ''}!", "info")
    return redirect(url_for("index"))

@app.route("/register", methods=["GET","POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("user_dashboard"))
    if request.method == "POST":
        name     = request.form.get("name","").strip()
        username = request.form.get("username","").strip()
        email    = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        confirm  = request.form.get("confirm","").strip()
        if not all([name, username, email, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))
        d = load()
        if any(u["username"]==username for u in d.get("users",[])):
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))
        if any(u["email"]==email for u in d.get("users",[])):
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))
        d["users"].append({
            "id":            max((u["id"] for u in d["users"]),default=0)+1,
            "username":      username,
            "password_hash": generate_password_hash(password),
            "email":         email,
            "role":          "user",
            "name":          name,
            "created":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "active":        True,
        })
        save(d)
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", d=load(), current_user=None)

# ── User dashboard ───────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def user_dashboard():
    d = load()
    user = get_current_user()
    my_apps   = [a for a in d["applications"]      if a.get("email","").lower()==user["email"].lower()]
    my_trials = [t for t in d["trial_submissions"] if t.get("email","").lower()==user["email"].lower()]
    return render_template("user_dashboard.html", d=d, current_user=user,
                           my_apps=my_apps, my_trials=my_trials)

# ── Admin routes ─────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_dashboard():
    d = load()
    stats = {
        "total_applications":   len(d["applications"]),
        "pending_applications": len([a for a in d["applications"] if a.get("status")=="pending"]),
        "total_trials":         len(d["trial_submissions"]),
        "total_contacts":       len(d["contact_submissions"]),
        "total_users":          len([u for u in d["users"] if u["role"]=="user"]),
    }
    recent_apps     = sorted(d["applications"],        key=lambda x:x["date"],reverse=True)[:5]
    recent_contacts = sorted(d["contact_submissions"], key=lambda x:x["date"],reverse=True)[:5]
    return render_template("admin/dashboard.html", d=d, current_user=get_current_user(),
                           stats=stats, recent_apps=recent_apps, recent_contacts=recent_contacts)

@app.route("/admin/applications")
@admin_required
def admin_applications():
    d = load()
    return render_template("admin/applications.html", d=d, current_user=get_current_user(),
                           apps=sorted(d["applications"],key=lambda x:x["date"],reverse=True))

@app.route("/admin/applications/<int:app_id>/status", methods=["POST"])
@admin_required
def admin_update_status(app_id):
    d = load()
    status = request.form.get("status","pending")
    for a in d["applications"]:
        if a["id"]==app_id:
            a["status"]=status; break
    save(d)
    flash(f"Application #{app_id} updated to '{status}'.", "success")
    return redirect(url_for("admin_applications"))

@app.route("/admin/trials")
@admin_required
def admin_trials():
    d = load()
    return render_template("admin/trials.html", d=d, current_user=get_current_user(),
                           trials=sorted(d["trial_submissions"],key=lambda x:x["date"],reverse=True))

@app.route("/admin/contacts")
@admin_required
def admin_contacts():
    d = load()
    return render_template("admin/contacts.html", d=d, current_user=get_current_user(),
                           contacts=sorted(d["contact_submissions"],key=lambda x:x["date"],reverse=True))

@app.route("/admin/users")
@admin_required
def admin_users():
    d = load()
    return render_template("admin/users.html", d=d, current_user=get_current_user(),
                           users=[safe_user(u) for u in d["users"]])

@app.route("/admin/users/<int:uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(uid):
    d = load()
    for u in d["users"]:
        if u["id"]==uid and u["role"]!="admin":
            u["active"] = not u.get("active",True); break
    save(d)
    flash("User status updated.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_add_user():
    d = load()
    name=request.form.get("name","").strip(); username=request.form.get("username","").strip()
    email=request.form.get("email","").strip(); password=request.form.get("password","").strip()
    if not all([name,username,email,password]):
        flash("All fields required.","danger"); return redirect(url_for("admin_users"))
    if len(password)<6:
        flash("Password must be at least 6 characters.","danger"); return redirect(url_for("admin_users"))
    if any(u["username"]==username for u in d["users"]):
        flash("Username already exists.","danger"); return redirect(url_for("admin_users"))
    if any(u["email"]==email for u in d["users"]):
        flash("Email already registered.","danger"); return redirect(url_for("admin_users"))
    d["users"].append({
        "id":max((u["id"] for u in d["users"]),default=0)+1,
        "username":username,"password_hash":generate_password_hash(password),
        "email":email,"role":"user","name":name,
        "created":datetime.now().strftime("%Y-%m-%d %H:%M"),"active":True,
    })
    save(d); flash(f"User '{username}' created.","success")
    return redirect(url_for("admin_users"))

@app.route("/admin/applications/<int:app_id>/delete", methods=["POST"])
@admin_required
def admin_delete_application(app_id):
    d = load()
    d["applications"]=[a for a in d["applications"] if a["id"]!=app_id]
    save(d); flash(f"Application #{app_id} deleted.","success")
    return redirect(url_for("admin_applications"))

@app.route("/admin/contacts/<int:cid>/delete", methods=["POST"])
@admin_required
def admin_delete_contact(cid):
    d = load()
    d["contact_submissions"]=[c for c in d["contact_submissions"] if c["id"]!=cid]
    save(d); flash(f"Message #{cid} deleted.","success")
    return redirect(url_for("admin_contacts"))

# ── API ──────────────────────────────────────────────────────────

@app.route("/api/plans")
def api_plans():
    return jsonify(load()["plans"])

@app.route("/api/stats")
def api_stats():
    return jsonify(load()["why_section"]["stats"])

# ── 404 ──────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", d=load(), current_user=get_current_user()), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
