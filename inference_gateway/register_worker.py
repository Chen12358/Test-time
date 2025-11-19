# register_worker.py
# This script now sends the absolute model path during registration.

import os
import requests
import socket
import time
import argparse
import logging

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')

def get_host_ip_address():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        logging.error(f"Could not determine hostname or IP address: {e}")
        return '127.0.0.1'

def register_with_gateway(gateway_url, worker_port, model_name, model_path):
    """
    Sends a registration request including the friendly name and absolute path.
    """
    worker_ip = get_host_ip_address()
    worker_url = f"http://{worker_ip}:{worker_port}"
    register_endpoint = f"{gateway_url}/register"
    
    # UPDATED: Payload now includes the model_path
    payload = {"url": worker_url, "model_name": model_name, "model_path": model_path}
    
    max_retries = 5
    retry_delay_seconds = 15

    for attempt in range(max_retries):
        try:
            logging.info(f"Attempting to register worker {worker_url} for model '{model_name}'...")
            response = requests.post(register_endpoint, json=payload, timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully registered with gateway.")
            return
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to register with gateway (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay_seconds)
            else:
                logging.error("Could not register with gateway after multiple retries.")
                raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register a vLLM worker with the API gateway.")
    parser.add_argument("--gateway-url", type=str, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model-name", type=str, required=True, help="The friendly name for the model.")
    # NEW: Argument for the absolute model path
    parser.add_argument("--model-path", type=str, required=True, help="The absolute path to the model files.")
    
    args = parser.parse_args()
    
    logging.info("Waiting for vLLM server to start before registration...")
    time.sleep(300)

    register_with_gateway(args.gateway_url, args.port, args.model_name, args.model_path)