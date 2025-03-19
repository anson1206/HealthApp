import openai
import streamlit as st
from datetime import datetime
import pandas as pd

class AIBot:
    def __init__(self, api_key, health_data):
        self.api_key = api_key
        self.health_data = self.merge_health_data(health_data)
        self.chat_history = []
        openai.api_key = self.api_key

    def merge_health_data(self, health_data):
        # Merges the health data with the water and calory intake data
        if 'water_intake_df' in st.session_state:
            health_data = pd.merge(health_data, st.session_state.water_intake_df, on='Date', how='left', sort = False)
        if 'calory_intake_df' in st.session_state:
            health_data = pd.merge(health_data, st.session_state.calory_intake_df, on='Date', how='left', sort=False)
        return health_data

    #Handles both general AI responses and health-related queries
    def get_response(self, prompt):
        date = self.extract_date_from_prompt(prompt)
        prompt_lower = prompt.lower()

        # Health Data Responses
        if "workouts" in prompt_lower:
            return self.get_workout_info(date)
        elif "heart rate range" in prompt_lower or "heart rate" in prompt_lower or "heartrate" in prompt_lower:
            return self.get_heart_rate_range(date)
        elif "calories" in prompt_lower:
            if "burned" in prompt_lower or "burn" in prompt_lower:
                return self.burned_calories(date)
            if "range" in prompt_lower:
                return self.cal_range(date)
            return self.recommend_calories(date)
        elif "stairs" in prompt_lower or "flights climbed" in prompt_lower:
            return self.get_flights_climbed(date)
        elif "hydration" in prompt_lower or "water" in prompt_lower:
            return self.recommend_hydration(date)
        # Goes back to the general response if there's no health data
        return self.get_general_ai_response(prompt)

   #Uses OpenAI to generate a response to the user's prompt
    def get_general_ai_response(self, prompt):
        if "openai_model" not in st.session_state:
            st.session_state["openai_model"] = "gpt-4"
        if "messages" not in st.session_state:
            st.session_state["messages"] = []
        st.session_state["messages"].append({"role": "user", "content": prompt})
        try:
            response = openai.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=st.session_state["messages"]
            )
            # Extract the response content correctly
            response_content = response.choices[0].message.content
            # Check if the response is empty
            if not response_content.strip():
                return "Sorry, I couldn't generate a response."
            # Append the response to the session history
            st.session_state["messages"].append({"role": "assistant", "content": response_content})
            return response_content
        except Exception as e:
            return f"Error with AI response: {str(e)}"

    #Retrieves workout types for a given date
    def get_workout_info(self, date):
        if self.health_data is None or "Workout" not in self.health_data.columns:
            return "No workout data available."

        if date:
            # Ensure we're working with datetime objects
            if not pd.api.types.is_datetime64_dtype(self.health_data['Date']):
                self.health_data['Date'] = pd.to_datetime(self.health_data['Date'])

            # Filter data for the specific date
            filtered_data = self.health_data[self.health_data["Date"].dt.date == date]

            workouts = filtered_data["WorkoutType"].dropna().unique().tolist()
            if workouts:
                return f"Workouts on {date}: {', '.join(workouts)}"
            return f"No workouts found for {date}."
        return "Please specify a date to check workout information."

    #Calculates the heart rate range for a given date
    def get_heart_rate_range(self, date):
        if self.health_data is None or "HeartRate" not in self.health_data.columns:
            return "No heart rate data available."

        if date:
            if not pd.api.types.is_datetime64_dtype(self.health_data['Date']):
                self.health_data['Date'] = pd.to_datetime(self.health_data['Date'])

            # Filter data for the specific date
            filtered_data = self.health_data[self.health_data["Date"].dt.date == date]

            # Filter out null/missing/zero heart rate values
            valid_hr_data = filtered_data[filtered_data["HeartRate"].notna() & (filtered_data["HeartRate"] > 0)]

            if not valid_hr_data.empty:
                min_hr = int(valid_hr_data["HeartRate"].min())
                max_hr = int(valid_hr_data["HeartRate"].max())
                return f"Heart rate range: {min_hr}-{max_hr} bpm"
            else:
                return "No valid heart rate data found for this date."
        else:
            return "No date specified for heart rate data."

    #Calculates the total calories burned for a given date
    def burned_calories(self, date):
        if self.health_data is None or "Calories" not in self.health_data.columns:
            return "No calorie data available."
        if date is None:
            return "Please specify a valid date to check calorie data."
        try:
            # Ensure we're working with datetime objects for proper comparison
            if not pd.api.types.is_datetime64_dtype(self.health_data['Date']):
                self.health_data['Date'] = pd.to_datetime(self.health_data['Date'])

            # Filter data for the specific date using date component comparison
            filtered_data = self.health_data[self.health_data["Date"].dt.date == date]

            if not filtered_data.empty:
                # Sum the calories for the date and format with 1 decimal place
                total_cal_burned = filtered_data["Calories"].sum()
                return f"You burned {total_cal_burned:.1f} calories on {date}."
            else:
                return f"No calorie data available for {date}."
        except Exception as e:
            return f"Error processing calorie data: {str(e)}"

    #Calculates the range of calories burned for a given date
    def cal_range(self, date):
        if self.health_data is None or "Calories" not in self.health_data.columns:
            return "No calorie data available."
        if date:
            # Ensure we're working with datetime objects
            if not pd.api.types.is_datetime64_dtype(self.health_data['Date']):
                self.health_data['Date'] = pd.to_datetime(self.health_data['Date'])

            # Filter data for the specific date using date component
            filtered_data = self.health_data[self.health_data["Date"].dt.date == date]

            if not filtered_data.empty:
                min_cal = filtered_data["Calories"].min()
                max_cal = filtered_data["Calories"].max()
                return f"Calories burned range: {min_cal:.1f}-{max_cal:.1f} kcal"
            return f"No calorie data available for {date}."
        return "Please specify a date to check calorie range."

    #Estimates daily calorie needs based on heart rate, calorie intake, and calories burned
    def recommend_calories(self, date):
        if self.health_data is None or "HeartRate" not in self.health_data.columns or "CaloriesIntake" not in self.health_data.columns or "CaloriesBurned" not in self.health_data.columns:
            return "Not enough data available."
        if date:
            filtered_data = self.health_data[self.health_data["Date"] == date]
        else:
            filtered_data = self.health_data
        if not filtered_data.empty:
            avg_hr = filtered_data["HeartRate"].mean()
            total_calories_intake = filtered_data["CaloriesIntake"].sum()
            total_calories_burned = filtered_data["Calories"].sum()
            if avg_hr < 60:
                calorie_recommendation = "1800-2200 kcal"
            elif avg_hr < 100:
                calorie_recommendation = "2200-2600 kcal"
            else:
                calorie_recommendation = "2600-3000 kcal"
            net_calories = total_calories_intake - total_calories_burned
            return f"Based on your heart rate, your calorie intake should be around {calorie_recommendation}. You have consumed {total_calories_intake} kcal and burned {total_calories_burned} kcal today, resulting in a net calorie intake of {net_calories} kcal."
        return "Not enough data available."

    #Returns the number of flights climbed for a given date
    def get_flights_climbed(self, date):
        if self.health_data is None or "Flights" not in self.health_data.columns:
            return "No stair climb data available."
        if date:
            if not pd.api.types.is_datetime64_dtype(self.health_data['Date']):
                self.health_data['Date'] = pd.to_datetime(self.health_data['Date'])
            filtered_data = self.health_data[self.health_data["Date"] == date]

            if not filtered_data.empty:
                total_flights = filtered_data["Flights"].sum()
                return f"You climbed {total_flights} flights of stairs."
        return "No flight climb data available for this date."

    #Providea a hydration recommendation based on the user's water intake
    def recommend_hydration(self, date):
        if self.health_data is None or "Water Intake (gallons)" not in self.health_data.columns:
            return "No water intake data available."
        if date:
            filtered_data = self.health_data[self.health_data["Date"] == date]
        else:
            filtered_data = self.health_data
        if not filtered_data.empty:
            avg_water = filtered_data["Water Intake (gallons)"].mean()
            if avg_water < 0.5:
                return "You should drink more water. Aim for at least 0.5 gallons per day."
            elif avg_water < 1:
                return "Good job! Try to drink a bit more to reach 1 gallon per day."
            else:
                return "Great! You are well-hydrated."
        return "No water intake data available to provide hydration tips."

    # Extracts a date from the user’s input if available
    def extract_date_from_prompt(self, prompt):
        for word in prompt.split():
            try:
                parsed_date = datetime.strptime(word, "%Y/%m/%d").date()
                return parsed_date
            except ValueError:
                continue
        return None

    # Display the chat interface

    def display_chat(self):
        st.subheader("AI Health & General Chatbot")

        # Display the chat history
        for message in self.chat_history:
            st.chat_message(message["role"]).write(message["content"])

        # User input field
        user_input = st.chat_input("Ask me anything (health or general)...")

        if user_input:
            # Append user input to the chat history
            self.chat_history.append({"role": "user", "content": user_input})

            # Get the response from the bot (general or health-related)
            response = self.get_response(user_input)

            # Append bot response to the chat history
            self.chat_history.append({"role": "assistant", "content": response})

            # Display user input and bot response
            st.chat_message("user").write(user_input)
            st.chat_message("assistant").write(response)