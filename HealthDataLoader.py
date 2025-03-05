import pandas as pd
import numpy as np
from lxml import etree
from datetime import datetime, timedelta
import streamlit as st
import gzip
from io import BytesIO

def compress_file(uploaded_file):
    """Compress uploaded XML file in-memory."""
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

    def load_data(self):
        """Load compressed XML and process data in chunks."""
        try:
            with gzip.GzipFile(fileobj=BytesIO(self.compressed_data), mode="rb") as f:
                context = etree.iterparse(f, events=('end',))

                heart_rate_data = []
                workout_data = []
                calories_data = []
                flights_data = []

                for event, elem in context:
                    tag = elem.tag.lower()
                    record_type = elem.get("type")

                    if record_type == "HKQuantityTypeIdentifierHeartRate":
                        heart_rate_data.append(self.extract_heart_rate_data(elem))
                    elif tag == "workout":
                        workout_data.extend(self.extract_workout_info(elem))
                    elif record_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                        calories_data.append(self.extract_calories_data(elem))
                    elif record_type == "HKQuantityTypeIdentifierFlightsClimbed":
                        flights_data.append(self.extract_flights_climbed(elem))

                    elem.clear()  # Free memory after processing

                return self.merge_data(heart_rate_data, workout_data, calories_data, flights_data)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Error parsing XML file: {e}")

    def merge_data(self, heart_rate_data, workout_data, calories_data, flights_data):
        """Merge all datasets efficiently and optimize memory usage."""
        heart_rate_df = pd.DataFrame(heart_rate_data)
        workout_df = pd.DataFrame(workout_data)
        calories_df = pd.DataFrame(calories_data)
        flights_df = pd.DataFrame(flights_data)

        # Merge all dataframes
        merged_df = (
            heart_rate_df
            .merge(workout_df, on=["Date", "Time"], how="left")
            .merge(calories_df, on=["Date", "Time"], how="left")
            .merge(flights_df, on=["Date", "Time"], how="left")
        )

        # ✅ Convert 'Date' column to datetime.date to avoid mixed types
        merged_df['Date'] = pd.to_datetime(merged_df['Date'], errors='coerce').dt.date

        # ✅ Drop rows where 'Date' is NaT (conversion errors)
        merged_df = merged_df.dropna(subset=['Date'])

        return merged_df

    @staticmethod
    def extract_heart_rate_data(elem):
        """Extract heart rate data from an element."""
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
        return {}

    @staticmethod
    def extract_workout_info(elem):
        """Extract workout data from an element."""
        data = []
        try:
            start_date = elem.get("startDate")
            end_date = elem.get("endDate")
            workout_type = elem.get("workoutActivityType")

            if start_date and end_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S %z")
                end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S %z")
                duration = int((end_date - start_date).total_seconds())

                data.extend([
                    {
                        "Date": (start_date + timedelta(seconds=second)).date(),
                        "Time": (start_date + timedelta(seconds=second)).time().strftime("%I:%M:%S %p"),
                        "WorkoutType": workout_type
                    }
                    for second in range(duration)
                ])
        except Exception as e:
            print(f"Error parsing workout data: {e}")
        return data

    @staticmethod
    def extract_calories_data(elem):
        """Extract calories data from an element."""
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
        return {}

    @staticmethod
    def extract_flights_climbed(elem):
        """Extract flights climbed data from an element."""
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
        return {}
