
import streamlit as st
import pandas as pd
from UserInputHandler import UserInputHandler

class HealthDataExplorer:
    def __init__(self, merged_df):
        self.merged_df = merged_df

    def display_data(self):
        selected_data = st.sidebar.radio("Select Data to Display", ["Heart Rate", "Distance", "Flights Climbed", "Calories", "Water Intake", "Convert to CSV", "Data Frame", "User Input"])
        selected_date = st.sidebar.date_input("Select Date", min_value=min(self.merged_df['Date']), max_value=max(self.merged_df['Date']), value=min(self.merged_df['Date']))

        if 'last_selected_date' not in st.session_state or st.session_state.last_selected_date != selected_date:
            st.session_state.last_selected_date = selected_date
            st.session_state.water_intake_oz = 0
            st.session_state.calory_intake = 0
            st.session_state.water_input = 0
            st.session_state.calory_input = 0

        filtered_df = self.merged_df[self.merged_df['Date'] == selected_date]

        if selected_data == "Heart Rate":
            st.write('Here is your heart rate and calories burned over time')
            st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
            st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
        elif selected_data == "Distance":
            distance_per_day = self.merged_df[self.merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].max().reset_index()
            st.write('Here is the total distance over time')
            st.bar_chart(distance_per_day.set_index('Date')['Distance'])
        elif selected_data == "Flights Climbed":
            st.write('You Climbed ', self.merged_df['Flights'].sum(), ' flights of stairs')
            st.bar_chart(self.merged_df.groupby('Date')['Flights'].sum().reset_index().set_index('Date')['Flights'])
        elif selected_data == "Calories":
            st.write('Here is the calories burned over time')
            st.bar_chart(self.merged_df.groupby('Date')['Calories'].sum().reset_index().set_index('Date')['Calories'])
        elif selected_data == "Data Frame":
            st.write('Here is the data frame where you can look through the data to see information')
            st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'Flights', 'WorkoutType', 'Calories']])
        elif selected_data == "User Input":
            water_intake, calory_intake = st.columns(2)
            with water_intake:
                st.write('Select the date first before entering the amount of water you drank')
                UserInputHandler().add_water_intake(selected_date)
            with calory_intake:
                st.write('Select the date first before entering the amount of calories you ate')
                UserInputHandler().add_calory_intake(selected_date)
        elif selected_data == "Convert to CSV":
            csv = self.merged_df.to_csv(index=False)
            st.sidebar.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')