# MTA CBDTP Visuals

## About the Project

Repo to create an internal website visualizing performance data for staff in Departments across MTA. There is both a [live website](https://gitlab.mtacp.info/mta-data-analytics/mta-internal-visuals) off the `main` branch and a [testing site](https://internal-dev.metrics.mta.info/) off the `develop` branch. Documentation for the project and code-review assignments can be found on the [project's associated sharepoint](https://nymta.sharepoint.com/sites/NYCTStrategicInitiatives/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FNYCTStrategicInitiatives%2FShared%20Documents%2FCurrent%20Projects%2FInternal%20Metrics&viewid=2dc0edae%2D9080%2D4295%2D9b06%2D5304c608f122).

## Description

The website is run using the [streamlit module](https://docs.streamlit.io/), and the app.py file creates the architecture of the website. Individual webpages displayed on the website are stored in the src/pages/ directory. They use CSS in the src/assets.py file and ag_grid_hack.py file, use data-loading functions in the minio_data_loader.py file, and use functions in the src/tools.py file.

OMB data is currently updated monthly. The basic workflow to update the website is to 1) upload the base-OMB data to the project's S3 bucket, and 2) run each of the src/dataprocessing scripts, which aggregate the base data and upload aggregated datasets to the S3 bucket. We do this to improve website performance. To see the website locally, run `streamlit run app.py` in your termminal.

This website will draws in webpages from the [Orca reports](https://gitlab.mtacp.info/mta-data-analytics/reporting-and-dashboards/orca-reports) repository as a [git subrepo](https://github.com/ingydotnet/git-subrepo#readme). We will use this structure to allow work on Orca reports to proceed mostly independently of work on this project, since not all transitioned Orca reports will become webpages on the internal site. As a subrepo, the Orca reports repository will be copied into this repository as a subdirectory. Once it's setup, you can pull updates in the Orca reports repository into this subdirectory; commits in that repository are squashed into one. You can also push from this repository to update the Orca reports repository. See the git-subrepo documentation for more information.

## Contributing

See [CONTRIBUTING.MD](/CONTRIBUTING.MD).

## Project Organization

The project organization below includes the [ORCA reports repo](https://gitlab.mtacp.info/mta-data-analytics/reporting-and-dashboards/orca-reports/) as a subrepo or subtree of this repo. As a subrepo or subtree, the ORCA reports repo will exist as a subidrectory of this repo, so webpages created in the ORCA repo can be directly folded into the internal website. We have not yet added the ORCA reports repo as a subtree, so the Orca reports repo is currently omitted from this repo.

```
------------

  |--- MTA Internal Visuals           <- The top-level directory for this project: https://gitlab.mtacp.info/mta-data-analytics/mta-internal-visuals. Orca reports is a subcomponent of MTA Internal Visuals
    |--- data
    |     |--- processed              <- Processed datasets (lookup files)
    |     |--- source                 <- Directory storing utility scripts, and scripts appearing on the external website. May have some redundancy with Orca reports
    |
    |
    |--- src                          <- Directory storing data-processing and pages directories, as well as a tools.py script with common functions and an assets.py file
    |     |--- dataprocessing         <- Scripts to aggregate raw data and push it to the S3 bucket. The internal website runs slower with bigger datasets, so this helps speed things up
    |     |--- pages                  <- Scripts for webpages on the internal website
    |
    |---Orca Reports                  <- Subrepo for Orca migration project
    |     |--- Replacement Dashboards <- Directory for scripts transitioning Orca reports that are not worth including on the internal website
    |     |--- Reports                <- Reports built in Orca
    |     |--- Resources              <- Resources for reports built in Orca
    |     |--- src                    <- Directory storing data-processing and pages directories, as well as a tools.py script with common functions and an assets.py file. May have some redundancy with MTA internal visuals files. 
    |     |     |- dataprocessing     <- Scripts to process raw data from s3 bucket, turn it into aggregated datasets, and push it back to the S3 bucket. 
    |     |     |- pages              <- Scripts for Orca reports that will be transitioned to webpages on the internal website. Structured to be run by the app.py script in the MTA Internal Visuals base-directory
    |     |--- assets                 <- Orca images, presumably used in reports built in Orca

  
```
