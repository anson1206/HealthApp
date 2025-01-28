import streamlit as st
import pandas as pd
from datetime import datetime

def add_data(entry):
    if 'Journal_data' not in st.session_state:
        st.session_state['Journal_data'] = []
    st.session_state['Journal_data'].append({
        "entry": entry,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time": datetime.now().strftime("%H:%M:%S")
    })

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
