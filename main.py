#!/usr/bin/env python3
import subprocess
import sys
import time
import requests
import os

def wait_for_service(url, service_name, max_attempts=30):
    print(f"⏳ Waiting for {service_name} to be ready...")
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} is ready!")
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            print(f"   Attempt {attempt + 1}/{max_attempts} - retrying in 2 seconds...")
            time.sleep(2)
    
    print(f"❌ {service_name} failed to start after {max_attempts} attempts")
    return False

def wait_for_ganache(url, max_attempts=30):
    print(f"⏳ Waiting for Ganache to be ready...")
    payload = {
        "jsonrpc": "2.0",
        "method": "web3_clientVersion",
        "params": [],
        "id": 1
    }
    for attempt in range(max_attempts):
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200 and "result" in response.json():
                print("✅ Ganache is ready!")
                return True
        except requests.RequestException:
            pass
        if attempt < max_attempts - 1:
            print(f"   Attempt {attempt + 1}/{max_attempts} - retrying in 2 seconds...")
            time.sleep(2)
    print(f"❌ Ganache failed to start after {max_attempts} attempts")
    return False

def run_command(cmd, desc):
    print(f"\n▶️  {desc}…")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅  {desc} completed.")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌  Error during {desc}: {e}")
        if e.stderr:
            print(f"   Error details: {e.stderr.strip()}")
        return False

def main():
    print("🚀 Starting Organic Certification Semantic Web Pipeline\n")

    fuseki_url = os.getenv('FUSEKI_URL', 'http://fuseki:3030')
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:8545')
    
    fuseki_ready = wait_for_service(fuseki_url, "Fuseki")
    ganache_ready = wait_for_ganache(ganache_url)
    
    if not (fuseki_ready and ganache_ready):
        print("❌ Required services are not ready. Exiting.")
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/ingest_sensor_data.py'], "Ingesting IoT sensor data"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/run_inference.py'], "Running semantic inference for organic certification"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/generate_reports.py'], "Generating compliance reports"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/generate_signed_proofs.py'], "Generating cryptographic proofs"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/post_to_blockchain.py'], "Posting signatures to blockchain"):
        sys.exit(1)
    
    print("\n🎉 Organic Certification Pipeline completed successfully!")
    print("📊 Check the generated reports in the 'reports/' directory")
    print("🔗 Blockchain proofs stored on-chain for immutable verification")

if __name__ == '__main__':
    main()