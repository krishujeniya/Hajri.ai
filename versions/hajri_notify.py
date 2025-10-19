# hajri_notify.py

import hajri_utils as utils
from dotenv import load_dotenv
import os
from datetime import datetime

def send_all_defaulter_reports():
    """
    This function runs through all subjects, finds defaulters, and sends emails.
    It's designed to be run by a scheduler (e.g., cron job).
    """
    print(f"[{datetime.now()}] --- Starting Weekly Defaulter Report ---")
    
    # Load environment variables (for email credentials)
    load_dotenv()
    
    if not os.getenv("SENDER_EMAIL") or not os.getenv("SENDER_PASSWORD"):
        print("ERROR: SENDER_EMAIL or SENDER_PASSWORD not found in .env file. Exiting.")
        return

    # 1. Get all subjects from the database
    all_subjects = utils.get_all_subjects_for_automation()
    if not all_subjects:
        print("No subjects found in the database. Exiting.")
        return
        
    print(f"Found {len(all_subjects)} subjects to check.")

    # 2. Loop through each subject
    for subject_name, subject_id in all_subjects.items():
        print(f"\nChecking subject: '{subject_name}'...")
        
        # 3. Get dashboard data for the subject (using a fixed threshold)
        # We pass a dummy admin user_id and role to get_subjects inside get_dashboard_data
        # This is a small hack; a better way would be to refactor get_dashboard_data
        # but this works without changing too much existing code.
        try:
            data = utils.get_dashboard_data(subject_id, threshold=75) # Fixed threshold of 75%
            
            if data['status'] == 'ok':
                defaulters_df = data.get('defaulters')
                if defaulters_df is not None and not defaulters_df.empty:
                    print(f"Found {len(defaulters_df)} defaulter(s). Sending emails...")
                    
                    # 4. Send emails to defaulters
                    errors = utils.email_defaulters(defaulters_df, subject_name)
                    
                    if not errors:
                        print("All emails sent successfully.")
                    else:
                        print("Some errors occurred while sending emails:")
                        for error in errors:
                            print(f"  - {error}")
                else:
                    print("No defaulters found for this subject. All good!")
            else:
                print(f"Could not process dashboard data: {data['message']}")

        except Exception as e:
            print(f"An unexpected error occurred while processing '{subject_name}': {e}")

    print(f"\n[{datetime.now()}] --- Weekly Defaulter Report Finished ---")


if __name__ == "__main__":
    send_all_defaulter_reports()