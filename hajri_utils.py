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
import base64
from fpdf import FPDF
import streamlit as st # Import streamlit for caching decorators

load_dotenv()

# ============================================
# CONFIGURATION & DATABASE (Mostly Unchanged)
# ============================================
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "hajri.db")
MODELS_DIR = os.path.join(DATA_DIR, "models")
TRAINING_IMAGES_DIR = os.path.join(DATA_DIR, "training_images")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(TRAINING_IMAGES_DIR, exist_ok=True)
transform = A.Compose([A.HorizontalFlip(p=0.5),A.RandomBrightnessContrast(p=0.3),A.ShiftScaleRotate(p=0.4),A.GaussNoise(p=0.2),A.MotionBlur(p=0.2),A.Resize(224, 224)])

# @st.cache_resource is useful for global resources like DB connections, but
# for SQLite it's generally better to open/close connection per function call
# to avoid multithreading issues. So, we won't cache connect_db directly.
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# init_db is only called once at startup, so no need to cache
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL, email TEXT, password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student'))
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT, subject_name TEXT NOT NULL UNIQUE
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teacher_subjects (
        user_id INTEGER, subject_id INTEGER, PRIMARY KEY (user_id, subject_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_subjects (
        user_id INTEGER, subject_id INTEGER, PRIMARY KEY (user_id, subject_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        lecture_id INTEGER PRIMARY KEY AUTOINCREMENT, subject_id INTEGER NOT NULL,
        lecture_name TEXT NOT NULL, date TEXT NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE,
        UNIQUE(subject_id, lecture_name)
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT, lecture_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('P', 'A')),
        FOREIGN KEY (lecture_id) REFERENCES lectures (lecture_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        UNIQUE(lecture_id, user_id)
    );""")
    conn.commit()
    conn.close()
    create_first_admin()

def create_first_admin():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        try:
            default_user = os.getenv("ADMIN_USERNAME", "admin")
            default_pass = os.getenv("ADMIN_PASSWORD", "changeme") # Use a placeholder if not set
            if default_pass == "changeme" and os.getenv("ADMIN_PASSWORD") is None:
                 print("\nWARNING: ADMIN_PASSWORD not set in .env. Using insecure 'changeme'. Set ADMIN_PASSWORD.\n")

            hashed_password = stauth.Hasher().hash(default_pass)
            cursor.execute(
                "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                (default_user, 'Default Admin', 'admin@example.com', hashed_password, 'admin')
            )
            conn.commit()
            print(f"Created default admin user. Username: '{default_user}' (Password from .env or 'changeme')")
        except Exception as e:
            print(f"Error creating default admin: {e}")
    conn.close()

@st.cache_data(ttl=3600) # Cache for 1 hour, or clear with st.cache_data.clear()
def get_all_users_for_auth() -> dict:
    conn = connect_db()
    try:
        users = pd.read_sql_query("SELECT username, name, password, email FROM users", conn) # Added email
        credentials = {"usernames": {}}
        for _, row in users.iterrows():
            credentials["usernames"][row['username']] = {
                "name": row['name'], "password": row['password'], "email": row['email'] # Added email
            }
        return credentials
    finally:
        conn.close()

@st.cache_data(ttl=3600)
def get_user_by_username(username: str) -> dict:
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role, name, email FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user: return {"user_id": user[0], "role": user[1], "name": user[2], "email": user[3]}
        return {}
    finally:
        conn.close()

# Functions that modify the DB should clear relevant caches
def create_user(username, name, email, password, role) -> Tuple[bool, str]:
    if not all([username, name, password, role]): return False, "Missing fields."
    conn = connect_db()
    try:
        hashed_password = stauth.Hasher().hash(password)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
            (username, name, email, hashed_password, role)
        )
        conn.commit()
        if role == 'student': os.makedirs(os.path.join(TRAINING_IMAGES_DIR, str(username)), exist_ok=True)
        return True, f"User '{name}' ({role}) created."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' exists."
    finally:
        conn.close()
        st.cache_data.clear() # Clear all st.cache_data to be safe
@st.cache_data(ttl=3600)
def get_lectures_for_subject(subject_id: int) -> pd.DataFrame:
    """Gets all lectures (id, name, date) for a specific subject, indexed by lecture_id."""
    conn = connect_db()
    try:
        query = """
        SELECT lecture_id, lecture_name, date 
        FROM lectures 
        WHERE subject_id = ?
        ORDER BY date DESC
        """
        df = pd.read_sql_query(query, conn, params=(subject_id,))
        # Set lecture_id as the index so it can be easily used in select boxes
        if not df.empty:
            df = df.set_index('lecture_id')
        return df
    except Exception as e:
        print(f"Error getting lectures for subject: {e}")
        return pd.DataFrame(columns=["lecture_name", "date"])
    finally:
        conn.close()
        
@st.cache_data(ttl=3600)
def get_users_by_role(role: str) -> pd.DataFrame:
    conn = connect_db()
    try:
        query = "SELECT user_id, username, name, email FROM users WHERE role = ? ORDER BY name"
        df = pd.read_sql_query(query, conn, params=(role,))
        if role == 'student': df = df.rename(columns={"username": "Enrollment", "user_id":"Student_ID"})
        return df
    finally: conn.close()

def delete_user(user_id: int) -> Tuple[bool, str]:
    conn = connect_db()
    try:
        cursor = conn.cursor(); cursor.execute("SELECT username, role FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone();
        if not user_data: return False, "User not found."
        username, role = user_data
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,)); conn.commit()
        if role == 'student':
            img_folder = os.path.join(TRAINING_IMAGES_DIR, str(username))
            if os.path.exists(img_folder): shutil.rmtree(img_folder)
            train_model() # Retrain model if student images were deleted
        return True, f"Deleted user {username}."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

@st.cache_data(ttl=3600)
def get_subjects(user_id: int, role: str) -> Dict[str, int]:
    conn = connect_db()
    try:
        if role == 'admin': query, params = "SELECT subject_id, subject_name FROM subjects ORDER BY subject_name", ()
        elif role == 'teacher': query, params = "SELECT s.subject_id, s.subject_name FROM subjects s JOIN teacher_subjects ts ON s.subject_id = ts.subject_id WHERE ts.user_id = ? ORDER BY s.subject_name", (user_id,)
        elif role == 'student': query, params = "SELECT s.subject_id, s.subject_name FROM subjects s JOIN student_subjects ss ON s.subject_id = ss.subject_id WHERE ss.user_id = ? ORDER BY s.subject_name", (user_id,)
        else: return {}
        df = pd.read_sql_query(query, conn, params=params)
        return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()
    finally: conn.close()

def add_subject(subject_name: str) -> Tuple[bool, str]:
    conn = connect_db(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subjects (subject_name) VALUES (?)", (subject_name,)); conn.commit();
        return True, f"Subject '{subject_name}' created."
    except sqlite3.IntegrityError:
        return False, f"Subject '{subject_name}' exists."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

def delete_subject(subject_id: int) -> Tuple[bool, str]:
    conn = connect_db(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,)); conn.commit();
        return True, "Subject deleted."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

@st.cache_data(ttl=3600)
def get_unassigned_subjects_for_teacher(user_id: int) -> Dict[str, int]:
    conn=connect_db(); query="SELECT subject_id, subject_name FROM subjects WHERE subject_id NOT IN (SELECT subject_id FROM teacher_subjects WHERE user_id = ?)"; df=pd.read_sql_query(query,conn,params=(user_id,)); conn.close(); return pd.Series(df.subject_id.values,index=df.subject_name).to_dict()

def assign_teacher_to_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
    conn=connect_db(); cursor=conn.cursor()
    try:
        cursor.execute("INSERT INTO teacher_subjects (user_id, subject_id) VALUES (?, ?)", (user_id, subject_id)); conn.commit();
        return True, "Assigned."
    except sqlite3.IntegrityError:
        return False, "Already assigned."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

def remove_teacher_from_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
    conn=connect_db(); cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM teacher_subjects WHERE user_id = ? AND subject_id = ?", (user_id, subject_id)); conn.commit();
        return True, "Removed."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

@st.cache_data(ttl=3600)
def get_students_for_subject(subject_id: int) -> pd.DataFrame:
    conn = connect_db()
    try:
        query = "SELECT u.user_id, u.username, u.name FROM users u JOIN student_subjects ss ON u.user_id = ss.user_id WHERE ss.subject_id = ? AND u.role = 'student' ORDER BY u.name"
        df = pd.read_sql_query(query, conn, params=(subject_id,))
        df = df.rename(columns={"username": "Enrollment", "user_id": "user_id_student"})
        return df
    finally: conn.close()

def add_multiple_students_to_subject(subject_id: int, student_user_ids: List[int]) -> Tuple[int, List[str]]:
    """Adds multiple students to a subject, returning count and errors."""
    success_count = 0
    errors = []
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT lecture_id FROM lectures WHERE subject_id = ?", (subject_id,))
        existing_lectures = cursor.fetchall()

        for user_id in student_user_ids:
            try:
                cursor.execute("INSERT INTO student_subjects (user_id, subject_id) VALUES (?, ?)", (user_id, subject_id))
                for (lec_id,) in existing_lectures:
                    cursor.execute("INSERT OR IGNORE INTO attendance (lecture_id, user_id, status) VALUES (?, ?, 'A')", (lec_id, user_id))
                success_count += 1
            except sqlite3.IntegrityError:
                errors.append(f"Student ID {user_id} might already be in subject.")
            except Exception as e:
                 errors.append(f"Error adding Student ID {user_id}: {e}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        errors.append(f"Major error during bulk add: {e}")
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches
    return success_count, errors

def remove_multiple_students_from_subject(subject_id: int, student_user_ids: List[int]) -> Tuple[int, List[str]]:
    """Removes multiple students from a subject, returning count and errors."""
    success_count = 0
    errors = []
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT lecture_id FROM lectures WHERE subject_id = ?", (subject_id,))
        lecture_ids = cursor.fetchall()
        lec_id_tuples = tuple([l[0] for l in lecture_ids]) if lecture_ids else tuple()
        placeholder_lectures = ','.join('?' for _ in lec_id_tuples)

        ids_tuple = tuple(student_user_ids)
        placeholder_students = ','.join('?' for _ in ids_tuple)

        query_link = f"DELETE FROM student_subjects WHERE subject_id = ? AND user_id IN ({placeholder_students})"
        params_link = (subject_id,) + ids_tuple
        cursor.execute(query_link, params_link)
        deleted_links = cursor.rowcount

        if lec_id_tuples:
            query_att = f"DELETE FROM attendance WHERE lecture_id IN ({placeholder_lectures}) AND user_id IN ({placeholder_students})"
            params_att = lec_id_tuples + ids_tuple
            cursor.execute(query_att, params_att)

        conn.commit()
        success_count = deleted_links
    except Exception as e:
        conn.rollback()
        errors.append(f"Major error during bulk remove: {e}")
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches
    return success_count, errors

def add_new_lecture(subject_id: int, lecture_name: str) -> int:
    conn=connect_db(); cursor=conn.cursor(); date_str=datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        cursor.execute("INSERT INTO lectures (subject_id, lecture_name, date) VALUES (?, ?, ?)", (subject_id, lecture_name, date_str)); lecture_id=cursor.lastrowid
        cursor.execute("SELECT user_id FROM student_subjects WHERE subject_id = ?", (subject_id,)); students=cursor.fetchall()
        attendance_records=[(lecture_id, s[0], 'A') for s in students]
        if attendance_records: cursor.executemany("INSERT INTO attendance (lecture_id, user_id, status) VALUES (?, ?, ?)", attendance_records)
        conn.commit();
        return lecture_id
    except sqlite3.IntegrityError:
        conn.rollback(); raise ValueError(f"Lecture '{lecture_name}' exists.")
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

def remove_lecture_from_subject(lecture_id: int):
    conn=connect_db(); cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM lectures WHERE lecture_id = ?", (lecture_id,)); conn.commit();
        return True, "Lecture removed."
    finally:
        conn.close();
        st.cache_data.clear() # Clear caches

def mark_attendance(lecture_id: int, edited_df: pd.DataFrame):
    conn=connect_db(); cursor=conn.cursor(); update_data=[]
    try:
        for _, row in edited_df.iterrows(): status="P" if row["Marked_Present"] else "A"; user_id=row["user_id_student"]; update_data.append((status, lecture_id, user_id))
        cursor.executemany("UPDATE attendance SET status = ? WHERE lecture_id = ? AND user_id = ?", update_data); conn.commit()
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

def mark_manual_attendance(lecture_id: int, enrollment: str):
    conn=connect_db(); cursor=conn.cursor()
    try:
        cursor.execute("SELECT user_id, name FROM users WHERE username = ? AND role = 'student'", (enrollment,)); student=cursor.fetchone()
        if not student: return False, f"Student '{enrollment}' not found."
        student_user_id, student_name = student
        cursor.execute("SELECT attendance_id FROM attendance WHERE lecture_id = ? AND user_id = ?", (lecture_id, student_user_id)); record=cursor.fetchone()
        if not record: return False, f"Student not in subject."
        cursor.execute("UPDATE attendance SET status = 'P' WHERE attendance_id = ?", (record[0],)); conn.commit()
        return True, f"Marked {student_name} ({enrollment}) as Present."
    finally:
        conn.close()
        st.cache_data.clear() # Clear caches

@st.cache_data(ttl=3600)
def get_attendance_for_lecture(lecture_id: int) -> pd.DataFrame:
    """Gets attendance details (student name, enrollment, status) for a specific lecture."""
    conn = connect_db()
    try:
        query = """
        SELECT u.username AS Enrollment, u.name AS Name, a.status AS Status
        FROM attendance a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.lecture_id = ? AND u.role = 'student'
        ORDER BY u.name
        """
        df = pd.read_sql_query(query, conn, params=(lecture_id,))
        return df
    except Exception as e:
        print(f"Error getting lecture attendance: {e}")
        return pd.DataFrame(columns=["Enrollment", "Name", "Status"])
    finally:
        conn.close()

@st.cache_data(ttl=3600)
def get_dashboard_data(subject_id: int, threshold: int):
    conn = connect_db()
    try:
        total_students = pd.read_sql_query("SELECT COUNT(*) FROM student_subjects WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
        total_lectures = pd.read_sql_query("SELECT COUNT(*) FROM lectures WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
        if total_students == 0: return {"status": "fail", "message": "No students enrolled."}
        if total_lectures == 0: return {"status": "fail", "message": "No lectures taken."}
        base_query = "SELECT a.user_id, u.username, u.name, u.email, l.lecture_name, a.status FROM attendance a JOIN lectures l ON a.lecture_id = l.lecture_id JOIN users u ON a.user_id = u.user_id WHERE l.subject_id = ? AND u.role = 'student'"
        df = pd.read_sql_query(base_query, conn, params=(subject_id,));
        if df.empty: return {"status": "fail", "message": "No attendance data."}
        full_report_df = df.pivot_table(index=['user_id', 'username', 'name', 'email'], columns='lecture_name', values='status', aggfunc='first').reset_index(); full_report_df.columns.name = None
        lecture_cols = [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email']]
        full_report_df["Total"] = full_report_df[lecture_cols].apply(lambda x: (x == "P").sum(), axis=1)
        full_report_df["Percentage"] = (full_report_df["Total"] / total_lectures) * 100
        overall_att = full_report_df["Percentage"].mean()
        defaulters = full_report_df[full_report_df["Percentage"] < threshold][["username", "name", "email", "Percentage"]].rename(columns={"username": "Enrollment", "name": "Name", "email": "Email"})
        trends_series = full_report_df[lecture_cols].apply(lambda x: (x == "P").sum()); trends = trends_series.reset_index(); trends.columns = ["Lecture", "Present Count"]
        return {"status": "ok", "metrics": {"total_students": total_students, "total_lectures": total_lectures, "overall_attendance": overall_att,}, "defaulters": defaulters, "trends": trends, "full_report": full_report_df}
    finally: conn.close()

@st.cache_data(ttl=3600)
def get_student_report(user_id: int) -> dict:
    subjects_dict = get_subjects(user_id, 'student'); report = {"status": "ok", "subjects": []}
    if not subjects_dict: return {"status": "fail", "message": "Not enrolled in any subjects."}
    conn = connect_db()
    try:
        for subject_name, subject_id in subjects_dict.items():
            lectures_df = pd.read_sql_query("SELECT lecture_id, lecture_name, date FROM lectures WHERE subject_id = ?", conn, params=(subject_id,)); total_lectures = len(lectures_df)
            if total_lectures == 0: report["subjects"].append({"subject_name": subject_name, "total_lectures": 0, "present": 0, "percentage": 100, "attendance_df": pd.DataFrame(columns=["Lecture", "Date", "Status"]) }); continue
            query = "SELECT l.lecture_name, l.date, a.status FROM attendance a JOIN lectures l ON a.lecture_id = l.lecture_id WHERE a.user_id = ? AND l.subject_id = ? ORDER BY l.date"
            attendance_df = pd.read_sql_query(query, conn, params=(user_id, subject_id)).rename(columns={"lecture_name": "Lecture", "date": "Date", "status": "Status"})
            present_count = (attendance_df["Status"] == "P").sum(); percentage = (present_count / total_lectures) * 100
            report["subjects"].append({"subject_name": subject_name, "total_lectures": total_lectures, "present": present_count, "percentage": percentage, "attendance_df": attendance_df})
        return report
    finally: conn.close()


def save_image_for_student(enrollment_username, name, image, capture_count):
    folder = os.path.join(TRAINING_IMAGES_DIR, str(enrollment_username)); os.makedirs(folder, exist_ok=True); path = os.path.join(folder, f"{capture_count}.jpg"); image.save(path); return path

def augment_training_images(enrollment_username, num_originals=10, num_target_total=50):
    folder = os.path.join(TRAINING_IMAGES_DIR, str(enrollment_username)); all_files = os.listdir(folder)
    for f in all_files:
        try: file_num = int(f.split('.')[0]);
        except ValueError: continue
        if file_num > num_originals: os.remove(os.path.join(folder, f))
    original_images = []
    for i in range(1, num_originals + 1):
        img_path = os.path.join(folder, f"{i}.jpg")
        if os.path.exists(img_path): image = cv2.imread(img_path);
        else: continue
        if image is None: continue; image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB); original_images.append(image)
    if not original_images: return False, "No original images found."
    num_to_generate = num_target_total - len(original_images)
    if num_to_generate <= 0: return True, "Sufficient images exist."
    current_img_count = num_originals + 1
    for _ in range(num_to_generate):
        base_image = original_images[np.random.randint(0, len(original_images))]; augmented = transform(image=base_image)['image']
        save_path = os.path.join(folder, f"{current_img_count}.jpg"); augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR); cv2.imwrite(save_path, augmented_bgr); current_img_count += 1
    return True, f"Generated {num_to_generate} new images."

# Use st.cache_resource for heavy AI model operations.
# This ensures DeepFace.find only re-initializes when db_path changes or explicitly cleared.
@st.cache_resource
def train_model_cached():
    """Wrapper for train_model to allow caching."""
    # The actual DeepFace.find call that builds the representations.pkl
    # is the heavy part.
    try:
        pkl_path = os.path.join(TRAINING_IMAGES_DIR, "representations_SFace.pkl")
        if os.path.exists(pkl_path):
            os.remove(pkl_path) # Always delete old pkl to force rebuild
        
        student_dirs = [d for d in os.listdir(TRAINING_IMAGES_DIR) if os.path.isdir(os.path.join(TRAINING_IMAGES_DIR, d))]
        if not student_dirs: return False, "No student images found for training."
        
        has_images = any(len(os.listdir(os.path.join(TRAINING_IMAGES_DIR, d))) > 0 for d in student_dirs)
        if not has_images: return False, "Student folders are empty, cannot train."
        
        # DeepFace.find needs at least one image to initialize the model and create representations.
        # We find a sample image from any student to trigger this.
        sample_img_path = None
        for student_dir in student_dirs:
            student_path = os.path.join(TRAINING_IMAGES_DIR, student_dir)
            images = [f for f in os.listdir(student_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            if images:
                sample_img_path = os.path.join(student_path, images[0])
                break
        
        if sample_img_path is None: return False, "Could not find valid sample image to initiate training."
        
        # This call will build the representations_SFace.pkl file in TRAINING_IMAGES_DIR
        DeepFace.find(img_path=sample_img_path, db_path=TRAINING_IMAGES_DIR, model_name="SFace", enforce_detection=False, silent=True)
        return True, "Model (re)trained successfully!"
    except Exception as e:
        return False, f"Training failed: {e}"

# Modified `train_model` to clear cache and call the cached version
def train_model():
    """Public facing train_model that clears the cache and calls the cached version."""
    train_model_cached.clear() # Clear the cached resource to force re-run
    return train_model_cached()


# @st.cache_data is not ideal here as the input image changes often.
# DeepFace.find itself is heavy, and caching its *results* would be tied to the exact image.
# We'll keep this as a direct call.
def recognize_face_in_image(pil_image):
    try:
        pkl_path = os.path.join(TRAINING_IMAGES_DIR, "representations_SFace.pkl");

        
        img_np = np.array(pil_image.convert('RGB')); 
        
        # DeepFace.find can be slow. Consider running this in a separate thread if it becomes a bottleneck,
        # but for simplicity, we'll keep it synchronous for now and let Streamlit's spinner handle it.
        results_list = DeepFace.find(img_path=img_np, db_path=TRAINING_IMAGES_DIR, model_name="SFace", enforce_detection=False, detector_backend='opencv', silent=True)
        recognized_data = []
        
        # Fetch students once outside the loop for efficiency
        students_df = get_users_by_role('student');
        if students_df.empty: return pd.DataFrame(), pd.DataFrame()
        
        # results_list can contain multiple dataframes if multiple faces detected
        for results_df in results_list:
            if not results_df.empty:
                # Top match for *each* detected face
                for _, top_match in results_df.iterrows(): # Iterate over all matches for each face
                    x, y, w, h = top_match['source_x'], top_match['source_y'], top_match['source_w'], top_match['source_h']
                    
                    # Ensure cropped_face is valid before liveness check
                    pad = 10;
                    cropped_face = img_np[max(0, y-pad):min(y+h+pad, img_np.shape[0]), max(0, x-pad):min(x+w+pad, img_np.shape[1])]
                    
                    if cropped_face.size == 0: continue
                    
                    is_real = True
                    
                    file_path = top_match["identity"]; 
                    if not isinstance(file_path, str): # Handle cases where identity might be None or not a string
                        continue
                    enroll_username = file_path.split(os.sep)[-2]
                    
                    student_row = students_df[students_df["Enrollment"].astype(str) == str(enroll_username)]
                    if not student_row.empty: 
                        recognized_data.append({"Enrollment": enroll_username, "Name": student_row.iloc[0]["name"], "Distance": round(top_match["distance"], 3), "x": x, "y": y, "w": w, "h": h, "is_real": is_real})
        
        if recognized_data: 
            all_results_df = pd.DataFrame(recognized_data)
            live_students_df = all_results_df[all_results_df["is_real"] == True]
            unique_live_students_df = live_students_df.drop_duplicates(subset=["Enrollment"])[["Enrollment", "Name"]]
            return all_results_df, unique_live_students_df
        else: 
            return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        if "representations_SFace.pkl" in str(e): print("Model not trained.");
        else: print(f"Recognition error: {e}"); 
        return pd.DataFrame(), pd.DataFrame()


# Caching `draw_on_image` is tricky because it depends on `pil_img` and `results_df`.
# Since `pil_img` changes every time, direct caching is not effective.
# We'll leave it as a direct call.
def draw_on_image(pil_img, results_df):
    img_draw = pil_img.copy(); draw = ImageDraw.Draw(img_draw)
    try: font = ImageFont.load_default(size=15)
    except IOError: font = ImageFont.load_default()
    if not results_df.empty:
        for _, row in results_df.iterrows():
            x, y, w, h = row['x'], row['y'], row['w'], row['h']; name, distance, is_real = row['Name'], row['Distance'], row['is_real']
            color = "lime" if is_real else "red"; text = f"{name} ({distance})" if is_real else f"SPOOF ({name})"
            draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=3); text_bbox = draw.textbbox((x, y - 20), text, font=font); draw.rectangle(text_bbox, fill=color); draw.text((x + 2, y - 20), text, fill="black", font=font)
    return img_draw

class PDF(FPDF):
    def header(self): self.set_font('Helvetica', 'B', 15); self.cell(0, 10, 'Hajri.ai - Attendance Report', 0, 1, 'C'); self.ln(10)
    def footer(self): self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# Caching PDF generation if inputs are hashable and don't change frequently
@st.cache_data(ttl=3600)
def generate_pdf_report(subject_name: str, metrics: dict, full_report_df: pd.DataFrame) -> bytes:
    pdf = PDF(); pdf.add_page(orientation='L'); pdf.set_font('Helvetica', '', 12)
    pdf.set_font('Helvetica', 'B', 14); pdf.cell(0, 10, f"Summary: {subject_name}", 0, 1, 'L'); pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, f"  Students: {metrics['total_students']}", 0, 1, 'L'); pdf.cell(0, 8, f"  Lectures: {metrics['total_lectures']}", 0, 1, 'L'); pdf.cell(0, 8, f"  Overall Attendance: {metrics['overall_attendance']:.2f}%", 0, 1, 'L'); pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 10)
    display_cols = ['name', 'username'] + [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email', 'Total', 'Percentage']] + ['Percentage']
    report_table_df = full_report_df[display_cols].rename(columns={"name": "Name", "username": "Enrollment"})
    page_width = pdf.w - 2 * pdf.l_margin; base_col_width = page_width * 0.15; percent_col_width = page_width * 0.10
    num_lecture_cols = len(display_cols) - 3; lecture_col_width = (page_width - (2 * base_col_width) - percent_col_width) / num_lecture_cols if num_lecture_cols > 0 else 0; lecture_col_width = min(lecture_col_width, 30)
    col_widths = [base_col_width, base_col_width] + [lecture_col_width] * num_lecture_cols + [percent_col_width]
    for i, header in enumerate(report_table_df.columns): display_header = (str(header)[:8] + '..') if len(str(header)) > 10 else str(header); pdf.cell(col_widths[i], 10, display_header, 1, 0, 'C'); pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    for _, row in report_table_df.iterrows():
        for i, item in enumerate(row): display_item = f"{item:.1f}%" if isinstance(item, float) else str(item); pdf.cell(col_widths[i], 10, display_item, 1, 0, 'C'); pdf.ln()
    return bytes(pdf.output(dest='S'))

@st.cache_data(ttl=3600)
def get_all_subjects_for_automation() -> Dict[str, int]:
    conn=connect_db(); df=pd.read_sql_query("SELECT subject_id, subject_name FROM subjects", conn); conn.close(); return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()

def send_email(receiver_email, student_name, percentage, subject_name, sender_email, sender_password) -> Tuple[bool, str]:
    try:
        message = MIMEMultipart("alternative"); message["Subject"] = f"Low Attendance: {subject_name}"; message["From"] = sender_email; message["To"] = receiver_email
        html = f"<html><body><p>Dear {student_name},</p><p>Your attendance for <strong>'{subject_name}'</strong> is currently <strong>{percentage}%</strong>.</p></body></html>"
        message.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server: server.starttls(); server.login(sender_email, sender_password); server.sendmail(sender_email, receiver_email, message.as_string())
        return True, ""
    except Exception as e: print(f"Email fail: {e}"); return False, str(e)

def email_defaulters(defaulters_df: pd.DataFrame, subject_name: str) -> List[str]:
    errors = []; sender_email = os.getenv("SENDER_EMAIL"); sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return ["Email credentials not set."]
    for _, row in defaulters_df.iterrows():
        receiver_email = row.get('Email')
        if receiver_email and "@" in str(receiver_email):
            success, error_msg = send_email(receiver_email, row["Name"], f"{row['Percentage']:.2f}", subject_name, sender_email, sender_password)
            if not success: errors.append(f"Failed {row['Name']}: {error_msg}")
        else: errors.append(f"Skipped {row['Name']}: Invalid/missing email.")
    return errors

@st.cache_data(ttl=3600) # Cache the base64 string
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError: print(f"Error: {image_path} not found."); return ""
    except Exception as e: print(f"Error encoding {image_path}: {e}"); return ""
