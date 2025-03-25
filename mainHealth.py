import streamlit as st
from datetime import datetime
from HealthDataLoader import HealthDataLoader
from HealthDataExplorer import HealthDataExplorer
from AIBot import AIBot
import Journal
from Map import GPXMap
from io import BytesIO

st.title("Health Data Explorer")



# File uploaders
uploaded_xml_file = st.sidebar.file_uploader("Choose an XML file", type=['xml'])
uploaded_gpx_file = st.sidebar.file_uploader("Choose a GPX file", type=['gpx'])


# Cache the processed health data
@st.cache_data
def load_cached_data(file_bytes, min_year=None):
    bio = BytesIO(file_bytes)
    file_obj = BytesIO()
    file_obj.write(bio.getvalue())
    file_obj.seek(0)

    data_loader = HealthDataLoader(file_obj, min_year=min_year)
    return data_loader.merged_df


health_data = None

#Makes sure that the year slider is only displayed if an XML file is uploaded
if uploaded_xml_file is not None:
    file_bytes = uploaded_xml_file.getvalue()
    health_data = load_cached_data(file_bytes)
    first_date = health_data['Date'].min().year
    last_date = health_data['Date'].max().year

    # Add slider for  year filter  in sidebar
    min_year = st.sidebar.slider("Year Filter", first_date, last_date, first_date)
    st.session_state['min_year'] = min_year
    include_all_years = st.sidebar.checkbox("Include all years", False)
    st.session_state['include_all_years'] = include_all_years

# Process uploaded files
if uploaded_xml_file is not None and uploaded_gpx_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.header("Health Data")
        if uploaded_xml_file is not None:
            with st.spinner("Processing health data..."):
                # Use the effective min_year
                effective_min_year = None if include_all_years else min_year
                # Get file bytes for caching
                file_bytes = uploaded_xml_file.getvalue()
                # Use cached data
                health_data = load_cached_data(file_bytes, effective_min_year)
                explorer = HealthDataExplorer(health_data)
                explorer.display_data()
    with col2:
        st.header("GPX Map")
        if uploaded_gpx_file is not None:
            map = GPXMap(uploaded_gpx_file)
            map.display_map()

elif uploaded_xml_file is not None and uploaded_gpx_file is None:
    with st.spinner("Processing health data..."):
        effective_min_year = None if include_all_years else min_year
        file_bytes = uploaded_xml_file.getvalue()
        health_data = load_cached_data(file_bytes, effective_min_year)
        explorer = HealthDataExplorer(health_data)
        explorer.display_data()

elif uploaded_xml_file is None and uploaded_gpx_file is not None:
    map = GPXMap(uploaded_gpx_file)
    map.display_map()

# Journal section
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

# Chatbot section
if st.sidebar.button("Open Chatbot"):
    st.session_state['show_chatbot'] = True

if st.session_state.get('show_chatbot', False):
    api_key = st.secrets["OPENAI_API_KEY"]
    chatbot = AIBot(api_key, health_data)
    chatbot.display_chat()
    if st.button("Close Chatbot"):
        st.session_state['show_chatbot'] = False



if uploaded_xml_file is None and uploaded_gpx_file is None:
    st.write("Please upload an XML file and/or a GPX file to proceed.")

# Convert to CSV button
if st.sidebar.button("Convert to CSV"):
    st.session_state['show_convert_to_csv'] = True

if st.session_state.get('show_convert_to_csv', False):
    st.write('You can download the data as a CSV file')
    if health_data is not None:
        csv = health_data.to_csv(index=False)
        st.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')
    else:
        st.write("No data to convert to CSV")
    if st.button("Close CSV"):
        st.session_state['show_convert_to_csv'] = False