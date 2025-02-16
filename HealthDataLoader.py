import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta




class HealthDataLoader:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.merged_df = self.load_data()

    def load_data(self):
        tree = ET.parse(self.uploaded_file)
        root = tree.getroot()

        heart_rate_data = self.extract_heart_rate_data(root)
        workout_info = self.extract_workout_info(root)
        calories_data = self.extract_calories_data(root)
        flights_climbed_data = self.extract_flights_climbed(root)

        heart_rate_df = pd.DataFrame(heart_rate_data)
        workoutNew_df = pd.DataFrame(workout_info)
        calories_df = pd.DataFrame(calories_data)
        stair_count_df = pd.DataFrame(flights_climbed_data)

        heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
        workoutNew_df['Date'] = pd.to_datetime(workoutNew_df['Date']).dt.date

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

        merged_df = pd.merge(heart_rate_df, workoutNew_df, on=['Date', 'Time'], how='left')
        merged_df = pd.merge(merged_df, stair_count_df, on=['Date', 'Time'], how='left')
        merged_df = pd.merge(merged_df, calories_df, on=['Date', 'Time'], how='left')

        return merged_df

    def extract_heart_rate_data(self, root):
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

        return heart_rate_data

    def extract_workout_info(self, root):
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
        return workout_info


    def extract_calories_data(self, root):
        # extracts the calories data
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
        return calories_data

    def extract_flights_climbed(self, root):
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
        return flights_climbed_data