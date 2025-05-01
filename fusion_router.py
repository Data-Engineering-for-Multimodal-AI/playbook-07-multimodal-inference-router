#!/usr/bin/env python3

import json
import os
import datetime
from tqdm import tqdm
from collections import defaultdict

# Input and output paths
INPUT_VISION_PATH = "normalized/vision_embeddings.jsonl"
INPUT_SOIL_PATH = "normalized/soil_vectors.jsonl"
OUTPUT_DIR = "output"
OUTPUT_FUSED_PATH = os.path.join(OUTPUT_DIR, "inference_queue_per_event.jsonl")
OUTPUT_VISION_ONLY_PATH = os.path.join(OUTPUT_DIR, "inference_queue_vision_only.jsonl")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Maximum allowed time difference in milliseconds for fusion
MAX_FUSION_GAP_MS = 500


def load_jsonl_data(file_path):
    """Load JSONL file and parse event_ts to datetime objects"""
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line)
            # Convert ISO timestamp to datetime object
            record['event_ts_dt'] = datetime.datetime.fromisoformat(record['event_ts'].replace('Z', '+00:00'))
            data.append(record)
    
    # Sort by event timestamp
    data.sort(key=lambda x: x['event_ts_dt'])
    return data


def organize_by_plot(data):
    """Organize records by plot_id for efficient lookup"""
    plot_data = defaultdict(list)
    for record in data:
        plot_data[record['plot_id']].append(record)
    return plot_data


def calculate_time_diff_ms(dt1, dt2):
    """Calculate absolute time difference in milliseconds between two datetime objects"""
    time_delta = abs(dt1 - dt2)
    return time_delta.total_seconds() * 1000


def fuse_and_route_data(vision_data, soil_data):
    """Perform sliding window fusion and routing"""
    # Organize data by plot_id
    vision_by_plot = organize_by_plot(vision_data)
    soil_by_plot = organize_by_plot(soil_data)
    
    fused_records = []
    vision_only_records = []
    
    # Process each vision record
    for vision_record in tqdm(vision_data, desc="Processing records for fusion"):
        plot_id = vision_record['plot_id']
        vision_ts = vision_record['event_ts_dt']
        
        # Check if plot exists in soil data
        if plot_id in soil_by_plot:
            # Find the closest soil record within the time window
            matching_soil = None
            min_gap = float('inf')
            
            for soil_record in soil_by_plot[plot_id]:
                soil_ts = soil_record['event_ts_dt']
                gap_ms = calculate_time_diff_ms(vision_ts, soil_ts)
                
                if gap_ms <= MAX_FUSION_GAP_MS and gap_ms < min_gap:
                    matching_soil = soil_record
                    min_gap = gap_ms
            
            if matching_soil:
                # Create fused record
                fused_record = {
                    "plot_id": plot_id,
                    "event_ts": vision_record['event_ts'],
                    "embedding": vision_record['embedding'],
                    "vwc": matching_soil['vwc'],
                    "ph": matching_soil['ph'],
                    "fusion_gap_ms": min_gap
                }
                fused_records.append(fused_record)
                continue
        
        # No matching soil record found, create vision-only record
        vision_only_record = {
            "plot_id": plot_id,
            "event_ts": vision_record['event_ts'],
            "embedding": vision_record['embedding']
        }
        vision_only_records.append(vision_only_record)
    
    return fused_records, vision_only_records


def save_jsonl_data(data, file_path):
    """Save data to JSONL file"""
    with open(file_path, 'w') as f:
        for record in data:
            f.write(json.dumps(record) + '\n')


def main():
    print("Starting event-time fusion and inference routing...")
    
    # Load data from JSONL files
    print(f"Loading vision data from {INPUT_VISION_PATH}...")
    vision_data = load_jsonl_data(INPUT_VISION_PATH)
    print(f"Loaded {len(vision_data)} vision records")
    
    print(f"Loading soil data from {INPUT_SOIL_PATH}...")
    soil_data = load_jsonl_data(INPUT_SOIL_PATH)
    print(f"Loaded {len(soil_data)} soil records")
    
    # Perform fusion and routing
    print("Performing windowed event-time fusion and routing...")
    fused_records, vision_only_records = fuse_and_route_data(vision_data, soil_data)
    
    # Save results
    save_jsonl_data(fused_records, OUTPUT_FUSED_PATH)
    print(f"Saved {len(fused_records)} fused records to {OUTPUT_FUSED_PATH}")
    
    save_jsonl_data(vision_only_records, OUTPUT_VISION_ONLY_PATH)
    print(f"Saved {len(vision_only_records)} vision-only records to {OUTPUT_VISION_ONLY_PATH}")
    
    print("\nFusion and routing complete!")
    
    # Print fusion statistics
    total_records = len(fused_records) + len(vision_only_records)
    fusion_rate = (len(fused_records) / total_records) * 100 if total_records > 0 else 0
    print(f"\nFusion statistics:")
    print(f"Total records processed: {total_records}")
    print(f"Records successfully fused: {len(fused_records)} ({fusion_rate:.1f}%)")
    print(f"Records routed to vision-only: {len(vision_only_records)} ({100-fusion_rate:.1f}%)")


if __name__ == "__main__":
    main() 