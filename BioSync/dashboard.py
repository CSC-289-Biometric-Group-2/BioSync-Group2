import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# page config
st.set_page_config (
    page_title = "BioSync Dashboard",
    page_icon = "💓",
    layout = "wide"
)

# style / theme

PRIMARY_COLOR = "#7B3FE4"
ACCENT_COLOR = "#FF6B6B"
BG_COLOR = "#0B1020"
CARD_BG = "#151A30"
TEXT_COLOR = "#FFFFFF"
MUTED_TEXT = "#A0A4B8"

st.markdown(
    f"""
    <style>
    .reportview-container {{
        background: {BG_COLOR};
        color: {TEXT_COLOR};
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .stMetric, .stCard {{
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

# mock data generation
def generate_mock_heart_rate(days: int = 7):
    now = datetime.now()
    timestamps = [now - timedelta(hours=i) for i in range(days * 24)]
    timestamps.reverse()
    data = {
        "timestamp": timestamps,
        "heart_rate": [65 + (i % 15) for i in range(len(timestamps))]
    }
    return pd.DataFrame(data)

def generate_mock_temperature(days: int = 7):
    now = datetime.now()
    timestamps = [now - timedelta(hours=i * 6) for i in range(days * 4)]
    timestamps.reverse()
    data = {
        "timestamp": timestamps,
        "temperature": [36.5 + (i % 5) * 0.1 for i in range(len(timestamps))]
    }
    return pd.DataFrame(data)

def generate_mock_cycle():
    today = datetime.today().date()
    cycle_start = today - timedelta(days=5)
    ovulation = cycle_start + timedelta(days=14)
    next_cycle = cycle_start + timedelta(days=28)
    return {
        "cycle_start": cycle_start,
        "ovulation": ovulation,
        "next_cycle": next_cycle
    }

def generate_mock_vitals():
    return {
        "Blood Pressure": "112 / 74",
        "Resting HR": "62 bpm",
        "SpO₂": "98%",
        "Weight": "142 lb"
    }

hr_df = generate_mock_heart_rate()
temp_df = generate_mock_temperature()
cycle_info = generate_mock_cycle()
vitals = generate_mock_vitals()

# layout

top_col1, top_col2, top_col3 = st.columns([2, 2, 1.5])

with top_col1:
    st.subheader("Heart Rate")
    hr_fig = px.line(
        hr_df,
        x="timestamp",
        y="heart_rate",
        title="Heart Rate (last 7 days)",
        markers=True,
        template="plotly_dark",
        color_discrete_sequence=[PRIMARY_COLOR]
    )
    hr_fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(hr_fig, use_container_width=True)

with top_col2:
    st.subheader("Temperature")
    temp_fig = px.line(
        temp_df,
        x="timestamp",
        y="temperature",
        title="Body Temperature (°C)",
        markers=True,
        template="plotly_dark",
        color_discrete_sequence=[ACCENT_COLOR]
    )
    temp_fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(temp_fig, use_container_width=True)

with top_col3:
    st.subheader("Vitals Summary")
    for label, value in vitals.items():
        st.metric(label=label, value=value)

st.markdown("---")

bottom_col1, bottom_col2 = st.columns([2, 1.5])

with bottom_col1:
    st.subheader("Cycle Calendar")
    st.write(f"**Current cycle start:** {cycle_info['cycle_start']}")
    st.write(f"**Estimated ovulation:** {cycle_info['ovulation']}")
    st.write(f"**Next expected cycle:** {cycle_info['next_cycle']}")
    st.info(
        "A full visual calendar view can be implemented later using a calendar component "
        "or custom grid layout."
    )

with bottom_col2:
    st.subheader("Other Tracking")
    st.write("- Sleep duration and quality")
    st.write("- Stress level")
    st.write("- Activity / steps")
    st.write("- Custom tags (e.g., mood, symptoms)")
    st.caption("These can be added as new cards and charts in future iterations.")