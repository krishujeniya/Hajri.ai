import pandas as pd
import streamlit as st
from src.database.db_manager import DBManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AttendanceService:
    @staticmethod
    @st.cache_data(ttl=3600)
    def get_dashboard_data(subject_id: int, threshold: int):
        conn = DBManager.connect_db()
        if not conn: return {"status": "fail", "message": "Database connection failed."}
        
        try:
            total_students = pd.read_sql_query("SELECT COUNT(*) FROM student_subjects WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
            total_lectures = pd.read_sql_query("SELECT COUNT(*) FROM lectures WHERE subject_id = ?", conn, params=(subject_id,)).iloc[0,0]
            
            if total_students == 0: return {"status": "fail", "message": "No students enrolled."}
            if total_lectures == 0: return {"status": "fail", "message": "No lectures taken."}
            
            base_query = """
                SELECT a.user_id, u.username, u.name, u.email, l.lecture_name, a.status 
                FROM attendance a 
                JOIN lectures l ON a.lecture_id = l.lecture_id 
                JOIN users u ON a.user_id = u.user_id 
                WHERE l.subject_id = ? AND u.role = 'student'
            """
            df = pd.read_sql_query(base_query, conn, params=(subject_id,))
            
            if df.empty: return {"status": "fail", "message": "No attendance data."}
            
            full_report_df = df.pivot_table(index=['user_id', 'username', 'name', 'email'], columns='lecture_name', values='status', aggfunc='first').reset_index()
            full_report_df.columns.name = None
            
            lecture_cols = [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email']]
            full_report_df["Total"] = full_report_df[lecture_cols].apply(lambda x: (x == "P").sum(), axis=1)
            full_report_df["Percentage"] = (full_report_df["Total"] / total_lectures) * 100
            
            overall_att = full_report_df["Percentage"].mean()
            
            defaulters = full_report_df[full_report_df["Percentage"] < threshold][["username", "name", "email", "Percentage"]].rename(columns={"username": "Enrollment", "name": "Name", "email": "Email"})
            
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
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {"status": "fail", "message": f"Error: {e}"}
        finally:
            conn.close()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_student_report(user_id: int) -> dict:
        subjects_dict = DBManager.get_subjects(user_id, 'student')
        report = {"status": "ok", "subjects": []}
        
        if not subjects_dict: return {"status": "fail", "message": "Not enrolled in any subjects."}
        
        conn = DBManager.connect_db()
        if not conn: return {"status": "fail", "message": "Database connection failed."}
        
        try:
            for subject_name, subject_id in subjects_dict.items():
                lectures_df = pd.read_sql_query("SELECT lecture_id, lecture_name, date FROM lectures WHERE subject_id = ?", conn, params=(subject_id,))
                total_lectures = len(lectures_df)
                
                if total_lectures == 0: 
                    report["subjects"].append({
                        "subject_name": subject_name, 
                        "total_lectures": 0, 
                        "present": 0, 
                        "percentage": 100, 
                        "attendance_df": pd.DataFrame(columns=["Lecture", "Date", "Status"]) 
                    })
                    continue
                
                query = """
                    SELECT l.lecture_name, l.date, a.status 
                    FROM attendance a 
                    JOIN lectures l ON a.lecture_id = l.lecture_id 
                    WHERE a.user_id = ? AND l.subject_id = ? 
                    ORDER BY l.date
                """
                attendance_df = pd.read_sql_query(query, conn, params=(user_id, subject_id)).rename(columns={"lecture_name": "Lecture", "date": "Date", "status": "Status"})
                
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
        except Exception as e:
            logger.error(f"Error getting student report: {e}")
            return {"status": "fail", "message": f"Error: {e}"}
        finally:
            conn.close()
