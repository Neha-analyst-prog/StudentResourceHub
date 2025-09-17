import os
import shutil
from datetime import datetime
from db import DB_FILE, RESOURCES_DIR, VIDEOS_DIR
import sqlite3
from utils import generate_share_link, log_interaction, create_notification

def upload_resource(username):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT is_verified FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        if not result or not result[0]:
            print("User not verified!")
            return
        
        title = input("Enter resource title: ")
        description = input("Enter resource description: ")
        category_name = input("Enter category name: ")
        tags = input("Enter tags (comma-separated): ")
        difficulty = input("Difficulty level (beginner/intermediate/advanced): ") or "beginner"
        estimated_time = input("Estimated study time (e.g., 30 minutes): ")
        
        c.execute("SELECT name FROM categories WHERE name = ?", (category_name,))
        if not c.fetchone():
            color = input("Enter category color (optional): ") or "#007bff"
            c.execute("INSERT INTO categories (name, description, color, created_by, created_date) VALUES (?, ?, ?, ?, ?)", 
                      (category_name, "", color, username, datetime.now().strftime("%Y-%m-%d")))
        
        file_path = input("Enter file path to upload: ").strip('"\'')
        if not os.path.exists(file_path):
            print(f"File not found at: {file_path}")
            return
        
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        is_video = 1 if file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'] else 0
        
        file_name = os.path.basename(file_path)
        dest_dir = VIDEOS_DIR if is_video else RESOURCES_DIR
        dest_path = os.path.join(dest_dir, file_name)
        
        # Close connection before file operations
        conn.close()
        conn = None
        
        # File copy without database connection open
        try:
            shutil.copy2(file_path, dest_path)
        except Exception as e:
            print(f"Error copying file: {e}")
            return
        
        video_duration = ""
        if is_video:
            video_duration = input("Enter video duration (e.g., 1h 30m): ") or "Unknown"
        
        share_link = generate_share_link()
        
        # Reopen connection for database insert
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        
        c.execute("""INSERT INTO resources 
                     (title, description, category_name, uploaded_by, file_path, file_type, 
                      upload_date, status, download_count, file_size, tags, is_video, video_duration, 
                      share_link, difficulty_level, estimated_time) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (title, description, category_name, username, dest_path, file_ext, 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pending", 0, file_size, 
                   tags, is_video, video_duration, share_link, difficulty, estimated_time))
        
        resource_id = c.lastrowid
        conn.commit()
        print(f"Resource uploaded (ID: {resource_id}) - Awaiting approval.")
        print(f"Share link: {share_link}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Upload error: {e}")
    finally:
        if conn:
            conn.close()

def view_resources(username):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        
        print("\n--- Filter Options ---")
        print("1. All approved resources")
        print("2. Videos only")
        print("3. Documents only")
        print("4. By category")
        print("5. Search by title/description")
        print("6. By difficulty level")
        print("7. Recommended for you")
        
        filter_choice = input("Choose filter (1-7): ")
        
        if filter_choice == "7":
            conn.close()
            conn = None
            get_recommendations(username)
            return
        
        base_query = """SELECT r.id, r.title, r.description, r.category_name, r.upload_date, 
                               r.download_count, r.is_video, r.video_duration, r.file_type,
                               r.difficulty_level, r.estimated_time, r.share_link,
                               COALESCE(AVG(rev.rating), 0) as avg_rating, COUNT(rev.id) as review_count
                        FROM resources r 
                        LEFT JOIN reviews rev ON r.id = rev.resource_id
                        WHERE r.status = 'approved'"""
        
        params = []
        
        if filter_choice == "2":
            base_query += " AND r.is_video = 1"
        elif filter_choice == "3":
            base_query += " AND r.is_video = 0"
        elif filter_choice == "4":
            category = input("Enter category name: ")
            base_query += " AND r.category_name LIKE ?"
            params.append(f"%{category}%")
        elif filter_choice == "5":
            search_term = input("Enter search term: ")
            base_query += " AND (r.title LIKE ? OR r.description LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        elif filter_choice == "6":
            difficulty = input("Difficulty (beginner/intermediate/advanced): ")
            base_query += " AND r.difficulty_level = ?"
            params.append(difficulty)
        
        base_query += " GROUP BY r.id ORDER BY r.upload_date DESC"
        
        c.execute(base_query, params)
        resources = c.fetchall()
        
        if not resources:
            print("No resources found.")
            return
        
        for resource in resources:
            video_info = f" | Duration: {resource[7]}" if resource[6] else ""
            rating_info = f" | Rating: {resource[12]:.1f}/5 ({resource[13]} reviews)" if resource[13] > 0 else " | No ratings yet"
            time_info = f" | Est. Time: {resource[10]}" if resource[10] else ""
            print(f"ID: {resource[0]} | Title: {resource[1]}")
            print(f"  Description: {resource[2]}")
            print(f"  Category: {resource[3]} | Difficulty: {resource[9]} | Type: {'Video' if resource[6] else 'Document'}{video_info}{time_info}")
            print(f"  Upload Date: {resource[4]} | Downloads: {resource[5]}{rating_info}")
            print(f"  Share Link: {resource[11]}")
            print("-" * 80)
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"View resources error: {e}")
    finally:
        if conn:
            conn.close()

def get_recommendations(username):
    """AI-based resource recommendations"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        
        # Get user's interaction history
        c.execute("""SELECT r.category_name, COUNT(*) as interaction_count
                     FROM user_interactions ui
                     JOIN resources r ON ui.resource_id = r.id
                     WHERE ui.user_id = ?
                     GROUP BY r.category_name
                     ORDER BY interaction_count DESC""", (username,))
        
        user_categories = c.fetchall()
        
        if not user_categories:
            print("No interaction history found. Showing popular resources instead.")
            c.execute("""SELECT r.id, r.title, r.category_name, r.download_count,
                                COALESCE(AVG(rev.rating), 0) as avg_rating
                         FROM resources r
                         LEFT JOIN reviews rev ON r.id = rev.resource_id
                         WHERE r.status = 'approved'
                         GROUP BY r.id
                         ORDER BY r.download_count DESC, avg_rating DESC
                         LIMIT 10""")
        else:
            # Recommend resources from user's preferred categories
            preferred_category = user_categories[0][0]
            c.execute("""SELECT r.id, r.title, r.category_name, r.download_count,
                                COALESCE(AVG(rev.rating), 0) as avg_rating
                         FROM resources r
                         LEFT JOIN reviews rev ON r.id = rev.resource_id
                         WHERE r.status = 'approved' AND r.category_name = ?
                         AND r.id NOT IN (
                             SELECT resource_id FROM user_interactions WHERE user_id = ?
                         )
                         GROUP BY r.id
                         ORDER BY avg_rating DESC, r.download_count DESC
                         LIMIT 10""", (preferred_category, username))
        
        recommendations = c.fetchall()
        
        if recommendations:
            print(f"\nRecommended Resources for {username}:")
            print("=" * 50)
            for rec in recommendations:
                rating_text = f" | Rating: {rec[4]:.1f}/5" if rec[4] > 0 else ""
                print(f"ID: {rec[0]} | {rec[1]} | Category: {rec[2]} | Downloads: {rec[3]}{rating_text}")
        else:
            print("No recommendations available at the moment.")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Recommendations error: {e}")
    finally:
        if conn:
            conn.close()

def download_resource(username):
    try:
        resource_id = int(input("Enter resource ID to download: "))
    except ValueError:
        print("Invalid resource ID!")
        return
    
    conn = None
    try:
        # STEP 1: Get resource info quickly and close connection
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT file_path, download_count, title FROM resources WHERE id = ? AND status = 'approved'", (resource_id,))
        result = c.fetchone()
        
        if not result:
            print("Resource not found or not approved!")
            return
            
        file_path, count, title = result
        conn.close()
        conn = None
        
        # STEP 2: Check file existence (no database connection open)
        if not os.path.exists(file_path):
            print("Source file no longer exists!")
            return
        
        print(f"Downloading '{title}'... (Current Downloads: {count})")
        
        # STEP 3: Perform file copy (no database connection open)
        try:
            downloaded_name = f"downloaded_{os.path.basename(file_path)}"
            with open(file_path, 'rb') as f:
                with open(downloaded_name, 'wb') as out:
                    out.write(f.read())
            print(f"File downloaded as: {downloaded_name}")
        except Exception as e:
            print(f"Error downloading file: {e}")
            return
        
        # STEP 4: Update database with separate, quick connection
        try:
            conn = sqlite3.connect(DB_FILE, timeout=30.0)
            c = conn.cursor()
            
            # Update download count
            c.execute("UPDATE resources SET download_count = COALESCE(download_count, 0) + 1 WHERE id = ?", (resource_id,))
            
            # Add to download history
            c.execute("INSERT INTO download_history (user_id, resource_id, download_date) VALUES (?, ?, ?)",
                      (username, resource_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            print(f"Updated download count to: {count + 1}")
            
            # Log interaction (handle gracefully if fails)
            try:
                log_interaction(username, resource_id, "download", 3)
            except Exception as e:
                print(f"Warning: Could not log interaction: {e}")
                
        except sqlite3.Error as e:
            print(f"Warning: Download successful but couldn't update statistics: {e}")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Download error: {e}")
    finally:
        if conn:
            conn.close()

def share_resource_link(username):
    """Generate and display shareable links"""
    try:
        resource_id = int(input("Enter resource ID to get share link: "))
    except ValueError:
        print("Invalid resource ID!")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT title, share_link FROM resources WHERE id = ? AND status = 'approved'", (resource_id,))
        result = c.fetchone()
        
        if result:
            title, share_link = result
            print(f"\nResource: {title}")
            print(f"Share Link: {share_link}")
            print(f"Anyone with this link can access the resource!")
            
            # Log interaction (handle gracefully if fails)
            try:
                log_interaction(username, resource_id, "share", 1)
            except Exception as e:
                print(f"Warning: Could not log interaction: {e}")
        else:
            print("Resource not found or not approved!")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Share link error: {e}")
    finally:
        if conn:
            conn.close()

def access_shared_resource():
    """Access resource via share link"""
    share_link = input("Enter share link: ")
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT id, title, description, uploaded_by FROM resources WHERE share_link = ? AND status = 'approved'", (share_link,))
        result = c.fetchone()
        
        if result:
            resource_id, title, description, uploader = result
            print(f"\nResource Found!")
            print(f"Title: {title}")
            print(f"Description: {description}")
            print(f"Uploaded by: {uploader}")
            
            if input("\nDownload this resource? (y/n): ").lower() == 'y':
                # Update download count for anonymous user
                c.execute("UPDATE resources SET download_count = COALESCE(download_count, 0) + 1 WHERE id = ?", (resource_id,))
                conn.commit()
                print("Resource download initiated!")
        else:
            print("Invalid share link or resource not found!")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Access shared resource error: {e}")
    finally:
        if conn:
            conn.close()

def rate_resource(username):
    try:
        resource_id = int(input("Enter resource ID to rate: "))
    except ValueError:
        print("Invalid resource ID!")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        
        # Check if resource exists and is approved
        c.execute("SELECT title FROM resources WHERE id = ? AND status = 'approved'", (resource_id,))
        resource = c.fetchone()
        if not resource:
            print("Resource not found or not approved!")
            return
        
        # Check if user already rated this resource
        c.execute("SELECT id FROM reviews WHERE resource_id = ? AND reviewer = ?", (resource_id, username))
        existing = c.fetchone()
        if existing:
            print("You have already rated this resource!")
            return
        
        print(f"Rating resource: {resource[0]}")
        
        # Get rating input
        try:
            rating = int(input("Enter rating (1-5): "))
            if rating < 1 or rating > 5:
                print("Rating must be between 1 and 5!")
                return
        except ValueError:
            print("Invalid rating!")
            return
        
        comment = input("Enter your review (optional): ")
        
        c.execute("INSERT INTO reviews (resource_id, reviewer, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)",
                  (resource_id, username, rating, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        print("Review submitted successfully!")
        
        # Log interaction (handle gracefully if fails)
        try:
            log_interaction(username, resource_id, "rate", rating)
        except Exception as e:
            print(f"Warning: Could not log interaction: {e}")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Rating error: {e}")
    finally:
        if conn:
            conn.close()

def view_reviews(username):
    try:
        resource_id = int(input("Enter resource ID to view reviews: "))
    except ValueError:
        print("Invalid resource ID!")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        c = conn.cursor()
        
        c.execute("SELECT title FROM resources WHERE id = ?", (resource_id,))
        resource = c.fetchone()
        if not resource:
            print("Resource not found!")
            return
        
        print(f"\nReviews for '{resource[0]}':")
        
        c.execute("""SELECT reviewer, rating, comment, review_date, helpfulness
                     FROM reviews WHERE resource_id = ? ORDER BY review_date DESC""", (resource_id,))
        reviews = c.fetchall()
        
        if reviews:
            for rev in reviews:
                print(f"Reviewer: {rev[0]} | Rating: {rev[1]}/5 | Date: {rev[3]}")
                if rev[2]:
                    print(f"Comment: {rev[2]}")
                print(f"Helpfulness: {rev[4]}")
                print("-" * 50)
        else:
            print("No reviews yet.")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"View reviews error: {e}")
    finally:
        if conn:
            conn.close()
