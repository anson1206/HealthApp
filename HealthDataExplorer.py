"""
HealthDataExplorer.py
Anson Graumann
This module is responsible for displaying the health data in a user-friendly way.
It includes filtering options, data visualization, and an overview of the data.
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from UserInputHandler import UserInputHandler


class HealthDataExplorer:
    def __init__(self, merged_df):
        self.merged_df = merged_df

    def display_data(self):
        if not pd.api.types.is_datetime64_dtype(self.merged_df['Date']):
            self.merged_df['Date'] = pd.to_datetime(self.merged_df['Date'], errors='coerce')

        # Filter out NaT values from the Date column
        valid_dates = self.merged_df['Date'].dropna()

        if valid_dates.empty:
            st.error("No valid dates available in the data.")
            return

        st.sidebar.subheader("Data Filtering")

        # Uses the already filtered dataframe directly
        date_filtered_df = self.merged_df

        selected_data = st.sidebar.radio("Select Data to Display",
                                         ["Heart Rate", "Workouts & Distance", "Flights Climbed",
                                          "Calories Burned",
                                          "Water Intake/ Calories Intake" ])
        overview_button = st.sidebar.button("Overview Page")


        if selected_data == "Heart Rate":

            view_option = st.radio("Select view", ['Daily', 'Weekly'])

            # Filter to only include rows with actual heart rate data
            heart_rate_df = self.merged_df.dropna(subset=['HeartRate']).copy()

            if heart_rate_df.empty:
                st.warning("No heart rate data available")
            else:
                # Create DateTime column for proper time-based plotting
                heart_rate_df['DateTime'] = pd.to_datetime(
                    heart_rate_df['Date'].astype(str) + ' ' + heart_rate_df['Time'], errors='coerce')

                # Drop rows where DateTime is NaT
                heart_rate_df = heart_rate_df.dropna(subset=['DateTime'])

                # Sort by DateTime
                heart_rate_df = heart_rate_df.sort_values('DateTime')


                if view_option == 'Daily':
                    selected_date = st.date_input("Select Date",
                                                          min_value=date_filtered_df['Date'].min(),
                                                          max_value=date_filtered_df['Date'].max(),
                                                          value=date_filtered_df['Date'].min(),
                                                          key='heart_rate_date')
                    # Get data for selected date
                    daily_data = heart_rate_df[heart_rate_df['Date'] == pd.to_datetime(selected_date)]

                    if daily_data.empty:
                        st.warning(f"No heart rate data available for {selected_date}")
                    else:
                        fig = px.line(daily_data, x='DateTime', y='HeartRate',
                                     title=f'Heart Rate on {selected_date}')

                        #  12-hour time format
                        fig.update_xaxes(
                            tickformat="%I:%M %p",
                            title="Time"
                        )

                        fig.update_layout(xaxis_title="Time of Day")
                        fig.update_xaxes(rangeslider_visible=True)
                        fig.update_traces(mode = 'lines+markers', connectgaps=False, marker=dict(size=5))
                        st.plotly_chart(fig)


                elif view_option == 'Weekly':
                    selected_date = st.date_input("Select Date",
                                                          min_value=date_filtered_df['Date'].min(),
                                                          max_value=date_filtered_df['Date'].max(),
                                                          value=date_filtered_df['Date'].min(),
                                                          key='heart_rate_date')
                    start_of_week = pd.to_datetime(selected_date) - pd.Timedelta(days=pd.to_datetime(selected_date).weekday())
                    end_of_week = start_of_week + pd.Timedelta(days=6)

                    # Get data for the entire week
                    week_df = heart_rate_df[(heart_rate_df['Date'] >= start_of_week) & (heart_rate_df['Date'] <= end_of_week)]

                    if week_df.empty:
                        st.warning(f"No heart rate data available for week of {start_of_week.date()} to {end_of_week.date()}")

                    else:
                        # Add day name for color-coding
                        week_df['Day'] = week_df['Date'].dt.strftime('%A')
                        # Sort by date and time
                        week_df = week_df.sort_values(['Date', 'Time'])
                        # Plot as separate traces for each day to avoid connecting points between days
                        fig = px.scatter(week_df,x='DateTime',y='HeartRate',color='Day',
                            title=f'Heart Rate Data from {start_of_week.date()} to {end_of_week.date()}',
                            labels={
                                'HeartRate': 'Heart Rate (bpm)',
                                'DateTime': 'Date & Time',
                                'Day': 'Day of Week'
                            }
                        )

                        # Update to add connecting lines only within close time points
                        for i, day in enumerate(week_df['Day'].unique()):
                            day_data = week_df[week_df['Day'] == day]
                            fig.add_scatter(
                                x=day_data['DateTime'],
                                y=day_data['HeartRate'],
                                mode='lines',
                                line=dict(width=1),
                                showlegend=False,
                                line_color=fig.data[i].marker.color,
                                legendgroup= day,
                                legendgrouptitle_text=day
                            )

                        fig.update_traces(mode='markers', marker=dict(size=6))
                        fig.update_layout(hovermode='closest')
                        fig.update_xaxes(rangeslider_visible=True)
                        fig.update_layout(xaxis={'categoryorder': 'total descending'})
                        fig.update_xaxes(
                            tickformat="%I:%M %p",
                            title="Time"
                        )
                        st.plotly_chart(fig)


        elif selected_data == "Workouts & Distance":
            selected_date = st.date_input("Select Date",
                                                  min_value=date_filtered_df['Date'].min(),
                                                  max_value=date_filtered_df['Date'].max(),
                                                  value=date_filtered_df['Date'].min(),
                                                  key='workout_date')
            # tabs for different views
            view_type = st.tabs(["Workout Details", "Statistics"])
            with view_type[0]:

                if 'WorkoutType' in self.merged_df.columns:
                    # Get non-null workout records
                    workout_data = self.merged_df[self.merged_df['WorkoutType'].notna()].copy()
                    if not workout_data.empty:
                        # Group by date and workout type to get unique workouts
                        unique_workouts = workout_data.groupby(['Date', 'WorkoutType'])['Distance'].max().reset_index()
                        if not unique_workouts.empty:
                            # Display workout summary
                            fig = px.bar(unique_workouts,
                                         x='Date',
                                         y='Distance',
                                         color='WorkoutType',
                                         title='Workouts by Date',
                                         labels={'Date': 'Date', 'Distance': 'Distance (miles)', 'WorkoutType': 'Type'})

                            fig.update_layout(xaxis={'categoryorder': 'total descending'})
                            fig.update_xaxes(rangeslider_visible=True)
                            st.plotly_chart(fig)
                            # Show workouts for selected date
                            selected_date_dt = pd.to_datetime(selected_date)

                            if not pd.api.types.is_datetime64_dtype(unique_workouts['Date']):
                                unique_workouts['Date'] = pd.to_datetime(unique_workouts['Date'])
                            date_workouts = unique_workouts[unique_workouts['Date'].dt.date == selected_date_dt.date()]

                            if not date_workouts.empty:
                                st.subheader(f"Workouts on {selected_date}")
                                for _, workout in date_workouts.iterrows():
                                    with st.expander(f"{workout['WorkoutType']} - {workout['Distance']:.2f} miles"):
                                        # Get all entries for this workout to show details
                                        workout_details = workout_data[(workout_data['Date'] == workout['Date']) &
                                                                       (workout_data['WorkoutType'] == workout[
                                                                           'WorkoutType'])]

                                        if 'Calories' in workout_details.columns:
                                            calories = workout_details['Calories'].sum()
                                            st.write(f"**Total Calories:** {calories:.1f}")

                                        if 'HeartRate' in workout_details.columns and not workout_details[
                                            'HeartRate'].isna().all():
                                            st.write(
                                                f"**Average Heart Rate:** {workout_details['HeartRate'].mean():.1f} bpm")
                                            st.write(
                                                f"**Max Heart Rate:** {workout_details['HeartRate'].max():.1f} bpm")

                            else:
                                st.info(f"No workouts found for {selected_date}")
                        else:
                            st.warning("No workout data available to display")
                    else:
                        st.warning("No workout data found in your health records")
                else:
                    st.error("WorkoutType column not found in the data")

            with view_type[1]:
                # Distance statistics
                if 'Distance' in self.merged_df.columns:
                    # Show overall distance stats
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Maximum distance", f"{self.merged_df['Distance'].max():.2f} miles")
                    with col2:
                        st.metric("Total distance", f"{self.merged_df['Distance'].sum():.2f} miles")
                    # Top distance records
                    top_distances = self.merged_df[self.merged_df['Distance'] > 0].sort_values('Distance',
                                                                                               ascending=False).head(10)
                    if not top_distances.empty:
                        fig = px.bar(top_distances,x='Date',y='Distance',hover_data=['Time', 'WorkoutType'],
                                     title="Top Distance Records",color='Distance')
                        st.plotly_chart(fig)
                    else:
                        st.warning("No distance records found")
                else:
                    st.error("Distance column not found in the data")

        elif selected_data == "Flights Climbed":
            st.write('You Climbed ', self.merged_df['Flights'].sum(), ' Flights of Stairs')
            if not pd.api.types.is_datetime64_dtype(self.merged_df['Date']):
                self.merged_df['Date'] = pd.to_datetime(self.merged_df['Date'], errors='coerce')

            filter_by_date = self.merged_df.groupby('Date')['Flights'].sum().reset_index()
            fig = px.bar(filter_by_date, x='Date', y='Flights', title='Flights Climbed Over Time', labels={'Date': 'Date', 'Flights': 'Flights Climbed'})
            fig.update_layout(hovermode='closest')
            fig.update_traces(marker_color = 'red')
            fig.update_xaxes(rangeslider_visible=True)
            st.plotly_chart(fig)

        elif selected_data == "Calories Burned":
            st.write('Here is the calories burned over time')
            if not pd.api.types.is_datetime64_dtype(self.merged_df['Date']):
                self.merged_df['Date'] = pd.to_datetime(self.merged_df['Date'], errors='coerce')
            filter_by_date = self.merged_df.groupby('Date')['Calories'].sum().reset_index()

            fig = px.bar(filter_by_date, x='Date', y='Calories', title='Calories Burned Over Time', labels={'Date': 'Date', 'Calories': 'Calories Burned'})
            fig.update_layout(hovermode='closest')
            fig.update_traces(marker_color = 'orange')
            fig.update_xaxes(rangeslider_visible=True)

            st.plotly_chart(fig)
        elif selected_data == "Water Intake/ Calories Intake":
            st.write("Here you can input the amount of water you drank and the amount of calories you ate")
            st.write("Select the date first before entering the amount of water you drank or the amount of calories you ate")
            selected_date = st.date_input("Select Date",
                                                  min_value=date_filtered_df['Date'].min(),
                                                  max_value=date_filtered_df['Date'].max(),
                                                  value=date_filtered_df['Date'].min())

            if 'last_selected_date' not in st.session_state or st.session_state.last_selected_date != selected_date:
                st.session_state.last_selected_date = selected_date
                st.session_state.water_intake_oz = 0
                st.session_state.calory_intake = 0
                st.session_state.water_input = 0
                st.session_state.calory_input = 0
            water_intake, calory_intake = st.columns(2)
            with water_intake:
                UserInputHandler().add_water_intake(selected_date)
            with calory_intake:
                UserInputHandler().add_calory_intake(selected_date)

        # Show overview button
        if overview_button :
            st.session_state['show_overview'] = True

        if st.session_state.get('show_overview', False):

            df_view_option = st.radio("Select display mode",
                                      ["Summarized View", "Filtered View", "Raw Data"],
                                      horizontal=True)
            #Summarized View Option
            if df_view_option == "Summarized View":
                st.info(
                    "This view aggregates data by hour, showing statistics for heart rate, totals distance, "
                    "flights of stairs climbed, and calories burned. It provides a condensed overview of your health data.")

                # Group by hour to reduce rows
                date_filtered_df['Hour'] = pd.to_datetime(date_filtered_df['Time'], format="%I:%M:%S %p").dt.hour
                hourly_summary = date_filtered_df.groupby(['Date', 'Hour', 'WorkoutType']).agg({
                    'HeartRate': ['mean', 'min', 'max', 'count'],
                    'Distance': 'sum',
                    'Flights': 'sum',
                    'Calories': 'sum'
                }).reset_index()

                # Format column names
                hourly_summary.columns = [f"{a}_{b}" if b else a for a, b in hourly_summary.columns]
                hourly_summary['Time'] = hourly_summary['Hour'].apply(lambda x: f"{x:02d}:00")

                # Creates readable summary table
                st.dataframe(hourly_summary[[
                    'Date', 'Time', 'WorkoutType',
                    'HeartRate_mean', 'HeartRate_min', 'HeartRate_max',
                    'Distance_sum', 'Flights_sum', 'Calories_sum'
                ]].rename(columns={
                    'HeartRate_mean': 'Avg HR',
                    'HeartRate_min': 'Min HR',
                    'HeartRate_max': 'Max HR',
                    'Distance_sum': 'Distance',
                    'Flights_sum': 'Flights',
                    'Calories_sum': 'Calories'
                }))

            #Filtered View Option
            elif df_view_option == "Filtered View":
                st.info(
                    "This view allows you to filter the data by date or workout type, showing specific records that match your criteria.")

                filter_type = st.radio("Select filter type", ["Date", "Workout Type"])
                #Drops rows that dont have heart rate data
                date_filtered_df = date_filtered_df.dropna(subset=['HeartRate'])

                #Shows the workout types for the selected date
                if filter_type == "Workout Type":
                    workout_options = list(date_filtered_df['WorkoutType'].dropna().unique())
                    workout_filter = st.selectbox("Filter by workout type", workout_options)
                    if workout_filter :
                        date_filtered_df = date_filtered_df[date_filtered_df['WorkoutType'] == workout_filter]
                        st.dataframe(date_filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'WorkoutType', 'Flights', 'Calories']])
                #Shows the data for the selected date
                elif filter_type == "Date":
                    selected_date = st.date_input("Select Date for Overview",
                                                  min_value=date_filtered_df['Date'].min(),
                                                  max_value=date_filtered_df['Date'].max(),
                                                  value=date_filtered_df['Date'].min(),
                                                  key='overview_date')
                    date_filtered_df = date_filtered_df[date_filtered_df['Date'] == pd.to_datetime(selected_date)]
                    st.dataframe(date_filtered_df[['Date', 'Time', 'HeartRate', 'Distance', 'WorkoutType', 'Flights', 'Calories']])

            #Raw Data Option
            elif df_view_option == "Raw Data":
                st.info(
                    "This view shows all individual data points with heart rate measurements. "
                    "Use the slider to change the amount of records displayed per page.")

                # Filters out the rows that dont have heart rate data
                date_filtered_df_with_hr = date_filtered_df.dropna(subset=['HeartRate'])

                # Creates a slider to change the amount of records displayed per page
                page_size = st.slider("Rows per page", min_value=10, max_value=100, value=25)
                max_pages = max(1, len(date_filtered_df_with_hr) // page_size)
                page_number = st.number_input("Page", min_value=1, max_value=max_pages, value=1)

                start_idx = (page_number - 1) * page_size
                end_idx = start_idx + page_size

                #Creates a dataframe with the selected amount of records
                st.dataframe(date_filtered_df_with_hr.iloc[start_idx:end_idx][['Date', 'Time', 'HeartRate',
                                                                                   'Distance', 'WorkoutType', 'Flights',
                                                                                   'Calories']])
            if st.button("Close Overview"):
                st.session_state['show_overview'] = False
                st.rerun()

