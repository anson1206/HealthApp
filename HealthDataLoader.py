"""
HealthDataLoader.py
Anson Graumann
This module is responsible for loading and processing health data from an XML file.
It takes in the uploaded XML file, compresses it, and extracts relevant health metrics such as heart rate,
"""

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
    def __init__(self, uploaded_file, min_year = None):
        self.uploaded_file = uploaded_file
        self.compressed_data = compress_file(self.uploaded_file)
        self.merged_df = self.load_data(min_year = min_year)

    #Load data from the compressed XML file
    def load_data(self, min_year=None):
        try:
            if min_year:
             print(f"Filtering data for year >= {min_year}")
            with gzip.GzipFile(fileobj=BytesIO(self.compressed_data), mode="rb") as f:
                context = etree.iterparse(f, events=('end',))

                # Initialize lists to store data
                heart_rate_data = []
                workout_info = []
                calories_data = []
                flights_climbed_data = []
                distance_data = []

                # Debug counters
                tag_counts = {}

                #Looks for key records in the XML file
                for event, elem in context:
                    # Get tag name without namespace
                    full_tag = elem.tag
                    tag = full_tag.split('}')[-1].lower() if '}' in full_tag else full_tag.lower()

                    # Count tag occurrences for debugging
                    if tag not in tag_counts:
                        tag_counts[tag] = 0
                    tag_counts[tag] += 1

                    # Check for WorkoutStatistics specifically, case-insensitive
                    if tag.lower() == 'workoutstatistics':
                        if elem.get("type") == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                            distance_record = self.extract_distance_data(elem)
                            if distance_record:
                                distance_data.append(distance_record)

                    # Process other record types as before
                    record_type = elem.get("type")

                    #Process heart rate data
                    if record_type == "HKQuantityTypeIdentifierHeartRate":
                        hr_data = self.extract_heart_rate_data(elem)
                        if hr_data:
                            # Only add the record if it meets the year criteria
                            if min_year is None or hr_data["Date"].year >= min_year:
                                heart_rate_data.append(hr_data)
                    # Process workout data
                    elif tag == 'workout':
                        workout_data = self.extract_workout_and_distance_info(elem)
                        if workout_data:
                            # Filter workout entries by year
                            if min_year is None:
                                workout_info.extend(workout_data)
                            else:
                                # Only keep records from min_year onwards
                                filtered_workout_data = [record for record in workout_data
                                                         if record["Date"].year >= min_year]
                                workout_info.extend(filtered_workout_data)

                    # Process distance data
                    elif record_type == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                        distance_record = self.extract_distance_data(elem)
                        if distance_record:
                            if min_year is None or distance_record["Date"].year >= min_year:
                                distance_data.append(distance_record)

                    # Processes calories data
                    elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                        calories_record = self.extract_calories_data(elem)
                        if calories_record:
                            if min_year is None or calories_record["Date"].year >= min_year:
                                calories_data.append(calories_record)

                    # Processes flights climbed data
                    elif record_type == "HKQuantityTypeIdentifierFlightsClimbed":
                            flights_record = self.extract_flights_climbed(elem)
                            if flights_record:
                                if min_year is None or flights_record["Date"].year >= min_year:
                                    flights_climbed_data.append(flights_record)

                    # Free memory after processing
                    elem.clear()

                return self.merge_data(heart_rate_data, workout_info, calories_data, flights_climbed_data,
                                       distance_data)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Error parsing XML file: {e}")


    #Merge all lists into a single DataFrame
    def merge_data(self, heart_rate_data, workout_info, calories_data, flights_climbed_data, distance_data=None):

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

        # Filter distance data to include only those records that are associated with workouts
        if not distance_df.empty and not workout_df.empty:
            distance_df = distance_df[
                distance_df['Date'].isin(workout_df['Date']) & distance_df['Time'].isin(workout_df['Time'])]

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

        # Create base dataframe with ALL timestamps
        all_dates_times = pd.DataFrame()
        for df in [heart_rate_df, workout_df, distance_df, calories_df, flights_df]:
            if not df.empty and 'Date' in df.columns and 'Time' in df.columns:
                df_dates = df[['Date', 'Time']].copy()
                all_dates_times = pd.concat([all_dates_times, df_dates])

        # Removes the duplicates
        all_dates_times = all_dates_times.drop_duplicates(subset=['Date', 'Time'])
        merged_df = all_dates_times.copy()

        # heart rate data as the base
        if not heart_rate_df.empty:
            merged_df = pd.merge(merged_df, heart_rate_df, on=['Date', 'Time'], how='left')
            merged_df = merged_df.drop_duplicates(subset=['Date', 'Time'])
        else:
            # Merges the workout data with the heart rate data
            if not workout_df.empty:
                merged_df = workout_df[['Date', 'Time']].copy()
                merged_df['HeartRate'] = np.nan
            else:
                # Goes through the other data amd merges them based on the date and time, drops empty data
                for df, col in [(distance_df, 'Distance'), (flights_df, 'Flights'), (calories_df, 'Calories')]:
                    if not df.empty:
                        merged_df = df[['Date', 'Time']].copy()
                        merged_df['HeartRate'] = np.nan
                        break
                else:
                    return pd.DataFrame(
                        columns=['Date', 'Time', 'HeartRate', 'Distance', 'WorkoutType', 'Flights', 'Calories'])

        # Add workout data
        if not workout_df.empty:
            #Creates a temporary DataFrame to merge with the main DataFrame
            workout_temp = workout_df.groupby(['Date', 'Time']).agg({
                'Distance': 'sum',
                'Workout': 'first',
                'WorkoutType': 'first'
            }).reset_index()
            merged_df = pd.merge(merged_df, workout_temp, on=['Date', 'Time'], how='left')
        else:
            merged_df['Distance'] = np.nan
            merged_df['WorkoutType'] = None

        # Add standalone distance data where available
        # Creates a temporary DataFrame to merge with the main DataFrame
        if not distance_df.empty:
            distance_temp = distance_df.copy()
            distance_temp = distance_temp.rename(columns={'Distance': 'Distance_standalone'})
            merged_df = pd.merge(merged_df, distance_temp, on=['Date', 'Time'], how='left')
            # Adds  standalone distance data to the main DataFrame
            if 'Distance' in merged_df.columns:
                mask = merged_df['Distance'].isna() & merged_df['Distance_standalone'].notna()
                merged_df.loc[mask, 'Distance'] = merged_df.loc[mask, 'Distance_standalone']
                mask = merged_df['Distance'].notna() & merged_df['Distance_standalone'].notna()
                merged_df.loc[mask, 'Distance'] = merged_df.loc[mask, ['Distance', 'Distance_standalone']].max(axis=1)
            else:
                merged_df['Distance'] = merged_df['Distance_standalone']
            if 'Distance_standalone' in merged_df.columns:
                merged_df = merged_df.drop('Distance_standalone', axis=1)

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

        return merged_df

    # Extracts heart rate data from an element
    @staticmethod
    def extract_heart_rate_data(elem):
        try:
            creation_date = elem.get("creationDate")
            value = elem.get("value")
            # Checks if the creation date and value are present
            if creation_date and value and value.isdigit():
                creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S %z")
               #Returns a dictionary with the date, time, and heart rate
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
    def extract_workout_and_distance_info(elem):
        data = []
        try:
            # Process the workout element directly
            start_date_str = elem.get("startDate")
            end_date_str = elem.get("endDate")
            workout_type = elem.get("workoutActivityType")

            # Check if start and end dates are present
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S %z")
                duration = (end_date - start_date).total_seconds()

                # Initialize distance and units
                distance = 0.0
                unit = elem.get('unit', 'mi')

                # Check for totalDistance
                total_distance = elem.get('totalDistance')
                if total_distance:
                    try:
                        distance = float(total_distance)
                    except (ValueError, TypeError):
                        pass

                # Looks for distance in WorkoutStatistics
                for value in elem.findall('.//WorkoutStatistics'):
                    stat_type = value.get('type')
                    #Gets the distance value
                    if stat_type and ('Distance' in stat_type or 'distance' in stat_type):
                        try:
                            sum_value = value.get('sum')
                            if sum_value:
                                distance = float(sum_value)
                                break
                        except (TypeError, ValueError):
                            pass

                # Looks for distance in WorkoutRoute
                for route in elem.findall('.//WorkoutRoute'):
                    for entry in route.findall('.//MetadataEntry'):
                        if entry.get('key') == 'HKMetadataKeyWorkoutDistance':
                            try:
                                value = entry.get('value')
                                if value:
                                    distance = float(value)
                                    break
                            except (TypeError, ValueError):
                                pass


                # Creates a record for the duration of the workout
                minute_interval = 60
                for i in range(0, int(duration)):
                    # Calculate the distance for each minute
                    minute_distance = distance / (duration / minute_interval) if duration > 0 else 0
                    #Appends the data to the list
                    data.append({
                        "Date": (start_date + timedelta(seconds=i)).date(),
                        "Time": (start_date + timedelta(seconds=i)).time().strftime("%I:%M:%S %p"),
                        "Distance": minute_distance,
                        "Unit": unit,
                        "Workout": workout_type
                    })

        except Exception as e:
            print(f"Error parsing workout data: {e}")
        return data



    #Extract standalone distance data from an element
    @staticmethod
    def extract_distance_data(elem):
        try:
            # Get element tag without namespace
            tag_name = elem.tag.split('}')[-1].lower() if '}' in elem.tag else elem.tag.lower()

            # Handles standalone distance data
            if tag_name == 'workoutstatistics' or elem.get("type") == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                start_date = elem.get("startDate") or elem.get("creationDate")
                value = elem.get("sum") or elem.get("value")
                unit = elem.get("unit", "mi")
                #Checks if the start date and value are present
                if start_date and value:
                    #Gets the distance value and returns the values
                    try:
                        distance = float(value)
                        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S %z")
                        return {
                            "Date": start_date.date(),
                            "Time": start_date.time().strftime("%I:%M:%S %p"),
                            "Distance": distance,
                            "Unit": unit
                        }
                    except (TypeError, ValueError) as e:
                        print(f"Error converting distance value: {e}")
                else:
                    print(f"Missing required fields - Date: {start_date}, Value: {value}")
        except Exception as e:
            print(f"Error parsing distance data: {e}")
        return None

    # Extract calories data from an element
    @staticmethod
    def extract_calories_data(elem):
       #Gets the date and values from the element to return
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
        #Gets the creation date and value from the element to return
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