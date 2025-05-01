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

# --------- Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Streamlit Setup ---------

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
tab1, tab2, tab3, tab4 = st.tabs(["🔰 Landing Page", "Scorecard Dashboard", "📊 Department Analytics", "📈 Success Metrics Overview"])
# --------- Landing Page ---------
    # --------- Department Analytics ---------
