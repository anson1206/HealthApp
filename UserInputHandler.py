import pandas as pd
import streamlit as st
class UserInputHandler:
    def __init__(self):
        #Check if the dataframes exist in the session state
        if 'water_intake_df' not in st.session_state:
            st.session_state.water_intake_df = pd.DataFrame(columns=['Date', 'Water Intake (gallons)'])
        if 'calory_intake_df' not in st.session_state:
            st.session_state.calory_intake_df = pd.DataFrame(columns=['Date', 'Calory Intake (calories)'])

    #Handles the input for water intake
    def add_water_intake(self, selected_date):
        # Input for water intake
        water_intake_oz = st.number_input("Enter the amount of water you drank (in oz)", min_value=0, value=0,
                                          key='water_input')

        # Debug statement
        st.write(f"Water intake (oz): {water_intake_oz}")
        water_intake_gallons = water_intake_oz / 128

        # Convert selected_date to pandas Timestamp for proper comparison
        selected_date_ts = pd.to_datetime(selected_date)

        # Ensure the Date column is also datetime
        if not pd.api.types.is_datetime64_dtype(st.session_state.water_intake_df['Date']):
            st.session_state.water_intake_df['Date'] = pd.to_datetime(st.session_state.water_intake_df['Date'])

        # Check to see if the date already exists in the data frame
        date_exists = (st.session_state.water_intake_df['Date'] == selected_date_ts).any()

        if date_exists:
            # Allows for multiple entries on the same day
            st.session_state.water_intake_df.loc[st.session_state.water_intake_df['Date'] == selected_date_ts,
            'Water Intake (gallons)'] = water_intake_gallons
        else:
            newEntry = pd.DataFrame({'Date': [selected_date_ts], 'Water Intake (gallons)': [water_intake_gallons]})
            st.session_state.water_intake_df = pd.concat([st.session_state.water_intake_df, newEntry],
                                                         ignore_index=True)

        # Display updated graph
        water_per_day = st.session_state.water_intake_df.groupby('Date')['Water Intake (gallons)'].sum().reset_index()
        st.bar_chart(water_per_day.set_index('Date')['Water Intake (gallons)'])

    #Handles the input for calory intake
    def add_calory_intake(self, selected_date):
        # Input for calories
        calory_intake_value = st.number_input("Enter the amount of calories you ate", min_value=0, value=0,
                                              key='calory_input')
        # Debug statement
        st.write(f"Calory intake: {calory_intake_value}")

        # Convert selected_date to pandas Timestamp for proper comparison
        selected_date_ts = pd.to_datetime(selected_date)

        # Ensure the Date column is also datetime
        if not pd.api.types.is_datetime64_dtype(st.session_state.calory_intake_df['Date']):
            st.session_state.calory_intake_df['Date'] = pd.to_datetime(st.session_state.calory_intake_df['Date'])

        # Checks to see if the date already exists in the data frame
        date_exists = (st.session_state.calory_intake_df['Date'] == selected_date_ts).any()

        if date_exists:
            st.session_state.calory_intake_df.loc[
                st.session_state.calory_intake_df['Date'] == selected_date_ts, 'CaloriesIntake'] = calory_intake_value
        else:
            # Adds new entry
            newEntry2 = pd.DataFrame({'Date': [selected_date_ts], 'CaloriesIntake': [calory_intake_value]})
            st.session_state.calory_intake_df = pd.concat([st.session_state.calory_intake_df, newEntry2],
                                                          ignore_index=True)

        # Displays updated graph
        calory_intake_per_day = st.session_state.calory_intake_df.groupby('Date')['CaloriesIntake'].sum().reset_index()
        st.bar_chart(calory_intake_per_day.set_index('Date')['CaloriesIntake'])
