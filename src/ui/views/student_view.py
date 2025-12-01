import streamlit as st
from src.services.attendance_service import AttendanceService

def student_app(authenticator):
    tab_titles = ["My Attendance", "👤 Profile"]
    tabs = st.tabs(tab_titles)

    # --- TAB 1: ATTENDANCE REPORT ---
    with tabs[0]:
        st.header("My Attendance Report")
        report_data = AttendanceService.get_student_report(st.session_state['user_id'])
        
        if report_data['status'] == 'fail': st.warning(report_data['message'])
        else:
            st.info(f"Enrolled in {len(report_data['subjects'])} subject(s).")
            for subject_report in report_data['subjects']:
                with st.container(border=True):
                    sub_name = subject_report['subject_name']
                    st.subheader(f"Subject: {sub_name}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Lectures", subject_report['total_lectures'])
                    c2.metric("Attended", subject_report['present'])
                    c3.metric("Overall", f"{subject_report['percentage']:.2f}%")
                    
                    with st.expander("View Details"): 
                        st.dataframe(subject_report['attendance_df'], use_container_width=True)

    # --- TAB 2: PROFILE (Student) ---
    with tabs[1]:
        st.header(f"👤 My Profile ({st.session_state['role'].title()})")
        try:
            if authenticator.update_user_details('Update Profile', location='main'):
                st.success('Profile details updated successfully')
                st.rerun()
        except Exception as e: st.error(f"Error updating profile: {e}")
        st.markdown("---")
        try:
            if authenticator.reset_password('Change Password', location='main'):
                st.success('Password modified successfully. You might need to log in again with the new password.')
        except Exception as e: st.error(f"Error changing password: {e}")
