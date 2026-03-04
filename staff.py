from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from db import get_db_connection
from datetime import date



staff_bp = Blueprint("staff", __name__, url_prefix="/staff")

@staff_bp.app_context_processor
def inject_staff_user():
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

# --- Dashboard (cards view) ---
@staff_bp.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # All tasks for staff
    cursor.execute("SELECT * FROM tasks WHERE assigned_to=%s ORDER BY deadline ASC", (user_id,))
    tasks = cursor.fetchall()

    # ✅ Add overdue flag
    from datetime import date
    for t in tasks:
        if t["deadline"] and t["status"] != "completed":
            if t["deadline"] < date.today():
                t["is_overdue"] = True
            else:
                t["is_overdue"] = False
        else:
            t["is_overdue"] = False

    # Today’s tasks
    cursor.execute("SELECT * FROM tasks WHERE assigned_to=%s AND DATE(created_at) = CURDATE()", (user_id,))
    today_tasks = cursor.fetchall()

    # Pending
    cursor.execute("SELECT * FROM tasks WHERE assigned_to=%s AND status='pending'", (user_id,))
    pending_tasks = cursor.fetchall()

    # Completed
    cursor.execute("SELECT * FROM tasks WHERE assigned_to=%s AND status='completed'", (user_id,))
    completed_tasks = cursor.fetchall()

    # Overdue (optional: keep DB query for direct list view)
    cursor.execute("""
        SELECT * FROM tasks 
        WHERE assigned_to=%s AND deadline IS NOT NULL AND deadline < CURDATE() AND status!='completed'
    """, (user_id,))
    overdue_tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("staff/dashboard.html",
                           tasks=tasks,
                           today_tasks=today_tasks,
                           pending_tasks=pending_tasks,
                           completed_tasks=completed_tasks,
                           overdue_tasks=overdue_tasks)

# --- My Tasks (table + yearly line graph) ---
@staff_bp.route("/my-tasks")
def my_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    # ✅ Pagination setup
    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    # ✅ Filters
    status = request.args.get("status")
    title = request.args.get("title")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Build query dynamically
    query = "SELECT SQL_CALC_FOUND_ROWS * FROM tasks WHERE assigned_to=%s"
    params = [user_id]

    if status:
        if status == "today":
            query += " AND DATE(created_at) = CURDATE()"
        elif status == "overdue":
            query += " AND deadline IS NOT NULL AND deadline < CURDATE() AND status!='completed'"
        else:
            query += " AND status=%s"
            params.append(status)

    if title:
        query += " AND title LIKE %s"
        params.append(f"%{title}%")

    query += " ORDER BY deadline ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cursor.execute(query, tuple(params))
    tasks = cursor.fetchall()

    # ✅ Get total count
    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    # ✅ Monthly stats (unchanged)
    cursor.execute("""
        SELECT MONTH(deadline) AS month, COUNT(*) AS total
        FROM tasks
        WHERE assigned_to=%s AND YEAR(deadline)=YEAR(CURDATE())
        GROUP BY MONTH(deadline)
    """, (user_id,))
    total_data = cursor.fetchall()

    cursor.execute("""
        SELECT MONTH(deadline) AS month, COUNT(*) AS completed
        FROM tasks
        WHERE assigned_to=%s AND status='completed' AND YEAR(deadline)=YEAR(CURDATE())
        GROUP BY MONTH(deadline)
    """, (user_id,))
    completed_data = cursor.fetchall()

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    total_counts = [0] * 12
    completed_counts = [0] * 12
    incomplete_counts = [0] * 12

    for row in total_data:
        if row["month"]:
            total_counts[row["month"] - 1] = row["total"]

    for row in completed_data:
        if row["month"]:
            completed_counts[row["month"] - 1] = row["completed"]

    for i in range(12):
        incomplete_counts[i] = total_counts[i] - completed_counts[i]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "staff/my_tasks.html",
        tasks=tasks,
        months=months,
        total_counts=total_counts,
        completed_counts=completed_counts,
        incomplete_counts=incomplete_counts,
        page=page,
        total_pages=total_pages
    )


# --- Task Graph (status overview pie chart) ---
@staff_bp.route("/task-graph")
def task_graph():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Completed count
    cursor.execute("SELECT COUNT(*) AS completed FROM tasks WHERE assigned_to=%s AND status='completed'", (user_id,))
    completed_row = cursor.fetchone()
    completed = completed_row["completed"] if completed_row else 0

    # ✅ Total count
    cursor.execute("SELECT COUNT(*) AS total FROM tasks WHERE assigned_to=%s", (user_id,))
    total_row = cursor.fetchone()
    total = total_row["total"] if total_row else 0

    # ✅ Incomplete = total - completed
    incomplete = total - completed

    # ✅ Overdue count
    cursor.execute("""
        SELECT COUNT(*) AS overdue 
        FROM tasks 
        WHERE assigned_to=%s 
          AND deadline IS NOT NULL 
          AND deadline < CURDATE() 
          AND status!='completed'
    """, (user_id,))
    overdue_row = cursor.fetchone()
    overdue = overdue_row["overdue"] if overdue_row else 0

    # ✅ Yearly stats
    cursor.execute("""
        SELECT MONTH(deadline) AS month, COUNT(*) AS total
        FROM tasks
        WHERE assigned_to=%s AND YEAR(deadline)=YEAR(CURDATE())
        GROUP BY MONTH(deadline)
    """, (user_id,))
    total_data = cursor.fetchall()

    cursor.execute("""
        SELECT MONTH(deadline) AS month, COUNT(*) AS completed
        FROM tasks
        WHERE assigned_to=%s AND status='completed' AND YEAR(deadline)=YEAR(CURDATE())
        GROUP BY MONTH(deadline)
    """, (user_id,))
    completed_data = cursor.fetchall()

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    total_counts = [0] * 12
    completed_counts = [0] * 12
    incomplete_counts = [0] * 12

    for row in total_data:
        if row["month"]:
            total_counts[row["month"] - 1] = row["total"]

    for row in completed_data:
        if row["month"]:
            completed_counts[row["month"] - 1] = row["completed"]

    for i in range(12):
        incomplete_counts[i] = total_counts[i] - completed_counts[i]

    cursor.close()
    conn.close()

    return render_template(
        "staff/task_graph.html",
        completed=completed,
        incomplete=incomplete,
        overdue=overdue,
        months=months,
        total_counts=total_counts,
        completed_counts=completed_counts,
        incomplete_counts=incomplete_counts
    )


# --- Mark Task Complete + Notify Admin ---
@staff_bp.route("/complete-task/<int:id>")
def complete_task(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='completed' WHERE id=%s AND assigned_to=%s", (id, user_id))
    cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, "Task completed"))
    conn.commit()
    cursor.close()
    conn.close()

    flash("✅ Task marked as completed", "success")
    return redirect(url_for("staff.dashboard"))


@staff_bp.route("/task/<int:id>")
def task_detail(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id=%s", (id,))
    task = cursor.fetchone()
    cursor.close()
    conn.close()

    if not task:
        abort(404)

    return render_template("staff/task_detail.html", task=task)

@staff_bp.route("/tasks/today")
def today_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    # ✅ Pagination setup
    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Fetch tasks created today for this staff with pagination
    cursor.execute("""
        SELECT SQL_CALC_FOUND_ROWS * 
        FROM tasks 
        WHERE assigned_to=%s AND DATE(created_at) = CURDATE()
        ORDER BY deadline ASC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    tasks = cursor.fetchall()

    # ✅ Get total count
    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("staff/task_list.html",
                           tasks=tasks,
                           title="Today’s Tasks",
                           page=page,
                           total_pages=total_pages)


@staff_bp.route("/tasks/pending")
def pending_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT SQL_CALC_FOUND_ROWS * 
        FROM tasks 
        WHERE assigned_to=%s AND status='pending'
        ORDER BY deadline ASC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("staff/task_list.html",
                           tasks=tasks,
                           title="Pending Tasks",
                           page=page,
                           total_pages=total_pages)


@staff_bp.route("/tasks/overdue")
def overdue_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Show all overdue tasks (deadline passed, not completed)
    cursor.execute("""
        SELECT SQL_CALC_FOUND_ROWS * 
        FROM tasks 
        WHERE assigned_to=%s 
          AND deadline IS NOT NULL 
          AND deadline < CURDATE() 
          AND status!='completed'
        ORDER BY deadline ASC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("staff/task_list.html",
                           tasks=tasks,
                           title="Overdue Tasks",
                           page=page,
                           total_pages=total_pages)

@staff_bp.route("/tasks/completed")
def completed_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT SQL_CALC_FOUND_ROWS * 
        FROM tasks 
        WHERE assigned_to=%s AND status='completed'
        ORDER BY deadline DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    tasks = cursor.fetchall()

    cursor.execute("SELECT FOUND_ROWS() AS total")
    total = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("staff/task_list.html",
                           tasks=tasks,
                           title="Completed Tasks",
                           page=page,
                           total_pages=total_pages)


@staff_bp.route("/create-task", methods=["GET","POST"])
def create_task():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        staff_ids = request.form.getlist("assigned_to")
        due_date = request.form["due_date"]
        created_by = user_id  # ✅ track who created

        for staff_id in staff_ids:
            cursor.execute("""
                INSERT INTO tasks (title, description, assigned_to, status, deadline, created_at, created_by)
                VALUES (%s, %s, %s, 'pending', %s, NOW(), %s)
            """, (title, description, staff_id, due_date, created_by))

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Task created successfully", "success")
        return redirect(url_for("staff.dashboard"))

    cursor.execute("SELECT * FROM users WHERE role='staff' AND is_active=1")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("staff/tasks.html", staff_list=staff_list)


@staff_bp.route("/profile", endpoint="profile")
def staff_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role, is_active, profile_pic FROM users WHERE id=%s", (user_id,))
    staff = cursor.fetchone()   # ✅ use staff here
    cursor.close()
    conn.close()

    if not staff:
        abort(404)

    return render_template("staff/profile.html", user=staff)

import os
from flask import current_app

@staff_bp.route("/edit_profile", methods=["GET", "POST"], endpoint="edit_profile")
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

        return redirect(url_for("staff.profile"))

    # GET → show form
    cursor.execute("SELECT id, name, email, profile_pic FROM users WHERE id=%s", (user_id,))
    staff = cursor.fetchone()   # ✅ use staff here
    cursor.close()
    conn.close()

    return render_template("staff/edit_profile.html", user=staff)
