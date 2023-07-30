from os import rename
import string
from attr import validate
import grpc
from numpy import dtype
import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import geopandas as gp
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar
import plotly.express as px
import itertools
import minio_data_loader as mdl

import yaml
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from pathlib import Path

import plotly.express as px

#######################################################
########## data processing/all purpose functions ######
#######################################################
## retro code review comment

def get_configuration_files(config_path: Path = Path() / "config" / "config.yml") -> dict:
    """Imports the configuration files.

    Args:
        config_path (Path, optional): Path to the configuration file. Defaults to Path()/"config"/"config.yml".

    Returns:
        dict: Python dictionary with all configuration variables in it.
    """
    return yaml.safe_load(config_path.read_text())


# nonholiday weekday function
@st.experimental_memo()
def nh_w_d():
    day1 = "2019-01-01"
    # calculate 3 months later
    day2 = (dt.datetime.now() + dt.timedelta(days = 90)).strftime("%x").replace("/", "-")
    us_bd = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    df_non_holiday = pd.date_range(start=day1, end=day2, freq=us_bd)
    # df_non_holiday=pd.DataFrame(df_non_holiday)
    return df_non_holiday

## retro code review comment

# holiday weekend
def holweekend(row):
    if row["NH Weekday"] == True:
        return "Weekday"
    if row["dow"] == 5:
        return "Saturday"
    if row["dow"] == 6:
        return "Sunday"
    else:
        return "Holiday, drop"

## retro code review comment
# function for grouping data for omny-use visualizations
# @st.experimental_memo()
def omny_grp(omnydf : pd.DataFrame, grparray: list | tuple = ["month_year_num", "RIDER_TYPE"], omnyfilt: bool = True):
    """Function to aggregate base-processed subway or bus ridership data to generate aggregated OMNY-usage data, with one row per month and other grouping columns

    Args:
        omnydf: Base bus or subway data, read in by
        grparray (list, tuple): Columns to group OMNY data by. First value should always be month_year_num, and last value RIDER_TYPE. Default ['month_year_num', 'RIDER_TYPE']
        omnyfilt (bool): Whether to filter the data to OMNY rider-types only. Default True.
    """

    # total ridership by grparray
    omnygrpdf = omnydf.groupby(grparray, as_index=False, observed=False)["RIDERSHIP"].agg("sum")

    # subset group array to higher-level group - e.g., overall month_year_num, overall month_year_num/bus depot.
    arraymin1 = grparray[0:-1]

    # total usage for total-group
    omnygrpdf["totusg"] = omnygrpdf.groupby(arraymin1, observed=False)["RIDERSHIP"].transform("sum")

    # percent usage
    omnygrpdf["percent_use"] = round(omnygrpdf["RIDERSHIP"] / omnygrpdf["totusg"], 4) * 100

    if omnyfilt:
        # filter to omny
        omnygrpdf = omnygrpdf.loc[omnygrpdf["RIDER_TYPE"] == "OMNY"]

    # associated description of month/year with number
    omny_monthyeardesc = omnydf[["month_year", "month_year_num"]].drop_duplicates()

    omnygrpdf = omnygrpdf.merge(omny_monthyeardesc)

    # error checks
    if any(omnygrpdf["percent_use"] < 0):
        raise Exception("Negative value in percent_use column")

    if any(omnygrpdf["percent_use"] > 100):
        raise Exception("percent_use exceeds 100")

    # calculate percentile usage
    omnygrpdf["pctile_use"] = omnygrpdf.groupby(["month_year_num", "RIDER_TYPE"], as_index=False)["percent_use"].rank(
        pct=True
    )

    # sort by month_year_num
    omnygrpdf.sort_values(by="month_year_num", ascending=True)

    # add in date column
    omnygrpdf["month_year_date"] = pd.to_datetime(omnygrpdf["month_year_num"], format = "%y-%m")

    return omnygrpdf
## retro code review comment

# route recode
def route_recode(busdf : pd.DataFrame, dicttype : str = "original", coloutput : str = "ROUTE_TYPE") -> pd.DataFrame:
    """Recode routetypes
    
    Recodes route-types from one-letter values to more expressive values

    args:
        busdf (pd.Dataframe): bus OMNY dataframe

        dicttype (str): "original" or "shorthand"; type of dictionary transformation making

        coloutput(str): name of output column, default "ROUTE_TYPE"

    returns:
        busdf with transformed route_type values
    """

    if dicttype == "original":

        route_typedict = {"E": "Express", "L": "Local / limited", "S": "Select Bus Service"}

    elif dicttype == "shorthand":

        route_typedict = {"Express": "Exp", "Local / limited": "Local", "Select Bus Service": "SBS"}

    else:
        raise Exception("dicttype must be one of 'original' or 'shorthand'")

    if (all(busdf["ROUTE_TYPE"].isin(route_typedict.keys())) == False):
        raise Exception("Some route types identified that not in route_typedict")

    busdf[coloutput] = busdf.apply(lambda row: route_typedict[row["ROUTE_TYPE"]], axis = 1)

    return busdf

# transform bus route to id local
@st.experimental_memo()
def busroute_reclass(busdf : pd.DataFrame) -> pd.DataFrame:
    """Transforms ROUTE column in bus data to include ROUTE_TYPE

    Creates a more descriptive ROUTE_TYPE column from base bus data; creates an abbreviated ROUTE_TYPE column; and modifies ROUTE to include ROUTE_TYPE

    returns:
        bus dataset with transformed ROUTE, ROUTE_TYPE columns, and ROUTE_TYPE_SHORT column
    """
    outbus = route_recode(busdf=busdf)

    outbus = route_recode(busdf=outbus, coloutput="ROUTE_TYPE_SHORT", dicttype="shorthand")

    if any(outbus.groupby(by = "ROUTE")[ "ROUTE_TYPE"].nunique() >1):
        raise Exception("Multiple ROUTE_TYPEs counted for some routes")

    outbus["ROUTE"] = outbus[["ROUTE_TYPE_SHORT", "ROUTE"]].apply(": ".join, axis = 1)

    return outbus

def routejoin(aggbusdf : pd.DataFrame, busroute_lookuptable: pd.DataFrame) -> pd.DataFrame:
    """Join lookup table to bus dataframe by ROUTE, and reclassify ROUTE_TYPE
    
    Parameters:
        aggbusdf: Base-processed bus dataframe

        busroute_lookuptable: Lookup table of bus routes and route types

    """

    outbus = aggbusdf.merge(busroute_lookuptable, how = "left", validate = "many_to_one")

    if any(outbus.groupby(by = "ROUTE")[ "ROUTE_TYPE"].nunique() >1):
        raise Exception("Multiple ROUTE_TYPEs counted for some routes")

    outbus = busroute_reclass(outbus)

    if any(outbus.groupby(by = "ROUTE")[ "ROUTE_TYPE"].nunique() >1):
        raise Exception("Multiple ROUTE_TYPEs counted for some routes")

    return(outbus)   

## 
def chartconfig(alt_chart: alt.Chart):
    outchart = (
        alt_chart
        .configure_legend(orient = "bottom")
        .configure_title(fontSize = 18)
    )

    return outchart
    

def stylecheck(colname: str, formtype: str = None, nomatch: str | None = ",.0f") -> str:
    """Return column format

    Checks type of column based on column name and returns format to display column in.

    Args:
        colname: Column name who's type is checked. Assumes that proportion columns have word proportion in them; percent columns percent; other numeric columns one of average, mean, total, or baseline
        formtype (str, optional): If formatting a datatable or map, the representation of the format is slightly different. Supply 'datatable' for formatting a dataframe visualized by st.write or st.dataframe, and 'map' for plotly express maps. Default None
        nomatch (str, none, optional): What format to return if no match to text pickups

    Returns:
        Format to feed into formatting function
    """
    if type(colname) != str:
        raise Exception("Type str required")

    if (colname == "Month/year"):
        toolformat = "%B %Y"

    elif (formtype is not None) & (formtype not in ("datatable", "map")):
        raise Exception(
            "formtype must be one of None (default), datatable, or map, corresponding to the type of output"
        )

    # omny datatables
    elif any(coltype in colname.casefold() for coltype in ("proportion", "saturday", "sunday", "weekday")):
        toolformat = ".2f"

    elif "percent" in colname.casefold():
        toolformat = ",.1f"
    
    elif any(coltype in colname.casefold() for coltype in ("average", "mean", "baseline", "total", "omny riders")) :
        toolformat = ",.0f"

    elif "change" in colname.casefold():
        toolformat = ",.2f"

    else:
        return nomatch

    # html formats for datatables slightly different
    if (formtype == "datatable") | (formtype == "map"):

        toolformat = "".join(["{0:", toolformat, "}"]) if "," in toolformat else "".join(["{0:,", toolformat, "}"])
        toolformat = toolformat.replace("%", "f") + "%" if "%" in toolformat else toolformat

    return toolformat


def tooltip_generate(toolitem: str) -> alt.Tooltip:
    """Generate altair tooltip

    Generates altair tooltip for line-chart labels.

    Args:
        toolitem: Column name that will be displayed in tooltip. Assumes that proportion columns have word proportion in them; percent columns percent; other numeric columns one of average, mean, total, or baseline

    Returns:
        alt.Tooltip with values formatted appropriately
    """

    colstyle = stylecheck(toolitem, nomatch=None)

    if colstyle is None:
        return alt.Tooltip(toolitem)

    # T for temporal data
    dtype = "T" if toolitem == "Month/year" else "Q"

    return alt.Tooltip(f"{toolitem}:{dtype}", format=colstyle)


# @st.experimental_memo
def style_table_cols(tabledf: pd.DataFrame) -> str:
    """Style columns for display in datatables

    Uses pd.DataFrame.style.format() to style columns for display in streamlit datatables. Assumes that proportion columns have word proportion in them; percent columns percent; other numeric columns one of average, mean, total, or baseline.

    Args:
        tabledf: Dataframe to be displayed in st.dataframe.

    Returns:
        Pandas Dataframe with styled columns

    """
    cols = tabledf.columns

    colformats = [stylecheck(colname, formtype="datatable", nomatch=None) for colname in cols]

    listdict = {cols[i]: colformats[i] for i in range(len(colformats)) if colformats[i] is not None}

    # return listdict

    return tabledf.style.format(listdict)


# @st.experimental_memo()
def finaltableprep(tbldf):
    reshapedf = tbldf.rename(
        columns={
            "ZIPCODE" : "Zip Code",
            "statline" : "Station/line",
            "ROUTE" : "Route"
        })

    reshapedf = reshapedf.set_index(keys = reshapedf.columns[0], inplace = False)
    reshapedf.index.name = reshapedf.columns[0]

    return style_table_cols(reshapedf)


# function for creating omny chart
#@st.experimental_memo()
def chartomny(df: pd.DataFrame, validid: str, routedomain : list | tuple = None) -> alt.Chart:

    # formatting of dates in tooltip problematic - last day of previous month by default - so add 1 to fix
    df["month_year_date"] = df.month_year_date + dt.timedelta(days = 1)

    dfrename = df.rename(
        columns={
            "month_year_date": "Month/year",
            "percent_use": "Percent usage",
            "RIDERSHIP": "OMNY riders",
            "totusg": "Total riders",
        }
    )

    toolcols = ["Month/year", "Percent usage", "OMNY riders", "Total riders"]

    toolcols = [tooltip_generate(toolitem=col) for col in toolcols]
    # print(toolcols)

    # accounts for proper order of overall, then route types, then data
    if routedomain is not None:
        sort = ["Overall"] + routedomain + list(dfrename[validid].unique())

    else:
        sort = ["Overall"] + dfrename[validid].unique()
        
    # create line chart of data
    omny_monthchart = (
        alt.Chart(
            dfrename,
            height=500,
            #    width = 500,
            title="OMNY Usage by Month",
        )
        .mark_line(
            point=True,
            size=3,
            smooth=True
        )
        .encode(
            alt.X("Month/year", title="Month/year", axis=alt.Axis(format="%b %y")),
            alt.Y("Percent usage", title="Percent usage", scale=alt.Scale(domain=[0, 100])),
            color= alt.Color(validid, sort = sort),
            tooltip=toolcols,
        )
    )

    return chartconfig(omny_monthchart)

## retro code review comment

# function for creating omnyuse charts
@st.experimental_memo()
def zipdisplaytbl(df, zipstat="ZIPCODE"):
    ziptbl = (
        df[[zipstat, "percent_use", "chng_percent_use", "RIDERSHIP", "totusg"]]
        .rename(
            columns={
                # "ZIPCODE": "Zip Code",
                #    "POPULATION": "Zip Population",
                "percent_use": "Percent OMNY",
                "chng_percent_use": "Change since last month",
                "RIDERSHIP": "OMNY Ridership",
                "totusg": "Total Ridership",
            }
        )
        .sort_values(by="Percent OMNY", ascending=False)
        .reset_index()
        .drop(columns="index")
    )

    if zipstat == "ZIPCODE":
        ziptbl = ziptbl.rename(columns={"ZIPCODE": "Zip Code"})
## retro code review comment

    elif zipstat == "statline":
        ziptbl = ziptbl.rename(columns={"statline": "Station/line"})

    elif zipstat == "ROUTE":
        ziptbl = ziptbl.rename(columns={"ROUTE": "Route"})

    ziptbl.index.name = "OMNY-Usage Rank"

    ziptbl["Percent OMNY"] = round(ziptbl["Percent OMNY"], 1)

    return ziptbl


# joins station data with zipcode info to omny dataset
st.experimental_memo()
## retro code review comment
def prepstationboothzip(omnydf, monthyrstr=False, zippath="data/processed/stationboothzip.csv", returnmissing=False):
    stationboothzip = pd.read_csv(zippath)

    stationboothzip["ZIPCODE"] = stationboothzip["ZIPCODE"].astype("str")

    # join noholiday dataset to stations/booths with zip codes
    statboothzip_omny = stationboothzip.merge(
        omnydf, how="right", right_on="BOOTH", left_on="LOC", validate="one_to_many"
    )

    # convert station id to category
    statboothzip_omny["Station ID"] = statboothzip_omny["Station ID"].astype("category")

    # filter out missing booths
    statboothzip_omny_filtzip = statboothzip_omny.loc[statboothzip_omny["ZIPCODE"].notna()]

    # returns booths/stations where zip code is missing
    if returnmissing:
        return statboothzip_omny.loc[statboothzip_omny["ZIPCODE"].isna()]

    # if month year should be string - convert string
    if monthyrstr:
        statboothzip_omny_filtzip["month_year_num"] = statboothzip_omny_filtzip["month_year_num"].astype("string")

    return statboothzip_omny_filtzip

## retro code review comment

# read processed station data
st.experimental_memo()
def readstat(path="./data/processed/STATIONS_PROCESS.csv"):
    return pd.read_csv(path)


# read base zip code data - subset necessary paths, give right crs
st.experimental_memo()
## retro code review comment
def readzip(path="./data/source/zipshp/ZIP_CODE_040114.shp"):
    zipshp = gp.read_file(path)

    zipshp = zipshp[["ZIPCODE", "POPULATION", "AREA", "PO_NAME", "geometry"]]

    zipshp.to_crs(epsg=4326)

    return zipshp


# filter to most recent month
@st.experimental_memo()
def recentfilt(df: pd.DataFrame, maxmonth: str):
    recentdf = df[df["month_year_num"] == maxmonth]

    return recentdf

## retro code review comment

# prepare dataset for csv
@st.cache()
def converttocsv(dataframe):
    # error with categorical data types
    for i in dataframe.columns:
        if dataframe[i].dtype.name == "category":
            dataframe[i] = dataframe[i].astype("string")

    return dataframe.to_csv().encode("utf-8")

## retro code review comment

# rename and drop columns in dataset before download
# @st.experimental_memo()
def ridership_dwnldready(_dataframe):

    if "geometry" in _dataframe.columns:
        _dataframe = pd.DataFrame(_dataframe)

    outdf = _dataframe.reset_index()

    outdf = outdf.drop(
        axis=1,
        columns=[
            "geometry",
            "AREA",
            "GTFS Latitude",
            "GTFS Longitude",
            "idcount",
            "Time-group",
            "RIDER_TYPE",
            "month_year",
            "Station and line",
            "Index",
        ],
        errors="ignore",
    )

    outdf = outdf.rename(
        columns={
            "PO_NAME": "ZIP Post Office Name",
            "ROUTE": "Route",
            "statline": "Station/line",
            "month_year_num": "Year/month",
            "holweekclass": "Day of week",
            "monthdaytot": "Total riders in month",
            "monthdaycount": "Days trains in service in zip",
            "base2019mean": "2019-average daily riders",
            "basetot2019": "Total riders in 2019",
            "counted_days_2019": "Days trains in service in 2019",
            "percent_use": "OMNY usage",
            "RIDERSHIP": "OMNY riders",
            "totusg": "Total riders",
        },
        errors="ignore",
    )

    return outdf
## retro code review comment

# match-filter dataframe of values want removed in another df, or 
@st.experimental_memo()
def remove(displaydf, removedf = None, buslist = None):

    # filter out low count or other routes
    if removedf is not None:
        removedf["Remove"] = True
        displaydf = displaydf.merge(
            removedf,
            how = "left",
            validate = "many_to_one"
        )

        displaydf = displaydf.loc[displaydf["Remove"] != True]

    if buslist is not None:
        displaydf = displaydf.loc[displaydf["ROUTE"].isin(buslist) == False]

    return displaydf

# processing function for base-data
def rollup_mclass_to_rider_type(m_class: int) -> str:
    """Function to turn M_CLASS column into a simpler OMNY vs. MetroCard column
    
    Usage: df["RIDER_TYPE"] = df["M_CLASS"].apply(rider_type)
    """
    if m_class >= 500:
        rider_type = "OMNY"
    else:
        rider_type = "MetroCard/Other"
    return rider_type


# calculate change in a value from the previous month
# @st.experimental_memo()
def calchng(lagdf : pd.DataFrame, grpcols : list, valcol : list or str):
    """Function to calculate change in a value from the previousmonth


    
    
    """
    returndf = lagdf

    if type(valcol) == list:
        for val in valcol:

            returndf = calchng(returndf, grpcols=grpcols, valcol=val)

    else:
        returndf = lagdf.sort_values("month_year_num")

        colprev = "prev_" + valcol
        colnew = "chng_" + valcol

        returndf[colprev] = returndf.groupby(grpcols, as_index=False)[valcol].shift()

        returndf[colnew] = returndf[valcol] - returndf[colprev]

    return returndf
## retro code review comment


# convert list to comma separated list in sentence
def commafy(list_items: list or str):

    if type(list_items) != list:
        list_items = list(list_items)

    if len(list_items) == 0:
        raise Exception("list_items is empty")

    list_items = list(map(str, list_items))

    if len(list_items) == 1:
        return list_items[0]

    elif len(list_items) == 2:
        return " and ".join(list_items)

    elif len(list_items) > 2:
        substring = ", ".join(list_items[:-1])
        return ", and ".join([substring, list_items[-1]])

## retro code review comment
def transformfilt_datecols(
    ombdf: pd.DataFrame, datecol: str = "R_DATE", datecolformat: str = "%Y-%m-%d"
) -> pd.DataFrame:
    """Function to turn date column of OMB ridership data into appropriate format, identify day of week, filter out holidays, and convert time column into descriptive text

    Args:
        ombdf (pd.DataFrame):
        timecol (str): Name of coded time column in OMB dataset; default "TOUR"
        datecol (str): Name of date column in OMB dataset; default "R_DATE"
        datecolformat (str): Format that datecol is in, for purpose of converting to datecol. Default "%Y-%m-%d"
    """

    # date conversions
    ombdf["date_format"] = pd.to_datetime(ombdf[datecol], format=datecolformat)
    ombdf["dow"] = ombdf["date_format"].dt.day_of_week

    ombdf["month_year"] = ombdf["date_format"].dt.strftime("%b-%y")
    ombdf["month_year"] = ombdf["month_year"].astype("category")

    ombdf["month_year_num"] = ombdf["date_format"].dt.strftime("%y-%m")
    ombdf["month_year_num"] = ombdf["month_year_num"].astype("category")

    # tour categorical
    ombdf["TOUR"] = ombdf["TOUR"].astype("category")

    # convert time column to meaningful values
    tourdict = {1: "12am-6am", 2: "6am-9am", 3: "9am-4pm", 4: "4pm-7pm", 5: "7pm-12am"}

    ombdf["Time"] = ombdf.apply(lambda x: tourdict[x["TOUR"]], axis=1).astype("category")

    # generate dataset of nonholiday workdays
    df_non_holiday = nh_w_d()

    # new column nh weekday
    ombdf["NH Weekday"] = ombdf["date_format"].isin(pd.Series(df_non_holiday))

    # subset to nonholiday workdays
    ombdf_noholiday = ombdf[ombdf["date_format"].isin(pd.Series(df_non_holiday))]

    # identify type of weekday
    ombdf["holweekclass"] = ombdf.apply(lambda row: holweekend(row), axis=1)

    # confirm holidays classified correctly
    # ombdf_holidays = ombdf[ombdf["holweekclass"] == "Holiday, drop"]

    # ombdf_holidays_list = ombdf_holidays[["R_DATE"]].drop_duplicates()

    # ombdf_dow_list = ombdf[ombdf["holweekclass"].isin(["Saturday", "Sunday"])][["holweekclass", "dow"]].drop_duplicates()

    # drop holidays
    ombdf_noholiday = ombdf[ombdf["holweekclass"] != "Holiday, drop"]

    return ombdf_noholiday


# agg bus riders
def aggbusriders(busdf: pd.DataFrame) -> pd.DataFrame:
    """Aggregate riders in OMB bus dataset, including all non-employee rides

    Args:

        busdf: OMB bus ridership data, with one row per route and ride_type in a given time period on a given day

    Returns:

        Aggregated OMB bus data, with one row per route in a given time period on a given day, excluding employee rides

    """

    busdf = busdf.drop(columns="R_DATE")

    # pull columns for grouping
    non_ridetypecols = list(busdf.columns)

    non_ridetypecols.remove("RIDE_TYPE")
    non_ridetypecols.remove("REVENUE")

    # filter out employee rides
    busdf = busdf.loc[busdf["RIDE_TYPE"] != 0]

    # aggregate by all non-ride type columns to get total non-employee ridership count
    bus_agg = busdf.groupby(non_ridetypecols, axis=0, observed=True, as_index=False).agg(
        {"RIDER_COUNT": sum, "REVENUE": sum}
    )

    # rename for consistency with
    bus_agg = bus_agg.rename({"RIDER_COUNT": "RIDERSHIP"})

    return bus_agg


# plotly express map formatting is pretty weird; this function formats columns
def formathovercol(hovercol: str, colindex: int) -> str:
    """Generates text to format a column appearing in a hover-template

    plotly express is pretty weird about formatting columns appearing in hovertext (e.g., two commas). This generates formatted text for an individual column based on the column name. It is looped within `maphoverformat()`.

    args:
        hovercol: Column being formatted in plotly express map
        colindex: Position of column in loop in plotly express map

    returns:
        formatted text for plotly express
    """

    # print(hovercol)
    # print("station" in hovercol.casefold())

    if "proportion" in hovercol.casefold():
        text = "".join([hovercol, ": %{", f"customdata[{colindex}]:,.2f", "}"])

    elif "percent" in hovercol.casefold():
        text = "".join([hovercol, ": %{", f"customdata[{colindex}]:,.1f", "}", "%"])

    elif (
        ("zipcode" in hovercol.casefold())
        | ("station" in hovercol.casefold())
        | ("statline" in hovercol.casefold())
        | ("line" in hovercol.casefold())
        | ("stop name" in hovercol.casefold())
        | ("bin" in hovercol.casefold())
    ):
        # print("Station recognized")
        text = "".join([hovercol.title(), ": %{", f"customdata[{colindex}]", "}"])

    else:
        text = "".join([hovercol, ": %{", f"customdata[{colindex}]:,.0f", "}"])

    return text


# format map hovertext
# @st.experimental_memo()
def maphoverformat(_geodf: gp.GeoDataFrame | pd.DataFrame, hovercols: list | tuple | str) -> dict:
    """Generates dict with values for 'custom_data' parameter in px.mapfunction(), and hovertemplate parameter of px.mapobj.update_traces() function

    Formatting text in plotly express maps is annoyingly tricky, so this function provides a quick way to do that for a given geodataframe or dataframe. Assumes formatting of all columns should be no 0s

    args:
        _geodf: Geopandas geodataframe or pandas dataframe
        hovercols: Columns to show when you mouse over a map shape

    returns:
        dict of list of columns to enter in custom_data parameter, and string to enter in hovertemplate parameter
    """

    # https://stackoverflow.com/questions/59057881/python-plotly-how-to-customize-hover-template-on-with-what-information-to-show
    # https://medium.com/analytics-vidhya/create-choropleth-maps-by-using-plotly-31771803da7
    custdata = _geodf

    # convert data to non-geodf if geodf
    if type(custdata) == gp.GeoDataFrame:
        custdata = pd.DataFrame(custdata.drop(columns="geometry"))

    custdata = custdata.reset_index()

    # pull vector of each columns
    custdata_enter = [custdata[col] for col in hovercols]

    # create array of values
    hovercols_text = "<br>".join([formathovercol(hovercols[i], i) for i in range(len(hovercols))])

    print(hovercols_text)

    return {"customdata": custdata_enter, "hovertemplate": hovercols_text}


################ OMNY usage functions
# function to create map of omny data
def mapomny(_geodf, maxrange):

    # generate styles for values
    hover_cols = ["ZIPCODE", "Percent OMNY", "OMNY Ridership", "Total Ridership", "Zip Population"]

    hoverformat = maphoverformat(_geodf=_geodf, hovercols=hover_cols)

    chlomap = px.choropleth_mapbox(
        data_frame=_geodf,
        geojson=_geodf.geometry,
        locations=_geodf.index,
        color="Percent OMNY",
        color_continuous_scale="RdYlGn",
        range_color=maxrange,
        zoom=9,
        mapbox_style="carto-positron",
        center={"lat": 40.724965, "lon": -73.972398},
        opacity=0.5,
        custom_data=hoverformat["customdata"],
        labels={"ZIPCODE": "Zip Code"},
    )

    chlomap.update_traces(hovertemplate=hoverformat["hovertemplate"])

    chlomap.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return chlomap

## retro code review comment

# function to create scatter map of omny data
def mapomny_scatter(geodf, maxrange):

    # geodf = geodf.rename(columns = {"statline" : "Station"})

    hoverformat = maphoverformat(
        _geodf=geodf, hovercols=["Station and line", "Percent OMNY", "OMNY Ridership", "Total Ridership"]
    )

    # print(hoverformat["hovertemplate"])

    chlomap = px.scatter_mapbox(
        geodf,
        lat=geodf.geometry.y,
        lon=geodf.geometry.x,
        center={"lat": 40.724965, "lon": -73.972398},
        mapbox_style="carto-positron",
        color="Percent OMNY",
        color_continuous_scale="RdYlGn",
        range_color=maxrange,
        custom_data=hoverformat["customdata"],
        labels={"statline": "Station/line"},
        zoom=9,
    )

    chlomap.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    chlomap.update_traces(hovertemplate=hoverformat["hovertemplate"], marker={"size": 10})

    return chlomap

## retro code review comment

# join recent station data to station geometry file - create statline column
@st.experimental_memo()
def prepstationgeom(_station_geom, stationdata_recent):
    statzipmerge = _station_geom.merge(stationdata_recent, how="inner", on="statline", validate="one_to_many")

    statzipmerge["Station and line"] = statzipmerge["statline"]

    statzipmerge = statzipmerge.set_index("statline")

    # statziprange = [statzipmerge.percent_use.min(), statzipmerge.percent_use.max()]

    statzipmerge = statzipmerge.rename(
        columns={
            "percent_use": "Percent OMNY",
            "RIDERSHIP": "OMNY Ridership",
            "totusg": "Total Ridership",
        }
    )

    return statzipmerge

## retro code review comment

# function to filter data to top 10 or bottom ten zip codes; can't hash
def filttopbottomzip(_df, bottom=True):
    return _df.sort_values(by="Percent OMNY", ascending=bottom)[0:10]

# @st.experimental_memo
def textgen_omnyrider(omny_onlymonth : pd.DataFrame, month_lookup : pd.DataFrame):
    # overall last month and overall percent use
    overall6 = omny_onlymonth.loc[omny_onlymonth["month_year_num"].isin(month_lookup["month_year_num"][-6:])]

    overall6_avgchng = round(overall6.chng_percent_use.mean(), 2)

    overall3 = omny_onlymonth.loc[omny_onlymonth["month_year_num"].isin(month_lookup["month_year_num"][-3:])]

    overall3_avgchng = round(overall3.chng_percent_use.mean(), 2)

    incdecoverall_6 = "increased" if overall6_avgchng >= 0 else "decreased"

    incdecoverall_3 = "increased" if overall6_avgchng >= 0 else "decreased"

    overall36_diff = round(overall3_avgchng - overall6_avgchng, 2)

    if overall36_diff > 0.25:

        incdec36_select = "increased"

    elif overall36_diff < -0.25:

        incdec36_select = "decreased"

    else:

        incdec36_select = "remained steady"

    filtdf_lastmonth = omny_onlymonth.loc[omny_onlymonth["month_year_num"] == max(month_lookup.month_year_num)]

    filtdf_lastmonth_avguse = round(filtdf_lastmonth.percent_use.mean(), 2)

    dictreturn = {
        "lastmonth_use": filtdf_lastmonth_avguse,
        "last6_chng": overall6_avgchng,
        "last3_chng": overall3_avgchng,
        "text_incdec_6": incdecoverall_6,
        "text_incdec_3": incdecoverall_3,
        "incdec_diff": overall36_diff,
        "text_incdec_36": incdec36_select,
    }

    return dictreturn
## retro code review comment

#@st.experimental_memo
def textgen_selectoverall(overalldict : dict, selectdict : dict):
    selecthighlow_diff = round(abs(selectdict["last6_chng"] - overalldict["last6_chng"]), 2)

    selecthighlow = "higher" if selectdict["last6_chng"] > overalldict["last6_chng"] else "lower"

    return {"selectov_diff": selecthighlow_diff, "text_selectov": selecthighlow}

## retro code review comment

#@st.experimental_memo
def textgen_omnydatatbl (tbldf):
    numzipabove50 = len(tbldf.loc[tbldf["Percent OMNY"] > 50])

    numzipbelow25 = len(tbldf.loc[tbldf["Percent OMNY"] < 25])

    numzipdecusg = len(tbldf.loc[tbldf["Change since last month"] < 0])

    numzip5inc = len(tbldf.loc[tbldf["Change since last month"] >= 5])

    return {"pct50": numzipabove50, "pct25": numzipbelow25, "decusg": numzipdecusg, "inc5": numzip5inc}


##############################################
########### # ridershipreturn specific functions
##############################################
# grouping function for ridershipreturn visualizations, calculating monthly average for given set of variables
## retro code review comment

# @st.experimental_memo()
def rider_grp(omnydf, riderdf, grparraykey="ZIPCODE", timefilt=None):

    # if timefilt is include - aggregate by time block
    if timefilt == "Include":
        grparray2019_date = [grparraykey, "holweekclass", "Time", "date_format"]
        grparray2019_agg = [grparraykey, "holweekclass", "Time"]
        grparray_date = ["month_year_num", "month_year", grparraykey, "holweekclass", "Time", "date_format"]
        grparray_agg = ["month_year_num", "month_year", grparraykey, "holweekclass", "Time"]
        grparray_pctile = ["month_year_num", "month_year", "holweekclass", "Time"]
    
    # timefilt parameter to allow you to group different blocks of time together, and then calculate statistics by day
    elif timefilt is not None:
        omnydf = omnydf.loc[omnydf["Time"].isin(timefilt)]

        riderdf = riderdf.loc[riderdf["Time"].isin(timefilt)]

    # group columns excluding time
    if timefilt != "Include":
        grparray2019_date = [grparraykey, "holweekclass", "date_format"]
        grparray2019_agg = [grparraykey, "holweekclass"]
        grparray_date = ["month_year_num", "month_year", grparraykey, "holweekclass", "date_format"]
        grparray_agg = ["month_year_num", "month_year", grparraykey, "holweekclass"]
        grparray_pctile = ["month_year_num", "month_year", "holweekclass"]

    # check for category dtypes that return problem values
    if "category" in omnydf[grparray_date].dtypes.values:
        raise Exception(f"One of following grouping columns is type category: {grparray_date}. Convert to type string")

    # aggregate data so each row = total ridership at a station or zip code on a date, across 2019
    riderdf_agg = riderdf.groupby(grparray2019_date, as_index=False)["RIDERSHIP"].agg("sum")

    # aggregate data so each row = average daily ridership at a zipcode or station
    riderdf_avg = riderdf_agg.groupby(grparray2019_agg, as_index=False)["RIDERSHIP"].agg(
        {"basetot2019": "sum", "base2019mean": "mean", "counted_days_2019": "size"}
    )

    # round to avoid errors
    riderdf_avg["base2019mean"] = round(riderdf_avg["base2019mean"], 2)

    # aggregate omny data so each row = daily ridership in a station or zip code - and join riderdf_avg to it
    omny_day = omnydf.groupby(grparray_date, as_index=False)[["RIDERSHIP"]].agg("sum")

    # calculate average ridership on a month's saturday/weekday/sunday for zip codes or stations
    omny_grp = (
        omny_day.groupby(grparray_agg, as_index=False)["RIDERSHIP"]
        .agg({"monthdailyavg": "mean", "monthdaytot": "sum", "monthdaycount": "size"})
        .merge(riderdf_avg, validate="many_to_one")
    )

    if any(omny_grp.monthdaycount > 30):
        raise Exception(
            "Counting more than 30 days in a holweekclass in a month; likely, an issue of a column being a category type"
        )

    # round
    omny_grp["monthdailyavg"] = round(omny_grp["monthdailyavg"], 2)

    # calculate average day-ridership in month / average day ridership across 2019
    omny_grp["prop_return"] = round(omny_grp["monthdailyavg"] / omny_grp["base2019mean"], 2)

    # calculate percentile prop_return
    omny_grp["pctile_return"] = omny_grp.groupby(grparray_pctile, as_index=False)["prop_return"].rank(pct=True)
    omny_grp["pctile_return"] = round(omny_grp["pctile_return"], 4) * 100

    omny_grp["month_year_date"] =  pd.to_datetime(omny_grp["month_year_num"], format = "%y-%m")

    return omny_grp

## retro code review comment

# function for aggregating different combinations of timegroup datasets
def timegrps(statboothzip_omny, rider_2019, tourdictvalues: list, grparraykey: str):

    outdf = pd.DataFrame()

    # create one big dataframe of all aggregated timegroup combinations
    for i in range(len(tourdictvalues) + 1):

        for subset in itertools.combinations(tourdictvalues, i):

            if len(subset) > 1 and len(subset) < len(tourdictvalues):

                subset = list(subset)
                subset.sort()

                # print(subset)

                aggdf = rider_grp(
                    omnydf=statboothzip_omny, riderdf=rider_2019, grparraykey=grparraykey, timefilt=subset
                )

                timestring = "".join(subset)

                # print(timestring)

                aggdf["Time-group"] = timestring

                outdf = pd.concat([outdf, aggdf], ignore_index=True)

    return outdf

## retro code review comment
# identify unique zip codes or stations or bus routes based on a selected value
@st.experimental_memo()
def uniqueids(basedf, idname):

    valget = {"Zip code": "ZIPCODE", "Station": "statline", "Bus": "ROUTE", "Route": "ROUTE"}[idname]

    vals = basedf[valget].unique()

    ## retro code review comment
    vals.sort()

    return vals


@st.experimental_memo(persist="disk")
def prepdow(dowdf):
    return dowdf.holweekclass.astype("string").unique()

## retro code review comment

@st.experimental_memo(persist="disk")
def unstackdf(df):

    # shape pivoted df as dataframe
    reshapedf = df.stack(0).reset_index()

    # filter out level in dataframe
    colnames = list(filter(lambda x: "level" in x, list(reshapedf.columns)))

    return reshapedf.drop(columns=colnames)


# calculate average ridership 2019
st.experimental_memo()
def prepbaseridership2019(statboothzipdf):

    statboothzipdf["filt2019"] = (statboothzipdf["date_format"] > dt.datetime(2018, 12, 31)) & (
        statboothzipdf["date_format"] < dt.datetime(2020, 1, 1)
    )

    rider_2019 = statboothzipdf.loc[statboothzipdf.filt2019]

    rider_2019["month_year_num"] = rider_2019["month_year_num"].astype("string")

    return rider_2019

## retro code review comment

@st.experimental_memo()
def aggtourzipdata(omnydf, grparray=["month_year_num", "ZIPCODE", "holweekclass"]):

    omnydf["month_year_num"] = omnydf["month_year_num"].astype("str")

    # create 2019 baseline
    omny_grp = omnydf.groupby(grparray, as_index=False, observed=False)[
        "USG", "TRANSFER", "RIDERSHIP", "basetot2019"
    ].agg("sum")

    # recalculate average with new group
    omny_grp["base2019"] = round(omny_grp["basetot2019"] / 6, 2)

    omny_grp["prop_return"] = round(omny_grp["RIDERSHIP"] / omny_grp["base2019"], 2)

    return omny_grp

## retro code review comment

# function for preparing ridership-return data at zip-code level for visualization
# @st.experimental_memo()
def prepselecttour(zipdf, zipdftour, timegrpsdf, _zipshp, tour, multi, mergecol="ZIPCODE"):
    # print(tour)

    if ("All" in tour and len(tour) == 1) | (len(tour) == 5):

        outdf = zipdf

        outdf = outdf[outdf["holweekclass"] == multi]

    elif len(tour) == 1:
        outdf = zipdftour[zipdftour["Time"].isin(tour)]

        # filter dataset to selected day of week
        outdf = outdf[outdf["holweekclass"] == multi]

    elif len(tour) > 1:

        # sort times
        tour.sort()

        # collapse times into string
        tourstr = "".join(tour)

        # timegroup column in timegrps df is all joined sorted time-combinations
        base = timegrpsdf.loc[timegrpsdf["Time-group"] == tourstr]

        # filter dataset to selected day of week
        outdf = base[base["holweekclass"] == multi]

    outdf = _zipshp.merge(
        outdf,
        how="inner",
        on=mergecol,
        # validate="one_to_many"
    ).set_index(keys=mergecol)

    outdf = outdf.rename(
        columns={
            "prop_return": "Proportion 2019 ridership",
            "monthdailyavg": "Average riders on day",
            "base2019mean": "2019 average-daily riders",
        }
    )

    # rename if dealing with stat column
    if "POPULATION" in list(outdf.columns):
        outdf = outdf.rename(columns={"POPULATION": "Zip Population"})

    # sort by prop return - so categorized correctly
    outdf = outdf.sort_values("Proportion 2019 ridership")

    # generate buckets for colors
    outdf["Proportion 2019"] = pd.qcut(outdf["Proportion 2019 ridership"], q=5)

    return outdf


# merges recent data at zip code level to zip shapefile
@st.experimental_memo()
def zipgeom_merge(_zipshp, ziprecent):

    zipshp_geom_all = _zipshp.merge(ziprecent, how="left", on="ZIPCODE").set_index("ZIPCODE")

    zipshp_geom_all = zipshp_geom_all.rename(
        columns={
            "percent_use": "Percent OMNY",
            "RIDERSHIP": "OMNY Ridership",
            "totusg": "Total Ridership",
            "POPULATION": "Zip Population",
        }
    )

    return zipshp_geom_all

## retro code review comment

def validkey(idname):
    valid = {"Zip code": "ZIPCODE", "Station": "statline", "Route": "ROUTE", "Bus": "ROUTE"}[idname]

    return valid
## retro code review comment


# filter dataset to given set of zip codes or stations for given weekday
# @st.experimental_memo()
def filtdata_monthhol(idname, monthdf, filtvals, filthold):

    vkey = validkey(idname)

    filtmonth = monthdf.loc[(monthdf[vkey].isin(filtvals)) & (monthdf.holweekclass == filthold)]

    return filtmonth
## retro code review comment


# create line chart of filtered zip or station data
# @st.experimental_memo()
def filtlinechart_gen(idname: str, filtmonth: pd.DataFrame, routedomain : list | tuple = None):

    # convert to datetime for alignment with other charts
    # filtmonth["month_year_num"] = pd.to_datetime(filtmonth["month_year_num"], format = "%y-%m")

    # formatting of dates in tooltip problematic - last day of previous month by default - so add 1 to fix
    filtmonth["month_year_date"] = filtmonth.month_year_date + dt.timedelta(days = 1)

    filtmonth = filtmonth.rename(
        columns={
            "monthdailyavg": "Average Ridership",
            "prop_return": "Proportion 2019",
            "chng_prop_return": "Proportion change since last month",
            "chng_monthdailyavg": "Change in average-riders since last month",
            "base2019mean": "2019 Baseline",
            "month_year_date": "Month/year",
            "ROUTE" : "Route",
            "ZIPCODE" : "Zip code",
            "statline": "Station"
        }
    ).sort_values("month_year_num")

    toollist = [
        idname,
        "Proportion 2019",
        "Average Ridership",
        "Proportion change since last month",
        "Change in average-riders since last month",
        "2019 Baseline",
    ]

    toollist = [tooltip_generate(toolitem) for toolitem in toollist]

    # proper ordering of ROUTE TYPE then specific routes in graph where both displayed
    if routedomain is not None:
        sort = list(routedomain) + list(filtmonth["Route"].unique())

    else:
        sort = filtmonth[idname].unique()
    

    multiline_statzip = (
        alt.Chart(
            filtmonth,
            height=500,
            #    width = 500,
            title="Return to ridership",
        )
        .mark_line(point=True, size=3)
        .encode(
            alt.X("Month/year", title="Month/year", axis=alt.Axis(format="%b %y")),
            alt.Y("Proportion 2019", title="Proportion of 2019-average"),
            tooltip=toollist,
            color=alt.Color(idname, sort = sort)
        )
    )

    return chartconfig(multiline_statzip)

## retro code review comment

# generate map of riders by zip-code compared to 2019
# st.experimental_memo()
def mapzip_riders(_zipgeodf: gp.GeoDataFrame):

    _zipgeodf = _zipgeodf.rename(columns={"Proportion 2019": "Proportion 2019 bin"})
    # generate styles for values
    hover_cols = ["ZIPCODE", "Proportion 2019 ridership", "2019 average-daily riders", "Zip Population"]

    hoverformat = maphoverformat(_geodf=_zipgeodf, hovercols=hover_cols)

    chlomap = px.choropleth_mapbox(
        data_frame=_zipgeodf,
        geojson=_zipgeodf.geometry,
        locations=_zipgeodf.index,
        color=_zipgeodf["Proportion 2019 bin"],
        color_discrete_sequence=["#d73027", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850"],
        # range_color= maxrange,
        zoom=9,
        mapbox_style="carto-positron",
        center={"lat": 40.724965, "lon": -73.972398},
        opacity=0.5,
        custom_data=hoverformat["customdata"],
    )

    chlomap.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    chlomap.update_traces(hovertemplate=hoverformat["hovertemplate"])

    return chlomap

## retro code review comment

# map station geometries as scatter map
def mapzip_station(_zipgeodf: gp.GeoDataFrame):

    # generate tooltip
    _zipgeodf = _zipgeodf.rename(columns={"Proportion 2019": "Proportion 2019 bin"})
    # generate styles for values
    hover_cols = [
        "Stop Name",
        "Line",
        "Proportion 2019 ridership",
        # "Monthly riders",
        "2019 average-daily riders",
    ]

    hoverformat = maphoverformat(_geodf=_zipgeodf, hovercols=hover_cols)

    scatmap = px.scatter_mapbox(
        data_frame=_zipgeodf,
        lat=_zipgeodf.geometry.y,
        lon=_zipgeodf.geometry.x,
        color=_zipgeodf["Proportion 2019 bin"],
        color_discrete_sequence=["#d73027", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850"],
        zoom=9,
        mapbox_style="carto-positron",
        center={"lat": 40.724965, "lon": -73.972398},
        opacity=0.5,
        custom_data=hoverformat["customdata"],
    )

    scatmap.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    scatmap.update_traces(marker={"size": 10}, hovertemplate=hoverformat["hovertemplate"])

    return scatmap

## retro code review comment

# generates set of text values to plug into standard sentence; accepts dataframe with each row df/time combo, filtered to some threshold (ridership above 1, ridership below 0.5). returns dict of values to pull into sentences
def textgen_ridership_tour(df_filtered: pd.DataFrame, tourvals_list: list or tuple) -> dict:

    displayzip_count = df_filtered.groupby(by="Time", axis=0)["Time"].agg(func="count")

    displayzip_count = displayzip_count.sort_values(ascending=False)

    maxdisplayzipcount = max(displayzip_count)

    displayzip_count_index = list(displayzip_count.index)

    maxlist = commafy(displayzip_count[displayzip_count == maxdisplayzipcount].index)

    if len(displayzip_count) < len(tourvals_list):

        mindisplayzipcount = 0

        mindisplayzip_id = tourvals_list[tourvals_list not in displayzip_count_index]

    else:

        mindisplayzipcount = min(displayzip_count)

        mindisplayzip_id = commafy(displayzip_count[displayzip_count == mindisplayzipcount].index)

    return {
        "maxlist": maxlist,
        "maxnum": maxdisplayzipcount,
        "minlist": mindisplayzip_id,
        "minnum": mindisplayzipcount,
    }

## retro code review comment

# transform data
st.experimental_memo()


def add_dow_tour():
    data = mdl.load_data("omb_bus_agg.parquet")  # change it to load bus data
    # add day of week and time columns
    data["R_DATE"] = pd.to_datetime(data["R_DATE"], format="%Y-%m-%d")
    data["dow"] = data["R_DATE"].dt.day_of_week
    days = {0: "Mon", 1: "Tues", 2: "Weds", 3: "Thurs", 4: "Fri", 5: "Sat", 6: "Sun"}
    data["dow"] = data["dow"].apply(lambda x: days[x])

    # tourdict = {1: "12am-6am", 2: "6am-9am", 3: "9am-4pm", 4: "4pm-7pm", 5: "7pm-12am"}
    # # tour categorical
    # data["TOUR"] = data["TOUR"].astype("category")
    # data["Time"] = data.apply(lambda x: tourdict[x["TOUR"]], axis=1).astype("category")
    # hold on tour data yet
    return data


@st.experimental_memo
def textgen_ridership_chart(filttextdf: pd.DataFrame, month_lookup: pd.DataFrame, zipstatcol: str) -> dict:

    last3mon = list(month_lookup["month_year_num"][-3:])

    last3monthdf = filttextdf.loc[filttextdf["month_year_num"].isin(last3mon)]

    last3monchng = int(last3monthdf.chng_monthdailyavg.mean())

    incdec3month = "increased" if last3monchng > 0 else "decreased"

    initprop = round(last3monthdf.loc[last3monthdf["month_year_num"] == last3mon[0]]["prop_return"].mean(), 2)

    endprop = round(last3monthdf.loc[last3monthdf["month_year_num"] == last3mon[2]]["prop_return"].mean(), 2)

    last1monthdf = filttextdf.loc[filttextdf["month_year_num"] == last3mon[-1]]

    last1monchng = int(last1monthdf.chng_monthdailyavg.mean())

    # sort by percentile - pull zip codes and values
    last1monthdf = last1monthdf.sort_values(by="pctile_return", axis=0, ascending=False)

    commasep_selectfilt = commafy(last1monthdf[zipstatcol])

    pctilevals = commafy(round(last1monthdf.pctile_return, 1))

    outdict = {
        "text_incdec3month": incdec3month,
        "last3monchng": last3monchng,
        "initprop": initprop,
        "endprop": endprop,
        "last1monchng": last1monchng,
        "zipstatlist": commasep_selectfilt,
        "pctilevals": pctilevals,
    }

    if any(last1monthdf.chng_prop_return > 0) & any(last1monthdf.chng_prop_return < 0):

        zip_below_zero = commafy(last1monthdf.loc[last1monthdf.chng_prop_return < 0][zipstatcol])

        zip_above_zero = commafy(last1monthdf.loc[last1monthdf.chng_prop_return > 0][zipstatcol])

        outdict["zip_below_zero"] = zip_below_zero
        outdict["zip_above_zero"] = zip_above_zero

    return outdict

def colcheck(df):

    collist = [col.casefold() for col in df.columns]

    if ("year" in collist) | ("month" in collist):
        st.markdown("**Issue**: Column called month or year present in dataset. There should just be one column called date. Remove redundant month and year column, and put date instead.")
        # st.markdown("")

def datecheck(drcol: pd.Series, freq : 'D | MS' = "D"):

    if type(drcol.iloc[0]) == str:
        st.write("**Issue**: Date column formatted as string (should be formatted as date)")

        drcol = pd.to_datetime(drcol)

    min = drcol.min()
    max = drcol.max()

    infreq = "daily"

    if freq == "MS":
        
        max = max.replace(day =1)
        min = min.replace(day = 1)

        infreq = "monthly"

    # st.write(min)
    # st.write(max)
    # st.write(freq)

    dr_compare = pd.Series(pd.date_range(
        start=min,
        end=max,
        freq = freq
    ))


    # st.write(dr_compare)

    # st.write(len(drcol))
    # st.write(len(dr_compare))

    missing_dates = dr_compare.loc[~dr_compare.isin(drcol)]

    passcheck = True

    if len(missing_dates) > 0:

        passcheck = False

        st.markdown(f"**Warning**: Based on this dataset's interval-frequency ({infreq}), there appear to be missing dates in the dataset")
        
        with st.expander("View and download missing dates"):

            st.write(missing_dates)

            st.download_button(
                "Download missing dates",
                missing_dates.to_csv(encoding = 'utf-8'),
                "missdates.csv"
            )

    if freq == "MS":

        day = drcol.dt.day != 1

        if any(day):

            passcheck = False

            filtday = drcol.loc[day]

            st.write("**Issue**: Dataset is supposed to be monthly, but some date days are not equal to 1 (in a monthly dataset, all days in date fields should be equal to 1)")

            with st.expander("See dates with days not equal to 1"):

                st.write(filtday)

                st.download_button(
                    "Download dates with non-equal days",
                    filtday.to_csv(encoding='utf-8'),
                    "filtdays.csv"
                )
    
    if passcheck:

        st.write("Date check passed!")

    return drcol

def fixed_range(df : pd.DataFrame, dfcolnum : str, min_val : 'int | float | None' = None, max_val : 'int | float | None' = None) -> None:

    maxstring, minstring = ["", ""]

    if min_val is not None:
        # st.write(dfcolnum)

        df_loc = df.loc[df[dfcolnum] < min_val]

        missrows = len(df_loc)

        minstring = f"in {missrows:,.0f} rows, column `{dfcolnum}` goes below minimum expected value, {min_val}" if missrows > 0 else minstring

    if max_val is not None:

        df_loc = df.loc[df[dfcolnum] > max_val]

        missrows = len(df_loc)
    
        maxstring = f"in {missrows:,.0f} rows, column `{dfcolnum}` goes above maximum expected value, {max_val}" if df[dfcolnum].max() > max_val else maxstring

    issstart = "**Issue**: "

    if (minstring != "") | (maxstring != ""):

        st.markdown(
            f"{issstart}{minstring}; {maxstring}.".replace("; .", "").replace(": ;", ": ")
        )

        df = df.loc[(df[dfcolnum] < min_val) | (df[dfcolnum] > max_val)]

        with st.expander(f"See information on unexpected values in column `{dfcolnum}`"):

            st.dataframe(df, use_container_width=True)

            st.download_button(
                f"Download data with outlier values in {dfcolnum}",
                df.to_csv(encoding = 'utf-8'),
                "outliers.csv"
            )

    else:
        st.write(f"Range check passed for `{dfcolnum}`!")


def hourcheck(df: pd.DataFrame, dfcolnum : str):

    fixed_range(df, dfcolnum=dfcolnum, min_val = 0, max_val= 23)

def fixed_categories(df : pd.DataFrame, colname : str, catlist : 'list | False'):

    if type(catlist) == str:
        catlist = [catlist]

    unique_vals = df[colname].unique().tolist()

    if catlist == False:

        st.write(f"**Issue**: Metadata does not define expected categories for column `{colname}`. Unique values in this field are: `{unique_vals}`")

    else:
        unexp = [cat for cat in unique_vals if cat not in catlist]

        if len(unexp) > 0:

            df_miscat = df[colname].loc[df[colname].isin(unexp)]

            st.markdown(f"**Issue**: In {len(df_miscat):,.0f} rows, categories are present in dataframe column `{colname}` outside of expected values. Expected values from open data portal are: `{catlist}`. Values other than those in dataset are: `{unexp}`")

            with st.expander(f"View and download unexpected {colname} rows"):

                df = df.loc[~df[colname].isin(catlist)]

                st.dataframe(df,use_container_width=True)

                st.button(
                    "Download data on unexpected values",
                    df.to_csv(encoding='utf-8'),
                    "unexpected.csv"
                )

        else:
            st.write(f"Category check passed for `{colname}`!")

def num_outliers(df, numcols = None, numstan : int = 3):

    numcols_indf = df.select_dtypes(include = 'number').columns.tolist()

    if numcols is None:
        numcols = numcols_indf

    else:

        notnum = [col for col in numcols if col not in numcols_indf]

        if len(notnum):
                
            st.markdown(f"**Issue**: some columns that should be numeric are coded as plain text: `{notnum}`.")
            
            df[numcols] = df[numcols].apply(pd.to_numeric, errors='coerce')

    for col in numcols:

        # Q1 = df[col].quantile(0.25)
        # Q3 = df[col].quantile(0.75)
        # IQR = Q3 - Q1

        # lower_bound = Q1 - 1.5 * IQR
        # upper_bound = Q3 + 1.5 * IQR

        mean = df[col].mean()
        std = df[col].std()
        lower_bound = mean - numstan * std
        upper_bound = mean + numstan * std

        outliers = df.loc[(df[col] < lower_bound) | (df[col] > upper_bound)]

        outs = len(outliers)

        if outs:
            
            st.markdown(f"**Warning**: {outs:,.0f} outlier values identified in column `{col}`. The mean is {mean:,.2f}, and the standard deviation is {std:,.2f}. Values are outliers if they are outside {numstan} standard deviations of the mean ({lower_bound:,.2f}, {upper_bound:,.2f})")

            with st.expander(f"View outlier values in column {col}"):
                st.dataframe(outliers)

                st.download_button(
                    f"Download outliers for column {col}",
                    outliers.to_csv(encoding = 'utf-8'),
                    "outliers.csv"
                )
        
        else:
            st.write(f"Outlier check passed for column `{col}`!")

    # so that other functions can still test the numeric values
    return df

def misscheck(df, nomiss = None):

    nomiss = df.columns.tolist() if nomiss == None else nomiss

    df = df[df[nomiss].isnull().any(axis = 1)]

    if len(df):

        missing_values = df[nomiss].isnull().sum()
        missing_values = missing_values.to_frame().T
        missing_values.index = ["Number of missing values"]

        st.markdown(f"**Warning**: Missing values present in dataset in columns where missing values not expected: *{'; '.join(missing_values.columns.tolist())}*. See number of missing values below")

        st.dataframe(missing_values)

        with st.expander("See rows with missing values"):
            
            st.dataframe(df)

            st.download_button("Download rows with missing values",
                               df.to_csv(encoding = 'utf-8'),
                               "missing.csv")

    else:
        st.write("Missing check passed!")

def pct_derived(df : pd.DataFrame, colnum : str, coldenom : str, colpct : str):

    df[f"derived_{colpct}"] = df[colnum] / df[colnum]

    df["Difference"] = df[f"derived_{colpct}"] - df[colpct]

    check = df["Difference"] > 0.1

    df_loc = df.loc[check]

    if df_loc.empty:
        st.write(f"Derived check passed! `{colpct}` is equal to `{colnum}` divided by `{coldenom}`")

    else:
        df_loc["Difference"] = df_loc[f"derived_{colpct}"] - df_loc[colpct]

        st.write(f"**Issue**: There are {len(df_loc):,.0f} rows where `{colpct}` is not equal to `{colnum}` divided by `{coldenom}`")

        with st.expander(f"View rows where {colpct} is not equal to {colnum} divided by {coldenom}"):

            st.write(df_loc)

            st.download_button(
                "Download data",
                df_loc.to_csv(encoding='utf-8'),
                f"notequal_{colpct}.csv"
            )


def total_derived(df: pd.DataFrame, colparts : list | tuple, coltot: str):
    df[f"derived_{coltot}"] = df[colparts].apply(sum, axis = 1)

    df["Difference"] = df[f"derived_{coltot}"] - df[coltot]

    check = df["Difference"] > 0.1

    df_loc = df.loc[check]

    if df_loc.empty:
        st.write(f"Derived check passed! `{coltot}` is equal to the sum of `{colparts}`")

    else:

        st.write(f"**Issue**: There are {len(df_loc):,.0f} rows where `{coltot}` is not equal to the sum of `{colparts}`")

        with st.expander(f"View rows where {coltot} is not equal to the sum of {colparts}"):

            st.write(df_loc)

            st.download_button(
                "Download data",
                df_loc.to_csv(encoding='utf-8'),
                f"notequal_{coltot}.csv"
            )

def product_derived(df : pd.DataFrame, colp1 : str, colp2 : str, colresult : str, type = 'float'):

    df[f"derived_{colresult}"] = pd.to_numeric(df[colp1] * df[colp2], downcast=type, errors='coerce')

    df["Difference"] = df[f"derived_{colresult}"] - df[colresult]

    check = df["Difference"] > 0.1

    df_loc = df.loc[check]

    if df_loc.empty:
        st.write(f"Derived check passed! `{colresult}` is equal to `{colp1}` times `{colp2}`")

    else:

        st.write(f"**Issue**: There are {len(df_loc):,.0f} rows where `{colresult}` is not equal to `{colp1}` times `{colp2}`")

        with st.expander(f"View rows where {colresult} is not equal to {colp1} times {colp2}"):

            st.write(df_loc)

            st.download_button(
                "Download data",
                df_loc.to_csv(encoding='utf-8'),
                f"notequal_{colresult}.csv"
            )

def component_check(df, coltot, colcomps : list | tuple):

    colcomps = [colcomps] if type(colcomps) == str else colcomps

    for col in colcomps:

        df = df.loc[df[col] > df[coltot]]

        if len(df) > 0:
            st.write(f"In {len(df):,.0f} rows, a total column--`{coltot}`--is less than one of its parts, `{col}`")

            with st.expander(
                f"View and download data where {col} exceeds {coltot}"
            ):

                st.dataframe(df)

                st.download_button("Download data?",
                                   df.to_csv(encoding='utf-8'),
                                   f"comp_{col}.csv")

        else:
            st.write(f"Component check passed for column `{col}`!")


@st.experimental_memo()
def cacheread(url):
    return pd.read_csv(
        url
    )

