
# import mysql.connector
# from werkzeug.security import generate_password_hash

# def get_db_connection():
#     """Return a new DB connection to hotel_app."""
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="",
#         charset="utf8mb4"
#     )

# def init_db():
#     """Initialize the database schema."""
#     conn = mysql.connector.connect(host="localhost", user="root", password="")
#     cursor = conn.cursor()

#     cursor.execute("CREATE DATABASE IF NOT EXISTS admin_db")
#     cursor.execute("USE admin_db")

#     # --- USERS (Admin, Owner, User) ---
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         name VARCHAR(100) NOT NULL,
#         email VARCHAR(100) UNIQUE NOT NULL,
#         password VARCHAR(255) NOT NULL,
#         role ENUM('admin','owner','user') NOT NULL,
#         city VARCHAR(100),
#         area VARCHAR(100),
#         is_active TINYINT DEFAULT 0,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )
#     """)

#     # --- Default Admin ---
#     admin_email = "imvignesh23@gmail.com"
#     cursor.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
#     if not cursor.fetchone():
#         cursor.execute("""
#             INSERT INTO users (name,email,password,role,is_active)
#             VALUES (%s,%s,%s,%s,%s)
#         """, ("Admin", admin_email, generate_password_hash("admin"), "admin", 1))

#     conn.commit()
#     cursor.close()
#     conn.close()

# # Optional: run directly
# if __name__ == "__main__":
#     init_db()
#     print("hotel_app database initialized successfully ✅")


# import mysql.connector
# from werkzeug.security import generate_password_hash

# def get_db_connection():
#     """Return a new DB connection to admin_db."""
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="",
#         database="admin_db",   # connect directly to our DB
#         charset="utf8mb4"
#     )

# def init_db():
#     """Initialize the database schema for Admin Project (drop + recreate)."""
#     conn = mysql.connector.connect(host="localhost", user="root", password="")
#     cursor = conn.cursor()

#     # --- Create Database ---
#     cursor.execute("CREATE DATABASE IF NOT EXISTS admin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
#     cursor.execute("USE admin_db")

#     # --- Drop old tables to avoid ENUM mismatch ---
#     cursor.execute("DROP TABLE IF EXISTS tasks")
#     cursor.execute("DROP TABLE IF EXISTS users")

#     # --- USERS Table ---
#     cursor.execute("""
#     CREATE TABLE users (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         name VARCHAR(100) NOT NULL,
#         email VARCHAR(100) UNIQUE NOT NULL,
#         password VARCHAR(255) NOT NULL,
#         role ENUM('admin','staff') NOT NULL,
#         city VARCHAR(100),
#         area VARCHAR(100),
#         is_active TINYINT DEFAULT 0,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )
#     """)

#     # --- TASKS Table ---
#     cursor.execute("""
#     CREATE TABLE tasks (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         title VARCHAR(200) NOT NULL,
#         description TEXT,
#         assigned_to INT NOT NULL,
#         status ENUM('pending','completed') DEFAULT 'pending',
#         deadline DATE,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#         FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE CASCADE
#     )
#     """)

#     # --- Default Admin Account ---
#     admin_email = "imvignesh23@gmail.com"
#     cursor.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
#     if not cursor.fetchone():
#         cursor.execute("""
#             INSERT INTO users (name,email,password,role,is_active)
#             VALUES (%s,%s,%s,%s,%s)
#         """, ("Admin", admin_email, generate_password_hash("admin"), "admin", 1))

#     conn.commit()
#     cursor.close()
#     conn.close()

# # Run directly
# if __name__ == "__main__":
#     init_db()
#     print("✅ admin_db dropped and recreated successfully")


# import mysql.connector
# from werkzeug.security import generate_password_hash

# def get_db_connection():
#     """Return a new DB connection to admin_db."""
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="",
#         database="admin_db",
#         charset="utf8mb4"
#     )

# def init_db():
#     """Initialize the database schema for Admin Project (create if not exists)."""
#     conn = mysql.connector.connect(host="localhost", user="root", password="")
#     cursor = conn.cursor()

#     # --- Create Database ---
#     cursor.execute("CREATE DATABASE IF NOT EXISTS admin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
#     cursor.execute("USE admin_db")

#     # --- USERS Table ---
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         name VARCHAR(100) NOT NULL,
#         email VARCHAR(100) UNIQUE NOT NULL,
#         password VARCHAR(255) NOT NULL,
#         role ENUM('admin','staff') NOT NULL,
#         city VARCHAR(100),
#         area VARCHAR(100),
#         is_active TINYINT DEFAULT 0,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )
#     """)

#     # --- TASKS Table ---
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS tasks (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         title VARCHAR(200) NOT NULL,
#         description TEXT,
#         assigned_to INT NOT NULL,
#         status ENUM('pending','completed') DEFAULT 'pending',
#         deadline DATE,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#         FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE CASCADE
#     )
#     """)

#     # --- Notifications Table ---
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS notifications (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         user_id INT NOT NULL,
#         message VARCHAR(255) NOT NULL,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
#     )
#     """)

#     # --- Default Admin Account ---
#     admin_email = "imvignesh23@gmail.com"
#     cursor.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
#     if not cursor.fetchone():
#         cursor.execute("""
#             INSERT INTO users (name,email,password,role,is_active)
#             VALUES (%s,%s,%s,%s,%s)
#         """, ("Admin", admin_email, generate_password_hash("admin"), "admin", 1))

#     # --- Default Staff Account ---
#     staff_email = "staff@example.com"
#     cursor.execute("SELECT id FROM users WHERE email=%s", (staff_email,))
#     if not cursor.fetchone():
#         cursor.execute("""
#             INSERT INTO users (name,email,password,role,is_active)
#             VALUES (%s,%s,%s,%s,%s)
#         """, ("Staff User", staff_email, generate_password_hash("staff123"), "staff", 1))

#     conn.commit()
#     cursor.close()
#     conn.close()

# # Run directly
# if __name__ == "__main__":
#     init_db()
#     print("✅ admin_db initialized successfully (no drop)")


import mysql.connector
from werkzeug.security import generate_password_hash

def get_db_connection():
    """Return a new DB connection to admin_db."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="admin_db",
        charset="utf8mb4"
    )

def init_db():
    """Initialize the database schema for Admin Project (create if not exists)."""
    conn = mysql.connector.connect(host="localhost", user="root", password="")
    cursor = conn.cursor()

    # --- Create Database ---
    cursor.execute("CREATE DATABASE IF NOT EXISTS admin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute("USE admin_db")

    # --- USERS Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        role ENUM('admin','staff') NOT NULL,
        city VARCHAR(100),
        area VARCHAR(100),
        is_active TINYINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # --- TASKS Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        assigned_to INT NOT NULL,
        status ENUM('pending','completed') DEFAULT 'pending',
        deadline DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # ✅ Ensure created_by column exists
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN created_by INT")
        cursor.execute("ALTER TABLE tasks ADD CONSTRAINT fk_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL")
    except mysql.connector.errors.ProgrammingError:
        # Column already exists, ignore
        pass

    # --- Notifications Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        message VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # --- Default Admin Account ---
    admin_email = "imvignesh23@gmail.com"
    cursor.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name,email,password,role,is_active)
            VALUES (%s,%s,%s,%s,%s)
        """, ("Admin", admin_email, generate_password_hash("admin"), "admin", 1))

    # --- Default Staff Account ---
    staff_email = "staff@example.com"
    cursor.execute("SELECT id FROM users WHERE email=%s", (staff_email,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name,email,password,role,is_active)
            VALUES (%s,%s,%s,%s,%s)
        """, ("Staff User", staff_email, generate_password_hash("staff123"), "staff", 1))

    conn.commit()
    cursor.close()
    conn.close()

# Run directly
if __name__ == "__main__":
    init_db()
    print("✅ admin_db initialized successfully (with ALTER check)")
