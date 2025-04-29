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
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

# Windows

```cmd
REM 1. Clone the repository
git clone https://github.com/ashutoshgi/ag_field_monitor.git
cd ag_field_monitor

REM 2. Create and activate virtual environment
python -m venv krishna
krishna\Scripts\activate

REM 3. Install dependencies
pip install -r requirements.txt
```


#Earth Engine Authentication

Before running the app for the first time:

```bash
python app.py
```

If you see:
```
Earth Engine not authenticated. Attempting inline authentication...
```

Follow these steps:
1. A URL will appear — open it in your browser
2. Sign in to your Google Earth Engine account
3. Copy the generated token and paste it into the terminal when prompted

This is a **one-time setup** per machine.

If the browser method fails (e.g., on Windows with firewalls), run in Python:

```python
import ee
ee.Authenticate(auth_mode='notebook')
ee.Initialize()
```

Then rerun `app.py`.


# Acknowledgements

Please cite the following if using the application:

Ashutosh Tiwari, Jaclyn Tech, Jacob Bailey, Reshmi Sarkar, Sk Musfiq Us Salehin, Mahendra Bhandari, Gurjindar Baath, Nithya Rajan, Raghavan Srinivasan, 2025. A web based toolbox for real time monitoring of agricultural crop fields. 

