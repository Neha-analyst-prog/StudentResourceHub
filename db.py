import os
import sqlite3
import bcrypt
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(filename='system.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

DB_FILE = "resources.db"
RESOURCES_DIR = "resources"
VIDEOS_DIR = "videos"
EXPORTS_DIR = "exports"


def get_connection():
    """Create a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initialize the database, directories, and default admin account."""
    try:
        os.makedirs(RESOURCES_DIR, exist_ok=True)
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        os.makedirs(EXPORTS_DIR, exist_ok=True)
    except OSError as e:
        print(f"❌ Failed to create directories: {e}")
        logging.error(f"Failed to create directories: {e}")
        exit(1)

    try:
        conn = get_connection()
        c = conn.cursor()

        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_verified INTEGER DEFAULT 0,
            full_name TEXT,
            email TEXT,
            user_type TEXT DEFAULT 'student',
            join_date TEXT DEFAULT (datetime('now')),
            last_active TEXT,
            study_streak INTEGER DEFAULT 0,
            total_study_hours INTEGER DEFAULT 0
        )''')

        # Categories
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            color TEXT,
            created_by TEXT,
            created_date TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(username) ON DELETE SET NULL
        )''')

        # Resources
        c.execute('''CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category_name TEXT,
            uploaded_by TEXT,
            file_path TEXT,
            file_type TEXT,
            upload_date TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending',
            download_count INTEGER DEFAULT 0,
            file_size INTEGER,
            tags TEXT,
            is_video INTEGER DEFAULT 0,
            video_duration TEXT,
            share_link TEXT,
            difficulty_level TEXT,
            estimated_time TEXT,
            FOREIGN KEY (category_name) REFERENCES categories(name) ON DELETE SET NULL,
            FOREIGN KEY (uploaded_by) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # Reviews
        c.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER,
            reviewer TEXT,
            rating INTEGER,
            comment TEXT,
            review_date TEXT DEFAULT (datetime('now')),
            helpfulness INTEGER DEFAULT 0,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # Favorites
        c.execute('''CREATE TABLE IF NOT EXISTS favorites (
            user_id TEXT,
            resource_id INTEGER,
            added_date TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, resource_id),
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )''')

        # Study groups
        c.execute('''CREATE TABLE IF NOT EXISTS study_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            subject TEXT,
            created_by TEXT,
            created_date TEXT DEFAULT (datetime('now')),
            max_members INTEGER DEFAULT 20,
            is_private INTEGER DEFAULT 0,
            meeting_schedule TEXT,
            group_code TEXT UNIQUE,
            FOREIGN KEY (created_by) REFERENCES users(username) ON DELETE SET NULL
        )''')

        # Group members
        c.execute('''CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            member_username TEXT,
            join_date TEXT DEFAULT (datetime('now')),
            role TEXT DEFAULT 'member',
            is_active INTEGER DEFAULT 1,
            contribution_score INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, member_username),
            FOREIGN KEY (group_id) REFERENCES study_groups(id) ON DELETE CASCADE,
            FOREIGN KEY (member_username) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # Messages
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            message TEXT,
            sent_date TEXT DEFAULT (datetime('now')),
            is_read INTEGER DEFAULT 0,
            message_type TEXT DEFAULT 'direct',
            group_id INTEGER DEFAULT NULL,
            FOREIGN KEY (sender) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (recipient) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES study_groups(id) ON DELETE SET NULL
        )''')

        # Notifications
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            notification_type TEXT,
            is_read INTEGER DEFAULT 0,
            created_date TEXT DEFAULT (datetime('now')),
            related_id INTEGER,
            action_url TEXT,
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # Download history
        c.execute('''CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            resource_id INTEGER,
            download_date TEXT DEFAULT (datetime('now')),
            source TEXT DEFAULT 'direct',
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )''')

        # Study sessions
        c.execute('''CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            resource_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration_minutes INTEGER,
            progress_percentage INTEGER,
            session_type TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )''')

        # Calendar events
        c.execute('''CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT,
            description TEXT,
            start_datetime TEXT,
            end_datetime TEXT,
            event_type TEXT,
            related_id INTEGER,
            reminder_minutes INTEGER DEFAULT 15,
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # Learning progress
        c.execute('''CREATE TABLE IF NOT EXISTS learning_progress (
            user_id TEXT,
            category_name TEXT,
            total_resources INTEGER,
            completed_resources INTEGER,
            total_time_minutes INTEGER,
            last_updated TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, category_name),
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE
        )''')

        # User interactions
        c.execute('''CREATE TABLE IF NOT EXISTS user_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            resource_id INTEGER,
            interaction_type TEXT,
            interaction_date TEXT DEFAULT (datetime('now')),
            interaction_value INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )''')

        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_resources_uploaded_by ON resources(uploaded_by)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_resource_id ON reviews(resource_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)")

        # Insert default admin
        c.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        if c.fetchone() is None:
            admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            c.execute(
                "INSERT INTO users (username, password, role, is_verified, user_type, join_date) VALUES (?, ?, ?, ?, ?, ?)",
                ("admin", admin_password, "admin", 1, "admin",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            print("✅ Default admin account created (username: admin, password: admin123)")
            logging.info("Default admin account created")

        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Database initialization failed: {e}")
        logging.error(f"Database initialization failed: {e}")
        exit(1)
    finally:
        conn.close()


def add_user(username, password, role="user", full_name=None, email=None, user_type="student"):
    """Add a new user to the database with a hashed password."""
    conn = get_connection()
    c = conn.cursor()
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute(
            "INSERT INTO users (username, password, role, is_verified, full_name, email, user_type, join_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, hashed_password, role, 0, full_name, email, user_type,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        logging.info(f"User '{username}' added with role '{role}' and user_type '{user_type}'")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to add user '{username}': Username already exists")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in add_user for '{username}': {e}")
        return False
    finally:
        conn.close()


def validate_user(username, password):
    """Validate user credentials and check if the account is verified."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT password, role FROM users WHERE username=? AND is_verified=1", (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            c.execute("UPDATE users SET last_active = ? WHERE username = ?",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
            conn.commit()
            logging.info(f"User '{username}' validated successfully")
            return result[1]
        logging.warning(f"User '{username}' validation failed: Invalid credentials or unverified")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in validate_user for '{username}': {e}")
        return None
    finally:
        conn.close()
