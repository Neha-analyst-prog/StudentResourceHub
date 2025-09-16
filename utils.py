import uuid
import hashlib
from datetime import datetime
from db import DB_FILE
import sqlite3

def generate_share_link():
    """Generate a unique shareable link for resources"""
    return str(uuid.uuid4())[:8]

def generate_group_code():
    """Generate a unique code for study groups"""
    return str(uuid.uuid4())[:6].upper()

def create_notification(user_id, message, notification_type, related_id=None, action_url=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO notifications (user_id, message, notification_type, created_date, related_id, action_url) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, message, notification_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), related_id, action_url))
    conn.commit()
    conn.close()

def log_interaction(user_id, resource_id, interaction_type, value=1):
    """Log user interactions for recommendation system"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO user_interactions (user_id, resource_id, interaction_type, interaction_date, interaction_value) VALUES (?, ?, ?, ?, ?)",
              (user_id, resource_id, interaction_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), value))
    conn.commit()
    conn.close()