
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Recruiter Platform", layout="wide")

# --------- Google Sheets Setup ---------
def load_google_sheet(sheet_url, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# --------- Load Data ---------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)
departments = sorted(df['Department'].dropna().unique().tolist())


# --------- Sidebar Filters Replaced with Inline Filter Bar ---------
st.markdown("### 🔍 Filter Candidates")

col1, col2, col3 = st.columns([1.5, 2, 2])

# Recruiter filter
recruiter_list = sorted(df['Recruiter'].dropna().unique().tolist()) if 'Recruiter' in df.columns else []
default_recruiter = recruiter_list[0] if recruiter_list else None
with col1:
    recruiter_filter = st.selectbox("👤 Recruiter", recruiter_list, key="recruiter_filter")

# Department filter as multi-select
department_list = sorted(df['Department'].dropna().unique().tolist()) if 'Department' in df.columns else []
with col2:
    selected_departments = st.multiselect("🏢 Department", department_list, default=department_list)

# Scorecard status radio
with col3:
    scorecard_status = st.radio("📋 Show Candidates With", ["Complete Scorecards", "Pending Scorecards", "All"], horizontal=True, key="scorecard_status")

# Apply filters
if recruiter_filter:
    df = df[df["Recruiter"] == recruiter_filter]

if selected_departments:
    df = df[df["Department"].isin(selected_departments)]

if scorecard_status == "Complete Scorecards":
    df = df[df["Score"].notna()]
elif scorecard_status == "Pending Scorecards":
    df = df[df["Score"].isna()]

# Optional reset button
if st.button("🔄 Reset Filters"):
    st.session_state.recruiter_filter = default_recruiter
    st.session_state.scorecard_status = "All"

    st.header("Filter Candidates")
    selected_department = st.selectbox("Department", ["All"] + departments)

# --------- Apply Filters ---------
if selected_department != "All":
    df = df[df["Department"] == selected_department]

# --------- Display Metrics ---------
st.title("Scorecard Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Total Candidates", len(df))
if "Score" in df.columns:
    col2.metric("Avg Score", round(df["Score"].mean(), 1))
    col3.metric("Missing Scores", df["Score"].isna().sum())
else:
    col2.write("Score column not found")
    col3.write("Score column not found")

# --------- Tabs for Views ---------
tab1, tab2 = st.tabs(["Candidate Summary", "Scorecard Completion"])

with tab1:
    st.subheader("Candidate Summary")
    def color_missing(val):
        return 'background-color: #ffcccc' if pd.isna(val) else ''
    st.dataframe(df.style.applymap(color_missing, subset=["Score"] if "Score" in df.columns else None))

with tab2:
    st.subheader("Scorecard Completion Rate by Department")
    if "Score" in df.columns and "Department" in df.columns:
        completion_df = df.groupby("Department")["Score"].apply(lambda x: x.notna().mean()).reset_index()
        completion_df.columns = ["Department", "Completion Rate"]
        completion_df["Completion Rate"] = (completion_df["Completion Rate"] * 100).round(1)
        st.dataframe(completion_df.style.format({"Completion Rate": "{:.1f}%"}).applymap(
            lambda x: "background-color: #d0f0c0" if isinstance(x, float) and x >= 90 else "background-color: #ffd6cc",
            subset=["Completion Rate"]
        ))
    else:
        st.warning("Missing required columns to display completion rates.")
