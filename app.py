# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 12:35:08 2024

@author: ashutosh.tiwari
"""


from flask import Flask, render_template, request, jsonify, send_file
import os
import ee
import geemap
import zipfile
import json

app = Flask(__name__)

import ee


try:
    ee.Initialize()
except Exception as e:
    print("Earth Engine not authenticated. Attempting inline authentication...")
    try:
        ee.Authenticate(auth_mode='notebook')
        ee.Initialize()
        print("Earth Engine authenticated successfully.")
    except Exception as auth_error:
        print("Authentication failed. Please manually run: ee.Authenticate(auth_mode='notebook')")
        exit(1)


# Upload folder configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variable to store AOI from file upload
file_aoi = None

# Function to compute statistics for a collection
def compute_statistics(image_collection, aoi):
    stats = image_collection.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.stdDev(),
            sharedInputs=True
        ),
        geometry=aoi,
        scale=10,
        maxPixels=1e13
    )
    return stats.getInfo()

# Function to generate tiles for the map
def generate_tiles(image, vis_params):
    try:
        tile_url = geemap.ee_tile_layer(image, vis_params).url
        return tile_url
    except Exception as e:
        print(f"Error generating tiles: {e}")
        return None

# Function to extract AOI from GeoJSON file
def extract_aoi_from_geojson(file_path):
    try:
        with open(file_path, 'r') as geojson_file:
            geojson_data = json.load(geojson_file)
        return ee.Geometry(geojson_data['features'][0]['geometry'])  # Extract AOI from GeoJSON
    except Exception as e:
        print(f"Error extracting AOI from GeoJSON: {e}")
        return None

# Function to extract AOI from KML/KMZ file
def extract_aoi_from_file(file_path):
    try:
        if file_path.endswith('.kmz'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(UPLOAD_FOLDER)
            kml_file = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.kml')][0]
            file_path = os.path.join(UPLOAD_FOLDER, kml_file)
        return geemap.kml_to_ee(file_path)
    except Exception as e:
        print(f"Error extracting AOI: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')


# NDVI comparison route
@app.route('/compare_ndvi', methods=['POST'])
def compare_ndvi():
    global file_aoi
    data = request.get_json()

    # Check if there's an AOI from file upload, otherwise use the one from the user
    if file_aoi:
        aoi = file_aoi
    else:
        aoi = ee.Geometry.Polygon(data['aoi']['geometry']['coordinates'])

    start1 = data['start1']
    end1 = data['end1']
    start2 = data['start2']
    end2 = data['end2']

    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')

    try:
        # NDVI calculation for first date range
        ndvi1 = sentinel2.filterDate(start1, end1).filterBounds(aoi).map(
            lambda img: img.normalizedDifference(['B8', 'B4']).rename("NDVI")
        ).mean().clip(aoi)

        # NDVI calculation for second date range
        ndvi2 = sentinel2.filterDate(start2, end2).filterBounds(aoi).map(
            lambda img: img.normalizedDifference(['B8', 'B4']).rename("NDVI")
        ).mean().clip(aoi)

        # Compute statistics to understand NDVI values for visualization
        stats1 = compute_statistics(ndvi1, aoi)
        stats2 = compute_statistics(ndvi2, aoi)

        # Adjust visualization parameters to reflect finer variations
        min_val = min(stats1['NDVI_mean'], stats2['NDVI_mean']) - 2 * max(stats1['NDVI_stdDev'], stats2['NDVI_stdDev'])
        max_val = max(stats1['NDVI_mean'], stats2['NDVI_mean']) + 2 * max(stats1['NDVI_stdDev'], stats2['NDVI_stdDev'])
        vis_params = {'min': min_val, 'max': max_val, 'palette': ['blue', 'green', 'yellow', 'orange', 'red']}

        # Generate map tiles for visualization
        ndvi_map_id1 = generate_tiles(ndvi1, vis_params)
        ndvi_map_id2 = generate_tiles(ndvi2, vis_params)

        # --- Time Series Calculation ---
        # Calculate the NDVI time series for the entire date range
        ndviTimeSeries = sentinel2.filterBounds(aoi).filterDate(start1, end2).map(
            lambda img: img.normalizedDifference(['B8', 'B4']).rename("NDVI").set('date', img.date().format('YYYY-MM-dd'))
        )

        # Reduce the time series to mean NDVI within AOI for each image
        def reduce_image(image):
            mean_ndvi = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).get('NDVI')
            date = image.get('date')
            # Filter out null values for NDVI and only return valid entries
            return ee.Feature(None, {'NDVI': ee.Algorithms.If(mean_ndvi, mean_ndvi, None), 'date': date})

        ndviTimeSeries = ndviTimeSeries.map(reduce_image)

        # Convert to list for frontend and filter out any 'None' values
        ndvi_stats = ndviTimeSeries.getInfo()['features']
        ndvi_series = [{'date': feature['properties']['date'], 'ndvi': feature['properties']['NDVI']} 
                        for feature in ndvi_stats if feature['properties']['NDVI'] is not None]

        return jsonify({
            "message": "NDVI comparison completed",
            "tile_url1": ndvi_map_id1,
            "tile_url2": ndvi_map_id2,
            "stats1": stats1,
            "stats2": stats2,
            "timeSeriesDates": [item['date'] for item in ndvi_series],
            "timeSeriesValues": [item['ndvi'] for item in ndvi_series],
            "vis_params": vis_params,
            "aoi_bounds": aoi.bounds().getInfo()  # Send the AOI bounds for zooming the map
        })
    except Exception as e:
        return jsonify({"message": f"Error occurred during NDVI computation: {e}"}), 500


# File upload route for GeoJSON, KML, and KMZ
@app.route('/upload', methods=['POST'])
def upload_file():
    global file_aoi
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Extract AOI based on file type
        if file.filename.endswith('.geojson'):
            file_aoi = extract_aoi_from_geojson(file_path)
        else:
            file_aoi = extract_aoi_from_file(file_path)

        if file_aoi:
            return jsonify({"message": "File uploaded successfully", "aoi": file_aoi.getInfo()})
        else:
            return jsonify({"message": "Error extracting AOI from file"}), 500


@app.route('/clear_aoi', methods=['POST'])
def clear_aoi():
    global file_aoi
    file_aoi = None  # Reset the file AOI
    return jsonify({"message": "AOI cleared, please draw a new one."})


# RVI comparison route
@app.route('/compare_rvi', methods=['POST'])
def compare_rvi():
    global file_aoi
    data = request.get_json()

    # Check if there's an AOI from file upload, otherwise use the one from the user
    if file_aoi:
        aoi = file_aoi
    else:
        aoi = ee.Geometry.Polygon(data['aoi']['geometry']['coordinates'])

    start1 = data['start1']
    end1 = data['end1']
    start2 = data['start2']
    end2 = data['end2']

    sentinel1 = ee.ImageCollection('COPERNICUS/S1_GRD')

    try:
        # RVI calculation for first date range
        rvi1 = sentinel1.filterDate(start1, end1).filterBounds(aoi).map(
            lambda img: img.expression('4 * VH / (VV + VH)', {'VH': img.select('VH'), 'VV': img.select('VV')})
            .rename("RVI")
        ).mean().clip(aoi)

        # RVI calculation for second date range
        rvi2 = sentinel1.filterDate(start2, end2).filterBounds(aoi).map(
            lambda img: img.expression('4 * VH / (VV + VH)', {'VH': img.select('VH'), 'VV': img.select('VV')})
            .rename("RVI")
        ).mean().clip(aoi)

        # Compute statistics to understand RVI values for visualization
        stats1 = compute_statistics(rvi1, aoi)
        stats2 = compute_statistics(rvi2, aoi)

        # Adjust visualization parameters
        min_val = min(stats1['RVI_mean'], stats2['RVI_mean']) - 2 * max(stats1['RVI_stdDev'], stats2['RVI_stdDev'])
        max_val = max(stats1['RVI_mean'], stats2['RVI_mean']) + 2 * max(stats1['RVI_stdDev'], stats2['RVI_stdDev'])
        vis_params = {'min': min_val, 'max': max_val, 'palette': ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']}

        # Generate map tiles for visualization
        rvi_map_id1 = generate_tiles(rvi1, vis_params)
        rvi_map_id2 = generate_tiles(rvi2, vis_params)

        # --- Time Series Calculation ---
        # Calculate the RVI time series for the entire date range
        rviTimeSeries = sentinel1.filterBounds(aoi).filterDate(start1, end2).map(
            lambda img: img.expression('4 * VH / (VV + VH)', {'VH': img.select('VH'), 'VV': img.select('VV')})
            .rename("RVI").set('date', img.date().format('YYYY-MM-dd'))
        )

        # Reduce the time series to mean RVI within AOI for each image
        def reduce_image(image):
            mean_rvi = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).get('RVI')
            date = image.get('date')
            return ee.Feature(None, {'RVI': ee.Algorithms.If(mean_rvi, mean_rvi, None), 'date': date})

        rviTimeSeries = rviTimeSeries.map(reduce_image)

        # Convert to list for frontend and filter out any 'None' values
        rvi_stats = rviTimeSeries.getInfo()['features']
        rvi_series = [{'date': feature['properties']['date'], 'rvi': feature['properties']['RVI']} 
                      for feature in rvi_stats if feature['properties']['RVI'] is not None]

        return jsonify({
            "message": "RVI comparison completed",
            "tile_url1": rvi_map_id1,
            "tile_url2": rvi_map_id2,
            "stats1": stats1,
            "stats2": stats2,
            "timeSeriesDates": [item['date'] for item in rvi_series],
            "timeSeriesValues": [item['rvi'] for item in rvi_series],
            "vis_params": vis_params,
            "aoi_bounds": aoi.bounds().getInfo()  # Send the AOI bounds for zooming the map
        })
    except Exception as e:
        return jsonify({"message": f"Error occurred during RVI computation: {e}"}), 500


# NDWI comparison route
@app.route('/compare_ndwi', methods=['POST'])
def compare_ndwi():
    global file_aoi
    data = request.get_json()

    if file_aoi:
        aoi = file_aoi
    else:
        aoi = ee.Geometry.Polygon(data['aoi']['geometry']['coordinates'])

    start1 = data['start1']
    end1 = data['end1']
    start2 = data['start2']
    end2 = data['end2']

    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')

    try:
        # NDWI calculation for first date range
        ndwi1 = sentinel2.filterDate(start1, end1).filterBounds(aoi).map(
            lambda img: img.normalizedDifference(['B3', 'B8']).rename("NDWI")
        ).mean().clip(aoi)

        # NDWI calculation for second date range
        ndwi2 = sentinel2.filterDate(start2, end2).filterBounds(aoi).map(
            lambda img: img.normalizedDifference(['B3', 'B8']).rename("NDWI")
        ).mean().clip(aoi)

        # Compute statistics to understand NDWI values for visualization
        stats1 = compute_statistics(ndwi1, aoi)
        stats2 = compute_statistics(ndwi2, aoi)

        # Adjust visualization parameters
        min_val = min(stats1['NDWI_mean'], stats2['NDWI_mean']) - 2 * max(stats1['NDWI_stdDev'], stats2['NDWI_stdDev'])
        max_val = max(stats1['NDWI_mean'], stats2['NDWI_mean']) + 2 * max(stats1['NDWI_stdDev'], stats2['NDWI_stdDev'])
        vis_params = {'min': min_val, 'max': max_val, 'palette': ['blue', 'green', 'yellow', 'orange', 'red']}

        # Generate map tiles for visualization
        ndwi_map_id1 = generate_tiles(ndwi1, vis_params)
        ndwi_map_id2 = generate_tiles(ndwi2, vis_params)

        # --- Time Series Calculation ---
        # Calculate the NDWI time series for the entire date range
        ndwiTimeSeries = sentinel2.filterBounds(aoi).filterDate(start1, end2).map(
            lambda img: img.normalizedDifference(['B3', 'B8']).rename("NDWI").set('date', img.date().format('YYYY-MM-dd'))
        )

        def reduce_image(image):
            mean_ndwi = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).get('NDWI')
            date = image.get('date')
            return ee.Feature(None, {'NDWI': ee.Algorithms.If(mean_ndwi, mean_ndwi, None), 'date': date})

        ndwiTimeSeries = ndwiTimeSeries.map(reduce_image)

        # Convert to list for frontend and filter out any 'None' values
        ndwi_stats = ndwiTimeSeries.getInfo()['features']
        ndwi_series = [{'date': feature['properties']['date'], 'ndwi': feature['properties']['NDWI']} 
                        for feature in ndwi_stats if feature['properties']['NDWI'] is not None]

        return jsonify({
            "message": "NDWI comparison completed",
            "tile_url1": ndwi_map_id1,
            "tile_url2": ndwi_map_id2,
            "stats1": stats1,
            "stats2": stats2,
            "timeSeriesDates": [item['date'] for item in ndwi_series],
            "timeSeriesValues": [item['ndwi'] for item in ndwi_series],
            "vis_params": vis_params,
            "aoi_bounds": aoi.bounds().getInfo()
        })
    except Exception as e:
        return jsonify({"message": f"Error occurred during NDWI computation: {e}"}), 500

# SAVI comparison route
@app.route('/compare_savi', methods=['POST'])
def compare_savi():
    global file_aoi
    data = request.get_json()

    if file_aoi:
        aoi = file_aoi
    else:
        aoi = ee.Geometry.Polygon(data['aoi']['geometry']['coordinates'])

    start1 = data['start1']
    end1 = data['end1']
    start2 = data['start2']
    end2 = data['end2']

    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')

    try:
        # SAVI calculation for first date range
        savi1 = sentinel2.filterDate(start1, end1).filterBounds(aoi).map(
            lambda img: img.expression(
                '((NIR - RED) / (NIR + RED + L)) * (1 + L)',
                {'NIR': img.select('B8'), 'RED': img.select('B4'), 'L': 0.5}
            ).rename("SAVI")
        ).mean().clip(aoi)

        # SAVI calculation for second date range
        savi2 = sentinel2.filterDate(start2, end2).filterBounds(aoi).map(
            lambda img: img.expression(
                '((NIR - RED) / (NIR + RED + L)) * (1 + L)',
                {'NIR': img.select('B8'), 'RED': img.select('B4'), 'L': 0.5}
            ).rename("SAVI")
        ).mean().clip(aoi)

        # Compute statistics to understand SAVI values for visualization
        stats1 = compute_statistics(savi1, aoi)
        stats2 = compute_statistics(savi2, aoi)

        # Adjust visualization parameters
        min_val = min(stats1['SAVI_mean'], stats2['SAVI_mean']) - 2 * max(stats1['SAVI_stdDev'], stats2['SAVI_stdDev'])
        max_val = max(stats1['SAVI_mean'], stats2['SAVI_mean']) + 2 * max(stats1['SAVI_stdDev'], stats2['SAVI_stdDev'])
        vis_params = {'min': min_val, 'max': max_val, 'palette': ['blue', 'green', 'yellow', 'orange', 'red']}

        # Generate map tiles for visualization
        savi_map_id1 = generate_tiles(savi1, vis_params)
        savi_map_id2 = generate_tiles(savi2, vis_params)

        # --- Time Series Calculation ---
        # Calculate the SAVI time series for the entire date range
        saviTimeSeries = sentinel2.filterBounds(aoi).filterDate(start1, end2).map(
            lambda img: img.expression(
                '((NIR - RED) / (NIR + RED + L)) * (1 + L)',
                {'NIR': img.select('B8'), 'RED': img.select('B4'), 'L': 0.5}
            ).rename("SAVI").set('date', img.date().format('YYYY-MM-dd'))
        )

        def reduce_image(image):
            mean_savi = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).get('SAVI')
            date = image.get('date')
            return ee.Feature(None, {'SAVI': ee.Algorithms.If(mean_savi, mean_savi, None), 'date': date})

        saviTimeSeries = saviTimeSeries.map(reduce_image)

        # Convert to list for frontend and filter out any 'None' values
        savi_stats = saviTimeSeries.getInfo()['features']
        savi_series = [{'date': feature['properties']['date'], 'savi': feature['properties']['SAVI']} 
                       for feature in savi_stats if feature['properties']['SAVI'] is not None]

        return jsonify({
            "message": "SAVI comparison completed",
            "tile_url1": savi_map_id1,
            "tile_url2": savi_map_id2,
            "stats1": stats1,
            "stats2": stats2,
            "timeSeriesDates": [item['date'] for item in savi_series],
            "timeSeriesValues": [item['savi'] for item in savi_series],
            "vis_params": vis_params,
            "aoi_bounds": aoi.bounds().getInfo()
        })
    except Exception as e:
        return jsonify({"message": f"Error occurred during SAVI computation: {e}"}), 500

# Report generation route (for downloading results)
@app.route('/download_report', methods=['POST'])
def download_report():
    # Placeholder for generating a report, e.g., PDF or CSV of results.
    return send_file('report.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
