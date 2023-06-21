# importing necessary libraries
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import src.assets

# This Streamlit application allows users to explore and visualize pickup and dropoff metrics for Taxi and FHV Trips in NYC
# Users can filter the data based on time period, CBDTP zones, industry, and metric
# The application presents a choropleth map, a bar chart, and a data table based on the user's selected filters 

# The CSV files for pickup and dropoff data is sourced internally from a TLC data cleaning and aggregation script in Databricks - https://adb-6027096853111749.9.azuredatabricks.net/?o=6027096853111749#notebook/771935850484747/command/3583169199257004
# The GeoJSON file is my combination of taxi zones and CBDTP zones, which is currently stored in CBDTP's blob container in Azure - storageexplorer://?v=2&tenantId=79c07380-cc98-41bd-806b-0ae925588f66&type=fileSystemPath&path=CBD_Taxi.geojson&container=cbdtp-data&serviceEndpoint=https%3A%2F%2Funifieddatadl02azemtd.dfs.core.windows.net

# loading and transforming data
@st.cache_data
def load_and_transform_data():
    gdf = gpd.read_file('C:\\Users\\C317851\\Downloads\\CBD_Taxi.geojson')
    pickup_df = pd.read_csv(
        r'C:\Users\C317851\Downloads\map_pickup.csv', 
        engine = 'pyarrow',
        usecols = ['service', 'month_year', 'PULocationID', 'PU_Monthly_Total', 'PU_Daily_Average']
    )
    dropoff_df = pd.read_csv(
        r'C:\Users\C317851\Downloads\map_dropoff.csv', 
        engine = 'pyarrow',
        usecols = ['service', 'month_year', 'DOLocationID', 'DO_Monthly_Total', 'DO_Daily_Average']
    )
    
    # joining pickup and dropoff datasets and then merging with GeoJSON file
    merged_df = pd.merge(dropoff_df, 
                         pickup_df[['month_year', 'PULocationID', 'PU_Monthly_Total', 'PU_Daily_Average']], 
                         how = 'left', 
                         left_on = ['DOLocationID', 'month_year'], 
                         right_on = ['PULocationID', 'month_year'])
    df = pd.merge(merged_df, 
                  gdf, 
                  how = 'left', 
                  left_on = 'DOLocationID', 
                  right_on = 'LocationID')

    df = df.drop(columns = ['PULocationID', 'DOLocationID', 'LocationID'])
    df = df.drop_duplicates(subset = ['month_year', 'service', 'geometry'], keep = 'first')
    df = df.dropna()
    df = df.rename(columns = {
        'PU_Daily_Average': 'Daily Average Pickups',
        'PU_Monthly_Total': 'Monthly Total Pickups',
        'DO_Daily_Average': 'Daily Average Dropoffs',
        'DO_Monthly_Total': 'Monthly Total Dropoffs'
    })
    
    # converting these columns to categorical data type for memory efficiency
    df["month_year"] = df["month_year"].astype("category")
    df["CBD_Zone"] = df["CBD_Zone"].astype("category")
    df["service"] = df["service"].astype("category")

    return gpd.GeoDataFrame(df) 

# creating data filters for time period, CBDTP zones, industry, and metric
def filter_data(geo_df):
    col1, col2 = st.columns([1.5, 1])
        
    with col1:
        time = st.select_slider(
            "Select Time Period:",
            options = geo_df["month_year"].unique(),
            key = 'randomkey1'
            )

    with col2:
        zone = st.multiselect(
            "Select Zone(s):",
            default = 'CBD', 
            options = geo_df["CBD_Zone"].unique(),
            key = 'randomkey2'
            )
            
    col3, col4, col5 = st.columns([1, 1, 1])
    
    with col3:
        service = st.selectbox(
            "Select an Industry:",
            options = geo_df['service'].unique(),
            key = 'randomkey3'
        )
            
    time_metric_options = {
        "Pickups": ['Daily Average Pickups', 'Monthly Total Pickups'],
        "Dropoffs": ['Daily Average Dropoffs', 'Monthly Total Dropoffs']
    }

    with col4:
        metric = st.selectbox(
            "Select a Metric:",
            options = ["Pickups", "Dropoffs"],
            key = 'randomkey4'
        )

    with col5:
        if metric in time_metric_options:
            time_metric = st.selectbox(
                "Select a Metric:",
                options = time_metric_options[metric],
                key = 'randomkey5'
            )

    # GeoDataFrame changes based on selected filters 
    all_data = geo_df[(geo_df["CBD_Zone"].isin(zone)) &
                 (geo_df["month_year"] == time) &
                 (geo_df["service"] == service)][['service', 'month_year', time_metric, 'zone', 'borough', 'CBD_Zone', 'geometry']]
   
    # This GeoDataFrame is for the gray layer of the choropleth map, which changes based on the zones not selected
    gray_data = geo_df[(~geo_df["CBD_Zone"].isin(zone)) &
                  (geo_df["month_year"] == time) &
                  (geo_df["service"] == service)]['geometry']
    
    return all_data, gray_data, time, service, time_metric
    
def app():
    
    st.title("Taxi & Limousine Commission Monthly Pickups and Dropoffs")
    
    geo_df = load_and_transform_data()
    all_data, gray_data, time, service, time_metric = filter_data(geo_df)
    
    # creating separate tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Map ", "Chart", "Data"])  

    with tab1:
        st.write(
            "The map below shows the monthly total or daily average number of pickups/dropoffs for taxi and for-hire-vehicle (FHV) trips in selected CBDTP zone(s), based on self-reported data by the Taxi & Limousine Commission from 2019 to present."
            )
        tlc_choromap(all_data, gray_data, time_metric)

    with tab2:
        st.write('The graph below shows the same data and will filter based on your selected criteria.')
        tlc_barchart(all_data, time_metric)
        
    with tab3:
        st.write(
        "This table dynamically changes to only display the raw data selected for the map/graph. It includes more in-depth information such as the geometric shape of each taxi zone."
        )
        tlc_table(all_data, time, service, time_metric)
        
    st.write('''
    This data does not include trips made by taxis and FHVs not licensed by the NYC TLC. Other for-hire-vehicle (e.g., black cars) trips are not shown because the NYC TLC does not collect trip start and end locations for those vehicles. Other for-hire-vehicle trips make up approximately X percent of monthly trips that NYC TLC records.\n

    Vehicles entering and remaining Manhattan south of 60th Street, excluding FDR Drive, West Side Highway/9A, Battery Park Underpass, and any surface roadway portions of the Hugh L. Carey Tunnel connecting to West Street, are tolled under the CBD Tolling Program.
    ''')
    st.write("Complete NYC TLC Taxi and FHV Trip Data and other visualization tools are available on the [TLC Data Hub](https://tlcanalytics.shinyapps.io/Data-hub/).")
    src.assets.create_footer()

# plotting choropleth map
def tlc_choromap(all_data, gray_data, time_metric):

    fig = choromap(all_data, time_metric)
    
    unselected_layer = px.choropleth_mapbox(
                            geojson = gray_data.geometry,
                            locations = gray_data.index,
                            color_discrete_sequence = ['gray'],
                            opacity = 0.8
                            )
    fig.add_trace(unselected_layer.data[0])
    st.plotly_chart(fig)

def choromap(all_data, time_metric):
    return px.choropleth_mapbox(
                geojson = all_data.geometry,
                locations = all_data.index,
                color = all_data[time_metric],
                hover_name = all_data['zone'],
                color_continuous_scale = 'Orrd',
                mapbox_style = 'carto-positron',
                zoom = 9.5, 
                opacity = 0.7,
                center = {"lat": 40.70, "lon": -73.97}
            ).update_layout(height = 600, width = 1400, 
                            margin = {"r":0,"t":0,"l":0,"b":0}, 
                            coloraxis_colorbar_title_text = '')

# plotting bar chart
def tlc_barchart(all_data, time_metric):
    bar_fig = px.bar(
                  x = all_data['zone'],
                  y = all_data[time_metric],
                  template = 'seaborn'
                  ).update_layout(xaxis_tickangle = -45,
                                  xaxis_title = '',
                                  yaxis_title = '',
                                  width = 1000,
                                  height = 600)
    st.plotly_chart(bar_fig)

# generating data table and download button for the filtered dataset
def tlc_table(all_data, time, service, time_metric):
    
    all_data = all_data.rename(columns = {'zone': 'Taxi Zone',
                                'borough': 'Borough',
                                'CBD_Zone': 'CBD Zone',
                                'geometry': 'Geometry'})
    
    csv = all_data.to_csv().encode('utf-8')
    st.download_button(
            label = f"{time} {service} {time_metric} Dataset", 
            data = csv, 
            file_name = f"{time}_{service}_{time_metric}.csv", 
            mime = 'text/csv' 
    )
    
    # styles the data table left-aligned text and inline display
    all_data['Geometry'] = all_data['Geometry'].astype(str)
    all_data = all_data.style.set_table_styles([
    {'selector': 'th', 'props': [('text-align', 'left')]},
    {'selector': 'td', 'props': [('text-align', 'left')]}
    ]).set_table_attributes("style='display:inline'")

    st.write(all_data)
    

    



