import logging
import sqlite3
from db import init_db, add_user, validate_user
from admin import enhanced_admin_menu
from resource import upload_resource, view_resources, download_resource, share_resource_link, rate_resource, view_reviews
from study_calendar import add_calendar_event, view_calendar_events
from study_groups import create_study_group, view_study_groups, join_study_group
from user import collect_user_details

# Configure logging
logging.basicConfig(filename='system.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def signup():
    """Register a new user."""
    username = input("Enter new username: ").strip()
    if not username or len(username) < 3:
        print("❌ Username must be at least 3 characters long!")
        return
    password = input("Enter new password: ").strip()
    if not password or len(password) < 6:
        print("❌ Password must be at least 6 characters long!")
        return
    full_name, email, user_type = collect_user_details()
    role = "user"
    if add_user(username, password, role, full_name, email, user_type):
        print("✅ User registered successfully! Awaiting admin verification.")
    else:
        print("❌ Username already exists!")


def login():
    """Authenticate a user and return username, role if success."""
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    role = validate_user(username, password)
    if role:
        print(f"✅ Login successful! Welcome {username} ({role})")
        return username, role
    else:
        print("❌ Login failed. Invalid credentials or account not verified.")
        return None, None


def user_menu(username):
    while True:
        print(f"\n=== User Menu - {username} ===")
        print("1. Upload Resource")
        print("2. View Resources")
        print("3. Download Resource")
        print("4. Share Resource Link")
        print("5. Rate/Review Resource")
        print("6. View Reviews")
        print("7. Calendar Management")
        print("8. Study Groups")
        print("9. Logout")
        choice = input("Choose (1-9): ").strip()
        if choice == "1":
            upload_resource(username)
        elif choice == "2":
            view_resources(username)
        elif choice == "3":
            download_resource(username)
        elif choice == "4":
            share_resource_link(username)
        elif choice == "5":
            rate_resource(username)
        elif choice == "6":
            view_reviews(username)
        elif choice == "7":
            calendar_menu(username)
        elif choice == "8":
            study_group_menu(username)
        elif choice == "9":
            print("🚪 Logging out...")
            break
        else:
            print("❌ Invalid choice. Try again.")


def calendar_menu(username):
    while True:
        print(f"\n=== Calendar Management - {username} ===")
        print("1. Add Calendar Event")
        print("2. View Calendar Events")
        print("3. Back")
        choice = input("Choose (1-3): ").strip()
        if choice == "1":
            add_calendar_event(username)
        elif choice == "2":
            view_calendar_events(username)
        elif choice == "3":
            break
        else:
            print("❌ Invalid choice. Try again.")


def study_group_menu(username):
    while True:
        print(f"\n=== Study Groups - {username} ===")
        print("1. Create Study Group")
        print("2. View My Study Groups")
        print("3. Join Study Group")
        print("4. Back")
        choice = input("Choose (1-4): ").strip()
        if choice == "1":
            create_study_group(username)
        elif choice == "2":
            view_study_groups(username)
        elif choice == "3":
            join_study_group(username)
        elif choice == "4":
            break
        else:
            print("❌ Invalid choice. Try again.")


def admin_menu(username):
    enhanced_admin_menu(username)


def main_menu():
    while True:
        print("\n=== Resource Management System ===")
        print("1. Sign Up")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose (1-3): ").strip()
        if choice == "1":
            signup()
        elif choice == "2":
            username, role = login()
            if role == "user":
                user_menu(username)
            elif role == "admin":
                admin_menu(username)
        elif choice == "3":
            print("👋 Exiting system. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")


if __name__ == "__main__":
    try:
        init_db()
        main_menu()
    except sqlite3.Error as e:
        print(f"❌ Database initialization failed: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ System error: {e}")
        exit(1)
