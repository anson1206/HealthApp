"""
Journal.py
Anson Graumann
In this module, a simple journal is created to log entries with a date and time.
"""

import streamlit as st
from datetime import datetime
import pytz

# Adds the data as a list to the session state
def add_data(date, entry):
    if 'Journal_data' not in st.session_state:
        st.session_state['Journal_data'] = []

    # Define the local timezone
    local_tz = pytz.timezone('America/New_York')

    # Parse the date and set it to the start of the day in the local timezone
    date = datetime.strptime(str(date), "%Y-%m-%d")
    date = local_tz.localize(date).date()

    # Get the current time in the local timezone
    now = datetime.now(pytz.utc).astimezone(local_tz)
    formatted_time = now.strftime("%I:%M:%S %p")

    # Add the entry to the session state
    st.session_state['Journal_data'].append({
        "entry": entry,
        "date": date,
        "time": formatted_time
    })

# Displays the data in the session state
def show_data():
    if 'Journal_data' in st.session_state and st.session_state['Journal_data']:
        st.write("Journal Entries")
        for i, entry in enumerate(st.session_state['Journal_data']):
            st.write(f"Entry {i + 1}")
            st.write(f"Date: {entry['date']}")
            st.write(f"Time: {entry['time']}")
            st.write(f"Entry: {entry['entry']}")
            st.write("----")
    else:
        st.write("No entries yet")
