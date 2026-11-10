"""National App — export all data, or selected state(s), as CSV."""
import streamlit as st
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from common import require_login, get_admin_client, fetch_all

require_login()
sb = get_admin_client()
st.title("Export")

states = fetch_all(lambda: sb.table("states").select("*").order("name"))
state_codes = [s["code"] for s in states] if states else []

pick = st.multiselect("Limit to state(s) — leave empty for ALL states", state_codes)

if pick:
    staff_data = fetch_all(lambda: sb.table("staff").select("*").in_("state_code", pick))
else:
    staff_data = fetch_all(lambda: sb.table("staff").select("*"))
staff_ids = [s["id"] for s in staff_data]

if pick:
    instances_data = fetch_all(
        lambda: sb.table("test_instances")
        .select("*, staff!inner(state_code, level, designation, tu)")
        .in_("staff.state_code", pick)
    )
else:
    instances_data = fetch_all(
        lambda: sb.table("test_instances").select("*, staff!inner(state_code, level, designation, tu)")
    )

staff_df = pd.DataFrame(staff_data)
instances_df = pd.json_normalize(instances_data)

st.subheader("Staff")
st.dataframe(staff_df, use_container_width=True)
st.subheader("Test instances")
st.dataframe(instances_df, use_container_width=True)

buf = BytesIO()
with ZipFile(buf, "w") as zf:
    zf.writestr("staff.csv", staff_df.to_csv(index=False))
    zf.writestr("test_instances.csv", instances_df.to_csv(index=False))

label = "all_states" if not pick else "_".join(pick)
st.download_button(
    f"Download CSV export ({'all states' if not pick else ', '.join(pick)}) as .zip",
    buf.getvalue(),
    file_name=f"expand_elevate_export_{label}.zip",
    mime="application/zip",
)
