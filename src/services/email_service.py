import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pandas as pd
from typing import Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_email(receiver_email, student_name, percentage, subject_name, sender_email, sender_password) -> Tuple[bool, str]:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Low Attendance: {subject_name}"
            message["From"] = sender_email
            message["To"] = receiver_email
            
            html = f"<html><body><p>Dear {student_name},</p><p>Your attendance for <strong>'{subject_name}'</strong> is currently <strong>{percentage}%</strong>.</p></body></html>"
            message.attach(MIMEText(html, "html"))
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server: 
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, message.as_string())
            return True, ""
        except Exception as e: 
            logger.error(f"Email fail: {e}")
            return False, str(e)

    @staticmethod
    def email_defaulters(defaulters_df: pd.DataFrame, subject_name: str) -> List[str]:
        errors = []
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        
        if not sender_email or not sender_password: return ["Email credentials not set."]
        
        for _, row in defaulters_df.iterrows():
            receiver_email = row.get('Email')
            if receiver_email and "@" in str(receiver_email):
                success, error_msg = EmailService.send_email(
                    receiver_email, 
                    row["Name"], 
                    f"{row['Percentage']:.2f}", 
                    subject_name, 
                    sender_email, 
                    sender_password
                )
                if not success: errors.append(f"Failed {row['Name']}: {error_msg}")
            else: 
                errors.append(f"Skipped {row['Name']}: Invalid/missing email.")
        return errors
