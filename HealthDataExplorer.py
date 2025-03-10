import gzip
from io import BytesIO

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from lxml import etree
import streamlit as st
import plotly.express as px
from UserInputHandler import UserInputHandler



class HealthDataExplorer:
    def __init__(self, merged_df):
        self.merged_df = merged_df

    def display_data(self):
        # Filter out NaT values from the Date column
        valid_dates = self.merged_df['Date'].dropna()

        if valid_dates.empty:
            st.error("No valid dates available in the data.")
            return

        selected_data = st.sidebar.radio("Select Data to Display",
                                         ["Heart Rate", "Distance", "Workouts", "Flights Climbed", "Calories", "Water Intake",
                                          "Convert to CSV", "Data Frame", "User Input"])
        selected_date = st.sidebar.date_input("Select Date", min_value=min(valid_dates), max_value=max(valid_dates),
                                              value=min(valid_dates))

        if 'last_selected_date' not in st.session_state or st.session_state.last_selected_date != selected_date:
            st.session_state.last_selected_date = selected_date
            st.session_state.water_intake_oz = 0
            st.session_state.calory_intake = 0
            st.session_state.water_input = 0
            st.session_state.calory_input = 0

        filtered_df = self.merged_df[self.merged_df['Date'] == selected_date]

        if selected_data == "Heart Rate":
            st.write('Here is your heart rate and calories burned over time')
            st.line_chart(filtered_df.set_index('Time')[['HeartRate']])
            st.dataframe(filtered_df[['Time', 'HeartRate', 'WorkoutType', 'Calories']])
            
        elif selected_data == "Workouts":
            # Display workout information
            st.write("## Workout Information")
            
            # Show what's in the data for debugging
            with st.expander("Data Inspection"):
                st.write("### Data Overview")
                st.write(f"Total rows in dataset: {len(self.merged_df)}")
                #st.write(f"Columns in dataset: {', '.join(self.merged_df.columns)}")
                
                if 'WorkoutType' in self.merged_df.columns:
                    non_null_workouts = self.merged_df['WorkoutType'].notna()
                    workout_count = non_null_workouts.sum()
                    st.write(f"Total rows with WorkoutType data: {workout_count}")
                    
                    if workout_count > 0:
                        workout_types = self.merged_df.loc[non_null_workouts, 'WorkoutType'].unique()
                        st.write(f"Unique workout types: {', '.join(str(t) for t in workout_types)}")
                        
                        # Show a sample of workout data
                        st.write("### Sample Workout Data")
                        sample_workouts = self.merged_df.loc[non_null_workouts].sample(min(5, workout_count))
                        st.dataframe(sample_workouts[['Date', 'Time', 'WorkoutType', 'Calories']])
                else:
                    st.error("WorkoutType column not found in the data!")
            
            # check if the WorkoutType column exists
            if 'WorkoutType' in self.merged_df.columns:
                # Get all rows with non-null WorkoutType
                workout_data = self.merged_df[self.merged_df['WorkoutType'].notna()]
                
                # Check if there's any workout data after filtering
                if workout_data.empty:
                    st.warning("No workout data found. Try uploading a different health data file with workout information.")
                    if st.button("Show Raw Data to Investigate"):
                        st.write("First 200 rows of raw data:")
                        st.dataframe(self.merged_df.head(200))
                    return
                
                # Show workout summary by type
                st.write("### Workout Summary by Type")
                # Count unique workout instances by date and type
                workout_by_type = workout_data.drop_duplicates(subset=['Date', 'Time', 'WorkoutType']).groupby('WorkoutType').size().reset_index(name='Count')
                st.bar_chart(workout_by_type.set_index('WorkoutType')['Count'])
                

                # Show all workouts
                st.write("### All Workouts")
                all_workouts = workout_data.drop_duplicates(subset=['Date', 'Time', 'WorkoutType']).sort_values('Date', ascending=False)
                st.dataframe(all_workouts[['Date', 'Time', 'WorkoutType',  'Calories']])
                
                # Advanced Analytics
                with st.expander("Workout Analytics"):
                    try:
                        # Total workout stats
                        total_distance = workout_data['Distance'].sum()
                        avg_distance = workout_data.groupby(['Date', 'Time', 'WorkoutType'])['Distance'].max().mean()
                        
                        st.write(f"**Total Distance:** {total_distance:.2f} miles")
                        st.write(f"**Average Workout Distance:** {avg_distance:.2f} miles")
                        
                        # Workouts by day of week
                        if not workout_data.empty:
                            workout_data['DayOfWeek'] = pd.to_datetime(workout_data['Date']).dt.day_name()
                            dow_counts = workout_data.drop_duplicates(subset=['Date', 'Time', 'WorkoutType']).groupby('DayOfWeek').size()
                            
                            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                            dow_counts = dow_counts.reindex(days_order).fillna(0)
                            
                            st.write("### Workouts by Day of Week")
                            st.bar_chart(dow_counts)
                    except Exception as e:
                        st.write(f"Error generating analytics: {e}")
            else:
                st.error("Required data columns are missing. The WorkoutType column could not be found in your data.")
                st.write("Please check your data file format and try again.")
                
                # Show available columns as a fallback
                st.write("Available columns in your data:")
                st.write(", ".join(self.merged_df.columns))
                
        elif selected_data == "Distance":
            # Check if Distance column exists and has data
            if 'Distance' not in self.merged_df.columns:
                st.error("Distance data not found in the dataset.")
                return

            # First, let's check if we have any valid distance data
            valid_distance = self.merged_df['Distance'].replace([0, None, np.nan], np.nan).dropna()

            if valid_distance.empty:
                st.warning(
                    "No distance data found in your health records. If you believe this is an error, check your XML file format.")
                return

            # Show overall stats
            st.write(f"## Distance Statistics")
            total_distance = valid_distance.sum()
            st.write(f"**Total distance recorded:** {total_distance:.2f} miles")
            
            # Create a date selector for distance data
            date_option = st.radio('Select time range:', ['Day', 'Week', 'Month', 'All Time'])
            
            # Filter distance data based on selected time range
            if date_option == 'Day':
                distance_df = self.merged_df[self.merged_df['Date'] == selected_date]
            elif date_option == 'Week':
                start_date = selected_date - pd.Timedelta(days=7)
                distance_df = self.merged_df[(self.merged_df['Date'] >= start_date) & (self.merged_df['Date'] <= selected_date)]
            elif date_option == 'Month':
                start_date = selected_date - pd.Timedelta(days=30)
                distance_df = self.merged_df[(self.merged_df['Date'] >= start_date) & (self.merged_df['Date'] <= selected_date)]
            else:  #
                distance_df = self.merged_df.copy()

            # filtered dataframe for distance by applying multiple filters
            workout_distance_df = distance_df[
                distance_df['WorkoutType'].isin(['Running', 'Walking', 'RunningWalking', 'Baseball'])]
            
            #If no data, try without filtering by workout type
            if workout_distance_df.empty or workout_distance_df['Distance'].sum() == 0:
                workout_distance_df = distance_df[distance_df['Distance'] > 0]
                
            #Group by date to get max distance per day
            if not workout_distance_df.empty and workout_distance_df['Distance'].sum() > 0:
                distance_per_day = workout_distance_df.groupby('Date')['Distance'].max().reset_index()
                
                # Show the daily distance chart
                st.write('## Daily Distance Over Time')
                st.bar_chart(distance_per_day.set_index('Date')['Distance'])
                
                # Show data table with distance information
                st.write('## Distance Data Details')
                workout_distance = workout_distance_df[workout_distance_df['Distance'] > 0].drop_duplicates(
                    subset=['Date', 'WorkoutType'])
                st.dataframe(
                    workout_distance[['Date', 'Time', 'WorkoutType', 'Distance']].sort_values(by='Date', ascending=False))
                
                # Show aggregate stats
                st.write("## Distance by Workout Type")
                type_distance = workout_distance.groupby('WorkoutType')['Distance'].sum().reset_index()
                st.bar_chart(type_distance.set_index('WorkoutType')['Distance'])
            else:
                st.warning("No distance data available to display in chart format.")
                
        elif selected_data == "Flights Climbed":
            st.write('You Climbed ', self.merged_df['Flights'].sum(), ' flights of stairs')
            st.bar_chart(self.merged_df.groupby('Date')['Flights'].sum().reset_index().set_index('Date')['Flights'])
            
        elif selected_data == "Calories":
            st.write('Here is the calories burned over time')
            st.bar_chart(self.merged_df.groupby('Date')['Calories'].sum().reset_index().set_index('Date')['Calories'])
            
        elif selected_data == "Data Frame":
            st.write('Here is the data frame where you can look through the data to see information')
            st.dataframe(filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'WorkoutType', 'Flights', 'Calories']])
            
        elif selected_data == "User Input":
            water_intake, calory_intake = st.columns(2)
            with water_intake:
                st.write('Select the date first before entering the amount of water you drank')
                UserInputHandler().add_water_intake(selected_date)
            with calory_intake:
                st.write('Select the date first before entering the amount of calories you ate')
                UserInputHandler().add_calory_intake(selected_date)
                
        elif selected_data == "Convert to CSV":
            csv = self.merged_df.to_csv(index=False)
            st.sidebar.download_button(label="Download CSV", data=csv, file_name='health_data.csv', mime='text/csv')