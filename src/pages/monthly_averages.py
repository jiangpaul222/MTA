# importing necessary libraries
import pandas as pd
import streamlit as st
import altair as alt
import src.assets
from datetime import datetime

# This Streamlit application allows users to explore and visualize monthly weekday average metrics for Taxi and FHV Trips within the CBD
# Users can filter the data based on metric and time period
# The application presents a stacked line chart and a data table based on the user's selected filters

#The dataset, which is a CSV file, is sourced internally from a TLC data cleaning and aggregation script in Databricks - https://adb-6027096853111749.9.azuredatabricks.net/?o=6027096853111749#notebook/771935850484747/command/3583169199257004

# loading and transforming data
def load_and_transform_data():
    df = pd.read_csv(
        r'C:\Users\C317851\Downloads\monthly.csv', 
        engine = 'pyarrow',
        usecols=['month_year', 'monthly_trips', 'monthly_miles', 'monthly_time', 'service']
    )
    
    # converting 'month year' column to a datetime datatype with abbrv. month name and last two digits of year
    df['month_year'] = pd.to_datetime(df['month_year'], format='%b-%y')
    
    return df

# creating data filters for date range and metric
def data_filters(df):
    date_filter, metric_filter = st.columns((2, 1))
    
    # setting the maximum and minimum boundaries for the date range
    max_date = df['month_year'].max()
    min_date = df['month_year'].min()
    
    with date_filter:
        date_filter = st.slider('Select Date Range:',
                                value=(min_date.date(),
                                        max_date.date()),
                                min_value=min_date.date(),
                                format='MMM YYYY')
        
        # retrieving the start and end date range selected by the user
        MIN_PICKED_DATE = date_filter[0]
        MAX_PICKED_DATE = date_filter[1]
    
    title_dict = {"monthly_trips": "Month to Month Weekday Average Trips To, From, and Within the CBD",
                "monthly_miles": "Month to Month Weekday Average Vehicle Miles Traveled To, From, and Within the CBD",
                "monthly_time": "Month to Month Weekday Average Vehicle Hours Traveled To, From, and Within the CBD"}

    tooltip_dict = {"monthly_trips": "Number of Trips",
                    "monthly_miles": "Vehicle Miles Traveled",
                    "monthly_time": "Vehicle Hours Traveled"}
        
    with metric_filter:
        metric_filter = st.selectbox('Select a Metric:', 
                                  options = list(tooltip_dict.keys()), 
                                  format_func = lambda x: tooltip_dict[x])
    
    # DataFrame changes based on selected filters        
    all_data = df[
    (df['month_year'] >= datetime.combine(MIN_PICKED_DATE, datetime.min.time())) &
    (df['month_year'] <= datetime.combine(MAX_PICKED_DATE, datetime.max.time()))]

    all_data = all_data.set_index("month_year", drop = False)
    
    return all_data, title_dict, tooltip_dict, metric_filter

def app():
    
    st.title("Taxi & Limousine Commission Monthly Averages")
    
    df = load_and_transform_data()
    all_data, title_dict, tooltip_dict, metric_filter = data_filters(df)
    
    domain = ["HVFHV", "Yellow Taxi", "Green Taxi"]
    range_ = ["Black", "Yellow", "Green"]

    #creating separate tabs for different visualizations
    tab1, tab2 = st.tabs(['Chart', 'Table'])
    
    with tab1:
        
        st.write(
        "The graph below shows the monthly weekday average metrics of taxi and for-hire-vehicle (FHV) trips that begin and/or end within Manhattan south of 60th Street (the Central Business District), based on self-reported data by the Taxi & Limousine Commission from 2019 to present."
        )
        
        # plotting stacked line chart and creating download button for the graph
        line_chart = (
            alt.Chart(all_data, height = 500, title = title_dict[metric_filter])
            .mark_line(point = True, size = 3)
            .encode(
                alt.X("month_year", title = "", axis = alt.Axis(format = '%b-%y')),
                alt.Y(metric_filter, title = tooltip_dict[metric_filter]),
                color = alt.Color("service", title = "Legend", scale = alt.Scale(domain = domain, range = range_)),
                tooltip = [
                    alt.Tooltip(metric_filter, title = tooltip_dict[metric_filter])
            ])
            .configure_legend(orient = "bottom")
            .configure_title(fontSize = 18)
        )
        st.altair_chart(line_chart, use_container_width = True)

        st.download_button(
            label = f"Download Monthly CBD Weekday Average {tooltip_dict[metric_filter]}",
            data=all_data.to_csv(index = False),
            file_name = "MTA beta, raw data.csv",
            mime = "text/csv"
        )
        
    with tab2:
        
        # generating data table and download button for the filtered dataset
        display_table = all_data[['month_year', 'service', metric_filter]] 
        display_table = display_table.rename(columns={'service': 'Industry', 'month_year': 'Month', metric_filter: tooltip_dict[metric_filter]})
        display_table['Month'] = display_table['Month'].dt.strftime('%b-%y')
        display_table[tooltip_dict[metric_filter]] = display_table[tooltip_dict[metric_filter]].apply(lambda x: '{:,}'.format(x))
        
        csv = display_table.to_csv().encode('utf-8')
        st.download_button(
            label = f"Average Hourly {tooltip_dict[metric_filter]} Dataset", 
            data = csv, 
            file_name = f"TLCMonthlyAverage{tooltip_dict[metric_filter]}.csv", 
            mime = 'text/csv' 
        )
        
        st.write(
        "This table dynamically changes to only display the raw data selected for the map/graph."
        )
        st.dataframe(display_table.set_index(display_table.columns[0]), use_container_width=True)
        
    st.write('''
    This data does not include trips made by taxis and FHVs not licensed by the NYC TLC. Other for-hire-vehicle (e.g., black cars) trips are not shown because the NYC TLC does not collect trip start and end locations for those vehicles. Other for-hire-vehicle trips make up approximately X percent of monthly trips that NYC TLC records.\n

    Vehicles entering and remaining Manhattan south of 60th Street, excluding FDR Drive, West Side Highway/9A, Battery Park Underpass, and any surface roadway portions of the Hugh L. Carey Tunnel connecting to West Street, are tolled under the CBD Tolling Program.
    ''')
    st.write("Complete NYC TLC Taxi and FHV Trip Data and other visualization tools are available on the [TLC Data Hub](https://tlcanalytics.shinyapps.io/Data-hub/).")
    
src.assets.create_footer()




