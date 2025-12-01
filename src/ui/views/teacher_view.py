import streamlit as st
from PIL import Image
from src.database.db_manager import DBManager
from src.services.image_service import ImageService
from src.services.attendance_service import AttendanceService
from src.services.report_service import ReportService

def teacher_app(authenticator):
    SUBJECTS_FROM_DB = DBManager.get_subjects(st.session_state['user_id'], 'teacher')
    tab_titles = ["📸 Take Attendance", "📊 Dashboard", "✍️ Manual Entry", "👤 Profile"]
    tabs = st.tabs(tab_titles)

    if not SUBJECTS_FROM_DB: st.warning("Not assigned subjects. Contact admin."); st.stop()

    # --- TAB 1: TAKE ATTENDANCE ---
    with tabs[0]:
        st.header("📸 Take Attendance")
        with st.container(border=True):
            st.subheader("Step 1: Configure")
            subject = st.selectbox("Select Subject", SUBJECTS_FROM_DB.keys(), key="att_sub_teach")
            subject_id = SUBJECTS_FROM_DB[subject]
            existing_lectures_df = DBManager.get_lectures_for_subject(subject_id)
            lecture_id = None
            lecture_name = None
            lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="att_lec_choice_teach", horizontal=True)
            
            if lec_choice == "Create New": 
                lecture_name = st.text_input("New Lecture Name", key="att_lecture_new_teach")
            else:
                if not existing_lectures_df.empty: 
                    lecture_id = st.selectbox("Select Lecture", options=existing_lectures_df.index, format_func=lambda x: existing_lectures_df.loc[x]['lecture_name'], key="att_lecture_existing_teach")
                else: st.info("No existing lectures.")
        
        if lecture_name or lecture_id:
            st.subheader("Step 2: Capture")
            mode = st.radio("Mode", ["Upload Image", "Capture Photo"], horizontal=True, key="att_mode_teach")
            img_file_buffer = None
            if mode == "Upload Image": img_file_buffer = st.file_uploader("Upload", type=['jpg', 'png', 'jpeg'], key="file_up_teach")
            elif mode == "Capture Photo": img_file_buffer = st.camera_input("Capture", key="cam_in_teach")
            
            if img_file_buffer:
                current_lecture_id = None
                try:
                    if lec_choice == "Create New" and lecture_name: 
                        current_lecture_id = DBManager.add_new_lecture(subject_id, lecture_name)
                        st.success(f"Created: {lecture_name}")
                    elif lecture_id: 
                        current_lecture_id = lecture_id
                    
                    if current_lecture_id is None: st.stop()
                except ValueError as e: st.error(f"Error: {e}"); st.stop()
                
                pil_img = Image.open(img_file_buffer)
                with st.spinner("🧠 Analyzing..."): 
                    results_df, live_students_df = ImageService.recognize_face_in_image(pil_img)
                    display_img = ImageService.draw_on_image(pil_img, results_df)
                
                st.image(display_img, caption="Results", use_container_width=True)
                st.markdown("---")
                
                st.subheader("Step 3: Verify & Save")
                all_students_in_subject = DBManager.get_students_for_subject(subject_id)
                if all_students_in_subject.empty: st.error(f"No students in '{subject}'.")
                else:
                    recognized_enrollments = []
                    if not live_students_df.empty:
                        recognized_enrollments = live_students_df['Enrollment'].astype(str).tolist()
                    else:
                        st.warning("No 'live' students were recognized in the photo.")

                    all_students_in_subject['Marked_Present'] = all_students_in_subject['Enrollment'].astype(str).isin(recognized_enrollments)
                    edited_df = st.data_editor(all_students_in_subject, use_container_width=True, disabled=["user_id_student", "Enrollment", "Name"], column_order=("Marked_Present", "Name", "Enrollment"))
                    
                    if st.button("Save Attendance", type="primary", key="save_att_teach"): 
                        DBManager.mark_attendance(current_lecture_id, edited_df)
                        st.success("Saved!")
                        st.balloons()    
        else: st.warning("Select or create lecture.")

    # --- TAB 2: DASHBOARD ---
    with tabs[1]:
        st.header("📊 Attendance Dashboard")
        subject = st.selectbox("Select Subject", SUBJECTS_FROM_DB.keys(), key="dash_sub_teach")
        subject_id = SUBJECTS_FROM_DB[subject]
        threshold = st.slider("Defaulter Threshold (%)", 0, 100, 75, key="threshold_teach")
        
        with st.container(border=True):
            st.subheader("Overall Statistics")
            data = AttendanceService.get_dashboard_data(subject_id, threshold)
            if data["status"] == "ok":
                m1, m2, m3 = st.columns(3)
                m1.metric("Students", data["metrics"]["total_students"])
                m2.metric("Lectures", data["metrics"]["total_lectures"])
                m3.metric("Overall", f"{data['metrics']['overall_attendance']:.2f}%")
                st.markdown("---")
                
                st.subheader("📈 Lecture Trends")
                chart_data = data["trends"].set_index("Lecture")
                st.line_chart(chart_data, use_container_width=True)
                st.markdown("---")
                
                st.subheader("⚠️ Defaulter List")
                if not data["defaulters"].empty: st.dataframe(data["defaulters"], use_container_width=True)
                else: st.success("🎉 No defaulters.")
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1: 
                    csv_data = data["full_report"].to_csv(index=False).encode('utf-8')
                    st.download_button("📥 CSV", csv_data, f'{subject}_report.csv', 'text/csv', key="dl_teach_csv", use_container_width=True)
                with col2: 
                    pdf_data = ReportService.generate_pdf_report(subject, data["metrics"], data["full_report"])
                    st.download_button("📄 PDF", pdf_data, f'{subject}_report.pdf', 'application/pdf', key="dl_teach_pdf", use_container_width=True)
            else: st.warning(f"📊 {data['message']}")
        
        st.markdown("---")
        with st.container(border=True):
            st.subheader("🧐 View Specific Lecture Attendance")
            lectures_df = DBManager.get_lectures_for_subject(subject_id)
            if not lectures_df.empty:
                lecture_id_to_view = st.selectbox("Select Lecture", options=lectures_df.index, format_func=lambda x: lectures_df.loc[x]['lecture_name'], key="detail_lec_select_teach")
                if lecture_id_to_view:
                    attendance_details_df = DBManager.get_attendance_for_lecture(lecture_id_to_view)
                    st.dataframe(attendance_details_df, use_container_width=True)
            else: st.info("No lectures found.")

    # --- TAB 3: MANUAL ENTRY ---
    with tabs[2]:
        st.header("✍️ Manual Attendance Entry")
        with st.container(border=True):
            manual_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manual_sub_teach")
            subject_id = SUBJECTS_FROM_DB[manual_sub]
            existing_manual_lectures_df = DBManager.get_lectures_for_subject(subject_id)
            lecture_id = None
            manual_lec_name = None
            manual_lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="manual_lec_choice_teach", horizontal=True)
            
            if manual_lec_choice == "Create New": 
                manual_lec_name = st.text_input("New Lecture Name", key="manual_lec_new_teach")
            else:
                if not existing_manual_lectures_df.empty: 
                    lecture_id = st.selectbox("Select Lecture", options=existing_manual_lectures_df.index, format_func=lambda x: existing_manual_lectures_df.loc[x]['lecture_name'], key="manual_lec_existing_teach")
                else: st.info("No existing lectures.")
            
            current_manual_lecture_id = None
            if manual_lec_name:
                try: 
                    current_manual_lecture_id = DBManager.add_new_lecture(subject_id, manual_lec_name)
                    st.success(f"Created: {manual_lec_name}")
                except ValueError as e: 
                    st.warning(f"Note: {e}")
                    existing_df = DBManager.get_lectures_for_subject(subject_id)
                    current_manual_lecture_id = existing_df[existing_df['lecture_name'] == manual_lec_name].index[0]
            elif lecture_id: 
                current_manual_lecture_id = lecture_id
            
            if current_manual_lecture_id:
                with st.form("manual_form_teach"):
                    enroll = st.text_input("Student Enrollment (Username)")
                    if st.form_submit_button("Mark Present"): 
                        success, message = DBManager.mark_manual_attendance(current_manual_lecture_id, enroll)
                        (st.success if success else st.error)(message)
            else: st.info("Select or create lecture.")

    # --- TAB 4: PROFILE (Teacher) ---
    with tabs[3]:
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
