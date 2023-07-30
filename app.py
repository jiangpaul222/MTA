import streamlit as st

st.set_page_config(layout="wide")

import threading

import src.pages.front_page as front_page
import src.pages.air_quality as air_quality
import src.pages.monthly_averages as monthly_averages
import src.pages.pickups_dropoffs as pickups_dropoffs

import ag_grid_hack

import base64
import json

## retro code review comment

PAGES = {
    "Central Business District Tolling Program": {
        "NYC Air Quality": air_quality,
        "TLC Monthly Averages": monthly_averages,
        "TLC Pickups and Dropoffs": pickups_dropoffs
    }
}

## retro code review comment

def set_session_state(page_session_key, parent_selection, child_selection):
    st.session_state[page_session_key] = {"parent_selection": parent_selection, "child_selection": child_selection}

## retro code review comment

def main() -> None:
    """Main function of the App"""
    # render_svg_example()

    ag_grid_hack.inject_css()

    st.markdown(
        """ <style>
        .css-18e3th9 {{
                padding-top: 0rem;
                padding-right: -1rem;
                padding-left: 1rem;
                padding-bottom: 0rem;
                width: 10rem;
            }}
        .css-12oz5g7 {{
            padding-top: 0rem;
            padding-right: -1rem;
            padding-left: 1rem;
            padding-bottom: 0rem;
            max-width: 80%;
        }}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
         </style> """,
        unsafe_allow_html=True,
    )
## retro code review comment

    # Initialize session state:
    page_session_key = "page_selected"
    if page_session_key not in st.session_state:
        st.session_state[page_session_key] = None

    # Multi hierarchy sidebar:
    with st.sidebar:
        parents = [k for k in PAGES.keys()]
        parent_selection = None
        child_selection = None
        expanders = {}
        for parent in parents:
            expanders[parent] = st.expander(parent, expanded=False)
            for page in PAGES[parent].keys():
                with expanders[parent]:
                    blank, button_col = st.columns((0.05, 0.95))
                    with button_col:
                        st.button(
                            page,
                            key=f"{parent}${page}",
                            on_click=set_session_state,
                            args=(page_session_key, parent, page),
                        )
## retro code review comment

    # Call page
    if st.session_state[page_session_key]:
        parent_selection = st.session_state[page_session_key]["parent_selection"]
        child_selection = st.session_state[page_session_key]["child_selection"]
        PAGES[parent_selection][child_selection].app()
        # report statistics
        # count_pageview(f"{parent_selection}: {child_selection}")
    else:
        front_page.app()


if __name__ == "__main__":
    # # Load CSS
    # with open(".streamlit/style") as css:
    #     st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    # Run app
    main()
