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
            row['Interview Score'] * 0.20 +
            row['Reference Score'] * 0.15 +
            row['Performance Review Avg'] * 0.25 +
            row['Promotion Score'] * 0.15 +
            row['Education Score'] * 0.10 +
            row['EQ Score'] * 0.10
        ), 1)
    except:
        return None

def generate_decision(row):
    try:
        if pd.isna(row['Interview Score']):
            return "🟡 Pending Scores"
        elif row['Interview Score'] <= 3.4:
            return "❌ Auto-Reject"
        elif row['Interview Score'] >= 3.5:
            return "✅ HM Discussion"
        return "⚠️ Needs Review"
    except:
        return "Error"

# --------- Load Data ---------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)

# --------- Data Cleanup ---------
numeric_cols = ['Interview Score', 'Reference Score', 'Performance Review Avg',
                'Promotion Score', 'Education Score', 'EQ Score', 'JD Match %']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['QoH Score'] = df.apply(calculate_qoh, axis=1)
df['Scorecard Submitted?'] = df['Interview Score'].apply(lambda x: "✅" if pd.notnull(x) else "❌")
df['Decision Recommendation'] = df.apply(generate_decision, axis=1)

# --------- Streamlit UI ---------
st.set_page_config(page_title="Candidate Scorecard Dashboard", layout="wide")
st.title("🎯 Candidate Scorecard + Quality of Hire Dashboard")
st.caption("Built to enable faster, data-driven hiring decisions — powered by real-time Google Sheets.")

# Sidebar Filter
selected_names = st.sidebar.multiselect("Compare Candidates:", df['Candidate Name'].unique().tolist(),
                                        default=df['Candidate Name'].unique().tolist())

filtered_df = df[df['Candidate Name'].isin(selected_names)]

# Decision Table
st.subheader("✅ Scorecard Submission + Decision Logic")
st.dataframe(
    filtered_df[['Candidate Name', 'Interview Score', 'Scorecard Submitted?', 'Decision Recommendation']],
    use_container_width=True
)

# Charts
st.subheader("📊 Score Comparisons")
score_metrics = ['QoH Score', 'JD Match %', 'Interview Score', 'Reference Score', 'EQ Score']
for metric in score_metrics:
    if metric in filtered_df.columns and filtered_df[metric].notnull().any():
        fig = px.bar(filtered_df, x='Candidate Name', y=metric, text_auto=True,
                     color='Candidate Name', title=f"{metric} Comparison")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

# Candidate Insights
st.subheader("🧠 Candidate Insight Cards")
for _, row in filtered_df.iterrows():
    with st.expander(f"🧾 {row['Candidate Name']}"):
        st.markdown(f"**Personality Type:** {row.get('Personality Type', 'N/A')}")
        st.markdown(f"**Reference Status:** {row.get('Reference Status', 'Unknown')}")
        st.markdown(f"**Skill Gaps:** {row.get('Skill Gaps', 'None')}")
        st.progress(
            int(row['QoH Score']) if pd.notnull(row['QoH Score']) else 0,
            text=f"QoH Score: {row['QoH Score']}%" if pd.notnull(row['QoH Score']) else "QoH Score: N/A"
        )
