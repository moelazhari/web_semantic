#!/usr/bin/env python3
import subprocess
import sys
import time
import requests
import os

def wait_for_jena(url, max_attempts=30):
    print("Attente du serveur Jena...")
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("Jena est prêt!")
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            print(f"   Tentative {attempt + 1}/{max_attempts} - nouvelle tentative dans 2 secondes...")
            time.sleep(2)
    
    print(f"Erreur: Jena n'a pas démarré après {max_attempts} tentatives")
    return False

def wait_for_ganache(url, max_attempts=30):
    print("Attente de Ganache...")
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
                print("Ganache est prêt!")
                return True
        except requests.RequestException:
            pass
        if attempt < max_attempts - 1:
            print(f"   Tentative {attempt + 1}/{max_attempts} - nouvelle tentative dans 2 secondes...")
            time.sleep(2)
    print(f"Erreur: Ganache n'a pas démarré après {max_attempts} tentatives")
    return False

def run_command(cmd, desc):
    print(f"\nExécution: {desc}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Terminé: {desc}")
        if result.stdout:
            print(f"   Sortie: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de {desc}: {e}")
        if e.stderr:
            print(f"   Détails: {e.stderr.strip()}")
        return False

def main():
    print("Démarrage du pipeline de certification bio")
    print("Système web sémantique pour l'agriculture biologique\n")

    fuseki_url = os.getenv('FUSEKI_URL', 'http://fuseki:3030')
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:8545')
    
    jena_ready = wait_for_jena(fuseki_url)
    ganache_ready = wait_for_ganache(ganache_url)
    
    if not (jena_ready and ganache_ready):
        print("Erreur: Les services requis ne sont pas prêts. Arrêt.")
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/ingest_sensor_data.py'], "Import des données capteurs IoT"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/run_inference.py'], "Inférence sémantique pour certification bio"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/generate_reports.py'], "Génération des rapports de conformité"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/generate_signed_proofs.py'], "Génération des preuves cryptographiques"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/post_to_blockchain.py'], "Publication des signatures sur la blockchain"):
        sys.exit(1)
    
    print("\nPipeline de certification bio terminé avec succès!")
    print("Consultez les rapports générés dans le dossier 'reports/'")
    print("Preuves blockchain stockées pour vérification immuable")

if __name__ == '__main__':
    main()