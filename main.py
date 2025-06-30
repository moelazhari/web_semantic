#!/usr/bin/env python3
import subprocess
import sys
import time
import requests
import os
from colorama import Fore, Style, init

init(autoreset=True)

def wait_for_jena(url, max_attempts=30):
    print(f"{Fore.YELLOW}⏳ Attente du serveur Jena...{Style.RESET_ALL}")
    for attempt in range(max_attempts):
        try:
            # Try to access the dataset info endpoint
            response = requests.get(f"{url}/organic", timeout=5)
            if response.status_code in [200, 404]:  # 404 is ok, means dataset not created yet
                print(f"{Fore.GREEN}✅ Jena est prêt!{Style.RESET_ALL}")
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            print(f"{Fore.YELLOW}   Tentative {attempt + 1}/{max_attempts} - nouvelle tentative dans 2 secondes...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}❌ Erreur: Jena n'a pas démarré après {max_attempts} tentatives{Style.RESET_ALL}")
    return False

def wait_for_ganache(url, max_attempts=30):
    print(f"{Fore.YELLOW}⏳ Attente de Ganache...{Style.RESET_ALL}")
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
                print(f"{Fore.GREEN}✅ Ganache est prêt!{Style.RESET_ALL}")
                return True
        except requests.RequestException:
            pass
        if attempt < max_attempts - 1:
            print(f"{Fore.YELLOW}   Tentative {attempt + 1}/{max_attempts} - nouvelle tentative dans 2 secondes...{Style.RESET_ALL}")
            time.sleep(2)
    print(f"{Fore.RED}❌ Erreur: Ganache n'a pas démarré après {max_attempts} tentatives{Style.RESET_ALL}")
    return False

def verify_data_loaded(fuseki_url, max_attempts=10):
    print(f"{Fore.YELLOW}⏳ Vérification du chargement des données...{Style.RESET_ALL}")
    headers = {
        'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/sparql-query'
    }
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT (COUNT(?p) as ?count) WHERE { ?p rdf:type :Product }
    """
    
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                f"{fuseki_url}/organic/query",
                headers=headers,
                data=query,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                count = int(data['results']['bindings'][0]['count']['value'])
                if count > 0:
                    print(f"{Fore.GREEN}✅ Données chargées avec succès ({count} produits){Style.RESET_ALL}")
                    return True
        except (requests.RequestException, KeyError, ValueError, IndexError):
            pass
        
        if attempt < max_attempts - 1:
            print(f"{Fore.YELLOW}   Données non chargées, nouvelle tentative dans 2 secondes...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}❌ Erreur: Les données n'ont pas été chargées correctement{Style.RESET_ALL}")
    return False

def run_command(cmd, desc, verify_func=None):
    print(f"{Fore.CYAN}\n🚀 Exécution: {desc}...{Style.RESET_ALL}")
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"{Fore.GREEN}✅ Terminé: {desc}{Style.RESET_ALL}")
            if result.stdout:
                print(f"{Fore.CYAN}   Sortie: {result.stdout.strip()}{Style.RESET_ALL}")
            
            # If a verification function is provided, run it
            if verify_func and not verify_func():
                if attempt < max_attempts - 1:
                    print(f"{Fore.YELLOW}   Vérification échouée, nouvelle tentative...{Style.RESET_ALL}")
                    time.sleep(5)  # Wait longer between retries
                    continue
                return False
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}❌ Erreur lors de {desc}: {e}{Style.RESET_ALL}")
            if e.stdout:
                print(f"{Fore.YELLOW}   Sortie standard: {e.stdout.strip()}{Style.RESET_ALL}")
            if e.stderr:
                print(f"{Fore.RED}   Erreur: {e.stderr.strip()}{Style.RESET_ALL}")
            
            if attempt < max_attempts - 1:
                print(f"{Fore.YELLOW}   Nouvelle tentative dans 5 secondes...{Style.RESET_ALL}")
                time.sleep(5)
            else:
                return False
    
    return False

def main():
    print(f"{Fore.MAGENTA}🎬 Démarrage du pipeline de certification bio{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌱 Système web sémantique pour l'agriculture biologique\n{Style.RESET_ALL}")

    fuseki_url = os.getenv('FUSEKI_URL', 'http://fuseki:3030')
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:8545')
    
    # Wait longer for initial services
    time.sleep(10)  # Give services more time to initialize
    
    jena_ready = wait_for_jena(fuseki_url)
    ganache_ready = wait_for_ganache(ganache_url)
    
    if not (jena_ready and ganache_ready):
        print(f"{Fore.RED}❌ Erreur: Les services requis ne sont pas prêts. Arrêt.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Run data ingestion with verification
    if not run_command(
        ['python3', 'scripts/ingest_sensor_data.py'],
        "Import des données capteurs IoT",
        lambda: verify_data_loaded(fuseki_url)
    ):
        sys.exit(1)
    
    # Give Jena time to process the data
    time.sleep(5)
    
    if not run_command(['python3', 'scripts/run_inference.py'], "Inférence sémantique pour certification bio"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/generate_reports.py'], "Génération des rapports de conformité"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/generate_signed_proofs.py'], "Génération des preuves cryptographiques"):
        sys.exit(1)
    
    if not run_command(['python3', 'scripts/blockchain/post_to_blockchain.py'], "Publication des signatures sur la blockchain"):
        sys.exit(1)
    
    print(f"{Fore.GREEN}\n🎉 Pipeline de certification bio terminé avec succès!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📁 Consultez les rapports générés dans le dossier 'reports/'{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔏 Preuves blockchain stockées pour vérification immuable{Style.RESET_ALL}")

if __name__ == '__main__':
    main()