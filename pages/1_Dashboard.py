"""National App — paired pre/post dashboard with paired t-tests."""
import streamlit as st
import pandas as pd
from scipy import stats
from common import require_login, get_admin_client

require_login()
sb = get_admin_client()
st.title("Dashboard — Paired Pre/Post Results")

qmeta = sb.table("questionnaire_meta").select("*").eq("is_active", True).limit(1).execute()
if not qmeta.data:
    st.info("No active questionnaire yet.")
    st.stop()
questionnaire_id = qmeta.data[0]["id"]
st.caption(f"Active questionnaire: **{qmeta.data[0]['title']}**")

instances = (
    sb.table("test_instances")
    .select("*, staff!inner(state_code, level, designation)")
    .eq("questionnaire_id", questionnaire_id)
    .eq("status", "completed")
    .execute()
)
df = pd.json_normalize(instances.data) if instances.data else pd.DataFrame()

if df.empty:
    st.info("No completed test instances yet.")
    st.stop()

df = df.rename(columns={"staff.state_code": "state_code", "staff.level": "level", "staff.designation": "designation"})

col1, col2 = st.columns(2)
with col1:
    states = ["All"] + sorted(df["state_code"].unique().tolist())
    pick_state = st.selectbox("Filter by state", states)
with col2:
    levels = ["All"] + sorted(df["level"].dropna().unique().tolist())
    pick_level = st.selectbox("Filter by level/designation", levels)

filtered = df.copy()
if pick_state != "All":
    filtered = filtered[filtered["state_code"] == pick_state]
if pick_level != "All":
    filtered = filtered[filtered["level"] == pick_level]

# Pair pre/post per staff_id
pre = filtered[filtered["stage"] == "pre"][["staff_id", "score"]].rename(columns={"score": "pre_score"})
post = filtered[filtered["stage"] == "post"][["staff_id", "score"]].rename(columns={"score": "post_score"})
paired = pre.merge(post, on="staff_id", how="inner").dropna()

st.metric("Staff with BOTH pre and post completed (paired)", len(paired))
st.metric("Total completed instances in view", len(filtered))

if len(paired) >= 2:
    t_stat, p_val = stats.ttest_rel(paired["post_score"], paired["pre_score"])
    mean_diff = (paired["post_score"] - paired["pre_score"]).mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Mean pre-score", round(paired["pre_score"].mean(), 2))
    c2.metric("Mean post-score", round(paired["post_score"].mean(), 2))
    c3.metric("Mean improvement", round(mean_diff, 2))
    st.subheader("Paired t-test (post vs pre)")
    st.write(f"t-statistic = **{t_stat:.3f}**, p-value = **{p_val:.4f}**")
    if p_val < 0.05:
        st.success("Statistically significant difference (p < 0.05).")
    else:
        st.warning("Not statistically significant at the 0.05 level.")

    st.subheader("Paired scores")
    st.dataframe(paired, use_container_width=True)
else:
    st.info("Need at least 2 staff with both pre and post completed to run a paired t-test.")
