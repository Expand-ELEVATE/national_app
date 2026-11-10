"""National App — create the single active questionnaire.

Only one questionnaire can be active at a time. To create a new one while
one already exists, the admin must go to the Admin -> Delete Data page
first (which forces a backup download before deleting).
"""
import streamlit as st
import pandas as pd
from common import require_login, get_admin_client

require_login()
sb = get_admin_client()
st.title("Questionnaire Builder")

existing = sb.table("questionnaire_meta").select("*").eq("is_active", True).limit(1).execute()

if existing.data:
    st.warning(
        f"An active questionnaire already exists: **{existing.data[0]['title']}**. "
        "Delete it from 'Admin — Delete Data' (with backup) before creating a new one."
    )
    qs = (
        sb.table("questions")
        .select("*")
        .eq("questionnaire_id", existing.data[0]["id"])
        .order("question_no")
        .execute()
    )
    st.dataframe(pd.DataFrame(qs.data), use_container_width=True)
    st.stop()

st.markdown(
    """
    Upload a CSV with exactly these columns:
    `question_no, question_text, option_a, option_b, option_c, option_d, correct_option`

    - `correct_option` must be one of `A`, `B`, `C`, `D`.
    - To **bold important words** in a question, wrap them in double
      asterisks in `question_text`, e.g. `What is the **maximum** value?`
      — this is the only markdown formatting staff will see; everything
      else (including Excel-formula-style text like `$A$2` or `=SUM(A2:A10)`)
      renders as plain literal text, never italic or broken formatting.
    - Option text (`option_a`..`option_d`) is always shown as plain text —
      bolding is not applied there, only in `question_text`.
    - See `docs/questionnaire_template.csv` in the repo for a template.
    """
)

title = st.text_input("Questionnaire title")
uploaded = st.file_uploader("Upload questions CSV", type="csv")

if uploaded and title:
    df = pd.read_csv(uploaded)
    required_cols = {
        "question_no", "question_text", "option_a", "option_b",
        "option_c", "option_d", "correct_option",
    }
    if not required_cols.issubset(df.columns):
        st.error(f"Missing required columns: {required_cols - set(df.columns)}")
    elif not df["correct_option"].isin(["A", "B", "C", "D"]).all():
        st.error("correct_option must be A, B, C, or D for every row.")
    else:
        st.dataframe(df, use_container_width=True)
        if st.button("Create this questionnaire"):
            meta = sb.table("questionnaire_meta").insert({"title": title, "is_active": True}).execute()
            qid = meta.data[0]["id"]
            records = [
                {
                    "questionnaire_id": qid,
                    "question_no": int(row["question_no"]),
                    "question_text": row["question_text"],
                    "option_a": row["option_a"],
                    "option_b": row["option_b"],
                    "option_c": row["option_c"],
                    "option_d": row["option_d"],
                    "correct_option": row["correct_option"],
                }
                for _, row in df.iterrows()
            ]
            sb.table("questions").insert(records).execute()
            st.success(f"Questionnaire '{title}' created with {len(records)} questions.")
            st.rerun()
