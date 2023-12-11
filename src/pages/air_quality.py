# importing necessary libraries
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import src.assets

# This Streamlit application allows users to explore and visualize air quality data for New York City
# Users can filter the data based on air quality indicator and time period
# The application presents a choropleth map, a bar chart, and a data table based on the user's selected filters 

# The air quality dataset is sourced from the Environmental and Health Data Portal GitHub - https://github.com/nychealth/EHDP-data/blob/production/neighborhood-reports/data/Outdoor_Air_and_Health_data.csv
# The GeoJSON file is from after conversion of EHDP GitHub's shapefiles - https://github.com/nychealth/EHDP-data/tree/production/geography/UHF%2042

# loading and transforming data
def load_and_transform_data():
    gdf = gpd.read_file('data/UHF_42_DOHMH.geojson')
    data_df = pd.read_csv(
        r'data/Outdoor_Air_and_Health_Data.csv', 
        engine = 'pyarrow'
    )
    
    # only including PM 2.5, NO2, and O3 measurements for air quality
    data_df = data_df[data_df['indicator_name'].isin(['Fine particles (PM 2.5)', 'Nitrogen dioxide (NO2)', 'Ozone (O3)'])]
    # joining GeoJSON file and CSV file
    df = pd.merge(data_df, gdf, how = 'left', right_on = 'UHFCODE', left_on = 'geo_join_id')
    # converting to GeoDataFrame with only necessary columns
    geo_df = gpd.GeoDataFrame(df[['indicator_name', 'measure_name', 'display_type', 'time', 'neighborhood', 'data_value', 'geometry']])
    
    return geo_df

# creating data filters for air quality indicator and time period
def filter_data(geo_df):
    col1, col2 = st.columns([1.5, 1])

    with col2:
        indicator = st.selectbox(
                "Select Indicator:", 
                options = geo_df['indicator_name'].unique(),
                key = 'randomkey3'
                )
            
    filtered_geo_df = geo_df[geo_df['indicator_name'] == indicator]
    
    with col1:
        time = st.select_slider(
                "Select Time Period:",
                options = filtered_geo_df["time"].unique(),
                key = 'randomkey1'
                )
    
    # GeoDataFrame changes based on selected filters         
    all_data = filtered_geo_df[(filtered_geo_df["time"] == time) & (filtered_geo_df["indicator_name"] == indicator)]
    
    return all_data, time, indicator

def app():
    
    st.title("NYC Air Quality")
    
    geo_df = load_and_transform_data()
    all_data, map_time, map_indicator = filter_data(geo_df)
    
    # creating separate tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Map ", "Chart", "Data"])  

    with tab1:
        st.write(
            "The map below shows the yearly average value for the selected air quality indicator, based on data from the New York City Community Air Survey (NYCCAS), NYC's comprehensive air quality monitoring and modeling network."
            )
        air_quality_choromap(all_data)

    with tab2:
        st.write('The graph below shows the same data and will filter based on your selected criteria.')
        air_quality_barchart(all_data)

    with tab3:
        st.write(
        "This table dynamically changes to only display the raw data selected for the map/graph. It includes more in-depth information such as the geometric shape of each neighborhood."
        )
        air_quality_table(all_data, map_time, map_indicator)

    st.write('''
             The Environment & Health Data Portal includes complete survey data, such as Real-Time Air Quality on the [Air Quality Hub](https://a816-dohbesp.nyc.gov/IndicatorPublic/beta/key-topics/airquality/).\n
             Monitoring locations for air pollution measurements can be found on the webpage for the [NYC Department of Health](https://nyccas.cityofnewyork.us/nyccas2021v9/report/2#Sites/).
             ''')
    src.assets.create_footer()

# plotting choroploeth map
def air_quality_choromap(all_data):
    map_fig = px.choropleth_mapbox(
                geojson = all_data.geometry,
                locations = all_data.index,
                color = all_data['data_value'],
                hover_name = all_data['neighborhood'],
                color_continuous_scale = 'Orrd',
                mapbox_style = 'carto-positron',
                zoom = 9.5, 
                opacity = 0.7,
                center = {"lat": 40.70, "lon": -73.97}
            ).update_layout(height = 600, width = 1400, 
                            margin = {"r":0,"t":0,"l":0,"b":0}, 
                            coloraxis_colorbar_title_text = '')
    st.plotly_chart(map_fig)

# plotting bar chart
def air_quality_barchart(all_data):
    bar_fig = px.bar(
                  x = all_data['neighborhood'],
                  y = all_data['data_value'],
                  template = 'seaborn'
                  ).update_layout(xaxis_tickangle = -45,
                                  xaxis_title = '',
                                  yaxis_title = '',
                                  width = 1000,
                                  height = 600)
    st.plotly_chart(bar_fig)

# generating data table and download button for the filtered dataset
def air_quality_table(all_data, map_time, map_indicator):
    
    all_data = all_data.rename(columns = {'indicator_name': 'Indicator', 
                                'measure_name': 'Measure', 
                                'time': 'Time', 
                                'neighborhood': 'Neighborhood', 
                                'data_value': 'Value', 
                                'geometry': 'Geometry',
                                })
    
    csv = all_data.to_csv().encode('utf-8')
    st.download_button(
            label = f"{map_time} {map_indicator} Dataset", 
            data = csv, 
            file_name = f"{map_time}_{map_indicator}.csv", 
            mime = 'text/csv' 
    )
    
    # styles the data table left-aligned text and inline display
    all_data['Geometry'] = all_data['Geometry'].astype(str)
    all_data = all_data.style.set_table_styles([
    {'selector': 'th', 'props': [('text-align', 'left')]},
    {'selector': 'td', 'props': [('text-align', 'left')]}
    ]).set_table_attributes("style='display:inline'")

    st.write(all_data)

            
    
