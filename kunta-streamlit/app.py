import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import re
import requests
import os, json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope and credentials for accessing Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Read the Google service account credentials from Streamlit secrets
service_account_info = st.secrets["google_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)

# Authenticate and create the gspread client
client = gspread.authorize(credentials)

# Open the Google Sheet
sheet_url = "https://docs.google.com/spreadsheets/d/13upFaGkAkZsu8Kfhjlk8CY5nEGtDkvop8nojoQk9hFQ/edit?usp=sharing"
sheet = client.open_by_url(sheet_url).sheet1

# Read data from the Google Sheet into a DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

def clean_and_convert_lat_long(coord):
    # Remove all non-numeric characters except the decimal point
    cleaned = re.sub(r'[^\d\.]', '', str(coord))
    return float(cleaned)

df["Latitude"] = df["Latitude"].apply(clean_and_convert_lat_long)
df["Longitude"] = df["Longitude"].apply(clean_and_convert_lat_long)
df['vierailtu_teksti'] = df['Vierailtu'].map({1: 'Nähty', 0: 'Pitäis nähdä'})

# Pinta-ala vierailut
total_area = df['Pinta-ala'].sum()
visited_area = df[df['Vierailtu'] == 1]['Pinta-ala'].sum()
visited_percentage = visited_area / total_area * 100

# Asukasluku vierailut
total_population = df['Asukasluku'].sum()
visited_population = df[df['Vierailtu'] == 1]['Asukasluku'].sum()
visited_population_percentage = visited_population / total_population * 100

# Display the DataFrame in Streamlit
st.header("Kuntabingo, täyttäkää tänne käydyt kunnat ja mitä siellä teitte!")
st.write(
        "Täyttäkää taulukkoon kunnat/kaupungit joissa olette käyneet, ja muistiinpanot-sarakkeeseen voitte kirjoittaa mitä siellä teitte. Käyty kunta = 1, ei käyty kunta = 0."
        " Tallentakaa muutokset painamalla alla olevaa nappia. Muutokset näkyvät vain nappia painamalla ja sivun päivittämisellä 😅")
edited_df = st.data_editor(df)

# Function to update the Google Sheet with the DataFrame
def update_sheet(updated_df):
    sheet.clear()  # Clear the existing content
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())  # Update with new data

# Button to save the edited DataFrame back to Google Sheets
if st.button("Tallenna muutokset kuntabingon tietokantaan 📝🚀 "):
    update_sheet(edited_df)
    st.success("Tietokanta päivitetty onnistuneesti! 🔥")

# Load the GeoJSON file for Finland
geojson_url = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries/FIN.geo.json'
response = requests.get(geojson_url)
finland_geojson = response.json()

# Define the display_map function to focus on Finland using GeoJSON
def display_map(dataframe, geojson):
    fig = go.Figure(go.Choroplethmapbox(
        geojson=geojson,
        locations=[0],  # dummy location
        z=[1],  # dummy value
        colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],  # transparent
        marker_line_width=1.5,
        marker_line_color='black'
    ))

    fig.add_trace(go.Scattermapbox(
        lat=dataframe['Latitude'],
        lon=dataframe['Longitude'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=20,
            color = dataframe['Vierailtu'].map({0: 'salmon', 1: 'lightskyblue'}),
        ),
        text=dataframe['Kunta'] + ': ' + 'asukasluku: ' + dataframe['Asukasluku'].astype(str)
        +  ' reissupäiväkirja: ' + dataframe['Muistiinpanot'],
        hoverinfo='text',
    ))
    fig.update_traces(
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial",
            namelength=-1  # Prevent truncation of text
        ),
    )
    fig.update_layout(
        mapbox=dict(
            style="white-bg",  # No underlying map
            center=dict(lat=64.0, lon=26.0),
            zoom=3.3,
            layers=[
                dict(
                    sourcetype='geojson',
                    source=geojson,
                    type='fill',
                    color='rgba(0,0,0,0)',
                    below="traces"
                ),
                dict(
                    sourcetype='geojson',
                    source=geojson,
                    type='line',
                    color='black'
                )
            ]
        ),
        hoverlabel=dict(
        font_size=16,  # Set the hover text font size
        bgcolor="white",  # Background color of the hover box
        bordercolor="black",  # Border color of the hover box
        font_family="Arial",  # Font family of the hover text
        align="left"  # Align text to the left
    ),
        margin={"r":0,"t":0,"l":0,"b":0},
    )
    return fig

# Display the unique municipalities visited
st.header("Statistiikkaa kuntabingosta! 📊👩🏻‍💻")
st.write("Tässä osiossa voitte tutkailla kartalla kyliä ja kaupunkeja, joissa olette käyneet tai haluatte käydä!"
         "Voitte myös filtteröidä kartan näyttämään vain käydyt tai käymättömät paikat. ✅❌")

# Filter to select visited or unvisited
filter_option = st.selectbox("Kuntafiltteri", ["Kaikki", "Nää mestat me ollaan nähty", "Tänne pitäis mennä vielä"])

if filter_option == "Nää mestat me ollaan nähty":
    filtered_df = df[df['Vierailtu'] == 1]
elif filter_option == "Tänne pitäis mennä vielä":
    filtered_df = df[df['Vierailtu'] == 0]
else:
    filtered_df = df

# Plot the map using Plotly and Streamlit
px_map = display_map(filtered_df, finland_geojson)
st.plotly_chart(px_map)

fig = px.pie(
    df,
    values='Pinta-ala',
    names='vierailtu_teksti',
    title='Pinta-alaa katettu matkustelemalla',
    color='Vierailtu',
    color_discrete_map={1: 'lightskyblue', 0: 'salmon'}
    )

st.plotly_chart(fig)

fig = px.pie(
    df,
    values='Asukasluku',
    names='vierailtu_teksti',
    title='Suomen kansaa tavattu matkustelemalla',
    color='Vierailtu',
    color_discrete_map={1: 'lightskyblue', 0: 'salmon'}
    )
st.plotly_chart(fig)
