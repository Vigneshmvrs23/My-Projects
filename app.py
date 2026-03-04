from flask import Flask, session, redirect, url_for
from auth import auth_bp
from admin import admin_bp
from staff import staff_bp   # 👈 new staff blueprint
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(staff_bp)

# Home route
@app.route("/")
def home():
    role = session.get("role")

    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    elif role == "staff":
        return redirect(url_for("staff.dashboard"))

    return redirect(url_for("auth.login"))

# Optional global logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return "Page Not Found", 404

if __name__ == "__main__":
    app.run(debug=True)
