import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="BioSync Dashboard",
    page_icon="💓",
    layout="wide"
)

# ---------- STYLE / THEME ----------
PRIMARY_COLOR = "#7B3FE4"
ACCENT_COLOR = "#FF6B6B"
BG_COLOR = "#0B1020"
CARD_BG = "#151A30"
TEXT_COLOR = "#FFFFFF"

st.markdown(
    f"""
    <style>
    .reportview-container {{
        background: {BG_COLOR};
        color: {TEXT_COLOR};
        font-family: 'Inter', system-ui, sans-serif;
    }}
    .stMetric {{
        background-color: {CARD_BG} !important;
        border-radius: 12px;
        padding: 12px;
    }}
    @media (max-width: 600px) {{
        .block-container {{
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        h1, h2, h3 {{
            font-size: 1.2rem !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("BioSync Health Dashboard")
st.caption("Visualizing your biometric trends for deeper body awareness.")

# ---------- DB HELPERS ----------
DB_PATH = "biosync.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS biometric_reading (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def insert_reading(metric: str, value: float, date: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO biometric_reading (metric, value, date) VALUES (?, ?, ?)",
        (metric, value, date)
    )
    conn.commit()
    conn.close()

def update_reading(reading_id: int, metric: str, value: float, date: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE biometric_reading SET metric=?, value=?, date=? WHERE id=?",
        (metric, value, date, reading_id)
    )
    conn.commit()
    conn.close()

def delete_reading(reading_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM biometric_reading WHERE id=?", (reading_id,))
    conn.commit()
    conn.close()

def get_all_readings() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM biometric_reading", conn)
    conn.close()
    return df

# ---------- VALIDATION ----------
def validate_reading(metric: str, value: float) -> str | None:
    if metric == "Heart Rate" and not (40 <= value <= 200):
        return "Heart rate must be between 40 and 200 bpm."
    if metric == "Temperature" and not (35 <= value <= 42):
        return "Temperature must be between 35°C and 42°C."
    if metric == "SpO₂" and not (70 <= value <= 100):
        return "SpO₂ must be between 70 and 100%."
    if metric == "Weight" and value <= 0:
        return "Weight must be greater than 0."
    return None

# ---------- INIT DB ----------
init_db()

# ---------- SESSION STATE ----------
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

# ---------- LOAD DB READINGS ----------
db_readings = get_all_readings()

# ---------- MOCK DATA GENERATION ----------
def generate_mock_heart_rate(days: int = 7):
    now = datetime.now()
    timestamps = [now - timedelta(hours=i) for i in range(days * 24)]
    timestamps.reverse()
    return pd.DataFrame({
        "timestamp": timestamps,
        "heart_rate": [65 + (i % 15) for i in range(len(timestamps))]
    })

def generate_mock_temperature(days: int = 7):
    now = datetime.now()
    timestamps = [now - timedelta(hours=i * 6) for i in range(days * 4)]
    timestamps.reverse()
    return pd.DataFrame({
        "timestamp": timestamps,
        "temperature": [36.5 + (i % 5) * 0.1 for i in range(len(timestamps))]
    })

def generate_mock_cycle():
    today = datetime.today().date()
    cycle_start = today - timedelta(days=5)
    return {
        "cycle_start": cycle_start,
        "ovulation": cycle_start + timedelta(days=14),
        "next_cycle": cycle_start + timedelta(days=28)
    }

def generate_mock_vitals():
    return {
        "Blood Pressure": "112 / 74",
        "Resting HR": "62 bpm",
        "SpO₂": "98%",
        "Weight": "142 lb"
    }

# ---------- MERGE MANUAL READINGS INTO CHARTS ----------
hr_df = generate_mock_heart_rate()
temp_df = generate_mock_temperature()

if not db_readings.empty:
    hr_manual = db_readings[db_readings["metric"] == "Heart Rate"].copy()
    if not hr_manual.empty:
        hr_manual["timestamp"] = pd.to_datetime(hr_manual["date"])
        hr_manual.rename(columns={"value": "heart_rate"}, inplace=True)
        hr_df = pd.concat([hr_df, hr_manual[["timestamp", "heart_rate"]]], ignore_index=True)
        hr_df.sort_values("timestamp", inplace=True)

    temp_manual = db_readings[db_readings["metric"] == "Temperature"].copy()
    if not temp_manual.empty:
        temp_manual["timestamp"] = pd.to_datetime(temp_manual["date"])
        temp_manual.rename(columns={"value": "temperature"}, inplace=True)
        temp_df = pd.concat([temp_df, temp_manual[["timestamp", "temperature"]]], ignore_index=True)
        temp_df.sort_values("timestamp", inplace=True)

cycle_info = generate_mock_cycle()
vitals = generate_mock_vitals()

# ---------- TOP DASHBOARD LAYOUT ----------
top_col1, top_col2, top_col3 = st.columns([2, 2, 1.5])

with top_col1:
    st.subheader("Heart Rate")
    st.plotly_chart(
        px.line(
            hr_df,
            x="timestamp",
            y="heart_rate",
            title="Heart Rate (mock + manual)",
            markers=True,
            template="plotly_dark",
            color_discrete_sequence=[PRIMARY_COLOR]
        ),
        use_container_width=True
    )

with top_col2:
    st.subheader("Temperature")
    st.plotly_chart(
        px.line(
            temp_df,
            x="timestamp",
            y="temperature",
            title="Temperature (mock + manual)",
            markers=True,
            template="plotly_dark",
            color_discrete_sequence=[ACCENT_COLOR]
        ),
        use_container_width=True
    )

with top_col3:
    st.subheader("Vitals Summary")
    for label, value in vitals.items():
        st.metric(label, value)

st.markdown("---")

# ---------- BASIC CYCLE + OTHER TRACKING ----------
bottom_col1, bottom_col2 = st.columns([2, 1.5])

with bottom_col1:
    st.subheader("Cycle Calendar (Summary)")
    st.write(f"**Current cycle start:** {cycle_info['cycle_start']}")
    st.write(f"**Estimated ovulation:** {cycle_info['ovulation']}")
    st.write(f"**Next expected cycle:** {cycle_info['next_cycle']}")
    st.info("A full visual calendar will be added below.")

with bottom_col2:
    st.subheader("Other Tracking (Planned)")
    st.write("- Sleep duration and quality")
    st.write("- Stress level")
    st.write("- Activity / steps")
    st.write("- Custom tags (e.g., mood, symptoms)")

# ---------- MANUAL ENTRY FORM ----------
st.markdown("---")
st.header("Add a Biometric Reading")

with st.form("manual_entry_form"):
    metric = st.selectbox("Metric", ["Heart Rate", "Temperature", "Weight", "SpO₂"])

    if metric == "Heart Rate":
        value = st.number_input("Heart rate (bpm)", min_value=0, step=1)
    elif metric == "Temperature":
        value = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, step=0.1)
    elif metric == "Weight":
        value = st.number_input("Weight (lb)", min_value=0.0, step=0.1)
    elif metric == "SpO₂":
        value = st.number_input("SpO₂ (%)", min_value=0.0, max_value=100.0, step=1.0)

    date = st.date_input("Date")
    submitted = st.form_submit_button("Add Reading")

if submitted:
    error = validate_reading(metric, float(value))
    if error:
        st.error(error)
    else:
        insert_reading(metric, float(value), str(date))
        st.success("Reading added")
        st.rerun()

# ---------- DISPLAY + EDIT + DELETE ----------
st.markdown("---")
st.header("Your Manual Entries")

db_readings = get_all_readings()

if db_readings.empty:
    st.caption("No manual entries yet.")
else:
    for _, row in db_readings.iterrows():
        rid = int(row["id"])

        if st.session_state.editing_id == rid:
            st.write(f"Editing entry #{rid}")

            new_metric = st.selectbox(
                "Metric",
                ["Heart Rate", "Temperature", "Weight", "SpO₂"],
                index=["Heart Rate", "Temperature", "Weight", "SpO₂"].index(row["metric"]),
                key=f"edit_metric_{rid}"
            )

            if new_metric == "Heart Rate":
                new_value = st.number_input("Heart rate (bpm)", min_value=0, step=1, key=f"edit_val_{rid}")
            elif new_metric == "Temperature":
                new_value = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, step=0.1, key=f"edit_val_{rid}")
            elif new_metric == "Weight":
                new_value = st.number_input("Weight (lb)", min_value=0.0, step=0.1, key=f"edit_val_{rid}")
            else:
                new_value = st.number_input("SpO₂ (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"edit_val_{rid}")

            new_date = st.date_input("Date", value=pd.to_datetime(row["date"]), key=f"edit_date_{rid}")

            save_col, cancel_col = st.columns(2)
            if save_col.button("Save", key=f"save_{rid}"):
                error = validate_reading(new_metric, float(new_value))
                if error:
                    st.error(error)
                else:
                    update_reading(rid, new_metric, float(new_value), str(new_date))
                    st.session_state.editing_id = None
                    st.rerun()

            if cancel_col.button("Cancel", key=f"cancel_{rid}"):
                st.session_state.editing_id = None
                st.rerun()

            st.markdown("---")

        else:
            cols = st.columns([3, 2, 2, 1, 1])
            cols[0].write(row["metric"])
            cols[1].write(row["value"])
            cols[2].write(row["date"])

            if cols[3].button("Edit", key=f"editbtn_{rid}"):
                st.session_state.editing_id = rid
                st.rerun()

            if cols[4].button("Delete", key=f"delbtn_{rid}"):
                delete_reading(rid)
                st.rerun()

            st.markdown("---")

# ---------- FILTERING SCAFFOLD ----------
st.markdown("---")
st.header("Filter Readings")

with st.expander("Filtering Options"):
    filter_metric = st.multiselect(
        "Filter by metric",
        ["Heart Rate", "Temperature", "Weight", "SpO₂", "Sleep", "Stress", "Steps", "Mood"]
    )
    filter_date_range = st.date_input("Date range", [])
    st.button("Apply Filters")
    st.caption("Filtering logic will be implemented later.")

# ---------- PAGINATION SCAFFOLD ----------
st.markdown("---")
st.header("Pagination")

colA, colB, colC = st.columns([1, 1, 1])
with colA:
    st.button("Previous Page")
with colB:
    st.write("Page 1 of N (placeholder)")
with colC:
    st.button("Next Page")
st.caption("Pagination logic will be added later.")

# ---------- USER ACCOUNTS SCAFFOLD ----------
st.markdown("---")
st.header("User Accounts")

with st.expander("Account Settings (Placeholder)"):
    st.text_input("Username")
    st.text_input("Email")
    st.text_input("Password", type="password")
    st.button("Create Account")
    st.button("Login")
    st.caption("User authentication and storage will be added later.")

# ---------- FULL CYCLE CALENDAR SCAFFOLD ----------
st.markdown("---")
st.header("Cycle Calendar (Full View)")

st.write("A full interactive cycle calendar will appear here in the future.")
st.info("Planned: visual grid with cycle phases, ovulation, symptoms overlay.")

# ---------- SYMPTOMS & MOOD TRACKING SCAFFOLD ----------
st.markdown("---")
st.header("Symptoms & Mood Tracking")

with st.form("symptom_form"):
    mood = st.selectbox("Mood", ["Happy", "Neutral", "Sad", "Stressed", "Irritable"])
    symptoms = st.multiselect(
        "Symptoms",
        ["Cramps", "Headache", "Fatigue", "Bloating", "Tender Breasts", "Back Pain"]
    )
    note = st.text_area("Notes")
    st.form_submit_button("Log Entry")
st.caption("Later: save to a symptom_log table and visualize trends.")

# ---------- ADDITIONAL BIOMETRIC CHARTS SCAFFOLD ----------
st.markdown("---")
st.header("Additional Biometric Charts")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Sleep Patterns")
    st.line_chart(pd.DataFrame({"sleep_hours": []}))
    st.caption("Placeholder for future sleep data.")

with chart_col2:
    st.subheader("Stress Levels")
    st.line_chart(pd.DataFrame({"stress_score": []}))
    st.caption("Placeholder for future stress data.")

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.subheader("Steps / Activity")
    st.line_chart(pd.DataFrame({"steps": []}))
    st.caption("Placeholder for future activity data.")

with chart_col4:
    st.subheader("Mood Tracking")
    st.line_chart(pd.DataFrame({"mood_score": []}))
    st.caption("Placeholder for future mood trend data.")