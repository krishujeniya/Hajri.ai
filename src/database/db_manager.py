import sqlite3
import pandas as pd
import os
import logging
import streamlit as st
import streamlit_authenticator as stauth
from typing import Tuple, List, Dict, Optional
from src.config.settings import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DBManager:
    @staticmethod
    def connect_db():
        """Establishes a connection to the SQLite database."""
        try:
            conn = sqlite3.connect(str(Config.DB_FILE))
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return None

    @staticmethod
    def init_db():
        """Initializes the database tables."""
        conn = DBManager.connect_db()
        if not conn:
            return

        try:
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
            DBManager.create_first_admin()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            conn.close()

    @staticmethod
    def create_first_admin():
        """Creates the default admin user if no users exist."""
        conn = DBManager.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                default_user = os.getenv("ADMIN_USERNAME", "admin")
                default_pass = os.getenv("ADMIN_PASSWORD", "changeme")
                
                if default_pass == "changeme" and os.getenv("ADMIN_PASSWORD") is None:
                     logger.warning("ADMIN_PASSWORD not set in .env. Using insecure 'changeme'.")

                hashed_password = stauth.Hasher().hash(default_pass)
                cursor.execute(
                    "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                    (default_user, 'Default Admin', 'admin@example.com', hashed_password, 'admin')
                )
                conn.commit()
                logger.info(f"Created default admin user: {default_user}")
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")
        finally:
            conn.close()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_all_users_for_auth() -> dict:
        """Retrieves all users for authentication."""
        conn = DBManager.connect_db()
        if not conn: return {"usernames": {}}

        try:
            users = pd.read_sql_query("SELECT username, name, password, email FROM users", conn)
            credentials = {"usernames": {}}
            for _, row in users.iterrows():
                credentials["usernames"][row['username']] = {
                    "name": row['name'], "password": row['password'], "email": row['email']
                }
            return credentials
        except Exception as e:
            logger.error(f"Error fetching users for auth: {e}")
            return {"usernames": {}}
        finally:
            conn.close()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_user_by_username(username: str) -> dict:
        """Retrieves user details by username."""
        conn = DBManager.connect_db()
        if not conn: return {}

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, role, name, email FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user: return {"user_id": user[0], "role": user[1], "name": user[2], "email": user[3]}
            return {}
        except Exception as e:
            logger.error(f"Error fetching user by username: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def create_user(username, name, email, password, role) -> Tuple[bool, str]:
        """Creates a new user."""
        if not all([username, name, password, role]): return False, "Missing fields."
        
        conn = DBManager.connect_db()
        if not conn: return False, "Database connection failed."

        try:
            hashed_password = stauth.Hasher().hash(password)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                (username, name, email, hashed_password, role)
            )
            conn.commit()
            
            # Create directory for student images if role is student
            if role == 'student': 
                os.makedirs(os.path.join(str(Config.TRAINING_IMAGES_DIR), str(username)), exist_ok=True)
                
            return True, f"User '{name}' ({role}) created."
        except sqlite3.IntegrityError:
            return False, f"Username '{username}' exists."
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error creating user: {e}"
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    def delete_user(user_id: int) -> Tuple[bool, str]:
        """Deletes a user."""
        conn = DBManager.connect_db()
        if not conn: return False, "Database connection failed."

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            if not user_data: return False, "User not found."
            
            username, role = user_data
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            
            # Cleanup student images is handled in ImageService usually, but we can do it here or let service handle it
            # For now, we return the info so the service can handle file cleanup if needed, 
            # OR we just do it here if we import shutil. Let's keep it simple and return success.
            # The actual file cleanup should ideally be in a service that calls this DB method.
            # However, to keep it self-contained as per previous logic:
            if role == 'student':
                import shutil
                img_folder = os.path.join(str(Config.TRAINING_IMAGES_DIR), str(username))
                if os.path.exists(img_folder): shutil.rmtree(img_folder)
                
            return True, f"Deleted user {username}."
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error deleting user: {e}"
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_subjects(user_id: int, role: str) -> Dict[str, int]:
        """Retrieves subjects based on user role."""
        conn = DBManager.connect_db()
        if not conn: return {}

        try:
            if role == 'admin': 
                query, params = "SELECT subject_id, subject_name FROM subjects ORDER BY subject_name", ()
            elif role == 'teacher': 
                query, params = "SELECT s.subject_id, s.subject_name FROM subjects s JOIN teacher_subjects ts ON s.subject_id = ts.subject_id WHERE ts.user_id = ? ORDER BY s.subject_name", (user_id,)
            elif role == 'student': 
                query, params = "SELECT s.subject_id, s.subject_name FROM subjects s JOIN student_subjects ss ON s.subject_id = ss.subject_id WHERE ss.user_id = ? ORDER BY s.subject_name", (user_id,)
            else: 
                return {}
            
            df = pd.read_sql_query(query, conn, params=params)
            return pd.Series(df.subject_id.values, index=df.subject_name).to_dict()
        except Exception as e:
            logger.error(f"Error getting subjects: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def add_subject(subject_name: str) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO subjects (subject_name) VALUES (?)", (subject_name,))
            conn.commit()
            return True, f"Subject '{subject_name}' created."
        except sqlite3.IntegrityError:
            return False, f"Subject '{subject_name}' exists."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    def delete_subject(subject_id: int) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
            conn.commit()
            return True, "Subject deleted."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_users_by_role(role: str) -> pd.DataFrame:
        conn = DBManager.connect_db()
        if not conn: return pd.DataFrame()
        try:
            query = "SELECT user_id, username, name, email FROM users WHERE role = ? ORDER BY name"
            df = pd.read_sql_query(query, conn, params=(role,))
            if role == 'student': df = df.rename(columns={"username": "Enrollment", "user_id":"Student_ID"})
            return df
        finally: conn.close()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_unassigned_subjects_for_teacher(user_id: int) -> Dict[str, int]:
        conn = DBManager.connect_db()
        if not conn: return {}
        try:
            query="SELECT subject_id, subject_name FROM subjects WHERE subject_id NOT IN (SELECT subject_id FROM teacher_subjects WHERE user_id = ?)"
            df=pd.read_sql_query(query,conn,params=(user_id,))
            return pd.Series(df.subject_id.values,index=df.subject_name).to_dict()
        finally: conn.close()

    @staticmethod
    def assign_teacher_to_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO teacher_subjects (user_id, subject_id) VALUES (?, ?)", (user_id, subject_id))
            conn.commit()
            return True, "Assigned."
        except sqlite3.IntegrityError:
            return False, "Already assigned."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    def remove_teacher_from_subject(user_id: int, subject_id: int) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor=conn.cursor()
            cursor.execute("DELETE FROM teacher_subjects WHERE user_id = ? AND subject_id = ?", (user_id, subject_id))
            conn.commit()
            return True, "Removed."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_students_for_subject(subject_id: int) -> pd.DataFrame:
        conn = DBManager.connect_db()
        if not conn: return pd.DataFrame()
        try:
            query = "SELECT u.user_id, u.username, u.name FROM users u JOIN student_subjects ss ON u.user_id = ss.user_id WHERE ss.subject_id = ? AND u.role = 'student' ORDER BY u.name"
            df = pd.read_sql_query(query, conn, params=(subject_id,))
            df = df.rename(columns={"username": "Enrollment", "user_id": "user_id_student"})
            return df
        finally: conn.close()

    @staticmethod
    def add_multiple_students_to_subject(subject_id: int, student_user_ids: List[int]) -> Tuple[int, List[str]]:
        success_count = 0
        errors = []
        conn = DBManager.connect_db()
        if not conn: return 0, ["Database connection failed"]
        
        try:
            cursor = conn.cursor()
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
            st.cache_data.clear()
        return success_count, errors

    @staticmethod
    def remove_multiple_students_from_subject(subject_id: int, student_user_ids: List[int]) -> Tuple[int, List[str]]:
        success_count = 0
        errors = []
        conn = DBManager.connect_db()
        if not conn: return 0, ["Database connection failed"]

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT lecture_id FROM lectures WHERE subject_id = ?", (subject_id,))
            lecture_ids = cursor.fetchall()
            lec_id_tuples = tuple([l[0] for l in lecture_ids]) if lecture_ids else tuple()
            
            ids_tuple = tuple(student_user_ids)
            if not ids_tuple: return 0, []

            # Construct queries safely
            placeholder_students = ','.join('?' for _ in ids_tuple)
            
            query_link = f"DELETE FROM student_subjects WHERE subject_id = ? AND user_id IN ({placeholder_students})"
            params_link = (subject_id,) + ids_tuple
            cursor.execute(query_link, params_link)
            deleted_links = cursor.rowcount

            if lec_id_tuples:
                placeholder_lectures = ','.join('?' for _ in lec_id_tuples)
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
            st.cache_data.clear()
        return success_count, errors

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_lectures_for_subject(subject_id: int) -> pd.DataFrame:
        conn = DBManager.connect_db()
        if not conn: return pd.DataFrame(columns=["lecture_name", "date"])
        try:
            query = """
            SELECT lecture_id, lecture_name, date 
            FROM lectures 
            WHERE subject_id = ?
            ORDER BY date DESC
            """
            df = pd.read_sql_query(query, conn, params=(subject_id,))
            if not df.empty:
                df = df.set_index('lecture_id')
            return df
        except Exception as e:
            logger.error(f"Error getting lectures: {e}")
            return pd.DataFrame(columns=["lecture_name", "date"])
        finally:
            conn.close()

    @staticmethod
    def add_new_lecture(subject_id: int, lecture_name: str) -> int:
        from datetime import datetime
        conn = DBManager.connect_db()
        if not conn: raise Exception("DB Connection failed")
        
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO lectures (subject_id, lecture_name, date) VALUES (?, ?, ?)", (subject_id, lecture_name, date_str))
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
            raise ValueError(f"Lecture '{lecture_name}' exists.")
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    def remove_lecture_from_subject(lecture_id: int) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lectures WHERE lecture_id = ?", (lecture_id,))
            conn.commit()
            return True, "Lecture removed."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    def mark_attendance(lecture_id: int, edited_df: pd.DataFrame):
        conn = DBManager.connect_db()
        if not conn: return
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
            st.cache_data.clear()

    @staticmethod
    def mark_manual_attendance(lecture_id: int, enrollment: str) -> Tuple[bool, str]:
        conn = DBManager.connect_db()
        if not conn: return False, "DB Error"
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name FROM users WHERE username = ? AND role = 'student'", (enrollment,))
            student = cursor.fetchone()
            if not student: return False, f"Student '{enrollment}' not found."
            
            student_user_id, student_name = student
            cursor.execute("SELECT attendance_id FROM attendance WHERE lecture_id = ? AND user_id = ?", (lecture_id, student_user_id))
            record = cursor.fetchone()
            
            if not record: return False, f"Student not in subject."
            
            cursor.execute("UPDATE attendance SET status = 'P' WHERE attendance_id = ?", (record[0],))
            conn.commit()
            return True, f"Marked {student_name} ({enrollment}) as Present."
        finally:
            conn.close()
            st.cache_data.clear()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_attendance_for_lecture(lecture_id: int) -> pd.DataFrame:
        conn = DBManager.connect_db()
        if not conn: return pd.DataFrame()
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
            logger.error(f"Error getting lecture attendance: {e}")
            return pd.DataFrame(columns=["Enrollment", "Name", "Status"])
        finally:
            conn.close()
