from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from db import get_db_connection
from werkzeug.security import generate_password_hash
from datetime import date
from calendar import monthrange
from datetime import date


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.app_context_processor
def inject_admin_user():
    user_id = session.get("user_id")
    if not user_id:
        return {}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, profile_pic FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return dict(user=user)

# --- Dashboard ---
@admin_bp.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- Staff stats ---
    cursor.execute("SELECT COUNT(*) AS staff_count FROM users WHERE role='staff'")
    staff_count = cursor.fetchone()["staff_count"]

    cursor.execute("SELECT COUNT(*) AS active_staff FROM users WHERE role='staff' AND is_active=1")
    active_staff = cursor.fetchone()["active_staff"]

    cursor.execute("SELECT COUNT(*) AS inactive_staff FROM users WHERE role='staff' AND is_active=0")
    inactive_staff = cursor.fetchone()["inactive_staff"]

    # --- Task stats ---
    cursor.execute("SELECT COUNT(*) AS task_count FROM tasks")
    task_count = cursor.fetchone()["task_count"]

    cursor.execute("SELECT COUNT(*) AS pending_tasks FROM tasks WHERE status='pending'")
    pending_tasks = cursor.fetchone()["pending_tasks"]

    cursor.execute("SELECT COUNT(*) AS completed_tasks FROM tasks WHERE status='completed'")
    completed_tasks = cursor.fetchone()["completed_tasks"]

    # --- Best Performer logic ---
    today = date.today()
    from calendar import monthrange
    first_day = today.replace(day=1)
    last_day = date(today.year, today.month, monthrange(today.year, today.month)[1])

    cursor.execute("""
        SELECT u.id, u.name,
               COUNT(t.id) AS total_tasks,
               SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) AS completed_tasks
        FROM users u
        LEFT JOIN tasks t ON u.id = t.assigned_to
        WHERE u.role='staff' AND t.deadline >= %s AND t.deadline <= %s
        GROUP BY u.id, u.name
    """, (first_day, last_day))

    staff_stats = cursor.fetchall()

    # Calculate stars
    for staff in staff_stats:
        if staff["total_tasks"] > 0:
            completion_rate = staff["completed_tasks"] / staff["total_tasks"]
            if completion_rate == 1:
                staff["stars"] = 5
            elif completion_rate >= 0.8:
                staff["stars"] = 4
            elif completion_rate >= 0.6:
                staff["stars"] = 3
            elif completion_rate >= 0.4:
                staff["stars"] = 2
            elif completion_rate >= 0.2:
                staff["stars"] = 1
            else:
                staff["stars"] = 0
        else:
            staff["stars"] = 0

    # Pick best performer(s)
    max_stars = max([s["stars"] for s in staff_stats]) if staff_stats else 0
    best_performers = [s for s in staff_stats if s["stars"] == max_stars]

    if len(best_performers) > 1:
        max_completed = max([s["completed_tasks"] for s in best_performers])
        best_performers = [s for s in best_performers if s["completed_tasks"] == max_completed]

    cursor.close()
    conn.close()

    return render_template("admin/dashboard.html",
                           staff_count=staff_count,
                           active_staff=active_staff,
                           inactive_staff=inactive_staff,
                           task_count=task_count,
                           pending_tasks=pending_tasks,
                           completed_tasks=completed_tasks,
                           best_performers=best_performers)


# --- Manage Staff (list + activate/deactivate) ---
@admin_bp.route("/manage-staff")
def manage_staff():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE role='staff'")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin/staff.html", staff_list=staff_list)

@admin_bp.route("/create-staff", methods=["GET","POST"])
def create_staff():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        city = request.form.get("city")
        area = request.form.get("area")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (name,email,password,role,city,area,is_active)
                VALUES (%s,%s,%s,'staff',%s,%s,1)
            """, (name, email, password, city, area))
            conn.commit()
            flash("✅ Staff created successfully", "success")
        except Exception as e:
            flash(f"Error: {e}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("admin.manage_staff"))

    return render_template("admin/create_staff.html")

@admin_bp.route("/activate-staff/<int:id>")
def activate_staff(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active=1 WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("✅ Staff activated", "success")
    return redirect(url_for("admin.manage_staff"))

@admin_bp.route("/deactivate-staff/<int:id>")
def deactivate_staff(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active=0 WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("⛔ Staff deactivated", "warning")
    return redirect(url_for("admin.manage_staff"))

# --- Create Task ---
@admin_bp.route("/create-task", methods=["GET","POST"])
def create_task():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        staff_ids = request.form.getlist("assigned_to")
        due_date = request.form["due_date"]   

        # Insert one task per selected staff
        for staff_id in staff_ids:
            cursor.execute("""
                INSERT INTO tasks (title, description, assigned_to, status, deadline, created_at)
                VALUES (%s, %s, %s, 'pending', %s, NOW())
            """, (title, description, staff_id, due_date))

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Task created successfully", "success")
        return redirect(url_for("admin.manage_tasks"))

    cursor.execute("SELECT * FROM users WHERE role='staff' AND is_active=1")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin/tasks.html", staff_list=staff_list)


# --- Manage Tasks ---
@admin_bp.route("/manage-tasks")
def manage_tasks():
    status = request.args.get("status")
    staff = request.args.get("staff")
    title = request.args.get("title")
    page = request.args.get("page", 1, type=int)
    per_page = 7
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Get active staff list
    cursor.execute("SELECT name FROM users WHERE is_active = 1 AND role = 'staff'")
    active_staff = cursor.fetchall()


    query = """
        SELECT SQL_CALC_FOUND_ROWS 
               t.id, t.title, t.description, t.status, DATE(t.deadline) AS deadline,
               u.name AS staff_name,
               c.name AS creator_name, c.role AS creator_role
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        LEFT JOIN users c ON t.created_by = c.id
        WHERE 1=1
    """
    params = []

    if status:
        if status == "today":
            query += " AND DATE(t.created_at) = CURDATE()"
        elif status == "completed":
            query += " AND t.status = 'completed'"
        elif status == "pending":
            query += " AND t.status = 'pending'"
        elif status == "overdue":
            query += " AND DATE(t.deadline) < CURDATE() AND t.status != 'completed'"

    if staff:
        query += " AND u.name = %s"
        params.append(staff)

    if title:
        query += " AND t.title LIKE %s"
        params.append(f"%{title}%")

    query += " ORDER BY t.deadline ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    cursor.execute(query, params)
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template(
        "admin/manage_tasks.html",
        tasks=tasks,
        page=page,
        total_pages=total_pages,
        active_staff=active_staff  # ✅ pass staff list to template
    )


@admin_bp.route("/complete-task/<int:id>")
def complete_task(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='completed' WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("✅ Task marked as completed", "success")
    return redirect(url_for("admin.manage_tasks"))

@admin_bp.route("/delete-task/<int:id>")
def delete_task(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("🗑️ Task deleted", "info")
    return redirect(url_for("admin.manage_tasks"))

@admin_bp.route("/delete-staff/<int:id>")
def delete_staff(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s AND role='staff'", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("✅ Staff deleted successfully", "success")
    return redirect(url_for("admin.manage_staff"))


@admin_bp.route("/tasks")
def all_tasks():
    status = request.args.get("status")
    staff = request.args.get("staff")
    title = request.args.get("title")
    page = request.args.get("page", 1, type=int)
    per_page = 8
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Get only active staff (exclude admins)
    cursor.execute("SELECT name FROM users WHERE is_active = 1 AND role = 'staff'")
    active_staff = cursor.fetchall()

    query = """
        SELECT SQL_CALC_FOUND_ROWS 
               t.id, t.title, t.description, t.status,
               DATE(t.deadline) AS deadline, DATE(t.created_at) AS created_at,
               u.name AS staff_name, u.email AS staff_email,
               c.name AS creator_name, c.role AS creator_role
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        LEFT JOIN users c ON t.created_by = c.id
        WHERE 1=1
    """
    params = []

    if status:
        if status == "today":
            query += " AND DATE(t.created_at) = CURDATE()"
        elif status == "completed":
            query += " AND t.status = 'completed'"
        elif status == "pending":
            query += " AND t.status = 'pending'"
        elif status == "overdue":
            query += " AND DATE(t.deadline) < CURDATE() AND t.status != 'completed'"

    if staff:
        query += " AND u.name = %s"
        params.append(staff)

    if title:
        query += " AND t.title LIKE %s"
        params.append(f"%{title}%")

    query += " ORDER BY t.deadline ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    cursor.execute(query, params)
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template(
        "admin/all_tasks.html",
        tasks=tasks,
        page=page,
        total_pages=total_pages,
        active_staff=active_staff  # ✅ pass staff list to template
    )



# --- Dashboard with 4 boxes ---
@admin_bp.route("/task-dashboard")
def task_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    today = date.today()

    # ✅ Tasks created today
    cursor.execute("""
        SELECT t.id, t.title, t.description, t.deadline, t.status, u.name AS staff_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE DATE(t.created_at) = CURDATE()
        ORDER BY t.created_at DESC
        LIMIT 3
    """)
    today_tasks = cursor.fetchall()

    # ✅ Completed tasks
    cursor.execute("""
        SELECT t.id, t.title, t.description, t.deadline, t.status, u.name AS staff_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.status = 'completed'
        ORDER BY t.created_at DESC
        LIMIT 3
    """)
    completed_tasks = cursor.fetchall()

    # ✅ Pending tasks
    cursor.execute("""
        SELECT t.id, t.title, t.description, t.deadline, t.status, u.name AS staff_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.status = 'pending'
        ORDER BY t.created_at DESC
        LIMIT 3
    """)
    pending_tasks = cursor.fetchall()

    # ✅ Overdue tasks (here we DO need a parameter)
    cursor.execute("""
        SELECT t.id, t.title, t.description, t.deadline, t.status, u.name AS staff_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.status = 'pending' AND t.deadline < %s
        ORDER BY t.deadline ASC
        LIMIT 3
    """, (today,))
    overdue_tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin/task_dashboard.html",
                           today_tasks=today_tasks,
                           completed_tasks=completed_tasks,
                           pending_tasks=pending_tasks,
                           overdue_tasks=overdue_tasks)


@admin_bp.route("/tasks/<category>")
def tasks_by_category(category):
    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    today = date.today()
    query = ""
    params = []

    if category == "today":
        query = """
            SELECT SQL_CALC_FOUND_ROWS t.id, t.title, t.description, DATE(t.deadline) AS deadline, t.status,
                   u.name AS staff_name
            FROM tasks t
            JOIN users u ON t.assigned_to = u.id
            WHERE DATE(t.created_at) = CURDATE()
            ORDER BY t.deadline ASC
            LIMIT %s OFFSET %s
        """
        params = [per_page, offset]

    elif category == "completed":
        query = """
            SELECT SQL_CALC_FOUND_ROWS t.id, t.title, t.description, DATE(t.deadline) AS deadline, t.status,
                   u.name AS staff_name
            FROM tasks t
            JOIN users u ON t.assigned_to = u.id
            WHERE t.status = 'completed'
            ORDER BY t.deadline ASC
            LIMIT %s OFFSET %s
        """
        params = [per_page, offset]

    elif category == "pending":
        query = """
            SELECT SQL_CALC_FOUND_ROWS t.id, t.title, t.description, DATE(t.deadline) AS deadline, t.status,
                   u.name AS staff_name
            FROM tasks t
            JOIN users u ON t.assigned_to = u.id
            WHERE t.status = 'pending'
            ORDER BY t.deadline ASC
            LIMIT %s OFFSET %s
        """
        params = [per_page, offset]

    elif category == "overdue":
        query = """
            SELECT SQL_CALC_FOUND_ROWS t.id, t.title, t.description, DATE(t.deadline) AS deadline, t.status,
                   u.name AS staff_name
            FROM tasks t
            JOIN users u ON t.assigned_to = u.id
            WHERE t.status = 'pending' AND t.deadline < %s
            ORDER BY t.deadline ASC
            LIMIT %s OFFSET %s
        """
        params = [today, per_page, offset]

    cursor.execute(query, params)
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template("admin/tasks_list.html", tasks=tasks, category=category, page=page, total_pages=total_pages)



# --- Task details ---
@admin_bp.route("/task/<int:id>")
def task_details(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.id, t.title, t.description, t.deadline, t.status,
               u.name AS staff_name, u.email AS staff_email
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.id=%s
    """, (id,))
    task = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("admin/task_details.html", task=task)


@admin_bp.route("/staff-performance")
def staff_performance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Current month range
    today = date.today()
    first_day = today.replace(day=1)
    last_day = date(today.year, today.month, monthrange(today.year, today.month)[1])

    cursor.execute("""
        SELECT u.id, u.name,
               COUNT(t.id) AS total_tasks,
               SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) AS completed_tasks
        FROM users u
        LEFT JOIN tasks t ON u.id = t.assigned_to
        WHERE u.role='staff' AND t.deadline >= %s AND t.deadline <= %s
        GROUP BY u.id, u.name
    """, (first_day, last_day))

    staff_stats = cursor.fetchall()

    # Calculate stars based on completion rate
    for staff in staff_stats:
        if staff["total_tasks"] > 0:
            completion_rate = staff["completed_tasks"] / staff["total_tasks"]
            if completion_rate == 1:
                staff["stars"] = 5
            elif completion_rate >= 0.8:
                staff["stars"] = 4
            elif completion_rate >= 0.6:
                staff["stars"] = 3
            elif completion_rate >= 0.4:
                staff["stars"] = 2
            elif completion_rate >= 0.2:
                staff["stars"] = 1
            else:
                staff["stars"] = 0
        else:
            staff["stars"] = 0

    # Best performer logic: stars first, then tie-break by completed tasks
    max_stars = max([s["stars"] for s in staff_stats]) if staff_stats else 0
    best_performers = [s for s in staff_stats if s["stars"] == max_stars]

    if len(best_performers) > 1:
        max_completed = max([s["completed_tasks"] for s in best_performers])
        best_performers = [s for s in best_performers if s["completed_tasks"] == max_completed]

    cursor.close()
    conn.close()

    # Pass month name + year for template header
    month_name = today.strftime("%B")
    return render_template("admin/staff_performance.html",
                           staff_stats=staff_stats,
                           best_performers=best_performers,
                           month_name=month_name,
                           year=today.year)


@admin_bp.route("/edit-staff/<int:id>", methods=["GET", "POST"])
def edit_staff(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        is_active = request.form.get("is_active", 0)

        cursor.execute("""
            UPDATE users
            SET name=%s, email=%s, is_active=%s
            WHERE id=%s AND role='staff'
        """, (name, email, is_active, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("✅ Staff updated successfully", "success")
        return redirect(url_for("admin.manage_staff"))

    cursor.execute("SELECT * FROM users WHERE id=%s AND role='staff'", (id,))
    staff = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("admin/edit_staff.html", staff=staff)


@admin_bp.route("/edit-task/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        deadline = request.form["deadline"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE tasks
            SET title=%s, description=%s, deadline=%s, status=%s
            WHERE id=%s
        """, (title, description, deadline, status, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("✅ Task updated successfully", "success")
        return redirect(url_for("admin.manage_tasks"))

    cursor.execute("SELECT * FROM tasks WHERE id=%s", (id,))
    task = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("admin/edit_task.html", task=task)


@admin_bp.route("/profile", endpoint="profile")
def admin_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role, is_active, profile_pic FROM users WHERE id=%s", (user_id,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if not admin:
        abort(404)

    return render_template("admin/profile.html", user=admin)

import os
from flask import current_app

@admin_bp.route("/edit_profile", methods=["GET", "POST"], endpoint="edit_profile")
def edit_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        # Get current profile_pic from DB
        cursor.execute("SELECT profile_pic FROM users WHERE id=%s", (user_id,))
        current_pic = cursor.fetchone()["profile_pic"]

        profile_pic = current_pic  # default to existing

        # Handle file upload only if new file is chosen
        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file and file.filename != "":
                import os
                from flask import current_app
                upload_folder = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)

                filename = f"user_{user_id}_{file.filename}"
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                profile_pic = f"/static/uploads/{filename}"

        # Update DB with new or existing pic
        cursor.execute("""
            UPDATE users SET name=%s, email=%s, profile_pic=%s WHERE id=%s
        """, (name, email, profile_pic, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("admin.profile"))

    # GET → show form
    cursor.execute("SELECT id, name, email, profile_pic FROM users WHERE id=%s", (user_id,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("admin/edit_profile.html", user=admin)
