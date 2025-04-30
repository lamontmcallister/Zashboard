import streamlit as st
import pandas as pd
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

# --------- Load Data ---------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)

# --------- Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Streamlit Setup ---------
st.set_page_config(page_title="Recruiter Platform", layout="wide")

st.markdown(
    '''
    <style>
        body {
            background-color: #ffffff;
            color: #1a1a1a;
        }
        .stButton button {
            border: 1px solid #1e90ff;
            background-color: #ffffff;
            color: #1e90ff;
        }
        th {
            font-weight: bold;
            background-color: #f0f8ff;
        }
        td {
            text-align: center !important;
        }
        .dataframe {
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    </style>
    ''',
    unsafe_allow_html=True
)

# --------- Navigation ---------
page = st.sidebar.selectbox("🔍 Navigate", ["🔰 Landing Page", "🎯 Recruiter Dashboard", "📊 Department Analytics"])

# --------- Landing Page ---------
if page == "🔰 Landing Page":
    st.title("Welcome to the Recruiter Decision Dashboard")
    st.markdown("This platform helps you evaluate candidates based on interviewer feedback, scorecard submissions, and department-level analytics — all in one view.")

    st.subheader("✨ Why This Matters")
    st.markdown("""
- Ensure fair, consistent hiring decisions  
- Track scorecard submission and identify bottlenecks  
- Empower recruiters with structured decision support
""")

    st.subheader("🧭 How to Use This Tool")
    st.markdown("""
1. Head to the **Recruiter Dashboard** tab  
2. Select a recruiter and optionally filter by department or scorecard status  
3. Review candidate decisions and send reminder nudges  
4. Use **Department Analytics** to track overall submission and scoring health
""")

    st.success("Tip: Click any candidate name in the dashboard to view interview details!")

# Remaining pages not included for brevity (Recruiter Dashboard, Analytics)...
