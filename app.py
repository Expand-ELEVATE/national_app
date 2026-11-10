"""Expand ELEVATE — National App entry point."""
import streamlit as st
from common import require_login

st.set_page_config(page_title="Expand ELEVATE — National App", layout="wide")
require_login()

st.title("Expand ELEVATE — National App")
st.caption(f"Logged in as: {st.session_state.get('nat_email', '')}")

st.markdown(
    """
    Use the sidebar pages to:
    - **Dashboard** — paired pre/post counts and paired t-tests, state or national level
    - **Questionnaire Builder** — create the single active questionnaire
    - **Admin — Delete Data** — destructive table operations with mandatory backup prompt
    - **Export** — download all data, or selected state(s), as CSV
    """
)

st.warning(
    "This app holds the Supabase **service_role** key and can delete all "
    "data. Treat access to this deployment as the most sensitive part of "
    "the whole platform."
)

if st.button("Log out"):
    st.session_state.clear()
    st.rerun()
