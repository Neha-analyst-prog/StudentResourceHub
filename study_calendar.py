from datetime import datetime
import sqlite3
from db import DB_FILE

def add_calendar_event(username):
    """Add a new event to the user's study calendar."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Verify user exists
    c.execute("SELECT username FROM users WHERE username = ?", (username,))
    if not c.fetchone():
        print("User not found!")
        conn.close()
        return
    
    title = input("Enter event title (e.g., Study Math Chapter 3): ")
    description = input("Enter event description (optional): ")
    start_datetime = input("Enter start date and time (YYYY-MM-DD HH:MM:SS): ")
    end_datetime = input("Enter end date and time (YYYY-MM-DD HH:MM:SS): ")
    event_type = input("Enter event type (e.g., study_session, deadline): ") or "study_session"
    
    try:
        # Validate datetime format
        datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("Invalid date format! Use YYYY-MM-DD HH:MM:SS (e.g., 2025-09-11 14:00:00)")
        conn.close()
        return
    
    reminder_minutes = input("Enter reminder minutes before event (default 15): ") or 15
    try:
        reminder_minutes = int(reminder_minutes)
        if reminder_minutes < 0:
            print("Reminder minutes must be non-negative!")
            conn.close()
            return
    except ValueError:
        print("Invalid reminder minutes! Using default (15).")
        reminder_minutes = 15
    
    related_id = input("Enter related resource or group ID (optional, press Enter to skip): ")
    related_id = int(related_id) if related_id.isdigit() else None
    
    c.execute("""INSERT INTO calendar_events 
                 (user_id, title, description, start_datetime, end_datetime, event_type, 
                  related_id, reminder_minutes, is_completed) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
              (username, title, description, start_datetime, end_datetime, event_type, 
               related_id, reminder_minutes))
    
    event_id = c.lastrowid
    conn.commit()
    print(f"Event added successfully (ID: {event_id})!")
    conn.close()

def view_calendar_events(username):
    """View all calendar events for the user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("""SELECT id, title, description, start_datetime, end_datetime, 
                        event_type, related_id, reminder_minutes, is_completed 
                 FROM calendar_events 
                 WHERE user_id = ? 
                 ORDER BY start_datetime""", (username,))
    events = c.fetchall()
    
    if not events:
        print("No calendar events found.")
        conn.close()
        return
    
    print(f"\n=== Calendar Events for {username} ===")
    for event in events:
        status = "Completed" if event[8] else "Not Completed"
        related_info = f" | Related ID: {event[6]}" if event[6] else ""
        print(f"ID: {event[0]} | Title: {event[1]}")
        print(f"  Description: {event[2] or 'None'}")
        print(f"  Start: {event[3]} | End: {event[4]} | Type: {event[5]}{related_info}")
        print(f"  Reminder: {event[7]} minutes before | Status: {status}")
        print("-" * 80)
    
    conn.close()