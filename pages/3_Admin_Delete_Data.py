"""National App — destructive admin operations.

Mandatory flow: export a full backup CSV first, confirm you have it,
THEN the delete button becomes available. This is the only place in
either app that can delete data, and it uses the service_role key.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from common import require_login, get_admin_client, fetch_all

require_login()
sb = get_admin_client()
st.title("Admin — Delete Data")

st.error(
    "This deletes the ENTIRE active questionnaire and ALL associated staff, "
    "test instances, responses and translations across EVERY state. "
    "This cannot be undone. You must download a full backup before this "
    "is allowed."
)

TABLES = ["responses", "test_instances", "state_questionnaire_translations", "staff", "questions", "questionnaire_meta"]


def build_backup_zip() -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        for t in TABLES:
            rows = fetch_all(lambda t=t: sb.table(t).select("*"))
            df = pd.DataFrame(rows) if rows else pd.DataFrame()
            zf.writestr(f"{t}.csv", df.to_csv(index=False))
    return buf.getvalue()


st.subheader("Step 1 — Download full backup")
backup_bytes = build_backup_zip()
st.download_button(
    "Download full backup (all tables, .zip of CSVs)",
    backup_bytes,
    file_name="expand_elevate_backup.zip",
    mime="application/zip",
)

st.subheader("Step 2 — Confirm and delete")
confirmed_download = st.checkbox("I have downloaded and safely stored the backup above.")
confirm_text = st.text_input("Type DELETE to confirm")

if confirmed_download and confirm_text == "DELETE":
    if st.button("Permanently delete all questionnaire data", type="primary"):
        # Delete in FK-safe order: children before parents. Supabase's
        # delete() requires a filter, so use a condition that matches every
        # row regardless of the primary key's type (uuid vs text).
        for t in ["responses", "test_instances", "state_questionnaire_translations", "staff", "questions", "questionnaire_meta"]:
            pk = "id"
            sb.table(t).delete().not_.is_(pk, "null").execute()
        st.success("All questionnaire data deleted. You can now create a new questionnaire.")
else:
    st.info("Download the backup and type DELETE to enable the delete button.")
