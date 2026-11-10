"""National App — create and revoke NATIONAL admin login credentials.

Same pattern as Manage State Logins, but for role='national' accounts
(state_code is always null). Mirrors that page's Admin API usage.

Deliberately guards against self-lockout: a national admin cannot revoke
their own currently logged-in account from this page.
"""
import streamlit as st
import pandas as pd
import secrets
import string
from common import require_login, get_admin_client

require_login()
sb = get_admin_client()
st.title("Manage National Logins")

st.warning(
    "National admin accounts have full administrative power, including "
    "delete access to all data across all states. Only create these for "
    "people who genuinely need that level of access."
)


def generate_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


st.subheader("Create a new National admin login")
with st.form("create_national_login"):
    email = st.text_input("Official email for the new national admin")
    submitted = st.form_submit_button("Create login")

if submitted:
    if not email.strip():
        st.error("Email is required.")
    else:
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
                {"user_id": created.user.id, "role": "national", "state_code": None}
            ).execute()
            st.success(f"Created National admin login for **{email}**.")
            st.info(
                f"**Temporary password (shown once — copy it now):** `{temp_password}`\n\n"
                "Share this over a secure channel (not plain chat/email where "
                "avoidable). Use 'Reset password' below if a new one is needed later."
            )
        except Exception as e:
            st.error(f"Could not create login: {e}")

st.divider()
st.subheader("Existing National admin logins")

profiles = sb.table("admin_profiles").select("user_id, role").eq("role", "national").execute()
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
            "user_id": p["user_id"],
            "status": "revoked" if banned else "active",
            "is_you": p["user_id"] == st.session_state.get("nat_user_id"),
        }
    )

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

if sum(r["status"] == "active" for r in rows) <= 1:
    st.error(
        "Only one active national admin login exists. Per the turnover "
        "guide (docs/TURNOVER_HANDOVER.md), create at least a second one "
        "before relying on this platform — losing the sole national login "
        "would require Supabase dashboard access to recover."
    )

st.divider()
st.subheader("Revoke a National admin login")
st.markdown(
    """
    Revoking disables the login immediately via a long ban (not deletion) —
    reversible, and any records referencing this admin (e.g. staff rows
    they created) remain intact. **You cannot revoke your own currently
    logged-in account here** — have a second national admin do it, or use
    the Supabase dashboard as a last resort.
    """
)

active_others = [r for r in rows if r["status"] == "active" and not r["is_you"]]
if active_others:
    choice = st.selectbox("Select a login to revoke", [r["email"] for r in active_others])
    if choice and st.button("Revoke this login", type="primary"):
        idx = [r["email"] for r in active_others].index(choice)
        user_id = active_others[idx]["user_id"]
        try:
            sb.auth.admin.update_user_by_id(user_id, {"ban_duration": "876000h"})
            st.success(f"Revoked login for {choice}.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not revoke: {e}")
else:
    st.info("No other active national admin logins to revoke.")

st.divider()
st.subheader("Reset a National admin's password")
active_all = [r for r in rows if r["status"] == "active"]
if active_all:
    choice2 = st.selectbox(
        "Select a login to reset", [r["email"] for r in active_all], key="reset_pick_nat"
    )
    if choice2 and st.button("Generate new temporary password"):
        idx = [r["email"] for r in active_all].index(choice2)
        user_id = active_all[idx]["user_id"]
        new_pw = generate_temp_password()
        try:
            sb.auth.admin.update_user_by_id(user_id, {"password": new_pw})
            st.success(f"Password reset for {choice2}.")
            st.info(f"**New temporary password (shown once):** `{new_pw}`")
        except Exception as e:
            st.error(f"Could not reset password: {e}")
