import logging
from datetime import datetime
from db import DB_FILE
import sqlite3

# Configure logging
logging.basicConfig(filename='system.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def collect_user_details():
    """Collect additional user details for registration."""
    full_name = input("Enter full name: ").strip()
    if not full_name:
        full_name = None
        logging.info("No full name provided during user registration")
    
    email = input("Enter email: ").strip()
    if not email:
        email = None
        logging.info("No email provided during user registration")
    
    user_type = input("Enter user type (student/teacher): ").strip().lower()
    if user_type not in ['student', 'teacher']:
        user_type = 'student'
        logging.warning(f"Invalid user type provided, defaulting to 'student'")
    
    return full_name, email, user_type

def update_user_profile(username, full_name=None, email=None, user_type=None):
    """Update a user's profile information."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        updates = []
        params = []
        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if user_type is not None:
            if user_type not in ['student', 'teacher']:
                user_type = 'student'
                logging.warning(f"Invalid user_type '{user_type}' for user '{username}', defaulting to 'student'")
            updates.append("user_type = ?")
            params.append(user_type)
        
        if updates:
            params.append(username)
            query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
            c.execute(query, params)
            conn.commit()
            print("✅ Profile updated successfully!")
            logging.info(f"Profile updated for user '{username}'")
        else:
            print("❌ No updates provided!")
            logging.warning(f"No updates provided for user '{username}'")
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        logging.error(f"Database error in update_user_profile for '{username}': {e}")
        conn.rollback()
    finally:
        conn.close()