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

# ---------- DASHBOARD LAYOUT ----------
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

# ---------- MANUAL ENTRY FORM ----------
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
            # EDIT MODE
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
            # NORMAL MODE
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