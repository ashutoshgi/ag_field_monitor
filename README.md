# ag_field_monitor
Web based toolbox for monitoring agricultural fields using satellite remote sensing datasets
# Web application for real time agricultural field monitoring using satellite remote sensing datasets

A cross-platform Flask-based web application to analyze satellite-derived vegetation indices (NDVI, SAVI, NDWI) and radar-based RVI using Google Earth Engine. Designed for agricultural monitoring under the MMRV (Multi-Mission Remote Vegetation) framework.

## Usage

- Upload `.geojson`, `.kml`, or `.kmz` files to define your Area of Interest (AOI)
- Compare satellite-derived indices (NDVI, RVI, SAVI, NDWI) over two date ranges
- Interactive map tile visualization using Earth Engine + geemap
- Works on **Linux**, **Windows**, and **macOS**

# Requirements

- Python 3.8 or above
- [Google Earth Engine account](https://signup.earthengine.google.com/)
- Internet access (for Earth Engine API)

## Installation Instructions

### Linux / macOS

```bash
# 1. Clone the repository
git clone https://github.com/ashutoshgi/ag_field_monitor.git
cd ag_field_monitor

# 2. Create and activate virtual environment

# 3. Install dependencies
pip install -r requirements.txt
```

# Windows

Open Windows command line and do the following:

1. Clone the repository
git clone https://github.com/ashutoshgi/ag_field_monitor.git
cd ag_field_monitor

2. Create and activate virtual environment


3. Install dependencies
pip install -r requirements.txt
```

#Earth Engine Authentication

Before running the app for the first time, the app requires Google Earth Engine account authentication. 

Once authenticated, run python app.py in terminal, and the app will be running in localhost.


# Acknowledgements

Please cite the following if using the application:

Ashutosh Tiwari, Jaclyn Tech, Jacob Bailey, Reshmi Sarkar, Sk Musfiq Us Salehin, Mahendra Bhandari, Gurjindar Baath, Nithya Rajan, Raghavan Srinivasan, 2025. A web based toolbox for real time monitoring of agricultural crop fields. 

