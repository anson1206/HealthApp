import streamlit as st
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET

tree = ET.parse('export.xml')
root = tree.getroot()

# Goes through the data from Apple Health and shows the heart rate over time
heart_rate_data = []
for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN"]'):
    creation_date_str = record.get('creationDate')
    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")

    for entry in record.findall('.//InstantaneousBeatsPerMinute'):
        time_str = entry.get('time')
        time = datetime.strptime(time_str, "%I:%M:%S.%f %p").time()
        heart_rate = int(entry.get('bpm'))

        heart_rate_data.append({
            'Date': creation_date.date(),
            'Time': time,
            'HeartRate': heart_rate
        })

heart_rate_df = pd.DataFrame(heart_rate_data)

#Goes through workouts set by the user and shows the distance the user had gone in miles
workout_info = []
for workout in root.findall('.//Workout'):
    distance = float('nan')
    start_date_str = workout.get('startDate')
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
    unit = workout.get('unit')
    workout_type = workout.get('workoutActivityType')
    for dist in workout.findall('WorkoutStatistics'):
        if dist.get('type') == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
            distance = float(dist.get('sum'))
    # If there isn't a distance, sets it to 0
    if pd.isna(distance):
        distance = 0.0
    workout_info.append({
        'Date': start_date.date(),
        'Distance': distance,
        'Unit': unit,
        'Workout': workout_type
    })
workoutNew_df = pd.DataFrame(workout_info)



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

# Convert 'Date' column to datetime in heart_rate_df and workoutNew_df
heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
workoutNew_df['Date'] = pd.to_datetime(workoutNew_df['Date']).dt.date

# Merge heart rate and workout data on Date
merged_df = pd.merge(heart_rate_df, workoutNew_df, on='Date', how='left')





# Converts time to string in 12-hour format from the heart rate df
merged_df['Time'] = merged_df['Time'].apply(lambda x: x.strftime("%I:%M:%S %p"))

# Group by Date and take the maximum Distance for each day
distance_per_day = merged_df[merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].max().reset_index()







#Shows the number of flight of stairs you went up
flights_climbed_data = []
for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierFlightsClimbed"]'):
    creation_date_str = record.get('creationDate')
    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
    flight_count = int(record.get('value'))
    print(creation_date)
    print(flight_count)

    flights_climbed_data.append({
        'Date': creation_date.date(),
        'Flights': flight_count
    })
stair_count_df = pd.DataFrame(flights_climbed_data)

#Counts the total number of stairs
total_flights = 0
for stairs in stair_count_df['Flights']:
    total_flights+= flight_count

print(total_flights)



# Streamlit App
st.title("Health Data Explorer")

# Sidebar for date and data selection
#selected_date = st.sidebar.date_input("Select Date", min_value=min(heart_rate_df['Date']),
                                     #max_value=max(heart_rate_df['Date']), value=min(heart_rate_df['Date']))

# The side bar for the user to select things
selected_data = st.sidebar.radio("Select Data to Display", ["Heart Rate", "Distance", "Flights Climbed"])

# Filter data for the selected date



# Plot the selected data over time
if selected_data == "Heart Rate":
    selected_date = st.sidebar.date_input("Select Date", min_value=min(heart_rate_df['Date']), max_value=max(heart_rate_df['Date']), value=min(heart_rate_df['Date']))
    filtered_df = merged_df[merged_df['Date'] == selected_date]

    st.write('Here is your heart rate over time')
    st.line_chart(filtered_df.set_index('Time')['HeartRate'])
elif selected_data == "Distance":
    st.bar_chart(distance_per_day.set_index('Date')['Distance'])
elif selected_data == "Flights Climbed":
    st.write('You Climbed ' , total_flights , ' flights of stairs')
    st.line_chart(stair_count_df.set_index('Date')['Flights'])

# Display the DataFrame
#st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance']])