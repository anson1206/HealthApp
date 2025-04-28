"""
mainHealth.py
Anson Graumann
In this module, the main functionality of the application is implemented.
This acts as the main entry point for the application.
"""


import streamlit as st
from datetime import datetime
from HealthDataLoader import HealthDataLoader
from HealthDataExplorer import HealthDataExplorer
from AIBot import AIBot
import Journal
from Map import GPXMap
from io import BytesIO
import pandas as pd

class Main:
    def __init__(self):
        # Initialize the sidebar file uploaders
        self.uploaded_xml_file = st.sidebar.file_uploader("Upload the Apple Health XML file", type=['xml'])
        self.uploaded_gpx_file = st.sidebar.file_uploader("Upload the Apple Health Workout Route GPX File", type=['gpx'])
        self.health_data = None

    # loades the data from the XML and GPX files, then caches it
    @st.cache_data
    def load_cached_data(_self, file_bytes, min_year=None):
        bio = BytesIO(file_bytes)
        file_obj = BytesIO()
        file_obj.write(bio.getvalue())
        file_obj.seek(0)

        data_loader = HealthDataLoader(file_obj, min_year=min_year)
        return data_loader.merged_df

    # Process the uploaded files
    def process_uploaded_files(self):
        # Check if the XML file is uploaded and load the data
        if self.uploaded_xml_file is not None:
            file_bytes = self.uploaded_xml_file.getvalue()
            self.health_data = self.load_cached_data(file_bytes)
            first_date = self.health_data['Date'].min().year
            last_date = self.health_data['Date'].max().year

            #Year filter for the XML file
            min_year = st.sidebar.slider("Year Filter", first_date, last_date, first_date)
            include_all_years = st.sidebar.checkbox("Include all years", False)

            #Checks if there is a effective min year, otherwise sets to all years
            effective_min_year = None if include_all_years else min_year
            self.health_data = self.load_cached_data(file_bytes, effective_min_year)

        #Checks if both files are uploaded
        if self.uploaded_xml_file and self.uploaded_gpx_file:
            col1, col2 = st.columns(2)
            #Seperates each file into its own column
            with col1:
                st.header("Health Data")
                explorer = HealthDataExplorer(self.health_data)
                explorer.display_data()
            with col2:
                st.header("GPX Map")
                map = GPXMap(self.uploaded_gpx_file)
                map.display_map()
        #Checks if only the XML file is uploaded
        elif self.uploaded_xml_file:
            st.header("Health Data")
            explorer = HealthDataExplorer(self.health_data)
            explorer.display_data()
       ##Checks if only the GPX file is uploaded
        elif self.uploaded_gpx_file:
            st.header("GPX Map")
            map = GPXMap(self.uploaded_gpx_file)
            map.display_map()

    #Displays the journal
    def display_journal(self):
        if st.sidebar.button("Open Journal"):
            st.session_state['show_journal'] = True

        if st.session_state.get('show_journal', False):
            st.title("Journal")
            #Gets the current data and time and sets a default min date
            current_date = datetime.now().date()
            min_date = datetime(2021, 1, 1).date()
            default_date = current_date

            #Checks to see if the health data is available and gets a min date
            if self.health_data is not None:
                dates_series = pd.to_datetime(self.health_data['Date'])
                if not dates_series.empty:
                    min_date = dates_series.dt.date.min()
            #Allows to select a date
            selected_date = st.date_input(
                "Select a date for your journal entry",
                value=default_date,
                min_value=min_date,
                max_value=current_date
            )

            #Adds user input to the journal when the button is pressed
            user_input = st.text_input("Enter your journal entry")
            if st.button("Submit"):
                Journal.add_data(selected_date, user_input)
                st.success("Entry added!")

            if st.button("Close Journal"):
                st.session_state['show_journal'] = False
                st.rerun()

            Journal.show_data()

    # Displays the AI chatbot
    def display_chatbot(self):
        if st.sidebar.button("Open Chatbot"):
            st.session_state['show_chatbot'] = True
        #Checks if the chatbot is open and if there is a valid API key
        if st.session_state.get('show_chatbot', False):
            api_key = st.secrets["OPENAI_API_KEY"]
            chatbot = AIBot(api_key, self.health_data if self.uploaded_xml_file else None)
            chatbot.display_chat()
            if st.button("Close Chatbot"):
                st.session_state['show_chatbot'] = False
                st.rerun()

    # Run method to start the application
    def run(self):
        st.title("Health Insights Dashboard")
        self.process_uploaded_files()
        self.display_journal()
        self.display_chatbot()

        if self.uploaded_xml_file is None and self.uploaded_gpx_file is None:
            st.write("Please upload an XML file and/or a GPX file to proceed.")

        if st.sidebar.button("Convert to CSV"):
            if self.health_data is not None:
                csv = self.health_data.to_csv(index=False)
                st.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')
            else:
                st.write("No data to convert to CSV")

# Run the application
if __name__ == "__main__":
    app = Main()
    app.run()

