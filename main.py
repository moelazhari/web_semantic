#!/usr/bin/env python3
import subprocess
import sys
import time

def run_command(cmd, desc):
    print(f"\n▶️  {desc}…")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅  {desc} completed.")
    except subprocess.CalledProcessError as e:
        print(f"❌  Error during {desc}: {e}")
        sys.exit(1)

def main():
    print("🚀 Starting Organic Certification pipeline\n")
    run_command(
        ['python3', 'scripts/ingest_sensor_data.py'],
        "Ingesting sensor data"
    )

    run_command(
        ['python3', 'scripts/blockchin/generate_signed_proofs.py'],
        "Generating signed RDF proofs"
    )

    run_command(
        ['python3', 'scripts//blockchin/post_to_blockchain.py'],
        "Posting signatures to blockchain (Web3.py)"
    )

    run_command(
        ['python3', 'scripts/post_to_blockchain.py'],
        "Posting signatures to blockchain"
    )

    print("\n🎉 All steps finished successfully.")

if __name__ == '__main__':
    main()
