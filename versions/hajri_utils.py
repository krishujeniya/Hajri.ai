# hajri_utils.py
import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from deepface import DeepFace
from datetime import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, List, Dict
import shutil
import albumentations as A
import sqlite3
import streamlit_authenticator as stauth
from fpdf import FPDF # <-- NEW: For PDF generation
import base64
load_dotenv()
# ============================================
# CONFIGURATION & DATABASE (Unchanged)
# ============================================
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "hajri.db")
MODELS_DIR = os.path.join(DATA_DIR, "models")
TRAINING_IMAGES_DIR = os.path.join(DATA_DIR, "training_images")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(TRAINING_IMAGES_DIR, exist_ok=True)
transform = A.Compose([A.HorizontalFlip(p=0.5),A.RandomBrightnessContrast(p=0.3),A.ShiftScaleRotate(p=0.4),A.GaussNoise(p=0.2),A.MotionBlur(p=0.2),A.Resize(224, 224)])
# ============================================
# DATABASE SETUP
# ============================================

def connect_db():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes all database tables."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # NEW: Master users table for all roles (replaces 'students')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student'))
    );
    """)
    
    # List of subjects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE
    );
    """)
    
    # NEW: Link table for teachers <-> subjects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teacher_subjects (
        user_id INTEGER,
        subject_id INTEGER,
        PRIMARY KEY (user_id, subject_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
    );
    """)

    # MODIFIED: Links students <-> subjects using user_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_subjects (
        user_id INTEGER,
        subject_id INTEGER,
        PRIMARY KEY (user_id, subject_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
    );
    """)
    
    # List of lectures for each subject
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        lecture_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        lecture_name TEXT NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE,
        UNIQUE(subject_id, lecture_name)
    );
    """)
    
    # MODIFIED: Attendance records use user_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('P', 'A')),
        FOREIGN KEY (lecture_id) REFERENCES lectures (lecture_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        UNIQUE(lecture_id, user_id)
    );
    """)
    
    conn.commit()
    conn.close()
    
    # NEW: Create a default admin user if no users exist
    create_first_admin()
def create_first_admin():
    """Creates a default admin user if the users table is empty."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        try:
            # --- MODIFIED SECTION ---
            # Read from .env, with fallbacks to the old insecure defaults
            default_user = os.getenv("ADMIN_USERNAME")
            default_pass = os.getenv("ADMIN_PASSWORD")

            if os.getenv("ADMIN_PASSWORD") is None:
                print("====================================================================")
                print("WARNING: ADMIN_PASSWORD not set in .env file.")
                print("Using insecure default password: 'defaultadminpass'")
                print("Please set ADMIN_PASSWORD in your .env file for security.")
                print("====================================================================")

            hashed_password = stauth.Hasher().hash(default_pass)
            cursor.execute(
                "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                (default_user, 'Default Admin', 'admin@example.com', hashed_password, 'admin')
            )
            # --- END MODIFIED SECTION ---
            
            conn.commit()
            print(f"Created default admin user. Username: '{default_user}'")
            print("Password set from ADMIN_PASSWORD in your .env file.")
        except Exception as e:
            print(f"Error creating default admin: {e}")
    conn.close()

# ============================================
# AUTH & USER FUNCTIONS
# ============================================

def get_all_users_for_auth() -> dict:
    """Fetches all user data in the format streamlit-authenticator needs."""
    conn = connect_db()
    try:
        users = pd.read_sql_query("SELECT username, name, password FROM users", conn)
        credentials = {
            "usernames": {}
        }
        for _, row in users.iterrows():
            credentials["usernames"][row['username']] = {
                "name": row['name'],
                "password": row['password']
            }
        return credentials
    except Exception as e:
        print(f"Error fetching users for auth: {e}")
        return {"usernames": {}}
    finally:
        conn.close()

def get_user_by_username(username: str) -> dict:
    """Gets a user's ID, role, and name from their username."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role, name, email FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return {"user_id": user[0], "role": user[1], "name": user[2], "email": user[3]}
        return {}
    finally:
        conn.close()

def create_user(username, name, email, password, role) -> Tuple[bool, str]:
    """Creates a new user (student, teacher, or admin)."""
    if not all([username, name, password, role]):
        return False, "Missing required fields."
    
    conn = connect_db()
    try:
        # NEW
        hashed_password = stauth.Hasher().hash(password)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
            (username, name, email, hashed_password, role)
        )
        conn.commit()
        
        if role == 'student':
            os.makedirs(os.path.join(TRAINING_IMAGES_DIR, str(username)), exist_ok=True)
            
        return True, f"User '{name}' ({role}) created successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as e:
        return False, f"An error occurred: {e}"
    finally:
        conn.close()

def get_users_by_role(role: str) -> pd.DataFrame:
    """Gets all users of a specific role."""
    conn = connect_db()
    try:
        query = "SELECT user_id, username, name, email FROM users WHERE role = ? ORDER BY name"
        df = pd.read_sql_query(query, conn, params=(role,))
        # Rename username to Enrollment for students for consistency in UI
        if role == 'student':
            df = df.rename(columns={"username": "Enrollment", "user_id":"Student_ID"})
        return df
    finally:
        conn.close()

def delete_user(user_id: int) -> Tuple[bool, str]:
    """Deletes a user and all their associated data."""
    conn = connect_db()
    try:
        # Get username and role before deleting
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return False, "User not found."
        
        username, role = user_data
        
        # This will cascade and delete from users, teacher_subjects, student_subjects, and attendance
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        
        # If student, remove training images
        if role == 'student':
            img_folder = os.path.join(TRAINING_IMAGES_DIR, str(username))
            if os.path.exists(img_folder):
                shutil.rmtree(img_folder)
            train_model()
        
        return True, f"Permanently deleted all data for user {username}."
    except Exception as e:
        return False, f"Error during deletion: {e}"
    finally:
        conn.close()

# ============================================
# SUBJECT & PERMISSION FUNCTIONS
# ============================================

def get_subjects(user_id: int, role: str) -> Dict[str, int]:
    """Gets a {subject_name: subject_id} dict based on user's role."""
    conn = connect_db()
    try:
        if role == 'admin':
            query = "SELECT subject_id, subject_name FROM subjects ORDER BY subject_name"
            params = ()
        elif role == 'teacher':
            query = """
                SELECT s.subject_id, s.subject_name FROM subjects s
                JOIN teacher_subjects ts ON s.subject_id = ts.subject_id
                WHERE ts.user_id = ? ORDER BY s.subject_name
            """
            params = (user_id,)
        elif role == 'student':
            query = """
                SELECT s.subject_id, s.subject_name FROM subjects s
                JOIN student_subjects ss ON s.subject_id = ss.subject_id
                WHERE ss.user_id = ? ORDER BY s.subject_name
            """
            params = (user_id,)
        else:
            return {}
            
        df = pd.read_sql_query(query, conn, params=params)
        return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()
    except Exception as e:
        print(f"Error getting subjects: {e}")
        return {}
    finally:
        conn.close()

def add_subject(subject_name: str) -> Tuple[bool, str]:
    """Adds a new subject (Admin only)."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO subjects (subject_name) VALUES (?)", (subject_name,))
        conn.commit()
        return True, f"Subject '{subject_name}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Subject '{subject_name}' already exists."
    finally:
        conn.close()

def delete_subject(subject_id: int) -> Tuple[bool, str]:
    """Deletes a subject and all associated data (Admin only)."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
        conn.commit()
        return True, "Subject and all associated data deleted."
    finally:
        conn.close()

def get_unassigned_subjects_for_teacher(user_id: int) -> Dict[str, int]:
    """Gets subjects a teacher is NOT yet assigned to."""
    conn = connect_db()
    try:
        query = """
            SELECT subject_id, subject_name FROM subjects
            WHERE subject_id NOT IN (
                SELECT subject_id FROM teacher_subjects WHERE user_id = ?
            )
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()
    finally:
        conn.close()

def assign_teacher_to_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO teacher_subjects (user_id, subject_id) VALUES (?, ?)", (user_id, subject_id))
        conn.commit()
        return True, "Teacher assigned to subject."
    except sqlite3.IntegrityError:
        return False, "Teacher is already assigned to this subject."
    finally:
        conn.close()

def remove_teacher_from_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM teacher_subjects WHERE user_id = ? AND subject_id = ?", (user_id, subject_id))
        conn.commit()
        return True, "Teacher unassigned from subject."
    finally:
        conn.close()

# ============================================
# STUDENT ENROLLMENT FUNCTIONS
# ============================================

def get_students_for_subject(subject_id: int) -> pd.DataFrame:
    """Gets all students enrolled in a specific subject."""
    conn = connect_db()
    try:
        query = """
        SELECT u.user_id, u.username, u.name FROM users u
        JOIN student_subjects ss ON u.user_id = ss.user_id
        WHERE ss.subject_id = ? AND u.role = 'student'
        ORDER BY u.name
        """
        df = pd.read_sql_query(query, conn, params=(subject_id,))
        df = df.rename(columns={"username": "Enrollment", "user_id": "user_id_student"})
        return df
    finally:
        conn.close()

def add_student_to_subject(student_user_id: int, subject_id: int):
    """Adds a registered student to a subject."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO student_subjects (user_id, subject_id) VALUES (?, ?)", (student_user_id, subject_id))
        
        # Back-fill attendance records for this student
        cursor.execute("SELECT lecture_id FROM lectures WHERE subject_id = ?", (subject_id,))
        existing_lectures = cursor.fetchall()
        for (lec_id,) in existing_lectures:
            cursor.execute("INSERT OR IGNORE INTO attendance (lecture_id, user_id, status) VALUES (?, ?, 'A')", (lec_id, student_user_id))
            
        conn.commit()
        return True, "Added student to subject."
    except sqlite3.IntegrityError:
        return False, "Student is already in this subject."
    finally:
        conn.close()

def remove_student_from_subject(student_user_id: int, subject_id: int):
    """Removes a student from a subject."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM student_subjects WHERE user_id = ? AND subject_id = ?", (student_user_id, subject_id))
        
        cursor.execute("SELECT lecture_id FROM lectures WHERE subject_id = ?", (subject_id,))
        lecture_ids = cursor.fetchall()
        
        if lecture_ids:
            lec_id_tuples = tuple([l[0] for l in lecture_ids])
            placeholder = ','.join('?' for _ in lec_id_tuples)
            query = f"DELETE FROM attendance WHERE user_id = ? AND lecture_id IN ({placeholder})"
            params = (student_user_id,) + lec_id_tuples
            cursor.execute(query, params)
            
        conn.commit()
        return True, "Removed student from subject."
    finally:
        conn.close()

# ============================================
# LECTURE & ATTENDANCE FUNCTIONS
# ============================================

def get_lectures_for_subject(subject_id: int) -> pd.DataFrame:
    """Gets all lectures for a subject, returning a DF with lecture_id as index."""
    if not subject_id:
        return pd.DataFrame(columns=["lecture_name", "date"])
    conn = connect_db()
    try:
        query = "SELECT lecture_id, lecture_name, date FROM lectures WHERE subject_id = ? ORDER BY date DESC"
        df = pd.read_sql_query(query, conn, params=(subject_id,), index_col='lecture_id')
        return df
    finally:
        conn.close()

def add_new_lecture(subject_id: int, lecture_name: str) -> int:
    """Creates a new lecture and populates 'A' for all students in that subject."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("INSERT INTO lectures (subject_id, lecture_name, date) VALUES (?, ?, ?)", 
                       (subject_id, lecture_name, date_str))
        lecture_id = cursor.lastrowid
        
        cursor.execute("SELECT user_id FROM student_subjects WHERE subject_id = ?", (subject_id,))
        students = cursor.fetchall()
        
        attendance_records = [(lecture_id, s[0], 'A') for s in students]
        if attendance_records:
            cursor.executemany("INSERT INTO attendance (lecture_id, user_id, status) VALUES (?, ?, ?)", attendance_records)
            
        conn.commit()
        return lecture_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Lecture name '{lecture_name}' already exists for this subject.")
    finally:
        conn.close()

def remove_lecture_from_subject(lecture_id: int):
    """Removes a lecture and all its associated attendance records."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lectures WHERE lecture_id = ?", (lecture_id,))
        conn.commit()
        return True, "Lecture removed."
    finally:
        conn.close()

def mark_attendance(lecture_id: int, edited_df: pd.DataFrame):
    """Saves the verified attendance from the data_editor."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        update_data = []
        for _, row in edited_df.iterrows():
            status = "P" if row["Marked_Present"] else "A"
            user_id = row["user_id_student"]
            update_data.append((status, lecture_id, user_id))
        
        cursor.executemany("UPDATE attendance SET status = ? WHERE lecture_id = ? AND user_id = ?", update_data)
        conn.commit()
    finally:
        conn.close()

def mark_manual_attendance(lecture_id: int, enrollment: str): # Enrollment is username
    """Manually marks a single student as present for a lecture."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        
        # Get user_id from enrollment (username)
        cursor.execute("SELECT user_id, name FROM users WHERE username = ? AND role = 'student'", (enrollment,))
        student = cursor.fetchone()
        if not student:
            return False, f"Student '{enrollment}' not found."
        
        student_user_id, student_name = student
        
        cursor.execute("SELECT attendance_id FROM attendance WHERE lecture_id = ? AND user_id = ?", (lecture_id, student_user_id))
        record = cursor.fetchone()
        
        if not record:
            return False, f"Student {enrollment} is not enrolled in the subject for this lecture."
        
        cursor.execute("UPDATE attendance SET status = 'P' WHERE attendance_id = ?", (record[0],))
        conn.commit()
        
        return True, f"Marked {student_name} ({enrollment}) as Present."
    finally:
        conn.close()

# ============================================
# DASHBOARD & STUDENT REPORT
# ============================================

def get_dashboard_data(subject_id: int, threshold: int):
    """Generates all dashboard stats for a subject."""
    conn = connect_db()
    try:
        total_students = pd.read_sql_query("SELECT COUNT(*) FROM student_subjects WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
        total_lectures = pd.read_sql_query("SELECT COUNT(*) FROM lectures WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
        
        if total_students == 0:
            return {"status": "fail", "message": "No students are enrolled in this subject."}
        if total_lectures == 0:
            return {"status": "fail", "message": "No lectures have been taken for this subject yet."}

        base_query = """
        SELECT a.user_id, u.username, u.name, u.email, l.lecture_name, a.status 
        FROM attendance a
        JOIN lectures l ON a.lecture_id = l.lecture_id
        JOIN users u ON a.user_id = u.user_id
        WHERE l.subject_id = ? AND u.role = 'student'
        """
        df = pd.read_sql_query(base_query, conn, params=(subject_id,))
        
        if df.empty:
             return {"status": "fail", "message": "No attendance data found for students."}

        full_report_df = df.pivot_table(index=['user_id', 'username', 'name', 'email'], columns='lecture_name', values='status', aggfunc='first').reset_index()
        full_report_df.columns.name = None
        
        lecture_cols = [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email']]
        
        full_report_df["Total"] = full_report_df[lecture_cols].apply(lambda x: (x == "P").sum(), axis=1)
        full_report_df["Percentage"] = (full_report_df["Total"] / total_lectures) * 100
        
        overall_att = full_report_df["Percentage"].mean()
        
        defaulters = full_report_df[full_report_df["Percentage"] < threshold][["username", "name", "email", "Percentage"]]
        defaulters = defaulters.rename(columns={"username": "Enrollment", "name": "Name", "email": "Email"})
        
        trends_series = full_report_df[lecture_cols].apply(lambda x: (x == "P").sum())
        trends = trends_series.reset_index()
        trends.columns = ["Lecture", "Present Count"]

        return {
            "status": "ok",
            "metrics": {
                "total_students": total_students,
                "total_lectures": total_lectures,
                "overall_attendance": overall_att,
            },
            "defaulters": defaulters,
            "trends": trends,
            "full_report": full_report_df
        }
    finally:
        conn.close()

# --- NEW FUNCTION ---
def get_student_report(user_id: int) -> dict:
    """Generates a full attendance report for a single student."""
    subjects_dict = get_subjects(user_id, 'student')
    if not subjects_dict:
        return {"status": "fail", "message": "You are not enrolled in any subjects."}
    
    conn = connect_db()
    try:
        report = {"status": "ok", "subjects": []}
        for subject_name, subject_id in subjects_dict.items():
            # Get all lectures for this subject
            lectures_df = pd.read_sql_query(
                "SELECT lecture_id, lecture_name, date FROM lectures WHERE subject_id = ?", 
                conn, params=(subject_id,)
            )
            total_lectures = len(lectures_df)
            if total_lectures == 0:
                report["subjects"].append({
                    "subject_name": subject_name,
                    "total_lectures": 0, "present": 0, "percentage": 100,
                    "attendance_df": pd.DataFrame(columns=["Lecture", "Date", "Status"])
                })
                continue
                
            # Get student's attendance for these lectures
            query = """
            SELECT l.lecture_name, l.date, a.status 
            FROM attendance a
            JOIN lectures l ON a.lecture_id = l.lecture_id
            WHERE a.user_id = ? AND l.subject_id = ?
            ORDER BY l.date
            """
            attendance_df = pd.read_sql_query(query, conn, params=(user_id, subject_id))
            attendance_df = attendance_df.rename(columns={"lecture_name": "Lecture", "date": "Date", "status": "Status"})
            
            present_count = (attendance_df["Status"] == "P").sum()
            percentage = (present_count / total_lectures) * 100
            
            report["subjects"].append({
                "subject_name": subject_name,
                "total_lectures": total_lectures,
                "present": present_count,
                "percentage": percentage,
                "attendance_df": attendance_df
            })
        return report
    finally:
        conn.close()

# ============================================
# AI/IMAGE FUNCTIONS (MODIFIED)
# ============================================

def save_image_for_student(enrollment_username, name, image, capture_count):
    """Save captured student face images."""
    folder = os.path.join(TRAINING_IMAGES_DIR, str(enrollment_username))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{capture_count}.jpg")
    image.save(path)
    return path

def augment_training_images(enrollment_username, num_originals=10, num_target_total=50):
    """Augments the original N images to create a larger dataset."""
    folder = os.path.join(TRAINING_IMAGES_DIR, str(enrollment_username))
    
    all_files = os.listdir(folder)
    for f in all_files:
        try:
            file_num = int(f.split('.')[0])
            if file_num > num_originals:
                os.remove(os.path.join(folder, f))
        except ValueError:
            continue
            
    original_images = []
    for i in range(1, num_originals + 1):
        img_path = os.path.join(folder, f"{i}.jpg")
        if os.path.exists(img_path):
            image = cv2.imread(img_path)
            if image is None: continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            original_images.append(image)
    
    if not original_images:
        return False, "No original images found to augment."
    
    num_to_generate = num_target_total - len(original_images)
    if num_to_generate <= 0:
        return True, "Sufficient images already exist."
    
    current_img_count = num_originals + 1
    for _ in range(num_to_generate):
        base_image = original_images[np.random.randint(0, len(original_images))]
        augmented = transform(image=base_image)['image']
        save_path = os.path.join(folder, f"{current_img_count}.jpg")
        augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR)
        cv2.imwrite(save_path, augmented_bgr)
        current_img_count += 1
        
    return True, f"Generated {num_to_generate} new augmented images."

def train_model():
    """Train DeepFace representations and save them."""
    try:
        pkl_path = os.path.join(TRAINING_IMAGES_DIR, "representations_SFace.pkl")
        if os.path.exists(pkl_path):
            os.remove(pkl_path)

        student_dirs = [d for d in os.listdir(TRAINING_IMAGES_DIR) if os.path.isdir(os.path.join(TRAINING_IMAGES_DIR, d))]
        if not student_dirs:
            return False, "No student images found to train."
            
        has_images = any(len(os.listdir(os.path.join(TRAINING_IMAGES_DIR, d))) > 0 for d in student_dirs)
        if not has_images:
             return False, "Student folders are empty. No images to train."

        sample_img_path = None
        for student_dir in student_dirs:
            student_path = os.path.join(TRAINING_IMAGES_DIR, student_dir)
            images = [f for f in os.listdir(student_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            if images:
                sample_img_path = os.path.join(student_path, images[0])
                break
        
        if sample_img_path is None:
            return False, "Could not find any valid sample image to initiate training."

        DeepFace.find(
            img_path=sample_img_path,
            db_path=TRAINING_IMAGES_DIR,
            model_name="SFace",
            enforce_detection=False,
            silent=True
        )

        return True, "Model (re)trained successfully!"
    except Exception as e:
        return False, f"Training failed: {e}"

def recognize_face_in_image(pil_image):
    """Detect, check for liveness, and recognize faces using DeepFace."""
    try:
        pkl_path = os.path.join(TRAINING_IMAGES_DIR, "representations_SFace.pkl")
        if not os.path.exists(pkl_path):
            return pd.DataFrame(), pd.DataFrame() 

        img_np = np.array(pil_image.convert('RGB'))

        results_list = DeepFace.find(
            img_path=img_np,
            db_path=TRAINING_IMAGES_DIR,
            model_name="SFace",
            enforce_detection=False,
            detector_backend='opencv',
            silent=True
        )

        recognized_data = []
        # Get all registered students (now users with role 'student')
        students_df = get_users_by_role('student') # Returns df with 'Enrollment' and 'Name'
        if students_df.empty:
            return pd.DataFrame(), pd.DataFrame() 

        for results_df in results_list:
            if not results_df.empty:
                top_match = results_df.iloc[0]
                
                x, y, w, h = top_match['source_x'], top_match['source_y'], top_match['source_w'], top_match['source_h']
                pad = 10
                cropped_face = img_np[max(0, y-pad):min(y+h+pad, img_np.shape[0]), 
                                      max(0, x-pad):min(x+w+pad, img_np.shape[1])]
                
                if cropped_face.size == 0: continue 

                is_real = False
                try:
                    liveness_result = DeepFace.analyze(
                        cropped_face, actions=['antispoofing'], enforce_detection=False, silent=True
                    )
                    is_real = liveness_result[0]['is_real']
                except Exception:
                    is_real = False 

                file_path = top_match["identity"]
                # Username (enrollment) is the folder name
                enroll_username = file_path.split(os.sep)[-2]
                student_row = students_df[students_df["Enrollment"].astype(str) == str(enroll_username)]
                
                if not student_row.empty:
                    recognized_data.append({
                        "Enrollment": enroll_username,
                        "Name": student_row.iloc[0]["Name"],
                        "Distance": round(top_match["distance"], 3),
                        "x": x, "y": y, "w": w, "h": h,
                        "is_real": is_real
                    })
        
        if recognized_data:
            all_results_df = pd.DataFrame(recognized_data)
            live_students_df = all_results_df[all_results_df["is_real"] == True]
            unique_live_students_df = live_students_df.drop_duplicates(subset=["Enrollment"])[["Enrollment", "Name"]]
            
            return all_results_df, unique_live_students_df
        else:
            return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        if "representations_SFace.pkl" in str(e):
             print("Model not trained. Please register a student first.")
        else:
             print(f"Recognition error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# ... (draw_on_image is unchanged) ...
def draw_on_image(pil_img, results_df):
    """Draw bounding boxes and liveness status on detected faces."""
    img_draw = pil_img.copy()
    draw = ImageDraw.Draw(img_draw)
    try: font = ImageFont.load_default(size=15)
    except IOError: font = ImageFont.load_default() 
    if not results_df.empty:
        for _, row in results_df.iterrows():
            x, y, w, h = row['x'], row['y'], row['w'], row['h']
            name, distance, is_real = row['Name'], row['Distance'], row['is_real']
            color = "lime" if is_real else "red"
            text = f"{name} ({distance})" if is_real else f"SPOOF (Likely {name})"
            draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=3)
            text_bbox = draw.textbbox((x, y - 20), text, font=font)
            draw.rectangle(text_bbox, fill=color)
            draw.text((x + 2, y - 20), text, fill="black", font=font)
    return img_draw

# ... (email_defaulters is unchanged) ...
def email_defaulters(defaulters_df: pd.DataFrame, subject_name: str) -> List[str]:
    errors = []
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password:
        errors.append("Email credentials not found in .env file.")
        return errors
    for _, row in defaulters_df.iterrows():
        receiver_email = row.get('Email')
        if receiver_email and "@" in str(receiver_email):
            # Re-using send_email, which is assumed to be defined below
            success, error_msg = send_email(
                receiver_email=receiver_email,
                student_name=row["Name"],
                percentage=f"{row['Percentage']:.2f}",
                subject_name=subject_name,
                sender_email=sender_email,
                sender_password=sender_password
            )
            if not success:
                errors.append(f"Failed to send to {row['Name']}: {error_msg}")
        else:
            errors.append(f"Skipped {row['Name']}: Invalid or missing email.")
    return errors

# ... (send_email is unchanged) ...
def send_email(receiver_email, student_name, percentage, subject_name, sender_email, sender_password) -> Tuple[bool, str]:
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Low Attendance Warning: {subject_name}"
        message["From"] = sender_email
        message["To"] = receiver_email
        html = f"""
        <html><body>
            <p>Dear {student_name},</p>
            <p>This is an automated notification to inform you that your attendance for <strong>'{subject_name}'</strong> is currently <strong>{percentage}%</strong>, which is below the threshold.</p>
            <p>Please ensure you attend future lectures regularly.</p>
        </body></html>
        """
        message.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True, ""
    except Exception as e:
        print(f"Failed to send email to {receiver_email}: {e}")
        return False, str(e)
# ============================================
# NEW PDF REPORTING & AUTOMATION FUNCTIONS
# ============================================

# --- NEW: Helper Class for PDF Generation ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'Hajri.ai - Attendance Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- NEW: Main PDF Generation Function ---
def generate_pdf_report(subject_name: str, metrics: dict, full_report_df: pd.DataFrame) -> bytes:
    """Generates a PDF report from dashboard data."""
    pdf = PDF()
    pdf.add_page(orientation='L') # Landscape mode for more columns
    pdf.set_font('Helvetica', '', 12)

    # --- Summary Section ---
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, f"Summary for Subject: {subject_name}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, f"  - Total Students Enrolled: {metrics['total_students']}", 0, 1, 'L')
    pdf.cell(0, 8, f"  - Total Lectures Taken: {metrics['total_lectures']}", 0, 1, 'L')
    pdf.cell(0, 8, f"  - Overall Class Attendance: {metrics['overall_attendance']:.2f}%", 0, 1, 'L')
    pdf.ln(10)

    # --- Table Section ---
    pdf.set_font('Helvetica', 'B', 10)
    
    # Filter to essential columns and shorten lecture names if needed
    display_cols = ['name', 'username'] + [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email', 'Total', 'Percentage']] + ['Percentage']
    report_table_df = full_report_df[display_cols].rename(columns={"name": "Name", "username": "Enrollment"})

    # Dynamic Column Widths
    page_width = pdf.w - 2 * pdf.l_margin
    base_col_width = page_width * 0.15  # For Name and Enrollment
    percent_col_width = page_width * 0.10 # For Percentage
    num_lecture_cols = len(display_cols) - 3 # Exclude Name, Enrollment, Percentage
    
    if num_lecture_cols > 0:
        lecture_col_width = (page_width - (2 * base_col_width) - percent_col_width) / num_lecture_cols
    else:
        lecture_col_width = 0

    # Ensure lecture columns are not too wide if there are few
    lecture_col_width = min(lecture_col_width, 30) # Max width for a lecture column
    
    col_widths = [base_col_width, base_col_width] + [lecture_col_width] * num_lecture_cols + [percent_col_width]
    
    # Headers
    for i, header in enumerate(report_table_df.columns):
        # Shorten long lecture names for header display
        display_header = (str(header)[:8] + '..') if len(str(header)) > 10 else str(header)
        pdf.cell(col_widths[i], 10, display_header, 1, 0, 'C')
    pdf.ln()

    # Rows
    pdf.set_font('Helvetica', '', 9)
    for _, row in report_table_df.iterrows():
        for i, item in enumerate(row):
            if isinstance(item, float):
                display_item = f"{item:.1f}%"
            else:
                display_item = str(item)
            pdf.cell(col_widths[i], 10, display_item, 1, 0, 'C')
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')

# --- NEW: Function for Automation Script ---
def get_all_subjects_for_automation() -> Dict[str, int]:
    """Gets all subjects from the DB, for use in automated scripts."""
    conn = connect_db()
    try:
        df = pd.read_sql_query("SELECT subject_id, subject_name FROM subjects", conn)
        return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()
    finally:
        conn.close()
        
# In hajri_utils.py

def get_base64_image(image_path):
    """Encodes an image to base64 for embedding in HTML."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        print(f"Error: {image_path} not found for base64 encoding.")
        return ""
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return ""

# ... (rest of your hajri_utils.py code)
