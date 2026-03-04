from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# --- LOGIN ---
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            if not user["is_active"]:
                flash("⛔ Account not approved by Admin yet", "error")
                return redirect(url_for("auth.login"))

            # Save session
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]

            flash("✅ Login successful", "success")

            # Redirect by role
            if user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user["role"] == "owner":
                return redirect(url_for("owners.dashboard"))
            elif user["role"] == "user":
                return redirect(url_for("users.dashboard"))
            elif user["role"] == "staff":   # 🔥 Added staff redirect
                return redirect(url_for("staff.dashboard"))
        else:
            flash("Invalid credentials", "error")

    return render_template("auth/login.html")


# --- REGISTER ---
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]  # must be 'admin', 'owner', or 'user'
        city = request.form.get("city")
        area = request.form.get("area")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (name,email,password,role,city,area,is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (name, email, password, role, city, area, 0))
            conn.commit()
            flash("✅ Account created! Wait for admin approval.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Error: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("auth/register.html")


# --- FORGOT PASSWORD ---
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        new_password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Password reset successful", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")
