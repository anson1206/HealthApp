
import streamlit as st
from HealthDataLoader import HealthDataLoader
from HealthDataExplorer import HealthDataExplorer
from AIBot import AIBot
import Journal
from Map import GPXMap
st.title("Health Data Explorer")

uploaded_xml_file = st.sidebar.file_uploader("Choose an XML file", type=['xml'])
uploaded_gpx_file = st.sidebar.file_uploader("Choose a GPX file", type=['gpx'])

if uploaded_xml_file is not None or uploaded_gpx_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.header("Health Data")
        if uploaded_xml_file is not None:
            data_loader = HealthDataLoader(uploaded_xml_file)
            explorer = HealthDataExplorer(data_loader.merged_df)
            explorer.display_data()
    with col2:
        st.header("GPX Map")
        if uploaded_gpx_file is not None:
            map = GPXMap(uploaded_gpx_file)
            map.display_map()

if st.sidebar.button("Open Journal"):
    st.session_state['show_journal'] = True
    st.divider()
if st.session_state.get('show_journal', False):
    st.title("Journal")
    user_input = st.text_input("Enter your journal entry")
    if st.button("Submit"):
        Journal.add_data(user_input)
        st.success("Entry added!")
    if st.button("Close Journal"):
        st.session_state['show_journal'] = False
    else:
        st.write("No Journal Entries")
    Journal.show_data()
    st.divider()

if st.sidebar.button("Open Chatbot"):
    st.session_state['show_chatbot'] = True
if st.session_state.get('show_chatbot', False):
    st.title("Chatbot")
    st.divider()
    aibot = AIBot()
    if 'user_input' not in st.session_state:
        st.session_state['user_input'] = ""
    st.session_state.user_input = st.text_input("Enter your message", value=st.session_state.user_input)
    if st.button("Submit"):
        st.write("Bot: ", aibot.chat(st.session_state.user_input))

if uploaded_xml_file is None and uploaded_gpx_file is None:
    st.write("Please upload an XML file and/or a GPX file to proceed.")