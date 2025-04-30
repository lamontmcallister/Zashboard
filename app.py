import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# Load and preprocess
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()

# Decision logic by candidate
decision_df = df.groupby("Candidate Name").agg(
    Avg_Score=('Interview Score', 'mean'),
    Submitted=('Scorecard submitted', lambda x: sum(x == "yes")),
    Department=('Department', 'first')
).reset_index()

def evaluate_status(score_count, avg_score):
    if score_count < 4:
        return "Pending"
    elif avg_score <= 3.4:
        return "Fail"
    elif avg_score >= 3.5:
        return "Pass"
    return "Review"

decision_df["Result"] = decision_df.apply(lambda row: evaluate_status(row["Submitted"], row["Avg_Score"]), axis=1)

# Interviewer-level summary
interviewer_df = df.groupby("Internal Interviewer").agg(
    Interviews_Completed=('Scorecard submitted', lambda x: sum(x == 'yes')),
    Total_Interviews=('Scorecard submitted', 'count'),
    Avg_Score=('Interview Score', 'mean')
).reset_index()

# UI setup
st.set_page_config(page_title="Interviewer Scorecard Analytics", layout="wide")
st.title("🎯 Interviewer Performance Dashboard")
st.caption("Track submission rates and score trends across all interviewers.")
st.markdown(
    "<style>body { background-color: white; color: #000; } div.stButton > button { color: white; background-color: #0066cc; }</style>",
    unsafe_allow_html=True
)

# Submission bar chart
st.subheader("📈 Scorecard Submittal Rate by Interviewer")
interviewer_df["Completion %"] = round((interviewer_df["Interviews_Completed"] / interviewer_df["Total_Interviews"]) * 100, 1)
fig1 = px.bar(interviewer_df, x="Internal Interviewer", y="Completion %", text_auto=True, color="Completion %",
              title="Interview Scorecard Submission Rates")
fig1.update_layout(showlegend=False)
st.plotly_chart(fig1, use_container_width=True)

# Avg scoring trends
st.subheader("📊 Interviewer Average Scores")
fig2 = px.bar(interviewer_df, x="Internal Interviewer", y="Avg_Score", color="Avg_Score", text_auto=True,
              title="Average Interview Scores by Interviewer")
fig2.update_layout(showlegend=False)
st.plotly_chart(fig2, use_container_width=True)

# Departmental pass/fail insight
st.subheader("🏢 Departmental Candidate Outcomes")
dept_summary = decision_df.groupby("Department")["Result"].value_counts().unstack().fillna(0).reset_index()
st.dataframe(dept_summary, use_container_width=True)
