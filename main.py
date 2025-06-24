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
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
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

def run_command(cmd, desc):
    print(f"{Fore.CYAN}\n🚀 Exécution: {desc}...{Style.RESET_ALL}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"{Fore.GREEN}✅ Terminé: {desc}{Style.RESET_ALL}")
        if result.stdout:
            print(f"{Fore.CYAN}   Sortie: {result.stdout.strip()}{Style.RESET_ALL}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}❌ Erreur lors de {desc}: {e}{Style.RESET_ALL}")
        if e.stderr:
            print(f"{Fore.YELLOW}   Détails: {e.stderr.strip()}{Style.RESET_ALL}")
        return False

def main():
    print(f"{Fore.MAGENTA}🎬 Démarrage du pipeline de certification bio{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌱 Système web sémantique pour l'agriculture biologique\n{Style.RESET_ALL}")

    fuseki_url = os.getenv('FUSEKI_URL', 'http://fuseki:3030')
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:8545')
    
    jena_ready = wait_for_jena(fuseki_url)
    ganache_ready = wait_for_ganache(ganache_url)
    
    if not (jena_ready and ganache_ready):
        print(f"{Fore.RED}❌ Erreur: Les services requis ne sont pas prêts. Arrêt.{Style.RESET_ALL}")
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
    
    print(f"{Fore.GREEN}\n🎉 Pipeline de certification bio terminé avec succès!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📁 Consultez les rapports générés dans le dossier 'reports/'{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔏 Preuves blockchain stockées pour vérification immuable{Style.RESET_ALL}")

if __name__ == '__main__':
    main()