"""
Authentication Manager Module
Handles user authentication with Supabase
"""

import streamlit as st
from supabase import create_client, Client
from typing import Optional

class AuthManager:
    """Manages user authentication and session state"""
    
    def __init__(self):
        """Initialize Supabase clients"""
        self.supabase = None
        self.supabase_admin = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Supabase clients with proper error handling"""
        try:
            # Get Supabase client for authentication (uses anon key)
            self.supabase = create_client(
                st.secrets["supabase_url"],
                st.secrets["supabase_key"]
            )
            
            # Get Supabase admin client for database operations (uses service role key)
            self.supabase_admin = create_client(
                st.secrets["supabase_url"],
                st.secrets["supabase_service_role_key"]
            )
        except Exception as e:
            st.error(f"Error connecting to Supabase: {e}")
            st.info("Please check your Supabase configuration in secrets.toml")
    
    def login(self, email: str, password: str) -> bool:
        """
        Attempt to log in a user
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.supabase:
            st.error("Authentication service is not available")
            return False
        
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if response.user:
                st.session_state.user = response.user.id
                st.session_state.user_email = response.user.email
                st.session_state.access_token = response.session.access_token
                return True
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
        return False
    
    def signup(self, email: str, password: str) -> bool:
        """
        Create a new user account
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            bool: True if signup successful, False otherwise
        """
        if not self.supabase:
            st.error("Authentication service is not available")
            return False
        
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            if response.user:
                st.success("Account created! Please check your email to verify your account, then log in.")
                return True
        except Exception as e:
            st.error(f"Sign up failed: {str(e)}")
        return False
    
    def logout(self):
        """Log out the current user"""
        st.session_state.user = None
        st.session_state.user_email = None
        st.session_state.access_token = None
        st.session_state.show_saved_recipes = False
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated"""
        return st.session_state.user is not None
    
    def get_user_id(self) -> Optional[str]:
        """Get the current user's ID"""
        return st.session_state.user
    
    def get_user_email(self) -> Optional[str]:
        """Get the current user's email"""
        return st.session_state.user_email
    
    def render_sidebar(self):
        """Render the authentication sidebar"""
        st.markdown("## 👤 Account")
        
        if not self.is_authenticated():
            # Show login/signup options
            auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])
            
            with auth_tab1:
                self._render_login_form()
            
            with auth_tab2:
                self._render_signup_form()
        else:
            # User is logged in
            st.success(f"Logged in as: {self.get_user_email()}")
            if st.button("Logout"):
                self.logout()
                st.rerun()
    
    def _render_login_form(self):
        """Render the login form"""
        st.subheader("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            if login_email and login_password:
                if self.login(login_email, login_password):
                    st.success(f"Welcome back, {login_email}!")
                    st.rerun()
            else:
                st.warning("Please enter email and password")
    
    def _render_signup_form(self):
        """Render the signup form"""
        st.subheader("Create Account")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
        
        if st.button("Sign Up", key="signup_btn"):
            if signup_email and signup_password:
                if signup_password == signup_password_confirm:
                    self.signup(signup_email, signup_password)
                else:
                    st.error("Passwords don't match!")
            else:
                st.warning("Please fill in all fields")
