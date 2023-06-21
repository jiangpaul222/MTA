# Developer's Guide

This document serves as a brief guide for developing in the code base. As you work, keep in mind [team guidance for code review](https://nymta.sharepoint.com/sites/NYCTStrategicInitiatives/Shared%20Documents/Forms/AllItems.aspx?newTargetListUrl=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents&viewpath=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FForms%2FAllItems%2Easpx&id=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FResources%2FCode%20Review%20Standards&viewid=2dc0edae%2D9080%2D4295%2D9b06%2D5304c608f122), and [guidance for using Git](https://nymta.sharepoint.com/:p:/r/sites/NYCTStrategicInitiatives/_layouts/15/doc2.aspx?sourcedoc=%7BDC05633B-7E84-4E0B-8032-3534A946B513%7D&file=Introduction%20to%20Git.pptx&action=edit&mobileredirect=true&PreviousSessionID=53080aa1-f862-e722-054d-bb1d1d7b584d&cid=23a11d79-8e0a-49b2-a9f2-37161a0cc15f) (the (`bus-pi`)[https://gitlab.mtacp.info/mta-data-analytics/service-performance/bus-pi/-/blob/main/CONTRIBUTING.md] contributing page also has some useful explanations of using git if you need additional assistance). The [sharepoint for the project](https://nymta.sharepoint.com/sites/NYCTStrategicInitiatives/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FCurrent%20Projects%2FInternal%20Metrics&viewid=2dc0edae%2D9080%2D4295%2D9b06%2D5304c608f122) has the [code_reviewer_tracker](https://nymta.sharepoint.com/:x:/r/sites/NYCTStrategicInitiatives/_layouts/15/Doc.aspx?sourcedoc=%7BEBA67611-9B3C-47AD-899E-B8AC025F394E%7D&file=code_review_tracker.xlsx&action=default&mobileredirect=true), and other documentation associated with the project.

## Getting Started

To read and write data, this project connects to an AWS S3 bucket. The functions that make this connection are in the `minio_data_loader.py` script. Locally on your computer, this script tries to read in three variables defined in a `local_config.py` script that the `.gitignore` file ignores, and sets two environmental variables that the functions in this script use. To get these scripts to work on your computer, you should create a `local_config.py` file in the top-level directory and enter the following three variables (you should get the secret and access key from a project manager).

```
am_i_local = True
MINIO_SECRET_KEY = 'XXXXXXXXXXXXXX'
MINIO_ACCESS_KEY = 'XXXXXXXXXXXXXX'
```

There are a few scripts and directories that are important to understand for contributing to this project. It's advisable to look at the documentation for the [streamlit module](https://docs.streamlit.io/) as well:

- `src/pages/`: This directory stores all webpages displayed on the website. Each `.py` script is an individual webpage. All of the content shown on the webpage goes inside an `app()` function. To add a new webpage, start by making a new `.py.` script and defining an `app()` function with its contents.

- `app.py`: This file creates the architecture of the website. Webpages are imported from the `src/pages/` directory, and the `PAGES` dict organizes the structure of the website. Currently, it's organized as `{"Sidebar webpage category" : {"Webpage name" : imported_src_pages_file}}`. When you want to include a new webpage, import your webpage and add it as another element to the dict.

- `src/dataprocessing/`: These scripts are used to read in base OMB data from the S3 bucket, aggregate it, and upload aggregated datasets to the S3 bucket. Webpages in `src/pages` read in and visualize the aggregated datasets, not the base datasets. This is because the base datasets are too big and slow down the website. When you're working on a new webpage, for each webpage, add a new `.py` file to the dataprocessing folder with the naming convention `processdata_webpagename.py`. The `webpagename` part of the filename should match the webpage name in the corresponding file in the `src/pages` folder. This script should aggregate the data as much as possible for all visualizations in the webpage, and upload the aggregated datasets to the S3 bucket. 

- `minio_data_loader.py`: Contains scripts for reading in data from the S3 bucket and writing data to the S3 bucket. You should use these scripts to read in and write datasets.

- `src/tools.py`: This script contains functions used throughout the project. As we progress, we will work to A) standardize and consolidate some of these functions (e.g., so that aesthetics are common across visuals) and B) consider breaking it up into subscripts to make the file more manageable. As you work on the project, you should use functions from this script for common visuals, and add common functions to this file. You should be careful about modifying functions in this script (and code-reviewers should be mindful of modifications to existing functions this script), because they are used in other files. When you add functions to this script, you are encouraged to use [typehints](https://docs.python.org/3/library/typing.html) and [docstrings](https://realpython.com/documenting-python-code/#documenting-your-python-code-base-using-docstrings) (or at a minimum, to provide comments describing their purpose) so that others understand the expected behavior of your functions.

- `src/assets.py`: You should import `create_header()` from `src.assets` and use it at the start of your `app()` functions in your webpages.

- `data/`: The base dataset and all aggregated datasets should be loaded to the S3 bucket and not stored locally. In the `src/dataprocessing/zipboothstation_process.py` script, we read in base datasets from `data/source/` of booths, stations, and zip-code geometries; produce lookup files so booths are associated with stations and zip codes; and output those lookup files to `data/processed/`. We use these lookup files in other `src/dataprocessing/` scripts to aggregate data by zip code and station. If you need to add or create your own lookup file, you should follow a similar process. If your lookup file is big, write it to the S3 bucket instead of saving it in the data folder.

When you've finished adding a webpage, run `streamlit run app.py` in your termminal to see a local version of the website.

If you add any new packages, be sure to edit the `requirements.txt` file so that it runs on the website.

## Basic Workflow for Adding a Webpage

1) Create a git branch off of the latest version of the develop branch. Create a gitlab issue for the webpage you're adding.

2) If you've never uploaded a webpage before, create a `local_config.py` file in the top-level `mta-internal-visuals` directory. Its contents follow. Ask a team member for the `MINIO_SECRET_KEY` and `MINIO_ACCESS_KEY`.

```
am_i_local = True
MINIO_SECRET_KEY = 'XXXXX'
MINIO_ACCESS_KEY = 'XXXXX'
```

2) Create a `processing_webpagename.py` script in the `src/dataprocessing/` directory. Import the `minio_data_loader` and use the `load_data` function to read the base dataset from the team's S3 bucket. Aggregate the dataset as much as possible for all visuals that will be displayed on the webpage, and write them to the S3 bucket using the `write_parquet_to_minio` function. If the base dataset hasn't been uploaded to the S3 bucket, read it in locally, and use the `write_parquet_to_minio` function to write the dataset to the AWS S3 bucket.

3) Create a `webpagename.py` file in the `src/pages/` directory (the name should match the second part of the `processing_webpagename.py` file). This should import the `minio_data_loader`, and use the `load_data` function read in aggregated datasets you uploaded in the processing function. Before writing your own visualization and aggregation functions, check the `src/tools.py` script. Add and document any new functions to `src/tools.py`, including decorators as appropriate.

4) Edit the dict at the start of `app.py` to link to the new webpage in the appropriate section. Use `streamlit run app.py` to test the webpage locally, and make sure it runs along with the other webpages.

5) Once the webpage is good to go, rebase and squash all commits into one, rebase against the latest version of the develop branch, and create a merge request into the develop branch, closing the issue associated with the webpage and [assigning the next reviewer in the queue](https://nymta.sharepoint.com/:x:/r/sites/NYCTStrategicInitiatives/_layouts/15/Doc.aspx?sourcedoc=%7BEBA67611-9B3C-47AD-899E-B8AC025F394E%7D&file=code_review_tracker.xlsx&action=default&mobileredirect=true).

## Caching

To improve performance, many functions use streamlit decorators (`@st.cache`)[https://docs.streamlit.io/library/api-reference/performance/st.cache], (`@st.experimental_memo`)[https://docs.streamlit.io/library/api-reference/performance/st.experimental_memo], and (`@st.experimental_singleton`)[https://docs.streamlit.io/library/api-reference/performance/st.experimental_singleton]. These tell streamlit to cache the output of functions the decorators precede, helping improve website performance.

If the script for your webpage performs operations on datasets you load in (e.g., filtering a dataset based on a selector, re-aggregating a dataset based on a selector, re-shaping a dataset for visualization in a datatable), you should consider defining a function for the operations and appending a decorator to it. Generally, you should use `st.experimental_memo` if the output of a function is a dataframe or similar object, and `st.experimental_singleton` if the output of the function is a database session, connection, or similar object. `st.cache` can be used for either type of object, but streamlit documentation currently advises that `st.experimental_memo` and `st.experimental_singleton` achieve better performance. For more information or if you are uncertain, consult the documentation.

Sometimes, you will want to clear your cache (e.g., if you modify a function, if the OMB base-datasets have been updated). Streamlit's caching decorators are supposed to track whether inputs change, but sometimes they can be finnicky. You can try using `st.experimental_memo.clear` to clear the cache of functions decorated with `st.experimental_memo`, and `st.experimental_singleton.clear` to clear the cache of functions decorated with `st.experimental_singleton`. If this doesn't work, try temporarily commenting out the decorator and re-running the script to get the cache to update. You can also try editing your functions to cause the cache to update; for instance, `minio_data_loader.load_data()` has a `today=datetime.date.today()` parameter that will artificially tell streamlit to update each day with the changing `today` input.

## Relative Filepaths

When deployed or running `streamlit run app.py`, streamlit treats file paths relative to the top-level directory (so `src/pages/webpage.py` is treated as `path_on_your_computer/mta-internal-visuals/src/pages/webpage.py`). 

However, the default behavior of VSCode is to treat the top-level directory of relative filepaths as the directory that the script is in. This is not ideal, because it means you are unable to access scripts in other directories without absolute filepaths, which will vary by computer. So if you are in `src/pages/webpage_name.py`, you cannot import `src/tools.py`.

To get around this, you can go to File -> Preferences -> Settings, search for Jupyter: Notebook File Root, and change the value to `${workspaceFolder}`. From then on, all you need to do is to use File -> Open Folder and select the `mta-internal-visuals` folder in VSCode, and it will set it as the working directory for filepaths.

## Git

Per [team standards for code-review](https://nymta.sharepoint.com/sites/NYCTStrategicInitiatives/Shared%20Documents/Forms/AllItems.aspx?newTargetListUrl=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents&viewpath=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FForms%2FAllItems%2Easpx&id=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FResources%2FCode%20Review%20Standards&viewid=2dc0edae%2D9080%2D4295%2D9b06%2D5304c608f122) and [guidance on using Git](https://nymta.sharepoint.com/:p:/r/sites/NYCTStrategicInitiatives/_layouts/15/doc2.aspx?sourcedoc=%7BDC05633B-7E84-4E0B-8032-3534A946B513%7D&file=Introduction%20to%20Git.pptx&action=edit&mobileredirect=true&PreviousSessionID=53080aa1-f862-e722-054d-bb1d1d7b584d&cid=23a11d79-8e0a-49b2-a9f2-37161a0cc15f), branches should be off of the develop branch and should address one gitlab issue. The branch name should describe the issue it's addressing (e.g., omny_usage rather than fred_work). Create an issue if it doesn't exist yet. Before merging into develop, you should rebase against the develop branch and squash your commits into one.

When you make a merge request from your branch into develop, make yourself the assignee, click the "close branch with merge request" box, and assign the [next reviewer in the queue](https://nymta.sharepoint.com/:x:/r/sites/NYCTStrategicInitiatives/_layouts/15/Doc.aspx?sourcedoc=%7BEBA67611-9B3C-47AD-899E-B8AC025F394E%7D&file=code_review_tracker.xlsx&action=default&mobileredirect=true). Don't approve your own merge requests.

## Webpage Format

The standard layout for webpages follows:

    Webpage name

    Question webpage is answering as header: E.g., how has ridership changed since COVID? How has OMNY usage changed over time?

    Brief description of visual or datatable that follows, including any necessary contextual information to understand the visual

    Visuals or datatables, including filters: You should also take advantage of pop-up text capabilities in streamlit and plotly visuals to allow users of the website to see more information when they hover their mouse over graphics

    Button to download data displayed in visuals or datatables

    Insights: Useful information from the visuals or datatables. Think in terms of performance-measurement when describing these, of things that would not be obvious from the visuals, and of what potential users of the data might want to know about. Ideally, these should be programmed so that they automatically update when the data changes (rather than requiring manual updates each month).

    Notes: Methodological or other notes about the data. We will eventually consolidate these into a separate webpage.

You are encouraged to use [streamlit layout and container functions](https://docs.streamlit.io/library/api-reference/layout) to organize information on your webpages, and prevent overcrowding on the page. For instance, `st.columns` may be useful if you have muliple select boxes, to save screenspace. `st.tabs` may be useful to show multiple types of visualizations in one webpage (e.g., a map, chart, and datatable). `st.expander` might be helpful to store multiple filters with default values that engaged users may want access to, but typical users may not (e.g., "Include holidays?" with a default value of false).

## Restricted Access Webpages

Some webpages available on the internal site will be available to all MTA employees, and should follow the standard webpage format. There may be some webpages that are inappropriate for a general audience or would clutter the website to include, and will only be viewable by specific users (e.g., migrated ORCA reports). It is less important that these webpages follow the standard format.

Note: We have not added any restricted-access webpages yet, and will update this section with instructions for how to make a webpage restricted access once we do.