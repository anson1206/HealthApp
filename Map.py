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
        #Calculate total flat distance including all tracks and segments
        total_distance = 0.0

        # Process all tracks and segments
        for track in self.gpx.tracks:
            for segment in track.segments:
                points = segment.points
                for i in range(1, len(points)):
                    prev = (points[i - 1].latitude, points[i - 1].longitude)
                    current = (points[i].latitude, points[i].longitude)

                    # Calculate flat distance between consecutive points
                    point_distance = geodesic(prev, current).miles
                    total_distance += point_distance

        return total_distance


    def create_map(self):
        if not self.coordinates:
            self.get_coordinates()
        m = folium.Map(location=[self.coordinates[0][0], self.coordinates[0][1]], zoom_start=15)
        folium.PolyLine(self.coordinates, color="red", weight=2.5, opacity=1).add_to(m)
        return m

    def display_map(self):
       # st.write(f"Total distance: {self.get_distance()} miles")
        st_folium(self.create_map(), width=700, height=500)

