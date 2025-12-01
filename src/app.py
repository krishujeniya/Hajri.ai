import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv
import streamlit_authenticator as stauth

# New structure imports
from src.ui.styles import CSS
from src.config.settings import Config
from src.database.db_manager import DBManager
from src.utils.helpers import Helpers
from src.ui.views.admin_view import admin_app
from src.ui.views.teacher_view import teacher_app
from src.ui.views.student_view import student_app
from src.services.image_service import ImageService

# Load environment variables
load_dotenv()

# --- DB INITIALIZATION ---
DBManager.init_db()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon=str(Config.LOGO_PATH) if Config.LOGO_PATH.exists() else Config.PAGE_ICON,
    layout=Config.LAYOUT,
    initial_sidebar_state=Config.SIDEBAR_STATE,
)

# --- LOGO CHECK ---
if not Config.LOGO_PATH.exists():
    print(f"\n⚠️  WARNING: {Config.LOGO_PATH} not found! Using fallback placeholders.\n")


# --- INITIALIZE SESSION STATE ---
if 'capture_count' not in st.session_state: st.session_state.capture_count = 0
if 'confirm_permanent_delete' not in st.session_state: st.session_state.confirm_permanent_delete = False; st.session_state.user_to_delete = None
if 'confirm_subject_delete' not in st.session_state: st.session_state.confirm_subject_delete = False; st.session_state.subject_to_delete = None
if 'authentication_status' not in st.session_state: st.session_state.authentication_status = None
if 'username' not in st.session_state: st.session_state.username = None
if 'name' not in st.session_state: st.session_state.name = None
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'role' not in st.session_state: st.session_state.role = None
if 'email' not in st.session_state: st.session_state.email = None

# New session state for UI flow
if 'show_login_form' not in st.session_state: st.session_state.show_login_form = True 
if 'show_register_form' not in st.session_state: st.session_state.show_register_form = False
if 'show_forgot_password_form' not in st.session_state: st.session_state.show_forgot_password_form = False
if 'show_reset_password_form' not in st.session_state: st.session_state.show_reset_password_form = False 


# ==============================================================================
# --- MAIN AUTHENTICATION & ROUTER ---
# ==============================================================================

# Fetch all user credentials from DB
credentials = DBManager.get_all_users_for_auth()
config = {
    'credentials': credentials,
    'cookie': {
        'name': Config.COOKIE_NAME,
        'key': Config.SECRET_KEY,
        'expiry_days': Config.COOKIE_EXPIRY_DAYS
    }
}

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- Check for reset_token in URL parameters ---
reset_token_from_url = st.query_params.get('reset_token')

if reset_token_from_url:
    st.session_state.show_reset_password_form = True
    st.session_state.show_login_form = False
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False

# --- Unauthenticated State ---
if st.session_state.authentication_status is None:
    st.markdown(CSS, unsafe_allow_html=True) 
    st.markdown(
        f"""
        <div class='login-container'>
            <img src='data:image/png;base64,{Helpers.get_base64_image(str(Config.LOGO_PATH))}' class='login-logo'>
            <h1>Welcome to Hajri.ai</h1>
            <h3>Please log in or register.</h3>
        </div>
        """, unsafe_allow_html=True
    )

    if st.session_state.show_reset_password_form:
        st.subheader("🔑 Reset Your Password")
        try:
            reset_status = authenticator.reset_password(location='main')
            if reset_status:
                st.success('Password has been reset successfully. Please login with the new temporary password sent to your email.')
                del st.query_params['reset_token']
                st.session_state.show_reset_password_form = False
                st.session_state.show_login_form = True 
                st.rerun()
        except Exception as e:
            st.error(f'Error during password reset: {e}')

    elif st.session_state.show_login_form:
        st.subheader("Login to Your Account")
        authenticator.login(location='main') 

        if st.session_state.authentication_status is False:
            st.error('Username/password is incorrect')
        elif st.session_state.authentication_status is None:
            pass 

        st.markdown("---")
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("New User? Register here", key="switch_to_register"):
                st.session_state.show_login_form = False
                st.session_state.show_register_form = True
                st.rerun()
        with col2:
            if st.button("Forgot Password?", key="switch_to_forgot"):
                st.session_state.show_login_form = False
                st.session_state.show_forgot_password_form = True
                st.rerun()

    elif st.session_state.show_register_form:
        st.subheader("Register a New User")
        
        with st.form("register_form"):
            role = st.radio("Role", ['student', 'teacher'], horizontal=True, key="reg_role_new")
            username = st.text_input("Username (Enrollment# for Students)", key="reg_username_new")
            name = st.text_input("Full Name", key="reg_name_new")
            email = st.text_input("Email", key="reg_email_new")
            password = st.text_input("Password", type="password", key="reg_password_new")
            register_button = st.form_submit_button("➕ Register User")

        if register_button:
            if username and name and email and password:
                success, message = DBManager.create_user(username, name, email, password, role)
                if success:
                    st.success(message)
                    if role == 'student':
                        st.session_state.capture_count = 1
                        st.session_state.enrollment_username = username
                        st.session_state.name = name
                    else: 
                        st.session_state.show_register_form = False
                        st.session_state.show_login_form = True
                        st.info("Registration complete. Please log in.")
                        st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill in all fields.")

        if st.session_state.get('capture_count', 0) > 0 and st.session_state.show_register_form:
            with st.container(border=True):
                st.subheader("Capture Student Images")
                if 1 <= st.session_state.capture_count <= 10:
                    st.info(f"Image {st.session_state.capture_count}/10 for {st.session_state.name} ({st.session_state.enrollment_username})")
                    st.progress(st.session_state.capture_count / 10)
                    img_buffer = st.camera_input(f"Capture #{st.session_state.capture_count}", key=f"capture_{st.session_state.capture_count}_reg")
                    if img_buffer:
                        ImageService.save_image_for_student(st.session_state.enrollment_username, st.session_state.name, Image.open(img_buffer), st.session_state.capture_count)
                        st.session_state.capture_count += 1
                        st.rerun()
                elif st.session_state.capture_count > 10:
                    st.success(f"✅ All 10 images captured for {st.session_state.name}!")
                    with st.spinner('Augmenting...'):
                        aug_ok, aug_msg = ImageService.augment_training_images(st.session_state.enrollment_username)
                        (st.success if aug_ok else st.error)(aug_msg)
                    
                    with st.spinner('Training AI...'):
                        ok, msg = ImageService.train_model()
                        (st.success if ok else st.error)(msg)
                        if ok: st.balloons()
                    
                    st.info("Registration and face training complete. You can now log in.")
                    if st.button("Go to Login", key="go_to_login_after_reg"):
                        st.session_state.capture_count = 0
                        st.session_state.show_register_form = False
                        st.session_state.show_login_form = True
                        st.rerun()


        st.markdown("---")
        if st.button("Already have an account? Login here", key="switch_to_login_from_reg"):
            st.session_state.show_register_form = False
            st.session_state.show_login_form = True
            st.session_state.capture_count = 0 
            st.rerun()

    elif st.session_state.show_forgot_password_form:
        st.subheader("Forgot Password")
        try:
            if authenticator.forgot_password(location='main'):
                st.success('Password reset email sent (check spam folder). Follow instructions in the email.')
        except Exception as e:
            st.error(f'Error sending reset email: {e}')
        
        st.markdown("---")
        if st.button("Back to Login", key="back_to_login_from_forgot"):
            st.session_state.show_forgot_password_form = False
            st.session_state.show_login_form = True
            st.rerun()

# --- ROUTER for Logged-in Users ---
elif st.session_state["authentication_status"]:
    st.session_state.show_login_form = False
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False
    st.session_state.show_reset_password_form = False

    st.markdown(CSS, unsafe_allow_html=True) 
    user_info = DBManager.get_user_by_username(st.session_state["username"])
    if not user_info:
        st.error("User details not found. Logging out."); authenticator.logout('Logout', 'main')
    else:
        st.session_state.update(user_info)

        col1, col2, col3 = st.columns([1.5, 3, 1])
        with col1: 
            try:
                st.image(str(Config.LOGO_PATH), width=70)
            except Exception:
                st.markdown("### 🎓") 
        with col2: st.markdown(f"<div class='centered-user-info'><strong>{st.session_state['name']}</strong><span>Logged in as: {st.session_state['role'].title()}</span></div>", unsafe_allow_html=True)
        with col3: authenticator.logout('Logout', 'main', key='main_logout')
        st.markdown("---")

        if st.session_state['role'] == 'admin': admin_app(authenticator)
        elif st.session_state['role'] == 'teacher': teacher_app(authenticator)
        elif st.session_state['role'] == 'student': student_app(authenticator)

elif st.session_state["authentication_status"] is False:
    st.markdown(CSS, unsafe_allow_html=True) 
    st.markdown( f""" <div class='login-container'> <img src='data:image/png;base64,{Helpers.get_base64_image(str(Config.LOGO_PATH))}' class='login-logo'> <h1>Welcome to Hajri.ai</h1> <h3>Please log in or register.</h3> </div> """, unsafe_allow_html=True)
    st.error('Username/password is incorrect')
    st.session_state.show_login_form = True
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False
    st.session_state.show_reset_password_form = False 
