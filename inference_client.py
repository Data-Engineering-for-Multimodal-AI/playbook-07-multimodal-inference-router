#!/usr/bin/env python3

import argparse
import json
import os
import time
import random
from tqdm import tqdm
import fused_record_pb2 as pb2
import fused_record_pb2_grpc as pb2_grpc

# Input and output paths
INPUT_FUSED_PATH = "output/inference_queue_per_event.jsonl"
OUTPUT_DIR = "output"
OUTPUT_RESULTS_PATH = os.path.join(OUTPUT_DIR, "inference_results.jsonl")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

class MockInferenceClient:
    """Mock gRPC client that simulates inference requests and responses"""
    
    def __init__(self):
        # In a real implementation, this would establish a gRPC channel
        print("Initializing mock inference client...")
    
    def predict(self, record_proto):
        """
        Mock prediction method that simulates server latency and returns a fixed response
        
        Args:
            record_proto: Serialized FusedRecord protobuf
            
        Returns:
            dict: A dictionary containing prediction results
        """
        # Simulate network and processing latency (20-100ms)
        latency = random.uniform(20, 100)
        time.sleep(latency / 1000)  # Convert to seconds
        
        # Generate a mock prediction
        actions = ["spray", "irrigate", "fertilize", "monitor", "harvest"]
        action = random.choice(actions)
        
        # Generate entropy (measure of prediction uncertainty)
        entropy = random.uniform(0.2, 0.8)
        
        # Generate confidence score (inverse of entropy)
        confidence = 1.0 - entropy
        
        return {
            "action": action,
            "confidence": confidence,
            "entropy": entropy,
            "latency_ms": latency
        }

def deserialize_embedding(embedding_str):
    """
    Convert embedding from various possible formats to a list of floats
    
    Args:
        embedding_str: Embedding in string or list format
        
    Returns:
        list: List of float values
    """
    if isinstance(embedding_str, list):
        return embedding_str
    
    try:
        # Try parsing as JSON string
        return json.loads(embedding_str)
    except (json.JSONDecodeError, TypeError):
        print(f"Warning: Failed to parse embedding: {embedding_str[:30]}...")
        # Return empty list as fallback
        return []

def record_to_proto(record):
    """
    Convert a JSON record to a FusedRecord protobuf object
    
    Args:
        record: Dictionary containing fused record data
        
    Returns:
        FusedRecord: Protobuf object
    """
    try:
        proto = pb2.FusedRecord()
        proto.plot_id = record.get("plot_id", "")
        proto.event_ts = record.get("event_ts", "")
        
        # Handle embedding - might be a string or list
        embedding = deserialize_embedding(record.get("embedding", []))
        proto.embedding.extend(embedding)
        
        # Handle numerical values
        proto.vwc = float(record.get("vwc", 0.0))
        proto.ph = float(record.get("ph", 0.0))
        proto.fusion_gap_ms = float(record.get("fusion_gap_ms", 0.0))
        
        return proto
    except Exception as e:
        print(f"Error serializing record: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Send fused records to the mock inference client")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for the mock predictions (default: 42)")
    random.seed(parser.parse_args().seed)

    # Initialize client
    client = MockInferenceClient()
    
    # Read fused records
    records = []
    with open(INPUT_FUSED_PATH, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping malformed JSON: {line[:50]}...")
    
    print(f"Processing {len(records)} fused records...")
    
    # Process records and write results
    with open(OUTPUT_RESULTS_PATH, 'w') as out_file:
        for record in tqdm(records, desc="Sending inference requests"):
            try:
                # Start timing
                start_time = time.time()
                
                # Convert to protobuf
                record_proto = record_to_proto(record)
                
                if record_proto is None:
                    # Fallback path if serialization fails
                    print(f"Warning: Using fallback for record with plot_id {record.get('plot_id', 'unknown')}")
                    result = {
                        "plot_id": record.get("plot_id", "unknown"),
                        "event_ts": record.get("event_ts", ""),
                        "action": "monitor",  # Default safe action
                        "confidence": 0.5,
                        "entropy": 0.5,
                        "latency_ms": 0,
                        "error": "Serialization failed"
                    }
                else:
                    # Make prediction request
                    prediction = client.predict(record_proto)
                    
                    # Calculate total processing time
                    end_time = time.time()
                    total_time_ms = (end_time - start_time) * 1000
                    
                    # Prepare result
                    result = {
                        "plot_id": record.get("plot_id", ""),
                        "event_ts": record.get("event_ts", ""),
                        "action": prediction["action"],
                        "confidence": prediction["confidence"],
                        "entropy": prediction["entropy"],
                        "latency_ms": total_time_ms,
                        "server_latency_ms": prediction["latency_ms"]
                    }
                
                # Write to output file
                out_file.write(json.dumps(result) + "\n")
                
            except Exception as e:
                print(f"Error processing record: {e}")
    
    print(f"Results written to {OUTPUT_RESULTS_PATH}")

if __name__ == "__main__":
    main() 