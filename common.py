"""Supabase client + auth helpers shared by national_app pages."""
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_anon_client() -> Client:
    """Used only for the login step (sign_in_with_password)."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


@st.cache_resource
def get_admin_client() -> Client:
    """service_role key — bypasses RLS. Used for all privileged data ops
    once the national role has been confirmed at login. This key must
    NEVER be exposed to state_app or any non-national deployment."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])


def login_screen():
    st.title("Expand ELEVATE — National Admin Login")

    if "nat_user_id" in st.session_state:
        return True

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        sb = get_anon_client()
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as e:
            st.error(f"Login failed: {e}")
            return False

        admin = get_admin_client()
        profile = (
            admin.table("admin_profiles")
            .select("role")
            .eq("user_id", res.user.id)
            .maybe_single()
            .execute()
        )
        if not profile or not profile.data or profile.data["role"] != "national":
            st.error("This account does not have national admin privileges.")
            sb.auth.sign_out()
            return False

        st.session_state["nat_user_id"] = res.user.id
        st.session_state["nat_email"] = email
        st.rerun()

    return False


def require_login():
    if not login_screen():
        st.stop()


def fetch_all(build_query, page_size: int = 1000) -> list[dict]:
    """Page through a Supabase/PostgREST query until all rows are fetched.

    PostgREST (and therefore supabase-py) silently caps any query at 1000
    rows by default — a plain .select("*").execute() on a large table
    returns only the first 1000 with NO error. This loops with .range()
    until a short page signals the end. `build_query` must be a zero-arg
    callable returning a FRESH query builder each call, since supabase-py
    query objects are consumed once .execute()'d.
    """
    rows: list[dict] = []
    offset = 0
    while True:
        res = build_query().range(offset, offset + page_size - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows
