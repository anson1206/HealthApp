from flask import Flask, render_template
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
app = Flask(__name__)

@app.route('/')
def display_data():


    # Read the XML file
    with open('export.xml', 'r') as file:
        xml_data = file.read()

    # Parse the XML using BeautifulSoup
    soup = BeautifulSoup(xml_data, 'xml')

    bpm = soup.find_all('InstantaneousBeatsPerMinute')
    for BPM in bpm:
        print(bpm.text)


    #return render_template('index.html', data=formatted_data)

if __name__ == '__main__':
    app.run(debug=True)
