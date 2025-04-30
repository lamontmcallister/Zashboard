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

# --------- QoH Score Calculation ---------
def calculate_qoh(row):
    try:
        return round((
            row['Avg Interview Score'] * 0.20 +
            row['Reference Score'] * 0.15 +
            row['Performance Review Avg'] * 0.25 +
            row['Promotion'] * 0.15
        ), 1)
    except:
        return None

def generate_decision(avg_score):
    if pd.isna(avg_score):
        return "🟡 Pending Scores"
    elif avg_score <= 3.4:
        return "❌ Auto-Reject"
    elif avg_score >= 3.5:
        return "✅ HM Discussion"
    return "⚠️ Needs Review"

# --------- Load Data ---------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)

# --------- Data Cleanup ---------
numeric_cols = ['Interview Score', 'Reference Score', 'Performance Review Avg', 'Promotion']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        st.warning(f"⚠️ Column not found in sheet: {col}")

# --------- Interview Count Validation ---------
interview_counts = df["Candidate Name"].value_counts()
invalid_counts = interview_counts[interview_counts != 4]

if not invalid_counts.empty:
    st.warning("⚠️ Some candidates do not have exactly 4 interviews:")
    st.dataframe(invalid_counts.rename("Interview Count"))

# --------- Group Data Per Candidate ---------
grouped = df.groupby("Candidate Name").agg({
    "Interview Score": "mean",
    "Scorecard submitted": lambda x: (x == "Yes").sum(),
    "Reference Score": "first",
    "Promotion": "first",
    "Performance Review Avg": "first"
}).reset_index()

grouped.rename(columns={
    "Interview Score": "Avg Interview Score",
    "Scorecard submitted": "# Scorecards Submitted"
}, inplace=True)

grouped["QoH Score"] = grouped.apply(calculate_qoh, axis=1)
grouped["Decision Recommendation"] = grouped["Avg Interview Score"].apply(generate_decision)

# --------- Streamlit UI ---------
st.set_page_config(page_title="Candidate Scorecard Dashboard", layout="wide")
st.title("🎯 Candidate Scorecard + Quality of Hire Dashboard")
st.caption("Built to enable faster, data-driven hiring decisions — powered by real-time Google Sheets.")

# Sidebar Filter
selected_names = st.sidebar.multiselect("Compare Candidates:", grouped['Candidate Name'].tolist(),
                                        default=grouped['Candidate Name'].tolist())

filtered_df = grouped[grouped['Candidate Name'].isin(selected_names)]

# Decision Table
st.subheader("✅ Scorecard Summary + Decision Logic")
st.dataframe(
    filtered_df[['Candidate Name', 'Avg Interview Score', '# Scorecards Submitted',
                 'Decision Recommendation', 'QoH Score']],
    use_container_width=True
)

# Charts
st.subheader("📊 Score Comparisons")
score_metrics = ['QoH Score', 'Avg Interview Score', 'Reference Score']
for metric in score_metrics:
    if metric in filtered_df.columns and filtered_df[metric].notnull().any():
        fig = px.bar(filtered_df, x='Candidate Name', y=metric, text_auto=True,
                     color='Candidate Name', title=f"{metric} Comparison")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
