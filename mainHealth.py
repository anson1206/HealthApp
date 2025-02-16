import streamlit as st
import pandas as pd
import gpxpy
from geopy.distance import geodesic
import folium
from streamlit import session_state
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import Journal
import Map
from Map import GPXMap
from UserInputHandler import UserInputHandler
from AIBot import AIBot

# Title for the app
st.title("Health Data Explorer")

# Create sidebar options for file input
uploaded_xml_file = st.sidebar.file_uploader("Choose an XML file", type=['xml'])
uploaded_gpx_file = st.sidebar.file_uploader("Choose a GPX file", type=['gpx'])

if uploaded_xml_file is not None:
    @st.cache_data
    def load_data(uploaded_file):
        tree = ET.parse(uploaded_file)
        root = tree.getroot()

        # Goes through the data from Apple Health and shows the heart rate over time
        heart_rate_data = []
        for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierHeartRate"]'):
            creation_date_str = record.get('creationDate')
            creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
            value = record.get('value')
            if value is not None and value.isdigit():
                heart_rate = int(value)
                heart_rate_data.append({
                    'Date': creation_date.date(),
                    'Time': creation_date.time().strftime("%I:%M:%S %p"),
                    'HeartRate': heart_rate
                })

        heart_rate_df = pd.DataFrame(heart_rate_data)

        # Ensure the 'Date' column exists before converting
        if 'Date' in heart_rate_df.columns:
            heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
        else:
            st.error("The 'Date' column does not exist in heart_rate_df")

        # Goes through workouts set by the user and shows the distance the user had gone in miles
        workout_info = []
        for workout in root.findall('.//Workout'):
            distance = float('nan')
            start_date_str = workout.get('startDate')
            end_date_str = workout.get('endDate')
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S %z")
            duration = (end_date - start_date).total_seconds()
            unit = workout.get('unit')
            workout_type = workout.get('workoutActivityType')
            for value in workout.findall('WorkoutStatistics'):
                if value.get('type') == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
                    distance = float(value.get('sum'))
            # If there isn't a distance, sets it to 0
            if pd.isna(distance):
                distance = 0.0
            for second in range(int(duration)):
                workout_info.append({
                    'Date': (start_date + timedelta(seconds=second)).date(),
                    'Time': (start_date + timedelta(seconds=second)).time().strftime("%I:%M:%S %p"),
                    'Distance': distance,
                    'Unit': unit,
                    'Workout': workout_type
                })
        workoutNew_df = pd.DataFrame(workout_info)

        #extracts the calories data
        calories_data = []
        for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierActiveEnergyBurned"]'):
            creation_date_str = record.get('creationDate')
            creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
            value = record.get('value')
            if value is not None:
                calories = float(value)
                calories_data.append({
                    'Date': creation_date.date(),
                    'Time': creation_date.time().strftime("%I:%M:%S %p"),
                    'Calories': calories
                })
        calories_df = pd.DataFrame(calories_data)

        # A dictionary for the activities. Makes it easier to read the activities
        activity_dictionary = {
            'HKWorkoutActivityTypeBaseball': 'Baseball',
            'HKWorkoutActivityTypeRunning': 'Running',
            'HKWorkoutActivityTypeWalking': 'Walking',
            'HKWorkoutActivityTypeTraditionalStrengthTraining': 'Strength Training',
            'HKQuantityTypeIdentifierDistanceWalkingRunning': 'RunningWalking'
        }

        # Uses the activity_dictionary to replace the Apple Health names
        workoutNew_df['WorkoutType'] = workoutNew_df['Workout'].map(activity_dictionary)

        # Converts the 'Date' column to datetime in heart_rate_df and workoutNew_df
        heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
        workoutNew_df['Date'] = pd.to_datetime(workoutNew_df['Date']).dt.date

        # Shows the number of flight of stairs you went up
        flights_climbed_data = []
        for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierFlightsClimbed"]'):
            creation_date_str = record.get('creationDate')
            creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
            value = record.get('value')
            if value is not None and value.isdigit():
                flight_count = int(value)
                flights_climbed_data.append({
                    'Date': creation_date.date(),
                    'Time': creation_date.time().strftime("%I:%M:%S %p"),
                    'Flights': flight_count
                })
        stair_count_df = pd.DataFrame(flights_climbed_data)

        # Counts the total number of flights
        total_flights = stair_count_df['Flights'].sum()

        # Merges the data frames together on Date and Time
        merged_df = pd.merge(heart_rate_df, workoutNew_df, on=['Date', 'Time'], how='left')
        merged_df = pd.merge(merged_df, stair_count_df, on=['Date', 'Time'], how='left')
        merged_df = pd.merge(merged_df, calories_df, on=['Date', 'Time'], how='left')

        return merged_df
    merged_df = load_data(uploaded_xml_file)

    # Group by Date and take the maximum Distance for each day
    distance_per_day = merged_df[merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].max().reset_index()
    #Group by Date and take the sum of calories for each day
    calories_per_day = merged_df.groupby('Date')['Calories'].sum().reset_index()

    # The side bar for the user to select things
    selected_data = st.sidebar.radio("Select Data to Display", ["Heart Rate", "Distance", "Flights Climbed", "Calories",
                                                                "Water Intake",  "Convert to CVS" , "Data Frame", "User Input"])

    # Create a date picker in the sidebar
    selected_date = st.sidebar.date_input("Select Date", min_value=min(merged_df['Date']), max_value=max(merged_df['Date']), value=min(merged_df['Date']))

    if 'last_selected_date' not in st.session_state or st.session_state.last_selected_date != selected_date:
        st.session_state.last_selected_date = selected_date
        st.session_state.water_intake_oz = 0
        st.session_state.calory_intake = 0
        st.session_state.water_input = 0
        st.session_state.calory_input = 0


    # Filter data for the selected date
    filtered_df = merged_df[merged_df['Date'] == selected_date]

    # Create a data frame for water intake
    if 'water_intake_df' not in st.session_state:
        st.session_state.water_intake_df = pd.DataFrame(columns=['Date', 'Water Intake (gallons)'])
    #creates a data frame for caloric intake
    if 'calory_intake_df' not in st.session_state:
        st.session_state.calory_intake_df = pd.DataFrame(columns=['Date', 'Calories'])

    # Plot the selected data over time
    #Shows the heart rate and calories burned over time
    if selected_data == "Heart Rate":
        st.write('Here is your heart rate and calories burned over time')
        st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
        st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
    #Shows the distance over time
    elif selected_data == "Distance":
        st.write('Here is the total distance over time')
        st.bar_chart(distance_per_day.set_index('Date')['Distance'])
   #Shows the flights climbed over time
    elif selected_data == "Flights Climbed":
        st.write('You Climbed ', merged_df['Flights'].sum(), ' flights of stairs')
        st.bar_chart(merged_df.groupby('Date')['Flights'].sum().reset_index().set_index('Date')['Flights'])
    #Shows the data frame
    elif selected_data == "Data Frame":
        st.write('Here is the data frame where you can look through the data to see information')
        st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'Flights', 'WorkoutType', 'Calories']])
    #Allows the user to input water and caloric intake
    elif selected_data == "User Input":
        water_intake, calory_intake = st.columns(2)

        with water_intake:
            st.write('Select the date first before entering the amount of water you drank')
            UserInputHandler().add_water_intake(selected_date)

        # Separate handling of calorie intake
        with calory_intake:
            st.write('Select the date first before entering the amount of calories you ate')
            UserInputHandler().add_calory_intake(selected_date)


    st.write(f"Selected date: {selected_date}")


if uploaded_xml_file is None and uploaded_gpx_file is None:
    st.write("Please upload an XML file and/or a GPX file to proceed.")

if st.sidebar.button("Convert to CSV"):
    csv = merged_df.to_csv(index=False)
    st.sidebar.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')

# Allows the user to open the journal
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

#Chatterbot
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

if uploaded_xml_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.header("Health Data")
        if selected_data == "Heart Rate":
            st.write('Here is your heart rate and calories burned over time')
            st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
            st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
        elif selected_data == "Calories":
            st.write('Here is the calories burned over time')
            st.bar_chart(merged_df.groupby('Date')['Calories'].sum().reset_index().set_index('Date')['Calories'])
            st.write('Select the date first before entering the amount of calories you ate')
        elif selected_data == "Distance":
            st.write('Here is the total distance over time')
            st.bar_chart(distance_per_day.set_index('Date')['Distance'])
        elif selected_data == "Flights Climbed":
            st.write('You Climbed ', merged_df['Flights'].sum(), ' flights of stairs')
            st.bar_chart(merged_df.groupby('Date')['Flights'].sum().reset_index().set_index('Date')['Flights'])
        elif selected_data == "Data Frame":
            st.write('Here is the data frame where you can look through the data to see information')
            st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'Flights', 'WorkoutType', 'Calories']])
    with col2:
        st.header("GPX Map")
        if uploaded_gpx_file is not None:
            map = GPXMap(uploaded_gpx_file)
            map.display_map()


