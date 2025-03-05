import pandas as pd
import numpy as np
from lxml import etree
from datetime import datetime, timedelta
import streamlit as st

class HealthDataLoader:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.merged_df = self.load_data()

    def load_data(self):
        tree = etree.parse(self.uploaded_file)
        root = tree.getroot()

        heart_rate_data = list(self.extract_heart_rate_data(root))
        workout_info = list(self.extract_workout_info(root))
        calories_data = list(self.extract_calories_data(root))
        flights_climbed_data = list(self.extract_flights_climbed(root))

        heart_rate_df = pd.DataFrame(heart_rate_data)
        workoutNew_df = pd.DataFrame(workout_info)
        calories_df = pd.DataFrame(calories_data)
        stair_count_df = pd.DataFrame(flights_climbed_data)

        heart_rate_df['Date'] = pd.to_datetime(heart_rate_df['Date']).dt.date
        workoutNew_df['Date'] = pd.to_datetime(workoutNew_df['Date']).dt.date

        activity_dictionary = {
            'HKWorkoutActivityTypeBaseball': 'Baseball',
            'HKWorkoutActivityTypeRunning': 'Running',
            'HKWorkoutActivityTypeWalking': 'Walking',
            'HKWorkoutActivityTypeTraditionalStrengthTraining': 'Strength Training',
            'HKQuantityTypeIdentifierDistanceWalkingRunning': 'RunningWalking'
        }

        workoutNew_df['WorkoutType'] = workoutNew_df['Workout'].map(activity_dictionary)

        merged_df = heart_rate_df.merge(workoutNew_df, on=['Date', 'Time'], how='left') \
                                 .merge(stair_count_df, on=['Date', 'Time'], how='left') \
                                 .merge(calories_df, on=['Date', 'Time'], how='left')

        return merged_df

    @staticmethod
    @st.cache_data
    def extract_heart_rate_data(_root):
        heart_rate_data = []
        for record in _root.xpath('.//Record[@type="HKQuantityTypeIdentifierHeartRate"]'):
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

    @staticmethod
    @st.cache_data
    def extract_workout_info(_root):
        workout_info = []
        for workout in _root.xpath('.//Workout'):
            distance = float('nan')
            start_date_str = workout.get('startDate')
            end_date_str = workout.get('endDate')
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S %z")
            duration = (end_date - start_date).total_seconds()
            unit = workout.get('unit')
            workout_type = workout.get('workoutActivityType')
            for value in workout.xpath('WorkoutStatistics[@type="HKQuantityTypeIdentifierDistanceWalkingRunning"]'):
                distance = float(value.get('sum'))
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

    @staticmethod
    @st.cache_data
    def extract_calories_data(_root):
        calories_data = []
        for record in _root.xpath('.//Record[@type="HKQuantityTypeIdentifierActiveEnergyBurned"]'):
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

    @staticmethod
    @st.cache_data
    def extract_flights_climbed(_root):
        flights_climbed_data = []
        for record in _root.xpath('.//Record[@type="HKQuantityTypeIdentifierFlightsClimbed"]'):
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