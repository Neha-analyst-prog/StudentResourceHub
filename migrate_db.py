import sqlite3
from db import DB_FILE

def migrate_database():
    """Migrate database to ensure all required columns exist"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print("Starting database migration...")
    
    try:
        # Check if user_type column exists in users table
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        if "user_type" not in columns:
            print("Adding user_type column to users table...")
            c.execute("ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT 'student'")
            print("✅ user_type column added")
        else:
            print("✅ user_type column already exists")
        
        # Ensure all other necessary columns exist
        missing_columns = []
        expected_columns = {
            "full_name": "TEXT",
            "email": "TEXT", 
            "last_active": "TEXT",
            "study_streak": "INTEGER DEFAULT 0",
            "total_study_hours": "INTEGER DEFAULT 0"
        }
        
        for col_name, col_type in expected_columns.items():
            if col_name not in columns:
                missing_columns.append((col_name, col_type))
        
        for col_name, col_type in missing_columns:
            print(f"Adding {col_name} column to users table...")
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ {col_name} column added")
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()