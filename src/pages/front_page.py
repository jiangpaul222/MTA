import streamlit as st
import src.assets

## retro code review comment

def app():
    src.assets.create_header("""MTA Internal Metrics""")
    st.write("""This page features ridership metrics for internal use only. """)
    st.write(
        """Landing page to come."""
    )

