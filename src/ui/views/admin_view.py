import streamlit as st
import pandas as pd
from PIL import Image
from src.database.db_manager import DBManager
from src.services.image_service import ImageService
from src.services.attendance_service import AttendanceService
from src.services.email_service import EmailService
from src.services.report_service import ReportService

def admin_app(authenticator):
    SUBJECTS_FROM_DB = DBManager.get_subjects(st.session_state['user_id'], 'admin')
    tab_titles = ["📸 Take Attendance", "📊 Dashboard", "✍️ Manual Entry", "⚙️ Manage", "🧑‍🎓 Register User", "👤 Profile"]
    tabs = st.tabs(tab_titles)

    # --- TAB 1: TAKE ATTENDANCE ---
    with tabs[0]:
        st.header("📸 Take Attendance")
        if not SUBJECTS_FROM_DB: st.warning("No subjects found. Go to 'Manage' tab.")
        else:
            with st.container(border=True):
                st.subheader("Step 1: Configure Session")
                subject = st.selectbox("Select Subject (All)", SUBJECTS_FROM_DB.keys(), key="att_sub_admin")
                subject_id = SUBJECTS_FROM_DB[subject]
                existing_lectures_df = DBManager.get_lectures_for_subject(subject_id)
                lecture_id = None
                lecture_name = None
                lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="att_lec_choice_admin", horizontal=True)
                
                if lec_choice == "Create New": 
                    lecture_name = st.text_input("New Lecture Name", key="att_lecture_new_admin")
                else:
                    if not existing_lectures_df.empty: 
                        lecture_id = st.selectbox("Select Existing Lecture", options=existing_lectures_df.index, format_func=lambda x: existing_lectures_df.loc[x]['lecture_name'], key="att_lecture_existing_admin")
                    else: st.info("No existing lectures.")
            
            if lecture_name or lecture_id:
                st.subheader("Step 2: Choose Mode & Capture")
                mode = st.radio("Select Attendance Mode", ["Upload Image", "Capture Photo"], horizontal=True, key="att_mode_admin")
                img_file_buffer = None
                if mode == "Upload Image": img_file_buffer = st.file_uploader("Upload photo", type=['jpg', 'png', 'jpeg'], key="file_up_admin")
                elif mode == "Capture Photo": img_file_buffer = st.camera_input("Capture photo", key="cam_in_admin")
                
                if img_file_buffer:
                    current_lecture_id = None
                    try:
                        if lec_choice == "Create New" and lecture_name: 
                            current_lecture_id = DBManager.add_new_lecture(subject_id, lecture_name)
                            st.success(f"Created lecture: {lecture_name}")
                        elif lecture_id: 
                            current_lecture_id = lecture_id
                        
                        if current_lecture_id is None: st.stop()
                    except ValueError as e: st.error(f"Error: {e}"); st.stop()
                    
                    pil_img = Image.open(img_file_buffer)
                    with st.spinner("🧠 Analyzing..."): 
                        results_df, live_students_df = ImageService.recognize_face_in_image(pil_img)
                        display_img = ImageService.draw_on_image(pil_img, results_df)
                    
                    st.image(display_img, caption="Recognition Results", use_container_width=True)
                    st.markdown("---")
                    
                    st.subheader("Step 3: Verify & Save")
                    all_students_in_subject = DBManager.get_students_for_subject(subject_id)
                    
                    if all_students_in_subject.empty: st.error(f"No students enrolled in '{subject}'.")
                    else:
                        recognized_enrollments = []
                        if not live_students_df.empty:
                            recognized_enrollments = live_students_df['Enrollment'].astype(str).tolist()
                        else:
                            st.warning("No 'live' students were recognized in the photo.")
                            
                        all_students_in_subject['Marked_Present'] = all_students_in_subject['Enrollment'].astype(str).isin(recognized_enrollments)
                        edited_df = st.data_editor(all_students_in_subject, use_container_width=True, disabled=["user_id_student", "Enrollment", "Name"], column_order=("Marked_Present", "Name", "Enrollment"))
                        
                        if st.button("Save Verified Attendance", type="primary", key="save_att_admin"): 
                            DBManager.mark_attendance(current_lecture_id, edited_df)
                            st.success("Attendance saved!")
                            st.balloons()
            else: st.warning("Select or create lecture.")

    # --- TAB 2: DASHBOARD ---
    with tabs[1]:
        st.header("📊 Attendance Dashboard")
        if not SUBJECTS_FROM_DB: st.warning("No subjects found.")
        else:
            subject = st.selectbox("Select Subject", SUBJECTS_FROM_DB.keys(), key="dash_sub_admin")
            subject_id = SUBJECTS_FROM_DB[subject]
            threshold = st.slider("Defaulter Threshold (%)", 0, 100, 75, key="threshold_admin")

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
                    if not data["defaulters"].empty:
                        st.dataframe(data["defaulters"], use_container_width=True)
                        with st.expander("📧 Email Notification Settings"):
                            if st.button("Send Email to All Defaulters", key="email_admin"):
                                errors = EmailService.email_defaulters(data["defaulters"], subject)
                                if not errors: st.success("Emails sent!")
                                else: st.error("Email errors:"); [st.warning(e) for e in errors]
                    else: st.success("🎉 No defaulters.")
                    
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1: 
                        csv_data = data["full_report"].to_csv(index=False).encode('utf-8')
                        st.download_button("📥 CSV Report", csv_data, f'{subject}_report.csv', 'text/csv', key="dl_admin_csv", use_container_width=True)
                    with col2: 
                        pdf_data = ReportService.generate_pdf_report(subject, data["metrics"], data["full_report"])
                        st.download_button("📄 PDF Report", pdf_data, f'{subject}_report.pdf', 'application/pdf', key="dl_admin_pdf", use_container_width=True)
                else: st.warning(f"📊 {data['message']}")

            st.markdown("---")
            with st.container(border=True):
                st.subheader("🧐 View Specific Lecture Attendance")
                lectures_df = DBManager.get_lectures_for_subject(subject_id)
                if not lectures_df.empty:
                    lecture_id_to_view = st.selectbox("Select Lecture", options=lectures_df.index, format_func=lambda x: lectures_df.loc[x]['lecture_name'], key="detail_lec_select_admin")
                    if lecture_id_to_view:
                        attendance_details_df = DBManager.get_attendance_for_lecture(lecture_id_to_view)
                        st.dataframe(attendance_details_df, use_container_width=True)
                else:
                    st.info("No lectures found for this subject yet.")

    # --- TAB 3: MANUAL ENTRY ---
    with tabs[2]:
        st.header("✍️ Manual Attendance Entry")
        if not SUBJECTS_FROM_DB: st.warning("No subjects found.")
        else:
            with st.container(border=True):
                manual_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manual_sub_admin")
                subject_id = SUBJECTS_FROM_DB[manual_sub]
                existing_manual_lectures_df = DBManager.get_lectures_for_subject(subject_id)
                lecture_id = None
                manual_lec_name = None
                manual_lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="manual_lec_choice_admin", horizontal=True)
                
                if manual_lec_choice == "Create New": 
                    manual_lec_name = st.text_input("New Lecture Name", key="manual_lec_new_admin")
                else:
                    if not existing_manual_lectures_df.empty: 
                        lecture_id = st.selectbox("Select Existing Lecture", options=existing_manual_lectures_df.index, format_func=lambda x: existing_manual_lectures_df.loc[x]['lecture_name'], key="manual_lec_existing_admin")
                    else: st.info("No existing lectures.")
                
                current_manual_lecture_id = None
                if manual_lec_name:
                    try: 
                        current_manual_lecture_id = DBManager.add_new_lecture(subject_id, manual_lec_name)
                        st.success(f"Created lecture: {manual_lec_name}")
                    except ValueError as e: 
                        st.warning(f"Note: {e}")
                        existing_df = DBManager.get_lectures_for_subject(subject_id)
                        current_manual_lecture_id = existing_df[existing_df['lecture_name'] == manual_lec_name].index[0]
                elif lecture_id: 
                    current_manual_lecture_id = lecture_id
                
                if current_manual_lecture_id:
                    with st.form("manual_form_admin"):
                        enroll = st.text_input("Student Enrollment (Username)")
                        if st.form_submit_button("Mark as Present"): 
                            success, message = DBManager.mark_manual_attendance(current_manual_lecture_id, enroll)
                            (st.success if success else st.error)(message)
                else: st.info("Select or create lecture.")

    # --- TAB 4: MANAGE ---
    with tabs[3]:
        st.header("⚙️ Data Management")
        st.subheader("📚 Manage Subjects")
        sub_c1, sub_c2 = st.columns(2)
        
        with sub_c1, st.container(border=True): 
            st.subheader("➕ Create")
            new_sub_name = st.text_input("New Subject Name", key="new_sub_name_input")
            if st.button("Create Subject"):
                if new_sub_name: 
                    success, message = DBManager.add_subject(new_sub_name)
                    (st.success(message) if success else st.error(message))
                    st.rerun()
        
        with sub_c2, st.container(border=True): 
            st.subheader("🗑️ Delete")
            if not SUBJECTS_FROM_DB: st.info("No subjects.")
            else:
                sub_name_to_delete = st.selectbox("Select Subject", SUBJECTS_FROM_DB.keys(), key="del_sub_select")
                if st.button("Delete Subject", type="primary"): 
                    st.session_state.confirm_subject_delete = True
                    st.session_state.subject_to_delete = {"id": SUBJECTS_FROM_DB[sub_name_to_delete], "name": sub_name_to_delete}
                    st.rerun()
                
                if st.session_state.confirm_subject_delete:
                    sub_info = st.session_state.subject_to_delete
                    st.warning(f"**ARE YOU SURE?** Delete **{sub_info['name']}** and ALL its data?")
                    c_del, c_can, _ = st.columns([1, 1, 4])
                    if c_del.button("YES, DELETE", type="primary"): 
                        DBManager.delete_subject(sub_info['id'])
                        st.success("Subject deleted.")
                        st.session_state.confirm_subject_delete = False
                        st.rerun()
                    if c_can.button("CANCEL"): 
                        st.session_state.confirm_subject_delete = False
                        st.rerun()
        
        st.markdown("---")
        st.subheader("🧑‍🏫 Manage Teacher Assignments")
        teachers_df = DBManager.get_users_by_role('teacher')
        
        if teachers_df.empty or not SUBJECTS_FROM_DB: st.info("Create Teacher & Subject first.")
        else:
            teacher_list = pd.Series(teachers_df.user_id.values, index=teachers_df.name).to_dict()
            teacher_name = st.selectbox("Select Teacher", teacher_list.keys(), key="assign_teacher_select")
            teacher_id = teacher_list[teacher_name]
            
            tc1, tc2 = st.columns(2)
            with tc1, st.container(border=True): 
                st.subheader("Assign")
                unassigned = DBManager.get_unassigned_subjects_for_teacher(teacher_id)
                if not unassigned: st.info("Assigned all.")
                else: 
                    sub_assign_name = st.selectbox("Select Subject", unassigned.keys())
                    sub_assign_id = unassigned[sub_assign_name]
                    if st.button("Assign Subject"): 
                        DBManager.assign_teacher_to_subject(teacher_id, sub_assign_id)
                        st.success("Assigned!")
                        st.rerun()
            
            with tc2, st.container(border=True): 
                st.subheader("Remove")
                assigned = DBManager.get_subjects(teacher_id, 'teacher')
                if not assigned: st.info("No assigned.")
                else: 
                    sub_remove_name = st.selectbox("Select Subject", assigned.keys())
                    sub_remove_id = assigned[sub_remove_name]
                    if st.button("Remove Subject", type="primary"): 
                        DBManager.remove_teacher_from_subject(teacher_id, sub_remove_id)
                        st.success("Removed!")
                        st.rerun()
        
        st.markdown("---")
        st.subheader("Manage Students & Lectures")
        if not SUBJECTS_FROM_DB: st.info("Create Subject first.")
        else:
            c1, c2 = st.columns(2)
            with c1, st.container(border=True):
                st.subheader("Manage Students in Subject")
                man_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manage_sub_admin")
                subject_id = SUBJECTS_FROM_DB[man_sub]
                action = st.radio("Action", ["Add Students", "Remove Students"], key="student_action_admin", horizontal=True)

                all_students_df = DBManager.get_users_by_role('student')
                students_in_subject_ids = DBManager.get_students_for_subject(subject_id)['user_id_student'].tolist()

                if action == "Add Students":
                    available_students = all_students_df[~all_students_df['Student_ID'].isin(students_in_subject_ids)]
                    if not available_students.empty:
                        student_options = pd.Series(available_students.Student_ID.values, index=available_students.name + " (" + available_students.Enrollment + ")").to_dict()
                        students_to_add_display = st.multiselect("Select Students to Add", student_options.keys())
                        students_to_add_ids = [student_options[name] for name in students_to_add_display]
                        if st.button("Add Selected Students"):
                            if students_to_add_ids:
                                count, errors = DBManager.add_multiple_students_to_subject(subject_id, students_to_add_ids)
                                st.success(f"Added {count} students.")
                                [st.warning(e) for e in errors]
                                st.rerun()
                            else: st.warning("No students selected.")
                    else: st.info("All students are in this subject.")

                else: # Remove Students
                    students_in_subject_df = all_students_df[all_students_df['Student_ID'].isin(students_in_subject_ids)]
                    if not students_in_subject_df.empty:
                        student_options = pd.Series(students_in_subject_df.Student_ID.values, index=students_in_subject_df.name + " (" + students_in_subject_df.Enrollment + ")").to_dict()
                        students_to_remove_display = st.multiselect("Select Students to Remove", student_options.keys())
                        students_to_remove_ids = [student_options[name] for name in students_to_remove_display]
                        if st.button("Remove Selected Students", type="primary"):
                            if students_to_remove_ids:
                                count, errors = DBManager.remove_multiple_students_from_subject(subject_id, students_to_remove_ids)
                                st.success(f"Removed {count} students.")
                                [st.warning(e) for e in errors]
                                st.rerun()
                            else: st.warning("No students selected.")
                    else: st.info("No students to remove.")
            
            with c2, st.container(border=True):
                st.subheader("Manage Lectures")
                lec_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="lecture_sub_admin")
                subject_id = SUBJECTS_FROM_DB[lec_sub]
                lectures_df = DBManager.get_lectures_for_subject(subject_id)
                if not lectures_df.empty:
                    lec_id_to_remove = st.selectbox("Select Lecture", options=lectures_df.index, format_func=lambda x: lectures_df.loc[x]['lecture_name'])
                    if st.button("Remove Lecture", type="primary"): 
                        DBManager.remove_lecture_from_subject(lec_id_to_remove)
                        st.success("Lecture removed.")
                        st.rerun()
                else: st.info("No lectures.")
        
        st.markdown("---")
        with st.container(border=True):
            st.subheader("🔥 Danger Zone: User Deletion")
            conn = DBManager.connect_db()
            all_users_for_del = pd.read_sql_query("SELECT user_id, name, username, role FROM users WHERE role != 'admin'", conn)
            conn.close()
            
            if not all_users_for_del.empty:
                all_users_for_del['display'] = all_users_for_del['name'] + " (" + all_users_for_del['role'] + ": " + all_users_for_del['username'] + ")"
                user_list = pd.Series(all_users_for_del.user_id.values, index=all_users_for_del.display).to_dict()
                user_del_display = st.selectbox("Select User", user_list.keys())
                user_del_id = user_list[user_del_display]
                
                if st.button("Delete User", type="primary"): 
                    st.session_state.confirm_permanent_delete = True
                    st.session_state.user_to_delete = {"id": user_del_id, "display": user_del_display}
                    st.rerun()
                
                if st.session_state.confirm_permanent_delete:
                    user_info = st.session_state.user_to_delete
                    st.warning(f"**ARE YOU SURE?** Delete **{user_info['display']}**?")
                    c_del, c_can, _ = st.columns([1, 1, 4])
                    if c_del.button("YES, DELETE", type="primary"): 
                        DBManager.delete_user(user_info['id'])
                        st.success("User deleted.")
                        st.session_state.confirm_permanent_delete = False
                        st.rerun()
                    if c_can.button("CANCEL"): 
                        st.session_state.confirm_permanent_delete = False
                        st.rerun()
            else: st.info("No non-admin users.")

    # --- TAB 5: REGISTER USER ---
    with tabs[4]:
        st.header("🧑‍🎓 New User Enrollment")
        with st.container(border=True):
            st.subheader("Create New User")
            role = st.radio("Role", ['student', 'teacher'], horizontal=True)
            username = st.text_input("Username (Enrollment#)")
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            if st.button("➕ Create User"): 
                success, message = DBManager.create_user(username, name, email, password, role) 
            
                if success:
                    st.success(message)
                    if role == 'student': 
                        st.session_state.capture_count = 1
                        st.session_state.enrollment_username = username
                        st.session_state.name = name
                        st.rerun()
                else: 
                    st.error(message)

        if st.session_state.get('capture_count', 0) > 0:
            with st.container(border=True):
                st.subheader("Capture Student Images")
                if 1 <= st.session_state.capture_count <= 10:
                    st.info(f"Image {st.session_state.capture_count}/10 for {st.session_state.name} ({st.session_state.enrollment_username})")
                    st.progress(st.session_state.capture_count / 10)
                    img_buffer = st.camera_input(f"Capture #{st.session_state.capture_count}", key=f"capture_{st.session_state.capture_count}")
                    if img_buffer: 
                        ImageService.save_image_for_student(st.session_state.enrollment_username, st.session_state.name, Image.open(img_buffer), st.session_state.capture_count)
                        st.session_state.capture_count += 1
                        st.rerun()
                elif st.session_state.capture_count > 10:
                    st.success(f"✅ Images captured!")
                    with st.spinner('Augmenting...'): 
                        aug_ok, aug_msg = ImageService.augment_training_images(st.session_state.enrollment_username)
                        (st.success if aug_ok else st.error)(aug_msg)
                    
                    with st.spinner('Training AI...'): 
                        ok, msg = ImageService.train_model()
                        (st.success if ok else st.error)(msg)
                        if ok: st.balloons()
                        
                    if st.button("Register Another"): 
                        st.session_state.capture_count = 0
                        st.rerun()

    # --- TAB 6: PROFILE (Admin) ---
    with tabs[5]:
        st.header(f"👤 My Profile ({st.session_state['role'].title()})")
        try:
            if authenticator.update_user_details('Update Profile', location='main'):
                st.success('Profile details updated successfully')
                st.rerun()
        except Exception as e:
            st.error(f"Error updating profile: {e}")
        st.markdown("---")
        try:
            if authenticator.reset_password('Change Password', location='main'):
                st.success('Password modified successfully. You might need to log in again with the new password.')
        except Exception as e:
            st.error(f"Error changing password: {e}")
