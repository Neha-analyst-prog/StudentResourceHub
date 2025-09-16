import logging
import re
import sqlite3
import time
from datetime import datetime
from contextlib import contextmanager
from db import DB_FILE
from utils import create_notification

# Configure logging
logging.basicConfig(filename='system.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

@contextmanager
def get_db_connection(timeout=30.0, retries=5):
    """Context manager for database connections with retry logic and extended timeout."""
    conn = None
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(DB_FILE, timeout=timeout)
            # Set pragmas for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")  # 30 second busy timeout
            yield conn
            return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < retries - 1:
                wait_time = (attempt + 1) * 2  # Progressive backoff: 2, 4, 6, 8 seconds
                print(f"⚠️  Database locked, retrying in {wait_time} seconds... (attempt {attempt + 1}/{retries})")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Database error after {retries} attempts: {e}")
                raise e
        except Exception as e:
            print(f"❌ Unexpected database error: {e}")
            raise e
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

def safe_input(prompt, default=""):
    """Safe input function with error handling."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️  Operation cancelled by user.")
        return default
    except Exception as e:
        print(f"❌ Input error: {e}")
        return default

def verify_user():
    """Verify pending user accounts with enhanced error handling."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get pending users
            c.execute("SELECT username, full_name, user_type, join_date FROM users WHERE is_verified = 0")
            pending = c.fetchall()
            
            if not pending:
                print("✅ No pending users to verify!")
                logging.info("No pending users for verification")
                return
            
            print("\n" + "="*60)
            print("🔍 PENDING USERS FOR VERIFICATION")
            print("="*60)
            
            for i, user in enumerate(pending, 1):
                print(f"\n{i}. 👤 Username: {user[0]}")
                full_name = user[1] if user[1] else "Not provided"
                print(f"   📝 Full Name: {full_name}")
                user_type = user[2] if user[2] else "student"
                print(f"   🏷️  User Type: {user_type}")
                join_date = user[3] if user[3] else "Unknown"
                print(f"   📅 Join Date: {join_date}")
                print("-" * 50)
            
            username = safe_input("\n➤ Enter username to verify (or 'back' to return): ")
            
            if username.lower() == 'back' or not username:
                if not username:
                    print("⚠️  Username cannot be empty!")
                    logging.warning("Empty username input for verification")
                return
            
            # Check if user exists and is not verified
            c.execute("SELECT is_verified, username FROM users WHERE username = ? COLLATE NOCASE", (username,))
            result = c.fetchone()
            
            if not result:
                print(f"❌ User '{username}' not found!")
                logging.warning(f"User '{username}' not found for verification")
                return
                
            if result[0]:  # Already verified
                print(f"⚠️  User '{username}' is already verified!")
                logging.warning(f"User '{username}' already verified")
                return
            
            # Verify the user
            c.execute("UPDATE users SET is_verified = 1 WHERE username = ? COLLATE NOCASE", (username,))
            
            # Create notification
            
            
            conn.commit()
            print(f"✅ User '{username}' verified successfully!")
            logging.info(f"User '{username}' verified successfully")
                
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        logging.error(f"Database error in verify_user: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error in verify_user: {e}")

def approve_resource():
    """Approve pending resources with enhanced error handling."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get pending resources
            c.execute("""SELECT id, title, uploaded_by, file_type, upload_date, category_name 
                         FROM resources WHERE status = 'pending' ORDER BY upload_date DESC""")
            pending = c.fetchall()
            
            if not pending:
                print("✅ No pending resources to approve!")
                logging.info("No pending resources for approval")
                return
            
            print("\n" + "="*80)
            print("📋 PENDING RESOURCES FOR APPROVAL")
            print("="*80)
            
            for resource in pending:
                print(f"\n🆔 ID: {resource[0]}")
                print(f"   📄 Title: {resource[1]}")
                print(f"   👤 Uploaded by: {resource[2]}")
                print(f"   📁 Type: {resource[3]}")
                print(f"   🏷️  Category: {resource[5] or 'Uncategorized'}")
                print(f"   📅 Upload Date: {resource[4]}")
                print("-" * 70)
            
            resource_input = safe_input("\n➤ Enter resource ID to approve (or 'back' to return): ")
            
            if resource_input.lower() == 'back':
                return
            
            if not resource_input or not resource_input.isdigit():
                print("❌ Resource ID must be a valid number!")
                logging.warning(f"Invalid resource ID input for approval: '{resource_input}'")
                return
            
            resource_id = int(resource_input)
            
            # Check if resource exists and is pending
            c.execute("SELECT status, uploaded_by, title FROM resources WHERE id = ?", (resource_id,))
            result = c.fetchone()
            
            if not result:
                print(f"❌ Resource with ID {resource_id} not found!")
                logging.warning(f"Resource ID {resource_id} not found for approval")
                return
            
            if result[0] != "pending":
                print(f"⚠️  Resource ID {resource_id} is not pending (current status: {result[0]})!")
                logging.warning(f"Resource ID {resource_id} not pending for approval")
                return
            
            # Approve the resource
            c.execute("UPDATE resources SET status = 'approved' WHERE id = ?", (resource_id,))
            
          
            conn.commit()
            print(f"✅ Resource ID {resource_id} approved successfully!")
            logging.info(f"Resource ID {resource_id} approved successfully")
                
    except (ValueError, sqlite3.Error) as e:
        print(f"❌ Error: {e}")
        logging.error(f"Error in approve_resource: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error in approve_resource: {e}")

def reject_resource():
    """Reject pending resources with a reason and enhanced error handling."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get pending resources
            c.execute("""SELECT id, title, uploaded_by, file_type, upload_date, category_name 
                         FROM resources WHERE status = 'pending' ORDER BY upload_date DESC""")
            pending = c.fetchall()
            
            if not pending:
                print("✅ No pending resources to reject!")
                logging.info("No pending resources for rejection")
                return
            
            print("\n" + "="*80)
            print("🚫 PENDING RESOURCES FOR REJECTION")
            print("="*80)
            
            for resource in pending:
                category = resource[5] if resource[5] else "Uncategorized"
                print(f"🆔 {resource[0]} | 📄 {resource[1]} | 👤 {resource[2]} | 📁 {resource[3]} | 🏷️  {category}")
            
            print("-" * 80)
            
            resource_input = safe_input("\n➤ Enter resource ID to reject (or 'back' to return): ")
            
            if resource_input.lower() == 'back':
                return
            
            if not resource_input or not resource_input.isdigit():
                print("❌ Resource ID must be a valid number!")
                logging.warning(f"Invalid resource ID input for rejection: '{resource_input}'")
                return
            
            resource_id = int(resource_input)
            
            # Get rejection reason
            reason = safe_input("➤ Enter rejection reason: ")
            
            if not reason:
                print("❌ Rejection reason cannot be empty!")
                logging.warning(f"Empty rejection reason for resource ID {resource_id}")
                return
            
            # Check if resource exists and is pending
            c.execute("SELECT status, uploaded_by, title FROM resources WHERE id = ?", (resource_id,))
            result = c.fetchone()
            
            if not result:
                print(f"❌ Resource with ID {resource_id} not found!")
                logging.warning(f"Resource ID {resource_id} not found for rejection")
                return
            
            if result[0] != "pending":
                print(f"⚠️  Resource ID {resource_id} is not pending (current status: {result[0]})!")
                logging.warning(f"Resource ID {resource_id} not pending for rejection")
                return
            
            # Reject the resource
            c.execute("UPDATE resources SET status = 'rejected' WHERE id = ?", (resource_id,))
            
                    
            
            conn.commit()
            print(f"✅ Resource ID {resource_id} rejected successfully!")
            logging.info(f"Resource ID {resource_id} rejected with reason: {reason}")
                
    except (ValueError, sqlite3.Error) as e:
        print(f"❌ Error: {e}")
        logging.error(f"Error in reject_resource: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error in reject_resource: {e}")

def manage_categories():
    """Manage categories with comprehensive error handling."""
    while True:
        try:
            print("\n" + "="*50)
            print("🗂️  CATEGORY MANAGEMENT SYSTEM")
            print("="*50)
            print("1. 👀 View all categories")
            print("2. ➕ Add new category")
            print("3. ✏️  Edit category")
            print("4. ❌ Deactivate category")
            print("5. ✅ Activate category")
            print("6. 🔙 Back to admin menu")
            
            choice = safe_input("➤ Choose option (1-6): ")
            if choice == "6":
                break
            
            if choice not in ["1", "2", "3", "4", "5"]:
                print("❌ Invalid choice! Please select 1-6.")
                continue
            
            with get_db_connection() as conn:
                c = conn.cursor()
                
                if choice == "1":
                    # View all categories
                    c.execute("""SELECT id, name, description, color, is_active, created_date 
                                 FROM categories ORDER BY is_active DESC, name ASC""")
                    categories = c.fetchall()
                    
                    if not categories:
                        print("\n📭 No categories found.")
                        logging.info("No categories found in manage_categories")
                        continue
                    
                    print("\n" + "="*80)
                    print("🗂️  ALL CATEGORIES")
                    print("="*80)
                    
                    for cat in categories:
                        status = "🟢 Active" if cat[4] else "🔴 Inactive"
                        description = cat[2] if cat[2] else "No description"
                        print(f"\n🆔 ID: {cat[0]} | 📝 Name: {cat[1]}")
                        print(f"   📄 Description: {description}")
                        print(f"   🎨 Color: {cat[3]} | {status}")
                        print(f"   📅 Created: {cat[5]}")
                        print("-" * 70)
                        
                elif choice == "2":
                    # Add new category
                    print("\n➕ ADD NEW CATEGORY")
                    print("-" * 30)
                    
                    name = safe_input("➤ Category name: ")
                    if not name:
                        print("❌ Category name cannot be empty!")
                        logging.warning("Empty category name input")
                        continue
                    
                    # Check if category already exists
                    c.execute("SELECT id FROM categories WHERE name = ? COLLATE NOCASE", (name,))
                    if c.fetchone():
                        print(f"❌ Category '{name}' already exists!")
                        logging.warning(f"Attempted to create duplicate category: {name}")
                        continue
                    
                    description = safe_input("➤ Description (optional): ")
                    color = safe_input("➤ Color (hex, e.g., #ff5733, default #007bff): ") or "#007bff"
                    
                    # Validate hex color
                    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
                        print("⚠️  Invalid hex color format! Using default (#007bff).")
                        logging.warning(f"Invalid hex color '{color}', using default #007bff")
                        color = "#007bff"
                    
                    # Insert new category
                    c.execute("""INSERT INTO categories (name, description, color, created_by, created_date, is_active) 
                                 VALUES (?, ?, ?, ?, ?, ?)""",
                              (name, description or None, color, "admin", 
                               datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
                    conn.commit()
                    
                    print(f"✅ Category '{name}' added successfully!")
                    logging.info(f"Category '{name}' added by admin")
                        
                elif choice == "3":
                    # Edit category
                    print("\n✏️  EDIT CATEGORY")
                    print("-" * 25)
                    
                    cat_input = safe_input("➤ Category ID to edit: ")
                    if not cat_input or not cat_input.isdigit():
                        print("❌ Category ID must be a valid number!")
                        logging.warning(f"Invalid category ID input for edit: '{cat_input}'")
                        continue
                    
                    cat_id = int(cat_input)
                    c.execute("SELECT name, description, color FROM categories WHERE id = ?", (cat_id,))
                    result = c.fetchone()
                    
                    if not result:
                        print(f"❌ Category with ID {cat_id} not found!")
                        logging.warning(f"Category ID {cat_id} not found for edit")
                        continue
                    
                    print(f"\n📋 Current Category Details:")
                    print(f"   Name: '{result[0]}'")
                    print(f"   Description: '{result[1] or 'None'}'")
                    print(f"   Color: '{result[2]}'")
                    
                    name = safe_input("➤ New name (press Enter to keep current): ") or result[0]
                    description = safe_input("➤ New description (press Enter to keep current): ") or result[1]
                    color = safe_input("➤ New color (press Enter to keep current): ") or result[2]
                    
                    # Validate hex color if changed
                    if color != result[2] and not re.match(r'^#[0-9A-Fa-f]{6}$', color):
                        print("⚠️  Invalid hex color format! Using current color.")
                        logging.warning(f"Invalid hex color '{color}' for category ID {cat_id}")
                        color = result[2]
                    
                    c.execute("UPDATE categories SET name = ?, description = ?, color = ? WHERE id = ?",
                              (name, description, color, cat_id))
                    conn.commit()
                    
                    print(f"✅ Category ID {cat_id} updated successfully!")
                    logging.info(f"Category ID {cat_id} updated")
                        
                elif choice == "4":
                    # Deactivate category
                    print("\n❌ DEACTIVATE CATEGORY")
                    print("-" * 30)
                    
                    cat_input = safe_input("➤ Category ID to deactivate: ")
                    if not cat_input or not cat_input.isdigit():
                        print("❌ Category ID must be a valid number!")
                        logging.warning(f"Invalid category ID input for deactivation: '{cat_input}'")
                        continue
                    
                    cat_id = int(cat_input)
                    
                    # Check if category exists and is active
                    c.execute("SELECT name, is_active FROM categories WHERE id = ?", (cat_id,))
                    result = c.fetchone()
                    
                    if not result:
                        print(f"❌ Category with ID {cat_id} not found!")
                        logging.warning(f"Category ID {cat_id} not found for deactivation")
                        continue
                    
                    if not result[1]:
                        print(f"⚠️  Category '{result[0]}' is already inactive!")
                        continue
                    
                    c.execute("UPDATE categories SET is_active = 0 WHERE id = ?", (cat_id,))
                    conn.commit()
                    
                    print(f"✅ Category '{result[0]}' deactivated successfully!")
                    logging.info(f"Category ID {cat_id} deactivated")
                        
                elif choice == "5":
                    # Activate category
                    print("\n✅ ACTIVATE CATEGORY")
                    print("-" * 28)
                    
                    cat_input = safe_input("➤ Category ID to activate: ")
                    if not cat_input or not cat_input.isdigit():
                        print("❌ Category ID must be a valid number!")
                        logging.warning(f"Invalid category ID input for activation: '{cat_input}'")
                        continue
                    
                    cat_id = int(cat_input)
                    
                    # Check if category exists and is inactive
                    c.execute("SELECT name, is_active FROM categories WHERE id = ?", (cat_id,))
                    result = c.fetchone()
                    
                    if not result:
                        print(f"❌ Category with ID {cat_id} not found!")
                        logging.warning(f"Category ID {cat_id} not found for activation")
                        continue
                    
                    if result[1]:
                        print(f"⚠️  Category '{result[0]}' is already active!")
                        continue
                    
                    c.execute("UPDATE categories SET is_active = 1 WHERE id = ?", (cat_id,))
                    conn.commit()
                    
                    print(f"✅ Category '{result[0]}' activated successfully!")
                    logging.info(f"Category ID {cat_id} activated")
                    
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            logging.error(f"Database error in manage_categories: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logging.error(f"Unexpected error in manage_categories: {e}")

def view_system_stats():
    """Display comprehensive system statistics with enhanced error handling."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            print("\n" + "="*70)
            print("📊 SYSTEM STATISTICS DASHBOARD")
            print("="*70)
            
            # User Statistics
            try:
                c.execute("SELECT COUNT(*) FROM users WHERE role = 'user' OR role IS NULL")
                total_users = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM users WHERE (role = 'user' OR role IS NULL) AND is_verified = 1")
                verified_users = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM users WHERE (role = 'user' OR role IS NULL) AND is_verified = 0")
                pending_users = c.fetchone()[0]
                
                print(f"\n👥 USER STATISTICS")
                print(f"   Total Users: {total_users}")
                print(f"   ✅ Verified: {verified_users}")
                print(f"   ⏳ Pending: {pending_users}")
                
            except sqlite3.Error as e:
                print(f"⚠️  Could not fetch user statistics: {e}")
                logging.error(f"Error fetching user statistics: {e}")
            
            # Resource Statistics
            try:
                c.execute("SELECT COUNT(*) FROM resources")
                total_resources = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM resources WHERE status = 'approved'")
                approved_resources = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM resources WHERE status = 'pending'")
                pending_resources = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM resources WHERE status = 'rejected'")
                rejected_resources = c.fetchone()[0]
                
                print(f"\n📄 RESOURCE STATISTICS")
                print(f"   Total Resources: {total_resources}")
                print(f"   ✅ Approved: {approved_resources}")
                print(f"   ⏳ Pending: {pending_resources}")
                print(f"   ❌ Rejected: {rejected_resources}")
                
            except sqlite3.Error as e:
                print(f"⚠️  Could not fetch resource statistics: {e}")
                logging.error(f"Error fetching resource statistics: {e}")
            
            # Category Statistics
            try:
                c.execute("SELECT COUNT(*) FROM categories")
                total_categories = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM categories WHERE is_active = 1")
                active_categories = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM categories WHERE is_active = 0")
                inactive_categories = c.fetchone()[0]
                
                print(f"\n🗂️  CATEGORY STATISTICS")
                print(f"   Total Categories: {total_categories}")
                print(f"   🟢 Active: {active_categories}")
                print(f"   🔴 Inactive: {inactive_categories}")
                
            except sqlite3.Error as e:
                print(f"⚠️  Could not fetch category statistics: {e}")
                logging.error(f"Error fetching category statistics: {e}")
            
            # Top Categories by Resource Count
            try:
                c.execute("""SELECT category_name, COUNT(*) as count 
                             FROM resources 
                             WHERE status = 'approved' AND category_name IS NOT NULL
                             GROUP BY category_name 
                             ORDER BY count DESC 
                             LIMIT 5""")
                top_categories = c.fetchall()
                
                if top_categories:
                    print(f"\n🏆 TOP CATEGORIES BY APPROVED RESOURCES")
                    for i, cat in enumerate(top_categories, 1):
                        print(f"   {i}. {cat[0]}: {cat[1]} resources")
                else:
                    print(f"\n📭 No approved resources with categories found.")
                    
            except sqlite3.Error as e:
                print(f"⚠️  Could not fetch top categories: {e}")
                logging.error(f"Error fetching top categories: {e}")
            
            # Recent Activity (if tables have timestamp columns)
            try:
                c.execute("""SELECT COUNT(*) FROM users 
                             WHERE join_date >= date('now', '-7 days')""")
                recent_users = c.fetchone()[0]
                
                c.execute("""SELECT COUNT(*) FROM resources 
                             WHERE upload_date >= date('now', '-7 days')""")
                recent_resources = c.fetchone()[0]
                
                print(f"\n📈 RECENT ACTIVITY (Last 7 Days)")
                print(f"   New Users: {recent_users}")
                print(f"   New Resources: {recent_resources}")
                
            except sqlite3.Error as e:
                print(f"⚠️  Could not fetch recent activity: {e}")
                logging.error(f"Error fetching recent activity: {e}")
            
            print("="*70)
            logging.info("System statistics viewed successfully")
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        logging.error(f"Database error in view_system_stats: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error in view_system_stats: {e}")

def enhanced_admin_menu(username):
    """Display and handle the enhanced admin menu with comprehensive error handling."""
    print(f"\n🎉 Welcome to Admin Panel, {username}!")
    
    while True:
        try:
            print("\n" + "="*60)
            print(f"🔧 ENHANCED ADMIN MENU - {username.upper()}")
            print("="*60)
            print("1. ✅ Verify Users")
            print("2. 👍 Approve Resources")
            print("3. 👎 Reject Resources") 
            print("4. 🗂️  Manage Categories")
            print("5. 📊 View System Statistics")
            print("6. 🚪 Back to Main Menu")
            
            choice = safe_input("➤ Choose option (1-6): ")
            
            if choice == "6":
                print("👋 Returning to main menu...")
                break
            elif choice == "1":
                print("\n🔍 Loading user verification...")
                verify_user()
            elif choice == "2":
                print("\n👍 Loading resource approval...")
                approve_resource()
            elif choice == "3":
                print("\n👎 Loading resource rejection...")
                reject_resource()
            elif choice == "4":
                print("\n🗂️  Loading category management...")
                manage_categories()
            elif choice == "5":
                print("\n📊 Loading system statistics...")
                view_system_stats()
            elif choice == "":
                print("⚠️  Please enter a valid option.")
                continue
            else:
                print("❌ Invalid choice! Please select an option from 1-6.")
                logging.warning(f"Invalid admin menu choice by '{username}': {choice}")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation interrupted by user. Returning to menu...")
            continue
        except Exception as e:
            print(f"❌ Unexpected error in admin menu: {e}")
            logging.error(f"Unexpected error in enhanced_admin_menu for '{username}': {e}")
            continue

# Optional: Add a test function to check database connectivity
def test_database_connection():
    """Test database connection and setup."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = c.fetchall()
            print(f"✅ Database connection successful. Found {len(tables)} tables.")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        logging.error(f"Database connection test failed: {e}")
        return False

# Main execution guard
if __name__ == "__main__":
    # Test database connection on module load
    if test_database_connection():
        print("🚀 Admin module loaded successfully!")
    else:
        print("⚠️  Warning: Database connection issues detected.")