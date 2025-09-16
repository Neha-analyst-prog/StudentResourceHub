from datetime import datetime
import sqlite3
from db import DB_FILE
from utils import generate_group_code

def create_study_group(username):
    """Create a new study group."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Verify user exists and is verified
    c.execute("SELECT is_verified FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if not result or not result[0]:
        print("User not verified or not found!")
        conn.close()
        return
    
    name = input("Enter study group name: ")
    description = input("Enter group description: ")
    subject = input("Enter subject (e.g., Math, Physics): ")
    max_members = input("Enter maximum members (default 20): ") or 20
    try:
        max_members = int(max_members)
        if max_members < 1:
            print("Maximum members must be at least 1!")
            conn.close()
            return
    except ValueError:
        print("Invalid number! Using default (20).")
        max_members = 20
    
    is_private = input("Is the group private? (y/n): ").lower() == 'y'
    meeting_schedule = input("Enter meeting schedule (e.g., Weekly, Mon 3PM): ") or "None"
    
    # Generate unique group code
    group_code = generate_group_code()
    
    # Insert study group into database
    c.execute("""INSERT INTO study_groups 
                 (name, description, subject, created_by, created_date, max_members, 
                  is_private, meeting_schedule, group_code) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, description, subject, username, 
               datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
               max_members, 1 if is_private else 0, meeting_schedule, group_code))
    
    group_id = c.lastrowid
    
    # Automatically add creator as a member with 'admin' role
    c.execute("""INSERT INTO group_members 
                 (group_id, member_username, join_date, role, is_active) 
                 VALUES (?, ?, ?, ?, ?)""",
              (group_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
               'admin', 1))
    
    conn.commit()
    print(f"Study group '{name}' created successfully (ID: {group_id}, Code: {group_code})!")
    if is_private:
        print(f"Share the group code '{group_code}' with others to join.")
    conn.close()

def view_study_groups(username):
    """View study groups the user is a member of or created."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get groups where the user is a member
    c.execute("""SELECT g.id, g.name, g.description, g.subject, g.created_by, 
                        g.created_date, g.max_members, g.is_private, g.meeting_schedule, 
                        g.group_code, gm.role 
                 FROM study_groups g 
                 JOIN group_members gm ON g.id = gm.group_id 
                 WHERE gm.member_username = ? AND gm.is_active = 1""", 
              (username,))
    groups = c.fetchall()
    
    if not groups:
        print("You are not a member of any study groups.")
        conn.close()
        return
    
    print(f"\n=== Study Groups for {username} ===")
    for group in groups:
        privacy = "Private" if group[7] else "Public"
        print(f"ID: {group[0]} | Name: {group[1]}")
        print(f"  Description: {group[2] or 'None'}")
        print(f"  Subject: {group[3]} | Created by: {group[4]} | Created: {group[5]}")
        print(f"  Max Members: {group[6]} | Privacy: {privacy}")
        print(f"  Meeting Schedule: {group[8] or 'None'} | Your Role: {group[10]}")
        if group[7]:  # If private, show group code
            print(f"  Group Code: {group[9]}")
        print("-" * 80)
    
    conn.close()

def join_study_group(username):
    """Join a study group using a group code."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT is_verified FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if not result or not result[0]:
        print("User not verified or not found!")
        conn.close()
        return
    
    group_code = input("Enter group code: ")
    c.execute("SELECT id, max_members FROM study_groups WHERE group_code = ?", (group_code,))
    group = c.fetchone()
    
    if not group:
        print("Invalid group code!")
        conn.close()
        return
    
    group_id, max_members = group
    
    # Check current member count
    c.execute("SELECT COUNT(*) FROM group_members WHERE group_id = ? AND is_active = 1", (group_id,))
    current_members = c.fetchone()[0]
    if current_members >= max_members:
        print("Group is full!")
        conn.close()
        return
    
    # Check if user is already a member
    c.execute("SELECT member_username FROM group_members WHERE group_id = ? AND member_username = ?", 
              (group_id, username))
    if c.fetchone():
        print("You are already a member of this group!")
        conn.close()
        return
    
    # Add user to group
    c.execute("""INSERT INTO group_members 
                 (group_id, member_username, join_date, role, is_active) 
                 VALUES (?, ?, ?, ?, ?)""",
              (group_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
               'member', 1))
    
    conn.commit()
    print(f"Joined study group successfully (ID: {group_id})!")
    conn.close()