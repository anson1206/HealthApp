
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

# Title for the app
st.title("Health Data Explorer")

# Create a sidebar option for file input that will then be parsed through
uploaded_file = st.sidebar.file_uploader("Choose a file", type=['xml', 'gpx'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.xml'):
        @st.cache_data
        def load_data(uploaded_file):
            tree = ET.parse(uploaded_file)
            root = tree.getroot()

            # Goes through the data from Apple Health and shows the heart rate over time
            heart_rate_data = []
            for record in root.findall('.//Record[@type="HKQuantityTypeIdentifierHeartRate"]'):
                creation_date_str = record.get('creationDate')
                creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S %z")
               # creation_date = creation_date.replace(second=0, microsecond=0)
                value = record.get('value')
                if value is not None and value.isdigit():
                    heart_rate = int(value)
                    heart_rate_data.append({
                        'Date': creation_date.date(),
                        'Time': creation_date.time().strftime("%I:%M:%S %p"),
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
                start_date_str = workout.get('startDate')
                end_date_str = workout.get('endDate')
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S %z")
                #start_date = start_date.replace(second=0, microsecond=0)
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
                #creation_date = creation_date.replace(second=0, microsecond=0)
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
                #creation_date = creation_date.replace(second=0, microsecond=0)
                value = record.get('value')
                if value is not None and value.isdigit():
                    flight_count = int(value)
                    flights_climbed_data.append({
                        'Date': creation_date.date(),
                        'Time': creation_date.time().strftime("%I:%M:%S %p"),
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

            return merged_df
        merged_df = load_data(uploaded_file)



        # Group by Date and take the maximum Distance for each day
        distance_per_day = merged_df[merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].max().reset_index()
        #Group by Date and take the sum of calories for each day
        calories_per_day = merged_df.groupby('Date')['Calories'].sum().reset_index()

        # The side bar for the user to select things
        selected_data = st.sidebar.radio("Select Data to Display", ["Heart Rate", "Distance", "Flights Climbed", "Calories",
                                                                    "Water Intake",  "Convert to CVS" , "Data Frame"])

        # Create a date picker in the sidebar
        selected_date = st.sidebar.date_input("Select Date", min_value=min(merged_df['Date']), max_value=max(merged_df['Date']), value=min(merged_df['Date']))

        # Filter data for the selected date
        filtered_df = merged_df[merged_df['Date'] == selected_date]


        # Create a data frame for water intake
        if 'water_intake_df' not in st.session_state:
            st.session_state.water_intake_df = pd.DataFrame(columns=['Date', 'Water Intake (gallons)'])
        #creates a data frame for caloric intake
        if 'calory_intake_df' not in st.session_state:
            st.session_state.calory_intake_df = pd.DataFrame(columns=['Date', 'Calories'])

        if selected_data == "Water Intake":
            st.write('Select the date first before enetering the amount of water you drank')
            water_intake_oz = st.sidebar.number_input("Enter the amount of water you drank in fluid ounces", min_value=0,  value=0)
            #turns the inputted water intake into gallons
            water_intake_gal = water_intake_oz / 128
            st.write('You drank', water_intake_gal, 'gallons of water today')
            #Display the data
            newEntry = pd.DataFrame({'Date': selected_date, 'Water Intake (gallons)': [water_intake_gal]})
            st.session_state.water_intake_df = pd.concat([st.session_state.water_intake_df, newEntry], ignore_index=True)
            water_per_day = st.session_state.water_intake_df.groupby('Date')['Water Intake (gallons)'].sum().reset_index()
            st.bar_chart(water_per_day.set_index('Date')['Water Intake (gallons)'])


        # Plot the selected data over time
        #Shows the heart rate and calories burned over time
        if selected_data == "Heart Rate":
            st.write('Here is your heart rate and calories burned over time')
            st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
            #st.line_chart(filtered_df.set_index('Time')[['Calories']])
            st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
        #Allows the user to choose the amount of calories they ate and see how many they ate over time
        elif selected_data == "Calories":
            st.write('Here is the calories burned over time')
            st.bar_chart(merged_df.groupby('Date')['Calories'].sum().reset_index().set_index('Date')['Calories'])
           # st.dataframe(merged_df.groupby('Date')['Calories'].sum().reset_index())


            #calory intake data
            st.write('Select the date first before entering the amount of calories you ate')
            calory_intake = st.sidebar.number_input("Enter the amount of calories you ate", min_value=0, value=0)

            newEntry = pd.DataFrame({'Date': selected_date, 'Calories': [calory_intake]})
            st.session_state.calory_intake_df = pd.concat([st.session_state.calory_intake_df, newEntry], ignore_index=True)
            calories_ate_per_day = st.session_state.calory_intake_df.groupby('Date')['Calories'].sum().reset_index()
            st.bar_chart(calories_ate_per_day.set_index('Date')['Calories'])
        #Shows the distance over time
        elif selected_data == "Distance":
            st.write('Here is the total distance over time')
            #st.bar_chart(merged_df[merged_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])].groupby('Date')['Distance'].sum().reset_index().set_index('Date')['Distance'])
            st.bar_chart(distance_per_day.set_index('Date')['Distance'])
       #Shows the flights climbed over time
        elif selected_data == "Flights Climbed":
            st.write('You Climbed ', merged_df['Flights'].sum(), ' flights of stairs')
            st.bar_chart(merged_df.groupby('Date')['Flights'].sum().reset_index().set_index('Date')['Flights'])
        #Shows the data frame
        elif selected_data == "Data Frame":
            st.write('Here is the data frame where you can look through the data to see information')
            st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'Flights', 'WorkoutType', 'Calories']])
        #Allows the user to download the data frame as a CSV file
        #elif selected_data == "Convert to CVS":
         #   st.write('Here is the data frame converted to a CSV file')
           # csv = merged_df.to_csv(index=False)
           # st.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')
    #Allows the user to input a gpx file
    elif uploaded_file.name.endswith('.gpx'):
        map = GPXMap(uploaded_file)
        map.display_map()

else:
    st.write("Please upload an XML file to proceed.")

if st.sidebar.button("Convert to CSV"):
    csv = merged_df.to_csv(index=False)
    st.sidebar.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')
#Allows the user to open the journal
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

