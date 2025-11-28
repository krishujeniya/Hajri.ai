import streamlit as st
from PIL import Image
import io
import pandas as pd
import os
from dotenv import load_dotenv
import streamlit_authenticator as stauth

# New structure imports
from src.ui.styles import CSS
from src.config.settings import Config

# Legacy imports (to be migrated)
import hajri_utils as utils
from hajri_views import admin_app, teacher_app, student_app

# Load environment variables
load_dotenv()

# --- DB INITIALIZATION ---
utils.init_db()
utils.create_first_admin()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Hajri.ai",
    page_icon="logo.png" if os.path.exists("logo.png") else "🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- LOGO CHECK ---
if not os.path.exists("logo.png"):
    print("\n⚠️  WARNING: logo.png not found! Using fallback placeholders.\n")


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
if 'show_login_form' not in st.session_state: st.session_state.show_login_form = True # Default to showing login
if 'show_register_form' not in st.session_state: st.session_state.show_register_form = False
if 'show_forgot_password_form' not in st.session_state: st.session_state.show_forgot_password_form = False
if 'show_reset_password_form' not in st.session_state: st.session_state.show_reset_password_form = False # For email link flow


# ==============================================================================
# --- MAIN AUTHENTICATION & ROUTER ---
# ==============================================================================

# Fetch all user credentials from DB
credentials = utils.get_all_users_for_auth()
config = {
    'credentials': credentials,
    'cookie': {
        'name': 'hajri_cookie_name',
        'key': os.getenv("SECRET_KEY", 'hajri_secret_key_123'),
        'expiry_days': 30
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

# Handle the reset password flow triggered by a URL token first, outside the main if/else for initial UI choices.
if reset_token_from_url:
    st.session_state.show_reset_password_form = True
    st.session_state.show_login_form = False
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False

# --- Unauthenticated State ---
if st.session_state.authentication_status is None:
    st.markdown(CSS, unsafe_allow_html=True) # Inject CSS for the login page
    st.markdown(
        f"""
        <div class='login-container'>
            <img src='data:image/png;base64,{utils.get_base64_image("logo.png")}' class='login-logo'>
            <h1>Welcome to Hajri.ai</h1>
            <h3>Please log in or register.</h3>
        </div>
        """, unsafe_allow_html=True
    )

    # Conditionally render forms based on session state
    if st.session_state.show_reset_password_form:
        st.subheader("🔑 Reset Your Password")
        try:
            reset_status = authenticator.reset_password(location='main')
            if reset_status:
                st.success('Password has been reset successfully. Please login with the new temporary password sent to your email.')
                del st.query_params['reset_token']
                st.session_state.show_reset_password_form = False
                st.session_state.show_login_form = True # Go back to login form
                st.rerun()
        except Exception as e:
            st.error(f'Error during password reset: {e}')

    elif st.session_state.show_login_form:
        st.subheader("Login to Your Account")
        authenticator.login(location='main') # This will update session_state.authentication_status

        if st.session_state.authentication_status is False:
            st.error('Username/password is incorrect')
        elif st.session_state.authentication_status is None:
            # User hasn't attempted login yet, or attempted but it's still None
            pass # Keep quiet if no attempt or successful login

        # Buttons to switch forms
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
        # In a real app, you might only allow admins to register, or use authenticator.register_user
        # For now, we use our existing utils.create_user which includes face capture flow for students.

        with st.form("register_form"):
            role = st.radio("Role", ['student', 'teacher'], horizontal=True, key="reg_role_new")
            username = st.text_input("Username (Enrollment# for Students)", key="reg_username_new")
            name = st.text_input("Full Name", key="reg_name_new")
            email = st.text_input("Email", key="reg_email_new")
            password = st.text_input("Password", type="password", key="reg_password_new")
            register_button = st.form_submit_button("➕ Register User")

        if register_button:
            if username and name and email and password:
                success, message = utils.create_user(username, name, email, password, role)
                if success:
                    st.success(message)
                    if role == 'student':
                        st.session_state.capture_count = 1
                        st.session_state.enrollment_username = username
                        st.session_state.name = name
                        # We stay on the register form to complete image capture for students
                    else: # For teachers, registration is complete
                        st.session_state.show_register_form = False
                        st.session_state.show_login_form = True
                        st.info("Registration complete. Please log in.")
                        st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill in all fields.")

        # Student image capture flow (moved from admin_app register tab)
        if st.session_state.get('capture_count', 0) > 0 and st.session_state.show_register_form:
            with st.container(border=True):
                st.subheader("Capture Student Images")
                if 1 <= st.session_state.capture_count <= 10:
                    st.info(f"Image {st.session_state.capture_count}/10 for {st.session_state.name} ({st.session_state.enrollment_username})")
                    st.progress(st.session_state.capture_count / 10)
                    img_buffer = st.camera_input(f"Capture #{st.session_state.capture_count}", key=f"capture_{st.session_state.capture_count}_reg")
                    if img_buffer:
                        utils.save_image_for_student(st.session_state.enrollment_username, st.session_state.name, Image.open(img_buffer), st.session_state.capture_count)
                        st.session_state.capture_count += 1
                        st.rerun()
                elif st.session_state.capture_count > 10:
                    st.success(f"✅ All 10 images captured for {st.session_state.name}!")
                    with st.spinner('Augmenting...'):
                        aug_ok, aug_msg = utils.augment_training_images(st.session_state.enrollment_username)
                        (st.success if aug_ok else st.error)(aug_msg)
                    
                    # We run training REGARDLESS of augmentation (as per our last fix)
                    with st.spinner('Training AI...'):
                        ok, msg = utils.train_model()
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
            st.session_state.capture_count = 0 # Reset capture state if user switches
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
    # Reset UI state variables when logged in
    st.session_state.show_login_form = False
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False
    st.session_state.show_reset_password_form = False

    st.markdown(CSS, unsafe_allow_html=True) # Inject CSS after login
    user_info = utils.get_user_by_username(st.session_state["username"])
    if not user_info:
        st.error("User details not found. Logging out."); authenticator.logout('Logout', 'main')
    else:
        # Update session state with full user info from DB
        st.session_state.update(user_info)

        # --- Render Header ---
        col1, col2, col3 = st.columns([1.5, 3, 1])
        with col1: 
            try:
                st.image("logo.png", width=70)
            except Exception:
                st.markdown("### 🎓")  # Fallback emoji if logo missing
        with col2: st.markdown(f"<div class='centered-user-info'><strong>{st.session_state['name']}</strong><span>Logged in as: {st.session_state['role'].title()}</span></div>", unsafe_allow_html=True)
        with col3: authenticator.logout('Logout', 'main', key='main_logout')
        st.markdown("---")

        # --- Render Role-Based App ---
        # Pass the authenticator object to the functions
        if st.session_state['role'] == 'admin': admin_app(authenticator)
        elif st.session_state['role'] == 'teacher': teacher_app(authenticator)
        elif st.session_state['role'] == 'student': student_app(authenticator)

# If authentication failed after a login attempt
elif st.session_state["authentication_status"] is False:
    st.markdown(CSS, unsafe_allow_html=True) # Inject CSS for login page
    st.markdown( f""" <div class='login-container'> <img src='data:image/png;base64,{utils.get_base64_image("logo.png")}' class='login-logo'> <h1>Welcome to Hajri.ai</h1> <h3>Please log in or register.</h3> </div> """, unsafe_allow_html=True)
    st.error('Username/password is incorrect')
    # If login failed, typically you'd want to stay on the login form
    st.session_state.show_login_form = True
    st.session_state.show_register_form = False
    st.session_state.show_forgot_password_form = False
    st.session_state.show_reset_password_form = False # Ensure this is false if login failed
    
    # You might want to re-render the login form here, or let the `if st.session_state.show_login_form:` block handle it.
    # For now, `st.rerun()` is implicit after error, and it will re-enter the `if st.session_state.authentication_status is None:` block.
    # Re-rendering `authenticator.login` here explicitly would be redundant given the flow.
    # Let's just ensure the correct UI state is set.

    # Optional: If you want to show 'Forgot Password' link even after a failed login, you can put it here.
    # For this flow, we're making it a separate "page" controlled by a button.
