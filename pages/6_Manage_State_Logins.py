"""National App — create and revoke State admin login credentials.

Uses the Supabase Auth Admin API (available because this app holds the
service_role key) to create/ban/delete users directly, instead of requiring
the national admin to go into the Supabase dashboard by hand.
"""
import streamlit as st
import pandas as pd
import secrets
import string
from common import require_login, get_admin_client

require_login()
sb = get_admin_client()
st.title("Manage State Logins")

states = sb.table("states").select("code, name").order("name").execute()
state_options = {s["name"]: s["code"] for s in states.data} if states.data else {}

if not state_options:
    st.warning("No states exist yet. Add states first on the 'Manage States' page.")
    st.stop()


def generate_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


st.subheader("Create a new State admin login")
with st.form("create_state_login"):
    state_name = st.selectbox("State", list(state_options.keys()))
    email = st.text_input("Official email for this state's analyst")
    submitted = st.form_submit_button("Create login")

if submitted:
    if not email.strip():
        st.error("Email is required.")
    else:
        code = state_options[state_name]
        temp_password = generate_temp_password()
        try:
            created = sb.auth.admin.create_user(
                {
                    "email": email.strip(),
                    "password": temp_password,
                    "email_confirm": True,
                }
            )
            sb.table("admin_profiles").insert(
                {"user_id": created.user.id, "role": "state", "state_code": code}
            ).execute()
            st.success(
                f"Created State admin login for **{email}** (state: {state_name}, code: {code})."
            )
            st.info(
                f"**Temporary password (shown once — copy it now):** `{temp_password}`\n\n"
                "Share this with the analyst over a secure channel (not plain chat/email "
                "if avoidable). They should log in once and there is currently no in-app "
                "'change password' flow — use 'Reset password' below later if needed."
            )
        except Exception as e:
            st.error(f"Could not create login: {e}")

st.divider()
st.subheader("Existing admin logins")

profiles = sb.table("admin_profiles").select("user_id, role, state_code").execute()
rows = []
for p in (profiles.data or []):
    try:
        user = sb.auth.admin.get_user_by_id(p["user_id"])
        email = user.user.email
        banned = getattr(user.user, "banned_until", None)
    except Exception:
        email = "(user record missing)"
        banned = None
    rows.append(
        {
            "email": email,
            "role": p["role"],
            "state_code": p["state_code"],
            "user_id": p["user_id"],
            "status": "revoked" if banned else "active",
        }
    )

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("Revoke a State admin login")
st.markdown(
    """
    Revoking disables the login immediately (it cannot sign in again) but
    keeps the historical record of who created which staff IDs/test
    instances intact — nothing in `staff` or `test_instances` is deleted.
    Use this the moment a state analyst's contract ends, per the turnover
    guide (`docs/TURNOVER_HANDOVER.md`).
    """
)

state_admins = [r for r in rows if r["role"] == "state" and r["status"] == "active"]
if state_admins:
    choice = st.selectbox(
        "Select a login to revoke",
        [f"{r['email']} ({r['state_code']})" for r in state_admins],
    )
    if choice and st.button("Revoke this login", type="primary"):
        idx = [f"{r['email']} ({r['state_code']})" for r in state_admins].index(choice)
        user_id = state_admins[idx]["user_id"]
        try:
            # Ban far into the future rather than delete — preserves audit
            # trail (created_by references on staff rows) and is reversible
            # if the revoke was a mistake.
            sb.auth.admin.update_user_by_id(user_id, {"ban_duration": "876000h"})
            st.success(f"Revoked login for {choice}.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not revoke: {e}")
else:
    st.info("No active state admin logins to revoke.")

st.divider()
st.subheader("Reset a State admin's password")
if state_admins:
    choice2 = st.selectbox(
        "Select a login to reset",
        [f"{r['email']} ({r['state_code']})" for r in state_admins],
        key="reset_pick",
    )
    if choice2 and st.button("Generate new temporary password"):
        idx = [f"{r['email']} ({r['state_code']})" for r in state_admins].index(choice2)
        user_id = state_admins[idx]["user_id"]
        new_pw = generate_temp_password()
        try:
            sb.auth.admin.update_user_by_id(user_id, {"password": new_pw})
            st.success(f"Password reset for {choice2}.")
            st.info(f"**New temporary password (shown once):** `{new_pw}`")
        except Exception as e:
            st.error(f"Could not reset password: {e}")
