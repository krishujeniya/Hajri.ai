"""
Email Notification Service for Hajri.ai
Handles sending attendance notifications to students
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, List
import pandas as pd

from src.config.settings import Config


def send_email(
    receiver_email: str,
    student_name: str,
    percentage: float,
    subject_name: str,
    sender_email: str = None,
    sender_password: str = None
) -> Tuple[bool, str]:
    """
    Send low attendance warning email to a student.
    
    Args:
        receiver_email: Student's email address
        student_name: Student's full name
        percentage: Current attendance percentage
        subject_name: Name of the subject
        sender_email: Sender's email (defaults to Config.SENDER_EMAIL)
        sender_password: Sender's password (defaults to Config.SENDER_PASSWORD)
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    sender_email = sender_email or Config.SENDER_EMAIL
    sender_password = sender_password or Config.SENDER_PASSWORD
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Low Attendance Alert: {subject_name}"
        message["From"] = sender_email
        message["To"] = receiver_email
        
        html = f"""
        <html>
            <body>
                <h2 style="color: #ef4444;">Low Attendance Alert</h2>
                <p>Dear <strong>{student_name}</strong>,</p>
                <p>Your attendance for <strong>'{subject_name}'</strong> is currently 
                <strong style="color: #ef4444;">{percentage:.2f}%</strong>.</p>
                <p>Please ensure you attend classes regularly to maintain the required attendance percentage.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Hajri.ai Attendance System.
                </p>
            </body>
        </html>
        """
        
        message.attach(MIMEText(html, "html"))
        
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        return True, ""
        
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False, str(e)


def email_defaulters(
    defaulters_df: pd.DataFrame,
    subject_name: str
) -> List[str]:
    """
    Send emails to all defaulters in the DataFrame.
    
    Args:
        defaulters_df: DataFrame with columns: Name, Email, Percentage
        subject_name: Name of the subject
        
    Returns:
        List of error messages (empty if all successful)
    """
    errors = []
    
    # Validate email credentials
    if not Config.SENDER_EMAIL or not Config.SENDER_PASSWORD:
        return ["Email credentials not configured in .env file"]
    
    for _, row in defaulters_df.iterrows():
        receiver_email = row.get('Email')
        
        # Validate email
        if not receiver_email or "@" not in str(receiver_email):
            errors.append(f"Skipped {row['Name']}: Invalid or missing email")
            continue
        
        # Send email
        success, error_msg = send_email(
            receiver_email=receiver_email,
            student_name=row["Name"],
            percentage=row['Percentage'],
            subject_name=subject_name
        )
        
        if not success:
            errors.append(f"Failed to send to {row['Name']}: {error_msg}")
    
    return errors


def send_bulk_defaulter_reports(threshold: int = None) -> dict:
    """
    Send defaulter reports for all subjects.
    Designed to be run by a scheduler (e.g., cron job).
    
    Args:
        threshold: Attendance percentage threshold (defaults to Config.DEFAULT_ATTENDANCE_THRESHOLD)
        
    Returns:
        Dictionary with results for each subject
    """
    from datetime import datetime
    
    threshold = threshold or Config.DEFAULT_ATTENDANCE_THRESHOLD
    results = {
        "timestamp": datetime.now().isoformat(),
        "threshold": threshold,
        "subjects": []
    }
    
    print(f"[{datetime.now()}] Starting bulk defaulter report (threshold: {threshold}%)")
    
    # This would need to import from services/attendance_service.py after migration
    # For now, keeping it as a placeholder
    print("Note: Bulk report functionality requires attendance service migration")
    
    return results
