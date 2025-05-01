#!/usr/bin/env python3

import json
import numpy as np
import os
from tqdm import tqdm
import re

# Paths
INPUT_DRONE_PATH = "raw data/droneImageMetadata.jsonl"
INPUT_SOIL_PATH = "raw data/soilSensorReading.jsonl"
OUTPUT_DIR = "normalized"
OUTPUT_VISION_PATH = os.path.join(OUTPUT_DIR, "vision_embeddings.jsonl")
OUTPUT_SOIL_PATH = os.path.join(OUTPUT_DIR, "soil_vectors.jsonl")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_numeric_value(value_string):
    """Extract numeric value from a string like '520 mV'"""
    match = re.search(r'(\d+)', value_string)
    if match:
        return int(match.group(1))
    return None

def normalize_volumetric_water_content(mV_value):
    """
    Convert volumetric water content from mV to [0.0, 1.0] scale
    Assuming 300-700 mV is the valid range
    """
    # Ensure value is in range for normalization
    mV_value = max(300, min(700, mV_value))
    # Normalize to [0, 1]
    return (mV_value - 300) / 400.0

def convert_voltage_to_ph(mV_value):
    """
    Convert soil pH voltage from mV to pH scale
    Map 1500-1800 mV to pH 5.5-7.5 linearly
    """
    # Ensure value is in range for conversion
    mV_value = max(1500, min(1800, mV_value))
    # Map 1500-1800 mV to pH 5.5-7.5
    return 5.5 + (mV_value - 1500) / 300.0 * 2.0

def generate_image_embedding():
    """Simulate a MobileNet-like image embedding"""
    return np.random.rand(256).tolist()

def process_drone_data():
    """Process drone image metadata and create embeddings"""
    records_processed = 0
    
    with open(INPUT_DRONE_PATH, 'r') as infile, open(OUTPUT_VISION_PATH, 'w') as outfile:
        # Count lines for progress bar
        total_lines = sum(1 for _ in open(INPUT_DRONE_PATH, 'r'))
        
        for line in tqdm(infile, total=total_lines, desc="Processing vision data"):
            record = json.loads(line)
            
            # Create new record with required fields
            new_record = {
                "event_ts": record["event_ts"],
                "plot_id": record["plot_id"],
                "modal_tag": record["modal_tag"],
                "embedding": generate_image_embedding()
            }
            
            # Write to output file
            outfile.write(json.dumps(new_record) + '\n')
            records_processed += 1
    
    return records_processed

def process_soil_data():
    """Process soil telemetry data and normalize values"""
    records_processed = 0
    
    with open(INPUT_SOIL_PATH, 'r') as infile, open(OUTPUT_SOIL_PATH, 'w') as outfile:
        # Count lines for progress bar
        total_lines = sum(1 for _ in open(INPUT_SOIL_PATH, 'r'))
        
        for line in tqdm(infile, total=total_lines, desc="Processing soil data"):
            record = json.loads(line)
            
            # Extract numeric values
            vwc_mV = extract_numeric_value(record["volumetric_water_content"])
            ph_mV = extract_numeric_value(record["soil_ph_voltage"])
            
            # Normalize values
            normalized_vwc = normalize_volumetric_water_content(vwc_mV)
            ph_value = convert_voltage_to_ph(ph_mV)
            
            # Create new record with required fields
            new_record = {
                "event_ts": record["event_ts"],
                "plot_id": record["plot_id"],
                "modal_tag": record["modal_tag"],
                "vwc": normalized_vwc,
                "ph": ph_value
            }
            
            # Write to output file
            outfile.write(json.dumps(new_record) + '\n')
            records_processed += 1
    
    return records_processed

def main():
    print("Starting preprocessing of sensor data...")
    
    # Process drone data
    vision_records = process_drone_data()
    print(f"Processed {vision_records} vision records and saved to {OUTPUT_VISION_PATH}")
    
    # Process soil data
    soil_records = process_soil_data()
    print(f"Processed {soil_records} soil records and saved to {OUTPUT_SOIL_PATH}")
    
    print("Preprocessing complete!")
    
    # Print message about expected location vs actual location
    print("\nNote: The output files are saved in the local 'normalized' folder.")
    print("In a production environment, these would go to '/mnt/data/normalized/' as specified in the requirements.")

if __name__ == "__main__":
    main() 