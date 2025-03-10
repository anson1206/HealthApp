import gzip
from io import BytesIO

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from lxml import etree

# Compress uploaded XML file in-memory
def compress_file(uploaded_file):
    if not uploaded_file or uploaded_file.getbuffer().nbytes == 0:
        raise ValueError("Uploaded file is empty or invalid")

    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as f_out:
        f_out.write(uploaded_file.getvalue())
    return buffer.getvalue()


class HealthDataLoader:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.compressed_data = compress_file(self.uploaded_file)
        self.merged_df = self.load_data()

    #Load data from the compressed XML file
    def load_data(self):
        try:
            with gzip.GzipFile(fileobj=BytesIO(self.compressed_data), mode="rb") as f:
                context = etree.iterparse(f, events=('end',))

                heart_rate_data = []
                workout_info = []
                calories_data = []
                flights_climbed_data = []
                distance_data = []

                for event, elem in context:
                    tag = elem.tag.lower()
                    record_type = elem.get("type")

                    if record_type == "HKQuantityTypeIdentifierHeartRate":
                        hr_data = self.extract_heart_rate_data(elem)
                        if hr_data:
                            heart_rate_data.append(hr_data)
                    elif tag == 'workout':
                        workout_data = self.extract_workout_info(elem)
                        if workout_data:
                            workout_info.extend(workout_data)
                    # Add explicit handling for distance records (in case they exist outside of workouts)
                    elif record_type == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                        distance_record = self.extract_distance_data(elem)
                        if distance_record:
                            distance_data.append(distance_record)
                    elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                        calories_record = self.extract_calories_data(elem)
                        if calories_record:
                            calories_data.append(calories_record)
                    elif record_type == "HKQuantityTypeIdentifierFlightsClimbed":
                        flights_record = self.extract_flights_climbed(elem)
                        if flights_record:
                            flights_climbed_data.append(flights_record)
                    # Free memory after processing
                    elem.clear()

                # Debug information to help diagnose issues
                print(f"Processed data counts: Heart rate={len(heart_rate_data)}, Workout={len(workout_info)}, "
                      f"Distance={len(distance_data)}, Calories={len(calories_data)}, Flights={len(flights_climbed_data)}")

                return self.merge_data(heart_rate_data, workout_info, calories_data, flights_climbed_data,
                                       distance_data)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Error parsing XML file: {e}")
    #Merge all datasets efficiently and optimize memory usage
    def merge_data(self, heart_rate_data, workout_info, calories_data, flights_climbed_data, distance_data=None):
        # Create dataframes from collected data
        heart_rate_df = pd.DataFrame(heart_rate_data) if heart_rate_data else pd.DataFrame(
            columns=['Date', 'Time', 'HeartRate'])
        workout_df = pd.DataFrame(workout_info) if workout_info else pd.DataFrame(
            columns=['Date', 'Time', 'Distance', 'Unit', 'WorkoutType'])
        calories_df = pd.DataFrame(calories_data) if calories_data else pd.DataFrame(
            columns=['Date', 'Time', 'Calories'])
        flights_df = pd.DataFrame(flights_climbed_data) if flights_climbed_data else pd.DataFrame(
            columns=['Date', 'Time', 'Flights'])
        distance_df = pd.DataFrame(distance_data) if distance_data else pd.DataFrame(
            columns=['Date', 'Time', 'Distance'])

        # Debug information
        for df_name, df in [("Heart rate", heart_rate_df), ("Workout", workout_df),
                            ("Distance", distance_df), ("Calories", calories_df),
                            ("Flights", flights_df)]:
            if not df.empty:
                print(f"{df_name} DataFrame has {len(df)} rows and columns: {df.columns.tolist()}")
                if 'Date' in df.columns:
                    print(f"{df_name} date range: {df['Date'].min()} to {df['Date'].max()}")
            else:
                print(f"Warning: Empty {df_name} DataFrame")

        # A dictionary for the activities. Makes it easier to read the activities
        activity_dictionary = {
            'HKWorkoutActivityTypeBaseball': 'Baseball',
            'HKWorkoutActivityTypeRunning': 'Running',
            'HKWorkoutActivityTypeWalking': 'Walking',
            'HKWorkoutActivityTypeTraditionalStrengthTraining': 'Strength Training',
            'HKQuantityTypeIdentifierDistanceWalkingRunning': 'RunningWalking'
        }

        # Uses the activity_dictionary to replace the Apple Health names
        if not workout_df.empty and 'Workout' in workout_df.columns:
            workout_df['WorkoutType'] = workout_df['Workout'].map(activity_dictionary)
            workout_df['WorkoutType'] = workout_df['WorkoutType'].fillna('Other')
            # Debug information
            print(f"Found workout types: {workout_df['Workout'].unique()}")
            print(f"Mapped workout types: {workout_df['WorkoutType'].unique()}")

        # Converts the 'Date' column to datetime in all dataframes
        for df in [heart_rate_df, workout_df, flights_df, calories_df, distance_df]:
            if not df.empty and 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date']).dt.date



        # heart rate data as the base
        if not heart_rate_df.empty:
            merged_df = heart_rate_df.copy()
            # Ensure we have unique rows by Date and Time
            merged_df = merged_df.drop_duplicates(subset=['Date', 'Time'])
        else:
            # If no heart rate data, create a base from workout data
            if not workout_df.empty:
                merged_df = workout_df[['Date', 'Time']].copy()
                merged_df['HeartRate'] = np.nan
            else:
                # If no workout data either, use any available data
                for df, col in [(distance_df, 'Distance'), (flights_df, 'Flights'), (calories_df, 'Calories')]:
                    if not df.empty:
                        merged_df = df[['Date', 'Time']].copy()
                        merged_df['HeartRate'] = np.nan
                        break
                else:
                    # If all data frames are empty, return an empty DataFrame
                    return pd.DataFrame(
                        columns=['Date', 'Time', 'HeartRate', 'Distance', 'WorkoutType', 'Flights', 'Calories'])


        # Add workout data
        if not workout_df.empty:
            # Create a temporary DataFrame with only essential columns
            workout_temp = workout_df[['Date', 'Time', 'Distance', 'Workout', 'WorkoutType']].copy()

            workout_temp = workout_temp.drop_duplicates(subset=['Date', 'Time'])

            # Left join to preserve heart rate records
            merged_df = pd.merge(merged_df, workout_temp, on=['Date', 'Time'], how='left')
        else:
            merged_df['Distance'] = np.nan
            merged_df['WorkoutType'] = None

        # Add standalone distance data where available
        if not distance_df.empty:
            distance_temp = distance_df[['Date', 'Time', 'Distance']].copy()
            distance_temp = distance_temp.rename(columns={'Distance': 'Distance_standalone'})
            distance_temp = distance_temp.drop_duplicates(subset=['Date', 'Time'])

            merged_df = pd.merge(merged_df, distance_temp, on=['Date', 'Time'], how='left')

            # Fill in missing Distance values from standalone distance records
            if 'Distance' in merged_df.columns:
                mask = merged_df['Distance'].isna() & merged_df['Distance_standalone'].notna()
                merged_df.loc[mask, 'Distance'] = merged_df.loc[mask, 'Distance_standalone']
            else:
                merged_df['Distance'] = merged_df['Distance_standalone']

            # Clean up
            if 'Distance_standalone' in merged_df.columns:
                merged_df.drop('Distance_standalone', axis=1, inplace=True)

        # Add flights data
        if not flights_df.empty:
            flights_temp = flights_df[['Date', 'Time', 'Flights']].copy()
            flights_temp = flights_temp.drop_duplicates(subset=['Date', 'Time'])
            merged_df = pd.merge(merged_df, flights_temp, on=['Date', 'Time'], how='left')
        else:
            merged_df['Flights'] = np.nan

        # Add calories data
        if not calories_df.empty:
            calories_temp = calories_df[['Date', 'Time', 'Calories']].copy()
            calories_temp = calories_temp.drop_duplicates(subset=['Date', 'Time'])
            merged_df = pd.merge(merged_df, calories_temp, on=['Date', 'Time'], how='left')
        else:
            merged_df['Calories'] = np.nan

        # Fill NaN values with appropriate defaults only where needed
        if 'Distance' in merged_df.columns:
            merged_df['Distance'] = merged_df['Distance'].fillna(0.0)
        if 'Flights' in merged_df.columns:
            merged_df['Flights'] = merged_df['Flights'].fillna(0)
        if 'Calories' in merged_df.columns:
            merged_df['Calories'] = merged_df['Calories'].fillna(0.0)

        # Final data cleanup and validation
        print(f"Final merged dataframe has {len(merged_df)} rows")
        if 'HeartRate' in merged_df.columns:
            print(f"Heart rate summary: {merged_df['HeartRate'].describe()}")
        if 'Distance' in merged_df.columns:
            print(f"Distance summary: {merged_df['Distance'].describe()}")

        return merged_df

    # Extract data from XML elements
    @staticmethod
    def extract_heart_rate_data(elem):
        try:
            creation_date = elem.get("creationDate")
            value = elem.get("value")
            if creation_date and value and value.isdigit():
                creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S %z")
                return {
                    "Date": creation_date.date(),
                    "Time": creation_date.time().strftime("%I:%M:%S %p"),
                    "HeartRate": int(value)
                }
        except Exception as e:
            print(f"Error parsing heart rate data: {e}")
        return None

    # Extract workout data from an element
    @staticmethod
    def extract_workout_info(elem):
        data = []
        try:
            # Process the workout element directly
            start_date_str = elem.get("startDate")
            end_date_str = elem.get("endDate")
            workout_type = elem.get("workoutActivityType")

            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S %z")
                duration = (end_date - start_date).total_seconds()

                # Initialize distance to 0
                distance = 0.0
                unit = elem.get('unit', 'mi')

                # Looks for distance metrics in WorkoutStatistics
                for value in elem.findall('./WorkoutStatistics'):
                    if value.get('type') == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
                        try:
                            sum_value = value.get('sum')
                            if sum_value:
                                distance = float(sum_value)
                                break
                        except (TypeError, ValueError) as e:
                            print(f"Error converting distance value: {e}")

                if pd.isna(distance):
                    distance = 0.0

                # Create entries for each second of the workout
                for i in range(int(duration)):
                    data.append({
                        "Date": (start_date + timedelta(seconds=i)).date(),
                        "Time": (start_date + timedelta(seconds=i)).time().strftime("%I:%M:%S %p"),
                        "Distance": distance,
                        "Unit": unit,
                        "Workout": workout_type
                    })

                print(f"Extracted workout: {workout_type} with {len(data)} entries")
        except Exception as e:
            print(f"Error parsing workout data: {e}")
        return data

    #Extract standalone distance data from an element
    @staticmethod
    def extract_distance_data(elem):
        try:
            creation_date = elem.get("creationDate")
            value = elem.get("value")
            unit = elem.get("unit", "mi")
            if creation_date and value:
                try:
                    distance = float(value)
                    creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S %z")
                    #print(f"Found standalone distance record: {distance} {unit}")
                    return {
                        "Date": creation_date.date(),
                        "Time": creation_date.time().strftime("%I:%M:%S %p"),
                        "Distance": distance,
                        "Unit": unit
                    }
                except (TypeError, ValueError) as e:
                    print(f"Error converting standalone distance value: {e}")
        except Exception as e:
            print(f"Error parsing standalone distance data: {e}")
        return None

    # Extract calories data from an element
    @staticmethod
    def extract_calories_data(elem):
        try:
            creation_date = elem.get("creationDate")
            value = elem.get("value")
            if creation_date and value:
                creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S %z")
                return {
                    "Date": creation_date.date(),
                    "Time": creation_date.time().strftime("%I:%M:%S %p"),
                    "Calories": float(value)
                }
        except Exception as e:
            print(f"Error parsing calories data: {e}")
        return None

    # Extract flights climbed data from an element
    @staticmethod
    def extract_flights_climbed(elem):
        try:
            creation_date = elem.get("creationDate")
            value = elem.get("value")
            if creation_date and value and value.isdigit():
                creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S %z")
                return {
                    "Date": creation_date.date(),
                    "Time": creation_date.time().strftime("%I:%M:%S %p"),
                    "Flights": int(value)
                }
        except Exception as e:
            print(f"Error parsing flights climbed data: {e}")
        return None
