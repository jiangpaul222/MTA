import streamlit as st

## retro code review comment

def create_header(title: str):
    return st.markdown(
        f"""
        <link rel="stylesheet" type="text/css" href="http://dashboard.mta.info/default.css">
        <link rel="stylesheet" type="text/css" href="http://dashboard.mta.info/app.css">
        <nav id="subway-nav-container" class="navbar">
            <div class="container-fluid">
                <div id="navbar-header-container" class="pull-left navbar-title">
                    <span class="navbar-brand" id="dashboard-title">{title}</span>
                </div>
            </div>
        </nav>
        """,
        unsafe_allow_html=True,
    )

## retro code review comment


def create_footer():
    return st.markdown(
        """
        <nav id="footer-nav-container" class="navbar">
            <!-- <div class="container-fluid"> -->
                <div id="navbar-footer-container">
                    <a id="footer-mta-website-link" href="http://www.mta.info">mta.info</a>
                    <span>|</span>
                    <a id="footer-pers-dashboard-link" href="https://new.mta.info/transparency/metrics">MTA Dashboards</a>
                </div>
            <!-- </div> -->
            </nav>
        """,
        unsafe_allow_html=True,
    )

