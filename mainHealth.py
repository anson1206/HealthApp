import streamlit as st
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET

# Title for the app
st.title("Health Data Explorer")

# Create a sidebar option for file input that will then be parsed through
uploaded_file = st.sidebar.file_uploader("Choose a file", type="xml")
if uploaded_file is not None:
    tree = ET.parse(uploaded_file)
    root = tree.getroot()

    # Goes through the data from Apple Health and shows the heart rate over time
    heart_rate_data = []
    for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierHeartRate"]'):
        creation_date_str = record.get('creationDate')
        creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
        creation_date = creation_date.replace(second=0, microsecond=0)

        value = record.get('value')
        if value is not None and value.isdigit():
            heart_rate = int(value)
            heart_rate_data.append({
                'Date': creation_date.date(),
                'Time': creation_date.time(),
                'HeartRate': heart_rate
            })

    heart_rate_df = pd.DataFrame(heart_rate_data)
    #st.write("Heart Rate Data:", heart_rate_df)  # Debug statement

    # Ensure the 'Date' column exists before converting
    if 'Date' in heart_rate_df.columns:
        heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
    else:
        st.error("The 'Date' column does not exist in heart_rate_df")

    # Goes through workouts set by the user and shows the distance the user had gone in miles
    workout_info = []
    for workout in root.findall('.//Workout'):
        distance = float('nan')
       # calories = float('nan')
        start_date_str = workout.get('startDate')
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
        start_date = start_date.replace(second=0, microsecond=0)
        unit = workout.get('unit')
        workout_type = workout.get('workoutActivityType')
        for value in workout.findall('WorkoutStatistics'):
            if value.get('type') == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
                distance = float(value.get('sum'))
        # If there isn't a distance, sets it to 0
        if pd.isna(distance):
            distance = 0.0
        workout_info.append({
            'Date': start_date.date(),
            'Time': start_date.time(),
            'Distance': distance,
            'Unit': unit,
            'Workout': workout_type
        })
    workoutNew_df = pd.DataFrame(workout_info)
   # st.write("Workout Data:", workoutNew_df)  # Debug statement

    #extracts the calories data
    calories_data = []
    for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierActiveEnergyBurned"]'):
        creation_date_str = record.get('creationDate')
        creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
        creation_date = creation_date.replace(second=0, microsecond=0)
        value = record.get('value')
        if value is not None:
            calories = float(value)
            calories_data.append({
                'Date': creation_date.date(),
                'Time': creation_date.time(),
                'Calories': calories
            })
    calories_df = pd.DataFrame(calories_data)
    #st.write("Calories Data:", calories_df)  # Debug statement

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
        creation_date = creation_date.replace(second=0, microsecond=0)
        value = record.get('value')
        if value is not None and value.isdigit():
            flight_count = int(value)
            flights_climbed_data.append({
                'Date': creation_date.date(),
                'Time': creation_date.time(),
                'Flights': flight_count
            })
    stair_count_df = pd.DataFrame(flights_climbed_data)
    #st.write("Flights Climbed Data:", stair_count_df)  # Debug statement

    # Counts the total number of flights
    total_flights = stair_count_df['Flights'].sum()

    # Merges the data frames together on Date and Time
    merged_df = pd.merge(heart_rate_df, workoutNew_df, on=['Date', 'Time'], how='left')
    merged_df = pd.merge(merged_df, stair_count_df, on=['Date', 'Time'], how='left')
    merged_df = pd.merge(merged_df, calories_df, on=['Date', 'Time'], how='left')
    #st.write("Merged Data:", merged_df)  # Debug statement


    # Converts time to string in 12-hour format from the heart rate df
    merged_df['Time'] = merged_df['Time'].apply(lambda x: x.strftime("%I:%M:%S %p"))

    # Group by Date and take the maximum Distance for each day
    distance_per_day = merged_df[merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].max().reset_index()
    #Group by Date and take the sum of calories for each day
    calories_per_day = merged_df.groupby('Date')['Calories'].sum().reset_index()

    # The side bar for the user to select things
    selected_data = st.sidebar.radio("Select Data to Display", ["Heart Rate", "Distance", "Flights Climbed", "Calories",  "Data Frame"])

    # Create a date picker in the sidebar
    selected_date = st.sidebar.date_input("Select Date", min_value=min(merged_df['Date']), max_value=max(merged_df['Date']), value=min(merged_df['Date']))

    # Filter data for the selected date
    filtered_df = merged_df[merged_df['Date'] == selected_date]
    #st.write("Filtered Data:", filtered_df)  # Debug statement

    # Plot the selected data over time
    if selected_data == "Heart Rate":
        st.write('Here is your heart rate and calories burned over time')
        st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
        #st.line_chart(filtered_df.set_index('Time')[['Calories']])
        st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
    elif selected_data == "Calories":
        st.write('Here is the calories burned over time')
        st.bar_chart(calories_per_day.set_index('Date')['Calories'])
        st.dataframe(calories_per_day.set_index('Date')[ 'Calories'])
        st.dataframe(calories_per_day)
    elif selected_data == "Distance":
        st.write('Here is the total distance over time')
        st.bar_chart(distance_per_day.set_index('Date')['Distance'])
    elif selected_data == "Flights Climbed":
        st.write('You Climbed ', total_flights, ' flights of stairs')
        st.bar_chart(stair_count_df.set_index('Date')['Flights'])
    elif selected_data == "Data Frame":
        st.write('Here is the data frame where you can look through the data to see information')
        st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'Flights', 'WorkoutType', 'Calories']])
else:
    st.write("Please upload an XML file to proceed.")