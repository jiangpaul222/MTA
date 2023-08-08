# MTA CBDTP Visuals

## About the Project

Repo to create a website visualizing performance data for the MTA's Central Business District Tolling Program. This is not representative of the MTA's final website as I am only responsible a small section of the data, which includes public information gathered from the Taxi & Limousine Commission and the New York State Department of Health.

## Description

The website is run using the [streamlit module](https://docs.streamlit.io/), and the app.py file creates the architecture of the website. Individual webpages displayed on the website are stored in the src/pages/ directory. They use CSS in the src/assets.py file and ag_grid_hack.py file, and use functions in the src/tools.py file.

TLC data is currently updated monthly and DOH data is updated annually. The basic workflow to update the website is to 1) automatically pull the data to the CBDTP's container in MTA's Azure Blob Storage account, and 2) run each of the src/dataprocessing scripts, which aggregate the base data and upload aggregated datasets to the container. We do this to improve website performance. To see the website locally, run `streamlit run app.py` in your termminal.

## Contributing

See [CONTRIBUTING.MD](/CONTRIBUTING.MD).

## Project Organization

```
------------

  |--- MTA CBDTP Visuals           <- The top-level directory for this project: https://github.com/jiangpaul222/MTA.
    |--- data
    |     |--- processed              <- Processed datasets (lookup files)
    |     |--- source                 <- Directory storing utility scripts, and scripts appearing on the external website. May have some redundancy with Orca reports
    |
    |
    |--- src                          <- Directory storing data-processing and pages directories, as well as a tools.py script with common functions and an assets.py file
    |     |--- dataprocessing         <- Scripts to aggregate raw data and push it to the S3 bucket. The internal website runs slower with bigger datasets, so this helps speed things up
    |     |--- pages                  <- Scripts for webpages on the internal website

  
```
