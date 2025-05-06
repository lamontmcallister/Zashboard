# recruiter_dashboard.py

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- Page Setup -----------------
st.set_page_config(page_title="Recruiter Platform", layout="wide")

# ----------------- Load Data from Google Sheets -----------------
@st.cache_data(ttl=600)
def load_google_sheet(sheet_url, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# ----------------- Data Prep -----------------
def prepare_dataframe(df):
    df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
    df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
    df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

    agg_df = df.groupby("Candidate").agg({
        "Recruiter": "first",
        "Interview Score": "mean",
        "Scorecard Complete": "sum"
    }).reset_index()

    agg_df.rename(columns={
        "Interview Score": "Avg_Interview_Score",
        "Scorecard Complete": "Scorecards_Submitted"
    }, inplace=True)
    return agg_df

def make_decision(row):
    if row['Scorecards_Submitted'] < 4:
        return "Waiting"
    elif row['Avg_Interview_Score'] <= 3.4:
        return "Reject"
    elif row['Avg_Interview_Score'] >= 3.5:
        return "HM Review"
    return "Discuss"

def status_badge(decision):
    color_map = {
        "Waiting": "orange",
        "Reject": "red",
        "HM Review": "green",
        "Discuss": "gray"
    }
    color = color_map.get(decision, "blue")
    return f"<span style='padding:4px 8px; background-color:{color}; color:white; border-radius:4px'>{decision}</span>"

# ----------------- Load & Process -----------------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"

raw_df = load_google_sheet(sheet_url, worksheet_name)
df = prepare_dataframe(raw_df)

df['Decision'] = df.apply(make_decision, axis=1)
df['Decision Badge'] = df['Decision'].apply(status_badge)

# ----------------- Filters -----------------
st.sidebar.title("Filters")
selected_recruiter = st.sidebar.selectbox("Select Recruiter", ["All"] + sorted(df["Recruiter"].dropna().unique()))
selected_decision = st.sidebar.selectbox("Select Decision", ["All"] + sorted(df["Decision"].unique()))

filtered_df = df.copy()
if selected_recruiter != "All":
    filtered_df = filtered_df[filtered_df["Recruiter"] == selected_recruiter]
if selected_decision != "All":
    filtered_df = filtered_df[filtered_df["Decision"] == selected_decision]

# ----------------- Summary Cards -----------------
st.title("Recruiter Dashboard")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Candidates", len(filtered_df))
col2.metric("Scorecards Submitted", filtered_df["Scorecards_Submitted"].sum())
col3.metric("Avg Interview Score", round(filtered_df["Avg_Interview_Score"].mean(), 2))
col4.metric("HM Reviews", (filtered_df["Decision"] == "HM Review").sum())

# ----------------- CSS Styling -----------------
st.markdown('''
<style>
    .stButton button {
        border: 1px solid #1e90ff;
        background-color: #ffffff;
        color: #1e90ff;
    }
    thead tr th:first-child {
        position: sticky;
        left: 0;
        background-color: #f9f9f9;
        z-index: 1;
    }
    th {
        background-color: #f0f8ff;
        text-align: center;
    }
    td {
        text-align: center !important;
    }
</style>
''', unsafe_allow_html=True)

# ----------------- Show Data Table -----------------
def color_score(val):
    if pd.isna(val):
        return ""
    if val >= 4:
        return "background-color: #d4edda"
    elif val <= 3:
        return "background-color: #f8d7da"
    return ""

styled_df = filtered_df[["Candidate", "Recruiter", "Avg_Interview_Score", "Scorecards_Submitted", "Decision Badge"]]
styled_df_display = styled_df.style.format(escape="html").applymap(color_score, subset=["Avg_Interview_Score"]).hide(axis="index")

st.write("### Candidate Table")
st.write(styled_df_display.to_html(escape=False), unsafe_allow_html=True)
