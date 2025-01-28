import gpxpy
from geopy.distance import geodesic
import folium
import streamlit as st
from streamlit_folium import st_folium

class GPXMap:

    def __init__(self, uploaded_file):
        self.gpx = gpxpy.parse(uploaded_file)
        self.tracks = self.gpx.tracks[0]
        self.segments = self.tracks.segments[0]
        self.coordinates = []


    def get_coordinates(self):
        for point in self.segments.points:
            self.coordinates.append([point.latitude, point.longitude])
        return self.coordinates

    def get_distance(self):
        if not self.coordinates:
           self.get_coordinates()
        total_distance = 0.0
        for i in range(1, len(self.coordinates)):
            total_distance += geodesic(self.coordinates[i - 1], self.coordinates[i]).miles
        return total_distance

    def create_map(self):
        if not self.coordinates:
            self.get_coordinates()
        m = folium.Map(location=[self.coordinates[0][0], self.coordinates[0][1]], zoom_start=15)
        folium.PolyLine(self.coordinates, color="red", weight=2.5, opacity=1).add_to(m)
        return m

    def display_map(self):
        st.write(f"Total distance: {self.get_distance()} miles")
        st_folium(self.create_map(), width=700, height=500)

