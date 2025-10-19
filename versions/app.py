import streamlit as st
from PIL import Image
import io
import pandas as pd
import hajri_utils as utils
from hajri_css import CSS  # <-- We import our CSS string
import os
from dotenv import load_dotenv
import streamlit_authenticator as stauth

# Load environment variables
load_dotenv()

# --- DB INITIALIZATION ---
utils.init_db()
# This helper now reads from .env
utils.create_first_admin() 

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Hajri.ai",
    page_icon="logo.png", # <--- UPDATED: Use your logo.png as favicon
    layout="wide",
    initial_sidebar_state="collapsed", 
)

# --- INITIALIZE SESSION STATE ---
if 'capture_count' not in st.session_state:
    st.session_state.capture_count = 0
if 'confirm_permanent_delete' not in st.session_state:
    st.session_state.confirm_permanent_delete = False
    st.session_state.user_to_delete = None
if 'confirm_subject_delete' not in st.session_state:
    st.session_state.confirm_subject_delete = False
    st.session_state.subject_to_delete = None


# ==============================================================================
# --- 1. ADMIN APPLICATION ---
# ==============================================================================
def admin_app():
    
    # Get subject {name: id} dict for the admin (all subjects)
    SUBJECTS_FROM_DB = utils.get_subjects(st.session_state['user_id'], 'admin')

    # --- TABS ---
    tab_titles = ["📸 Take Attendance", "📊 Dashboard", "✍️ Manual Entry", "⚙️ Manage", "🧑‍🎓 Register User"]
    tabs = st.tabs(tab_titles)

    # ========================== ADMIN TAB 1: TAKE ATTENDANCE ==========================
    with tabs[0]:
        st.header("📸 Take Attendance")
        
        if not SUBJECTS_FROM_DB:
            st.warning("No subjects found. Please go to the 'Manage' tab to create a subject.")
        else:
            with st.container(border=True):
                st.subheader("Step 1: Configure Session")
                subject = st.selectbox("Select Subject (All)", SUBJECTS_FROM_DB.keys(), key="att_sub_admin")
                subject_id = SUBJECTS_FROM_DB[subject]

                existing_lectures_df = utils.get_lectures_for_subject(subject_id)
                lecture_id = None
                lecture_name = None

                lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="att_lec_choice_admin", horizontal=True)

                if lec_choice == "Create New":
                    lecture_name = st.text_input("New Lecture Name", placeholder="e.g., AI - Week 4", key="att_lecture_new_admin")
                else:
                    if not existing_lectures_df.empty:
                        lecture_id = st.selectbox("Select Existing Lecture", 
                                                  options=existing_lectures_df.index,
                                                  format_func=lambda x: existing_lectures_df.loc[x]['lecture_name'],
                                                  key="att_lecture_existing_admin")
                    else:
                        st.info("No existing lectures.")

            if lecture_name or lecture_id:
                st.subheader("Step 2: Choose Mode & Capture")
                mode = st.radio("Select Attendance Mode", ["Upload Image", "Capture Photo"], horizontal=True, key="att_mode_admin")

                img_file_buffer = None
                if mode == "Upload Image":
                    img_file_buffer = st.file_uploader("Upload a clear class photo", type=['jpg', 'png', 'jpeg'], key="file_up_admin")
                elif mode == "Capture Photo":
                    img_file_buffer = st.camera_input("Center the camera and capture", key="cam_in_admin")

                if img_file_buffer:
                    current_lecture_id = None
                    try:
                        if lec_choice == "Create New" and lecture_name:
                            with st.spinner(f"Creating new lecture '{lecture_name}'..."):
                                current_lecture_id = utils.add_new_lecture(subject_id, lecture_name)
                            st.success(f"Created new lecture: {lecture_name}")
                        elif lecture_id:
                            current_lecture_id = lecture_id
                        
                        if current_lecture_id is None: st.stop()
                            
                    except ValueError as e:
                        st.error(f"Error: {e}"); st.stop()

                    pil_img = Image.open(img_file_buffer)
                    
                    with st.spinner("🧠 Analyzing image..."):
                        results_df, live_students_df = utils.recognize_face_in_image(pil_img)
                        display_img = utils.draw_on_image(pil_img, results_df)
                    
                    st.image(display_img, caption="Recognition Results", use_container_width=True)
                    st.markdown("---")
                    
                    st.subheader("Step 3: Verify & Save Attendance")
                    all_students_in_subject = utils.get_students_for_subject(subject_id)
                    
                    if all_students_in_subject.empty:
                        st.error(f"No students are enrolled in '{subject}'.")
                    else:
                        recognized_enrollments = live_students_df['Enrollment'].astype(str).tolist()
                        all_students_in_subject['Marked_Present'] = all_students_in_subject['Enrollment'].astype(str).isin(recognized_enrollments)
                        
                        edited_df = st.data_editor(
                            all_students_in_subject, use_container_width=True,
                            disabled=["user_id_student", "Enrollment", "Name"],
                            column_order=("Marked_Present", "Name", "Enrollment")
                        )
                        
                        if st.button("Save Verified Attendance", type="primary", key="save_att_admin"):
                            utils.mark_attendance(current_lecture_id, edited_df)
                            st.success("Verified attendance saved!"); st.balloons()
            else:
                st.warning("Please select or create a lecture to proceed.")

    # ========================== ADMIN TAB 2: DASHBOARD ==========================
    with tabs[1]:
        st.header("📊 Attendance Dashboard")
        if not SUBJECTS_FROM_DB:
            st.warning("No subjects found.")
        else:
            subject = st.selectbox("Select Subject to View", SUBJECTS_FROM_DB.keys(), key="dash_sub_admin")
            subject_id = SUBJECTS_FROM_DB[subject]
            threshold = st.slider("Set Defaulter Threshold (%)", 0, 100, 75, key="threshold_admin")

            with st.container(border=True):
                data = utils.get_dashboard_data(subject_id, threshold)

                if data["status"] == "ok":
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Students", data["metrics"]["total_students"])
                    m2.metric("Total Lectures", data["metrics"]["total_lectures"])
                    m3.metric("Overall Attendance", f"{data['metrics']['overall_attendance']:.2f}%")
                    st.markdown("---")

                    st.subheader("📈 Lecture Attendance Trends")
                    chart_data = data["trends"].set_index("Lecture")
                    st.line_chart(chart_data, use_container_width=True)
                    st.markdown("---")

                    st.subheader("⚠️ Attendance Defaulter List")
                    if not data["defaulters"].empty:
                        st.dataframe(data["defaulters"], use_container_width=True)
                        with st.expander("📧 Email Notification Settings"):
                            if st.button("Send Email to All Defaulters", key="email_admin"):
                                errors = utils.email_defaulters(data["defaulters"], subject)
                                if not errors:
                                    st.success("All notification emails sent successfully!")
                                else:
                                    st.error("Errors occurred while sending emails:")
                                    for error in errors:
                                        st.warning(error)
                    else:
                        st.success("🎉 No defaulters.")
                    
                    st.markdown("---")
                    
                    # --- PDF/CSV Download Buttons ---
                    col1, col2 = st.columns(2)
                    with col1:
                        csv_data = data["full_report"].to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download CSV Report", csv_data, f'{subject}_report.csv', 'text/csv', key="dl_admin_csv", use_container_width=True)
                    with col2:
                        pdf_data = utils.generate_pdf_report(
                            subject_name=subject,
                            metrics=data["metrics"],
                            full_report_df=data["full_report"]
                        )
                        st.download_button("📄 Download PDF Report", pdf_data, f'{subject}_report.pdf', 'application/pdf', key="dl_admin_pdf", use_container_width=True)
                
                else:
                    st.warning(f"📊 {data['message']}")

    # ========================== ADMIN TAB 3: MANUAL ENTRY ==========================
    with tabs[2]:
        st.header("✍️ Manual Attendance Entry")
        if not SUBJECTS_FROM_DB:
            st.warning("No subjects found.")
        else:
            with st.container(border=True):
                manual_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manual_sub_admin")
                subject_id = SUBJECTS_FROM_DB[manual_sub]

                existing_manual_lectures_df = utils.get_lectures_for_subject(subject_id)
                lecture_id = None
                manual_lec_name = None

                manual_lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="manual_lec_choice_admin", horizontal=True)

                if manual_lec_choice == "Create New":
                    manual_lec_name = st.text_input("New Lecture Name", key="manual_lec_new_admin")
                else:
                    if not existing_manual_lectures_df.empty:
                        lecture_id = st.selectbox("Select Existing Lecture", 
                                                  options=existing_manual_lectures_df.index,
                                                  format_func=lambda x: existing_manual_lectures_df.loc[x]['lecture_name'],
                                                  key="manual_lec_existing_admin")
                    else:
                        st.info("No existing lectures.")

                current_manual_lecture_id = None
                if manual_lec_name:
                    try:
                        current_manual_lecture_id = utils.add_new_lecture(subject_id, manual_lec_name)
                        st.success(f"Created new lecture: {manual_lec_name}")
                    except ValueError as e:
                        st.warning(f"Note: {e}") # Lecture might already exist
                        existing_df = utils.get_lectures_for_subject(subject_id)
                        current_manual_lecture_id = existing_df[existing_df['lecture_name'] == manual_lec_name].index[0]
                elif lecture_id:
                    current_manual_lecture_id = lecture_id

                if current_manual_lecture_id:
                    with st.form("manual_form_admin"):
                        enroll = st.text_input("Student Enrollment Number (Username)")
                        if st.form_submit_button("Mark as Present"):
                            success, message = utils.mark_manual_attendance(current_manual_lecture_id, enroll)
                            if success: st.success(message)
                            else: st.error(message)
                else:
                    st.info("Select or create a lecture name to proceed.")

    # ========================== ADMIN TAB 4: MANAGE ==========================
    with tabs[3]:
        st.header("⚙️ Data Management")
        
        st.subheader("📚 Manage Subjects")
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1, st.container(border=True):
            st.subheader("➕ Create New Subject")
            new_sub_name = st.text_input("New Subject Name", key="new_sub_name_input")
            if st.button("Create Subject"):
                if new_sub_name:
                    success, message = utils.add_subject(new_sub_name)
                    if success: st.success(message); st.rerun()
                    else: st.error(message)
        
        with sub_c2, st.container(border=True):
            st.subheader("🗑️ Delete Subject")
            if not SUBJECTS_FROM_DB:
                st.info("No subjects to delete.")
            else:
                sub_name_to_delete = st.selectbox("Select Subject to Delete", SUBJECTS_FROM_DB.keys(), key="del_sub_select")
                if st.button("Delete Subject Permanently", type="primary"):
                    st.session_state.confirm_subject_delete = True
                    st.session_state.subject_to_delete = {"id": SUBJECTS_FROM_DB[sub_name_to_delete], "name": sub_name_to_delete}
                    st.rerun()
                if st.session_state.confirm_subject_delete:
                    sub_info = st.session_state.subject_to_delete
                    st.warning(f"**ARE YOU SURE?** This will delete **{sub_info['name']}** and ALL its data.")
                    c_del, c_can, _ = st.columns([1, 1, 4])
                    if c_del.button("YES, DELETE", type="primary", key="confirm_del_sub_btn"):
                        utils.delete_subject(sub_info['id']); st.success("Subject deleted."); st.session_state.confirm_subject_delete = False; st.rerun()
                    if c_can.button("CANCEL", key="cancel_del_sub_btn"):
                        st.session_state.confirm_subject_delete = False; st.rerun()
        
        st.markdown("---")
        st.subheader("🧑‍🏫 Manage Teacher Assignments")
        teachers_df = utils.get_users_by_role('teacher')
        if teachers_df.empty or not SUBJECTS_FROM_DB:
            st.info("Create a Teacher and a Subject to begin assignments.")
        else:
            teacher_list = pd.Series(teachers_df.user_id.values, index=teachers_df.name).to_dict()
            teacher_name = st.selectbox("Select Teacher", teacher_list.keys(), key="assign_teacher_select")
            teacher_id = teacher_list[teacher_name]
            
            tc1, tc2 = st.columns(2)
            with tc1, st.container(border=True):
                st.subheader("Assign Subject")
                unassigned_subjects = utils.get_unassigned_subjects_for_teacher(teacher_id)
                if not unassigned_subjects:
                    st.info("This teacher is assigned to all available subjects.")
                else:
                    sub_to_assign_name = st.selectbox("Select Subject to Assign", unassigned_subjects.keys())
                    sub_to_assign_id = unassigned_subjects[sub_to_assign_name]
                    if st.button("Assign Subject"):
                        utils.assign_teacher_to_subject(teacher_id, sub_to_assign_id); st.success("Assigned!"); st.rerun()
            
            with tc2, st.container(border=True):
                st.subheader("Remove Subject")
                assigned_subjects = utils.get_subjects(teacher_id, 'teacher')
                if not assigned_subjects:
                    st.info("This teacher has no assigned subjects.")
                else:
                    sub_to_remove_name = st.selectbox("Select Subject to Remove", assigned_subjects.keys())
                    sub_to_remove_id = assigned_subjects[sub_to_remove_name]
                    if st.button("Remove Subject", type="primary"):
                        utils.remove_teacher_from_subject(teacher_id, sub_to_remove_id); st.success("Removed!"); st.rerun()

        st.markdown("---")
        st.subheader("Manage Students & Lectures")
        if not SUBJECTS_FROM_DB:
            st.info("Create a subject to manage students and lectures.")
        else:
            c1, c2 = st.columns(2)
            with c1, st.container(border=True):
                st.subheader("Manage Students in Subject")
                man_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manage_sub_admin")
                subject_id = SUBJECTS_FROM_DB[man_sub]
                action = st.radio("Action", ["Add Student", "Remove Student"], key="student_action_admin", horizontal=True)

                if action == "Add Student":
                    all_students_df = utils.get_users_by_role('student')
                    students_in_subject = utils.get_students_for_subject(subject_id)['user_id_student'].tolist()
                    available_students = all_students_df[~all_students_df['Student_ID'].isin(students_in_subject)]
                    
                    if not available_students.empty:
                        student_list = pd.Series(available_students.Student_ID.values, index=available_students.Name).to_dict()
                        student_to_add_name = st.selectbox("Select Registered Student", student_list.keys())
                        student_to_add_id = student_list[student_to_add_name]
                        if st.button("Add to Subject"):
                            utils.add_student_to_subject(student_to_add_id, subject_id); st.success("Added!"); st.rerun()
                    else: st.info("All registered students are already in this subject.")
                else: # Remove Student
                    students_in_subject_df = utils.get_students_for_subject(subject_id)
                    if not students_in_subject_df.empty:
                        student_list = pd.Series(students_in_subject_df.user_id_student.values, index=students_in_subject_df.Name).to_dict()
                        student_to_remove_name = st.selectbox("Select Student to Remove", student_list.keys())
                        student_to_remove_id = student_list[student_to_remove_name]
                        if st.button("Remove from Subject", type="primary"):
                            utils.remove_student_from_subject(student_to_remove_id, subject_id); st.success("Removed!"); st.rerun()
                    else: st.info("No students to remove.")
            
            with c2, st.container(border=True):
                st.subheader("Manage Lectures")
                lec_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="lecture_sub_admin")
                subject_id = SUBJECTS_FROM_DB[lec_sub]
                lectures_df = utils.get_lectures_for_subject(subject_id)

                if not lectures_df.empty:
                    lec_id_to_remove = st.selectbox("Select Lecture to Remove", 
                                                    options=lectures_df.index,
                                                    format_func=lambda x: lectures_df.loc[x]['lecture_name'])
                    if st.button("Remove Selected Lecture", type="primary"):
                        utils.remove_lecture_from_subject(lec_id_to_remove); st.success("Lecture removed."); st.rerun()
                else: st.info("No lectures to remove.")

        st.markdown("---")
        with st.container(border=True):
            st.subheader("🔥 Danger Zone: Permanent User Deletion")
            all_users_for_del = pd.read_sql_query("SELECT user_id, name, username, role FROM users WHERE role != 'admin'", utils.connect_db())
            
            if not all_users_for_del.empty:
                all_users_for_del['display'] = all_users_for_del['name'] + " (" + all_users_for_del['role'] + ": " + all_users_for_del['username'] + ")"
                user_list = pd.Series(all_users_for_del.user_id.values, index=all_users_for_del.display).to_dict()
                
                user_to_delete_display = st.selectbox("Select User to Delete Permanently", user_list.keys())
                user_to_delete_id = user_list[user_to_delete_display]

                if st.button("Delete User Permanently", type="primary"):
                    st.session_state.confirm_permanent_delete = True
                    st.session_state.user_to_delete = {"id": user_to_delete_id, "display": user_to_delete_display}
                    st.rerun()
                if st.session_state.confirm_permanent_delete:
                    user_info = st.session_state.user_to_delete
                    st.warning(f"**ARE YOU SURE?** This will delete **{user_info['display']}** and all their data.")
                    c_del, c_can, _ = st.columns([1, 1, 4])
                    if c_del.button("YES, I AM SURE", type="primary"):
                        utils.delete_user(user_info['id']); st.success("User deleted."); st.session_state.confirm_permanent_delete = False; st.rerun()
                    if c_can.button("CANCEL"):
                        st.session_state.confirm_permanent_delete = False; st.rerun()
            else: st.info("No non-admin users to delete.")

    # ========================== ADMIN TAB 5: REGISTER USER ==========================
    with tabs[4]:
        st.header("🧑‍🎓 New User Enrollment")
        
        with st.container(border=True):
            st.subheader("Create New User")
            role = st.radio("User Role", ['student', 'teacher'], horizontal=True)
            username = st.text_input("Username (Enrollment # for students)", placeholder="e.g., 2101003 or prof.smith")
            name = st.text_input("User Full Name", placeholder="e.g., Peter Jones")
            email = st.text_input("User Email", placeholder="e.g., peter.j@example.com")
            password = st.text_input("New Password", type="password")
            
            if st.button("➕ Create User Account"):
                success, message = utils.create_user(username, name, email, password, role)
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
                    st.info(f"Capturing image **{st.session_state.capture_count} of 10** for **{st.session_state.name}** ({st.session_state.enrollment_username})")
                    st.progress(st.session_state.capture_count / 10)
                    img_buffer = st.camera_input(f"Capture #{st.session_state.capture_count}", key=f"capture_{st.session_state.capture_count}")
                    if img_buffer:
                        utils.save_image_for_student(st.session_state.enrollment_username, st.session_state.name, Image.open(img_buffer), st.session_state.capture_count)
                        st.session_state.capture_count += 1
                        st.rerun()
                elif st.session_state.capture_count > 10:
                    st.success(f"✅ All 10 base images for {st.session_state.name} captured!")
                    with st.spinner('🎨 Generating augmented images...'):
                        aug_ok, aug_msg = utils.augment_training_images(st.session_state.enrollment_username)
                        if aug_ok: st.success(aug_msg)
                        else: st.error(aug_msg)
                    if aug_ok:
                        with st.spinner('🤖 Training the AI model...'):
                            ok, msg = utils.train_model()
                            if ok: st.success(msg); st.balloons()
                            else: st.error(msg)
                    if st.button("Register Another User"):
                        st.session_state.capture_count = 0; st.rerun()


# ==============================================================================
# --- 2. TEACHER APPLICATION ---
# ==============================================================================
def teacher_app():
    
    SUBJECTS_FROM_DB = utils.get_subjects(st.session_state['user_id'], 'teacher')

    # --- TABS ---
    tab_titles = ["📸 Take Attendance", "📊 Dashboard", "✍️ Manual Entry"]
    tabs = st.tabs(tab_titles)

    if not SUBJECTS_FROM_DB:
        st.warning("You are not assigned to any subjects. Please contact an administrator.")
        st.stop()

    # ========================== TEACHER TAB 1: TAKE ATTENDANCE ==========================
    with tabs[0]:
        st.header("📸 Take Attendance")
        with st.container(border=True):
            st.subheader("Step 1: Configure Session")
            subject = st.selectbox("Select Your Subject", SUBJECTS_FROM_DB.keys(), key="att_sub_teach")
            subject_id = SUBJECTS_FROM_DB[subject]
            existing_lectures_df = utils.get_lectures_for_subject(subject_id)
            lecture_id = None
            lecture_name = None
            lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="att_lec_choice_teach", horizontal=True)
            if lec_choice == "Create New":
                lecture_name = st.text_input("New Lecture Name", placeholder="e.g., AI - Week 4", key="att_lecture_new_teach")
            else:
                if not existing_lectures_df.empty:
                    lecture_id = st.selectbox("Select Existing Lecture", 
                                              options=existing_lectures_df.index,
                                              format_func=lambda x: existing_lectures_df.loc[x]['lecture_name'],
                                              key="att_lecture_existing_teach")
                else: st.info("No existing lectures.")
        if lecture_name or lecture_id:
            st.subheader("Step 2: Choose Mode & Capture")
            mode = st.radio("Select Attendance Mode", ["Upload Image", "Capture Photo"], horizontal=True, key="att_mode_teach")
            img_file_buffer = None
            if mode == "Upload Image":
                img_file_buffer = st.file_uploader("Upload a clear class photo", type=['jpg', 'png', 'jpeg'], key="file_up_teach")
            elif mode == "Capture Photo":
                img_file_buffer = st.camera_input("Center the camera and capture", key="cam_in_teach")
            if img_file_buffer:
                current_lecture_id = None
                try:
                    if lec_choice == "Create New" and lecture_name:
                        current_lecture_id = utils.add_new_lecture(subject_id, lecture_name)
                        st.success(f"Created new lecture: {lecture_name}")
                    elif lecture_id: current_lecture_id = lecture_id
                    if current_lecture_id is None: st.stop()
                except ValueError as e: st.error(f"Error: {e}"); st.stop()
                pil_img = Image.open(img_file_buffer)
                with st.spinner("🧠 Analyzing image..."):
                    results_df, live_students_df = utils.recognize_face_in_image(pil_img)
                    display_img = utils.draw_on_image(pil_img, results_df)
                st.image(display_img, caption="Recognition Results", use_container_width=True)
                st.markdown("---")
                st.subheader("Step 3: Verify & Save Attendance")
                all_students_in_subject = utils.get_students_for_subject(subject_id)
                if all_students_in_subject.empty: st.error(f"No students are enrolled in '{subject}'.")
                else:
                    recognized_enrollments = live_students_df['Enrollment'].astype(str).tolist()
                    all_students_in_subject['Marked_Present'] = all_students_in_subject['Enrollment'].astype(str).isin(recognized_enrollments)
                    edited_df = st.data_editor(
                        all_students_in_subject, use_container_width=True,
                        disabled=["user_id_student", "Enrollment", "Name"],
                        column_order=("Marked_Present", "Name", "Enrollment")
                    )
                    if st.button("Save Verified Attendance", type="primary", key="save_att_teach"):
                        utils.mark_attendance(current_lecture_id, edited_df); st.success("Verified attendance saved!"); st.balloons()
        else: st.warning("Please select or create a lecture to proceed.")
    
    # ========================== TEACHER TAB 2: DASHBOARD ==========================
    with tabs[1]:
        st.header("📊 Attendance Dashboard")
        subject = st.selectbox("Select Subject to View", SUBJECTS_FROM_DB.keys(), key="dash_sub_teach")
        subject_id = SUBJECTS_FROM_DB[subject]
        threshold = st.slider("Set Defaulter Threshold (%)", 0, 100, 75, key="threshold_teach")
        with st.container(border=True):
            data = utils.get_dashboard_data(subject_id, threshold)
            if data["status"] == "ok":
                m1, m2, m3 = st.columns(3); m1.metric("Students", data["metrics"]["total_students"]); m2.metric("Lectures", data["metrics"]["total_lectures"]); m3.metric("Overall", f"{data['metrics']['overall_attendance']:.2f}%"); st.markdown("---")
                st.subheader("📈 Lecture Trends"); chart_data = data["trends"].set_index("Lecture"); st.line_chart(chart_data, use_container_width=True); st.markdown("---")
                st.subheader("⚠️ Defaulter List")
                if not data["defaulters"].empty:
                    st.dataframe(data["defaulters"], use_container_width=True)
                else: st.success("🎉 No defaulters.")
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    csv_data = data["full_report"].to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV Report", csv_data, f'{subject}_report.csv', 'text/csv', key="dl_teach_csv", use_container_width=True)
                with col2:
                    pdf_data = utils.generate_pdf_report(
                        subject_name=subject,
                        metrics=data["metrics"],
                        full_report_df=data["full_report"]
                    )
                    st.download_button("📄 Download PDF Report", pdf_data, f'{subject}_report.pdf', 'application/pdf', key="dl_teach_pdf", use_container_width=True)
            else: st.warning(f"📊 {data['message']}")

    # ========================== TEACHER TAB 3: MANUAL ENTRY ==========================
    with tabs[2]:
        st.header("✍️ Manual Attendance Entry")
        with st.container(border=True):
            manual_sub = st.selectbox("Subject", SUBJECTS_FROM_DB.keys(), key="manual_sub_teach")
            subject_id = SUBJECTS_FROM_DB[manual_sub]
            existing_manual_lectures_df = utils.get_lectures_for_subject(subject_id)
            lecture_id = None; manual_lec_name = None
            manual_lec_choice = st.radio("Lecture Option", ["Create New", "Use Existing"], key="manual_lec_choice_teach", horizontal=True)
            if manual_lec_choice == "Create New":
                manual_lec_name = st.text_input("New Lecture Name", key="manual_lec_new_teach")
            else:
                if not existing_manual_lectures_df.empty:
                    lecture_id = st.selectbox("Select Existing Lecture", options=existing_manual_lectures_df.index, format_func=lambda x: existing_manual_lectures_df.loc[x]['lecture_name'], key="manual_lec_existing_teach")
                else: st.info("No existing lectures.")
            current_manual_lecture_id = None
            if manual_lec_name:
                try:
                    current_manual_lecture_id = utils.add_new_lecture(subject_id, manual_lec_name)
                    st.success(f"Created new lecture: {manual_lec_name}")
                except ValueError as e:
                    st.warning(f"Note: {e}")
                    existing_df = utils.get_lectures_for_subject(subject_id)
                    current_manual_lecture_id = existing_df[existing_df['lecture_name'] == manual_lec_name].index[0]
            elif lecture_id: current_manual_lecture_id = lecture_id
            if current_manual_lecture_id:
                with st.form("manual_form_teach"):
                    enroll = st.text_input("Student Enrollment Number (Username)")
                    if st.form_submit_button("Mark as Present"):
                        success, message = utils.mark_manual_attendance(current_manual_lecture_id, enroll)
                        if success: st.success(message)
                        else: st.error(message)
            else: st.info("Select or create a lecture name to proceed.")


# ==============================================================================
# --- 3. STUDENT APPLICATION ---
# ==============================================================================
def student_app():
    st.header("My Attendance Report")
    
    report_data = utils.get_student_report(st.session_state['user_id'])
    
    if report_data['status'] == 'fail':
        st.warning(report_data['message'])
    else:
        st.info(f"You are enrolled in {len(report_data['subjects'])} subject(s).")
        
        for subject_report in report_data['subjects']:
            with st.container(border=True):
                sub_name = subject_report['subject_name']
                st.subheader(f"Subject: {sub_name}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Lectures", subject_report['total_lectures'])
                c2.metric("Lectures Attended", subject_report['present'])
                c3.metric("Overall Percentage", f"{subject_report['percentage']:.2f}%")
                
                with st.expander("View Detailed Lecture-wise Report"):
                    st.dataframe(subject_report['attendance_df'], use_container_width=True)
# ==============================================================================
# --- MAIN AUTHENTICATION ROUTER ---
# ==============================================================================

# Fetch all user credentials from DB
credentials = utils.get_all_users_for_auth()

# Initialize the authenticator
authenticator = stauth.Authenticate(
    credentials,
    "hajri_cookie_name",
    "hajri_random_key",
    cookie_expiry_days=30
)

# Render the login module
authenticator.login(location='main')


# --- ROUTER (THIS IS THE FULLY REVISED SECTION) ---
if st.session_state["authentication_status"]:
    # --- Inject the final, perfected CSS ---
    st.markdown(CSS, unsafe_allow_html=True)
    
    # --- Get user info after successful login ---
    user_info = utils.get_user_by_username(st.session_state["username"])
    if not user_info:
        st.error("Could not find user details. Contact admin.")
        authenticator.logout('Logout', 'main')
    else:
        # --- Store user info in session state ---
        st.session_state['user_id'] = user_info['user_id']
        st.session_state['role'] = user_info['role']
        st.session_state['name'] = user_info['name']
        st.session_state['email'] = user_info['email']
        
        # --- NEW, PERFECTED HEADER using st.columns ---
        col1, col2, col3 = st.columns([1.5, 3, 1]) # Asymmetric columns for balance

        with col1:
            st.image("logo.png", width=100)

        with col2:
            # This custom HTML centers the text vertically and horizontally
            st.markdown(f"""
            <div class="centered-user-info">
                <strong>{st.session_state['name']}</strong>
                <span>Logged in as: {st.session_state['role'].title()}</span>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            # The logout button is now cleanly in its own column
            authenticator.logout('Logout', 'main', key='main_logout')
        
        st.markdown("---")
        
        # --- Role-based app routing ---
        if st.session_state['role'] == 'admin':
            admin_app()
        elif st.session_state['role'] == 'teacher':
            teacher_app()
        elif st.session_state['role'] == 'student':
            student_app()
            
elif st.session_state["authentication_status"] is False:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='login-container'>
            <img src='data:image/png;base64,{utils.get_base64_image("logo.png")}' class='login-logo'>
            <h1>Welcome to Hajri.ai</h1>
            <h3>Please log in to continue.</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.error('Username/password is incorrect')

elif st.session_state["authentication_status"] is None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='login-container'>
            <img src='data:image/png;base64,{utils.get_base64_image("logo.png")}' class='login-logo'>
            <h1>Welcome to Hajri.ai</h1>
            <h3>Please log in to continue.</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
