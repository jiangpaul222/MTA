import plotly.express as px
import streamlit as st
import altair as alt
import pandas as pd
from altair.utils.schemapi import Undefined


def px_configure(plot : 'px chart', y_range : list | tuple, tick_marks : int = 5, yformat : str = ",.0f") -> 'px chart':

    y_min, y_max = y_range
    # scale_range = y_max - y_min
    # how far apart each bin
    # mark_bin = scale_range / tick_marks
    
    # tick_values = [y_min + mark_bin * i for i in range(tick_marks + 1)]

    # X-axis ticks
    # x_min = df_monthly['month'].min()
    # x_tick_vals = df_monthly['rank'].unique().tolist()
    # x_ticks_text = df_monthly['f_date'].unique().tolist()
    
    # X-axis design
    plot.update_xaxes(
        showgrid=True,
        showline=True,
        linecolor='#888888',
        tickcolor='#888888',
        gridcolor='#D3D3D5',
        # Time ticks:
        # tickmode='array',
        # tickvals=x_tick_vals,
        # ticktext=x_ticks_text,
        # range=[df_monthly['rank'].min(), df_monthly['rank'].max()],
        # title=f'<b>{y_label}</b>',
        mirror=True
    )
    # st.write(tick_values)

    # for some reason '0' tick not being colored
    rangefloor = y_min - 5 if y_min != 0 else y_min - 0.5

    # Y-axis design
    plot.update_yaxes(
        showgrid=True,
        showline=True,
        linecolor='#888888',
        tickcolor='#888888',
        gridcolor='#D3D3D5',
        # Time ticks:
        range = [rangefloor, y_max + 5],
        # tickmode='array',
        # tickvals=tick_values,
        # ticktext=tick_values,
        # title = "",
        # title_text = f'<b>{y_label}</b>',
        # title= dict(
        #     title_text=f'<b>{y_label}</b>',
        #     # standoff=0
        # ),
        mirror=True,
        title_font=dict(
            size=12,
            family='Helvetica',
            # standoff = 5
        )
    )

    plot.update_layout(
        # Put legend on bottom
        legend=dict(
            yanchor='top',
            xanchor='left',
            orientation='h',
            title = "",
            # font = 8,
            itemwidth = 30,
            itemsizing = 'constant',
            borderwidth = 0,
            tracegroupgap = 0,
            font = dict(size = 12),
            # xanchor = -0.5
            # entrywidth=0.1, # change it to 0.3
            # entrywidthmode='fraction',
            # y=-0.2,
            x = -0.05
        ),
        # title_y = 0.999,
        # title_x = 0.06,
        # Font
        font=dict(
            size=12,
            family='Helvetica'
        ),
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.9)'
        ),
        margin=dict(l=40, r=0, b=0, t=0, pad=0)
    )

    # Tooltip    
    plot.update_traces(
        # customdata=df_monthly[category_field_name],
        hovertemplate = "Date: %{x|%b %Y}<br>Value: %{y:" + yformat +"}<br>Category: %{customdata[0]}"
    )

    # Last configs for layout
    plot.update_layout(
        # Background color
        dict(
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)'
        ),
        # Dimensions
        autosize=True
    )

    return plot


def colordict_plotly(
        cat_list : list | tuple, 
        custscheme : 'list | tuple | None' = None
    ) -> dict | None:
    """Generate a dict of colors for a list of categories to give to a plotly color parameter
    
    params
    - cat_list (list | tuple): list of categories to generate unique colors for using a px.colors palette
    - custscheme (list, None): a custom list of colors to use instead of a prebuilt plotly color scheme. Default None, to use a plotly one
    
    returns:
    - dict with keys of categories, and values of colors. Or None if length of cat_list exceeds length of prebuilt plotly color schemes"""
    
    lencats = len(cat_list)

    if custscheme != None:
        custscheme = custscheme

    elif lencats <= 10:
        pxcolors = px.colors.qualitative.Plotly

    elif lencats <= 12:
        pxcolors = px.colors.qualitative.Set3

    elif lencats <= 26:
        pxcolors = px.colors.qualitative.Alphabet

    else:
        Warning("Length of cat_list exceeds length of prebuilt plotly color schemes")

        return None
    
    return dict(
        zip(
            cat_list,
            pxcolors[:lencats]
        )
    )


def stacked_bar_plotly(df: pd.DataFrame,
                       y_axis: str,
                       category : str,
                       datecol :str = "month",
                       y_title : str = "",
                       colordict : 'dict | None | "generate"' = None
                    #    plot_title : str =""
                       ) -> px.bar:
    
    if len(df) == 0:
        st.write("Your selections produced an empty dataset. Try a different set of selections.")

    else:    

        if colordict == "generate":
            colordict = colordict_plotly(sorted(df.category.unique().tolist()))

        plot = px.bar(
            df,
            x = datecol,
            y = y_axis,
            # title = f"<b><i>{plot_title}</b></i>",
            color = category,
            custom_data=[category],
            color_discrete_map=colordict,
            barmode="stack",
            labels = {datecol : "", y_axis: f"<b>{y_title}</b>"}
        )

        max = df.groupby(datecol, as_index = False).agg(sum)[y_axis].max()
        max = max * 1.1

        y_range = [0, max]

        plot = px_configure(plot, y_range = y_range, tick_marks=5)

        return plot

def st_plotly(chart: 'px Chart') -> None:
    """Print plotly chart to streamlit, with default parameters set for streamlit 1.19

    params:
    - chart: Plotly chart to print to streamlit

    returns:
    - Nothing; plotly chart printed to streamlit with st.altair_chart

    """
    st.plotly_chart(
        chart,
        use_container_width=True,
        theme=None
    )

def create_mean_chart(
        df_monthly: pd.DataFrame,
        title: str,
        domain: list,
        y_axis_scale: list,
        aggSum: bool,
        tick_min_step=Undefined
) -> st.altair_chart:
    """Function to create primary chart for the metric, returning the series on the chart for later use.

    @param df_monthly: Pandas dataframe with one row per month and numerator/denominator columns.
    @param title: The title of the metric, mostly used for the y axis label and tooltips
    @param domain: A list of series, typically ['Monthly', '12-Month Average']
    @param y_axis_scale: Start and end of Y axis range
    @param aggSum: Summing the denominator or not

    Returns:
        st.altair_chart: Prints the altair chart to the streamlit page.

    """

    if len(df_monthly) == 0:
        st.write("Your selections produced an empty dataset. Try changing your selections.")

    else:

        # Scaling buffers
        min_scale = y_axis_scale[0]
        min_scale = min_scale * 0.7 if min_scale > 0 else min_scale
        max_scale = y_axis_scale[1]
        max_scale = max_scale * 1.1
        y_axis_scale = (min_scale, max_scale)

        # Start by aggregating the data and setting up the 12 month average
        df_monthly['month'] = df_monthly['month'] + pd.offsets.Hour(5)
        if aggSum:
            df_sum = df_monthly.groupby(["month"]).agg({"numerator": "sum", "denominator": "sum"})
        else:
            df_sum = df_monthly.groupby(["month"]).agg({"numerator": "sum", "denominator": "first"})
        df_sum.reset_index(inplace=True)
        df_sum["Monthly"] = df_sum.numerator / df_sum.denominator
        df_sum["12-Month Average"] = df_sum.numerator.rolling(12).sum() / df_sum.denominator.rolling(12).sum()
        df_sum.drop(["numerator", "denominator"], axis=1, inplace=True)
        df_sum = df_sum.melt("month", var_name="series", value_name="value")
        df_sum.sort_values(by=["month", "series"], inplace=True)

        if aggSum:
            df_sum["perc_label"] = df_sum["value"].apply(lambda x: f"{x:.0f}")
        else:
            df_sum["perc_label"] = df_sum["value"].apply(lambda x: f"{x:.1f}")
        df_sum["value"] = df_sum["value"].apply(lambda x: f"{x:.2f}")

        # Now create the monthly chart
        df_monthly_sum = df_sum.loc[df_sum.series == "Monthly"]
        range_ = ["#00284D", "#86C4FF"]
        chart_monthly = (
            alt.Chart(df_monthly_sum)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:T", title="", axis=alt.Axis(format="%b %y", tickCount='month')),
                y=alt.Y("value:Q", scale=alt.Scale(domain=y_axis_scale), title=title,
                        axis=alt.Axis(tickMinStep=tick_min_step)
                        ),
                color=alt.Color("series:N", title="Legend", scale=alt.Scale(domain=domain, range=range_)),
                tooltip=[
                    alt.Tooltip("month", title="Month", format='%B'),
                    alt.Tooltip("value:Q", title=title),
                ],
            )
        )

        # If we want a 12-month average, then it's created here
        if "12-Month Average" in domain:
            df_12_month_sum = df_sum.loc[df_sum.series == "12-Month Average"]
            chart_12_month_sum = (
                alt.Chart(df_12_month_sum)
                .mark_line(strokeDash=[5, 5])
                .encode(
                    x=alt.X("month:T", title="", axis=alt.Axis(format="%b %y", tickCount='month')),
                    y=alt.Y("value:Q", scale=alt.Scale(domain=y_axis_scale), title=title, ),
                    color=alt.Color("series:N", title="Legend", scale=alt.Scale(domain=domain, range=range_)),
                )
            )

            output_chart = (
                (chart_12_month_sum + chart_monthly).configure_legend(orient="bottom").properties(background="white")
            )
        else:
            output_chart = (chart_monthly).configure_legend(orient="bottom").properties(background="white")

        return st.altair_chart(output_chart, use_container_width=True, theme=None)

