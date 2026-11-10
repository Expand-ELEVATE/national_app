"""National App — manage the list of participating states/UTs.

This is the master lookup table (`states`) that every state_app deployment
and every staff/dropdown in the system depends on. Only the national admin
can add, rename, or remove entries here.
"""
import streamlit as st
import pandas as pd
from common import require_login, get_admin_client

require_login()
sb = get_admin_client()
st.title("Manage States")

st.markdown(
    """
    This is the master list of participating states/UTs. A state's
    `code` here **must exactly match** the `STATE_CODE` secret that state's
    own Streamlit deployment is configured with — mismatches will cause
    that state's login to fail with a "state does not match deployment"
    error.
    """
)

existing = sb.table("states").select("*").order("name").execute()
st.subheader("Current states")
st.dataframe(pd.DataFrame(existing.data), use_container_width=True)

st.divider()
st.subheader("Add a new state")

with st.form("add_state"):
    code = st.text_input("Code (short, unique, e.g. 'MH', 'KA', 'DL')").strip().upper()
    name = st.text_input("Full name (e.g. 'Maharashtra')").strip()
    submitted = st.form_submit_button("Add state")

if submitted:
    if not code or not name:
        st.error("Both code and name are required.")
    else:
        existing_codes = {s["code"] for s in existing.data} if existing.data else set()
        if code in existing_codes:
            st.error(f"Code '{code}' already exists.")
        else:
            sb.table("states").insert({"code": code, "name": name}).execute()
            st.success(
                f"Added state: {code} — {name}. "
                f"Give this exact code to that state's data analyst for their "
                f"Streamlit secrets (`STATE_CODE = \"{code}\"`)."
            )
            st.rerun()

st.divider()
st.subheader("Remove a state")
st.warning(
    "Only remove a state if it has NO staff records, test instances, or "
    "translations yet — those reference the state code via foreign keys "
    "and removal will fail (safely) if any exist. This prevents accidental "
    "data loss; delete the dependent records first via 'Admin — Delete Data' "
    "if you really need to retire a state with existing data."
)
state_codes = [s["code"] for s in existing.data] if existing.data else []
if state_codes:
    to_remove = st.selectbox("Select a state code to remove", [""] + state_codes)
    if to_remove and st.button(f"Remove {to_remove}", type="primary"):
        try:
            sb.table("states").delete().eq("code", to_remove).execute()
            st.success(f"Removed state {to_remove}.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not remove — likely has existing data referencing it: {e}")
