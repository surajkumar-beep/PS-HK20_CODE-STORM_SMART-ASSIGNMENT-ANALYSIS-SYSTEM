from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
from db.database import get_connection, hash_password

auth_bp = Blueprint("auth", __name__)

# ---------------- LOGIN ----------------

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        # Hash the password for comparison
        hashed_password = hash_password(password)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, ps_id FROM teachers WHERE email=? AND password=?",
            (email, hashed_password)
        )

        row = cur.fetchone()
        conn.close()

        if row:
            session["teacher_id"] = row[0]
            session["teacher_name"] = row[1]
            session["ps_id"] = row[2]
            return redirect(url_for("index"))

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


# ---------------- REGISTER ----------------

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        ps_id = request.form["ps_id"]
        email = request.form["email"]
        password = request.form["password"]
        
        # Hash the password for storage
        hashed_password = hash_password(password)

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO teachers(ps_id, name, email, password) VALUES(?,?,?,?)",
                (ps_id, name, email, hashed_password)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("auth.login"))

        except sqlite3.IntegrityError as e:
            error_msg = "Registration failed"
            if "ps_id" in str(e):
                error_msg = "PS ID already registered"
            elif "email" in str(e):
                error_msg = "Email already registered"
            return render_template("register.html", error=error_msg)

    return render_template("register.html")


# ---------------- LOGOUT ----------------

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
