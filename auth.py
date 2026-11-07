"""Role-separated demo login, not deployment-grade authentication."""
import streamlit as st
from storage import verify_credentials


def require_login():
    user = st.session_state.get("ClassPair_auth")
    if user:
        with st.sidebar:
            st.caption(f"Signed in as {user['role']}")
            st.write(user["email"])
            if st.button("Sign out", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key != "_streamlit_internal":
                        del st.session_state[key]
                st.rerun()
        return user

    st.markdown("## Welcome to ClassPair")
    st.write("Your learning space, designed for understanding—not surveillance.")
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        role = st.radio("Sign in to", ["Student", "Professor"], horizontal=True)
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="student@ClassPair.demo")
            password = st.text_input("Password", type="password")
            pressed = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        if pressed:
            attempts = st.session_state.get("login_attempts", 0)
            if attempts >= 8:
                st.error("Too many attempts this session. Please start a new session.")
            else:
                u = verify_credentials(email, password, role)
                if u:
                    st.session_state["ClassPair_auth"] = u
                    st.session_state["login_attempts"] = 0
                    st.rerun()
                else:
                    st.session_state["login_attempts"] = attempts + 1
                    st.error("Invalid credentials for this portal.")
        st.caption("Hackathon demo accounts only. Do not deploy this authentication system for real students.")
    return None
