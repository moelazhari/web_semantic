#!/usr/bin/env python3
import json
import requests
import time
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import XSD
from colorama import Fore, Style, init
import os
import traceback

init(autoreset=True)

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://fuseki:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
FUSEKI_USER = os.getenv('FUSEKI_USER', 'admin')
FUSEKI_PASSWORD = os.getenv('FUSEKI_PASSWORD', 'admin123')

def clear_existing_data():
    print(f"{Fore.YELLOW}🗑️ Nettoyage des données existantes...{Style.RESET_ALL}")
    try:
        # Use SPARQL UPDATE to clear the graph
        headers = {
            'Content-Type': 'application/sparql-update',
        }
        update_query = "CLEAR ALL"
        
        response = requests.post(
            f"{FUSEKI_ENDPOINT}/update",
            auth=(FUSEKI_USER, FUSEKI_PASSWORD),
            headers=headers,
            data=update_query,
            timeout=10
        )
        if response.status_code in [200, 204]:
            print(f"{Fore.GREEN}✅ Données existantes nettoyées{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Erreur lors du nettoyage: HTTP {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
            return False
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ Erreur lors du nettoyage: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}Stack trace: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def load_data_to_fuseki(data, max_attempts=3):
    print(f"{Fore.CYAN}📤 Chargement des données dans Fuseki...{Style.RESET_ALL}")
    
    headers = {'Content-Type': 'text/turtle'}
    
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                f"{FUSEKI_ENDPOINT}/data",
                auth=(FUSEKI_USER, FUSEKI_PASSWORD),
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Données chargées avec succès{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}❌ Erreur lors du chargement: HTTP {response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
                if attempt < max_attempts - 1:
                    print(f"{Fore.YELLOW}   Nouvelle tentative dans 5 secondes...{Style.RESET_ALL}")
                    time.sleep(5)
                    continue
                return False
                
        except requests.RequestException as e:
            print(f"{Fore.RED}❌ Erreur lors du chargement: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.RED}Stack trace: {traceback.format_exc()}{Style.RESET_ALL}")
            if attempt < max_attempts - 1:
                print(f"{Fore.YELLOW}   Nouvelle tentative dans 5 secondes...{Style.RESET_ALL}")
                time.sleep(5)
                continue
            return False
    
    return False

def main():
    print(f"{Fore.CYAN}📥 Lecture des données capteurs...{Style.RESET_ALL}")

    # Define which chemicals are prohibited vs allowed
    PROHIBITED_CHEMICALS = {'Glyphosate', 'DDT', 'Atrazine'}
    ALLOWED_CHEMICALS = {'Sulfur', 'Pyrethrin', 'CopperSulfate'}

    try:
        with open('scripts/sensor_data.json') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"{Fore.RED}❌ Erreur lors de la lecture des données: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}Stack trace: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

    g = Graph()
    ns = Namespace("http://example.org/organic#")

    print(f"{Fore.CYAN}🔄 Traitement de {len(entries)} échantillons...{Style.RESET_ALL}")

    # First define chemical types
    for chemical in PROHIBITED_CHEMICALS:
        chem_uri = URIRef(ns + chemical)
        g.add((chem_uri, RDF.type, ns.ProhibitedChemical))

    for chemical in ALLOWED_CHEMICALS:
        chem_uri = URIRef(ns + chemical)
        g.add((chem_uri, RDF.type, ns.AllowedChemical))
        # Add max allowed levels
        if chemical == 'Sulfur':
            g.add((chem_uri, ns.maxAllowedLevel, Literal(0.25, datatype=XSD.float)))
        elif chemical == 'Pyrethrin':
            g.add((chem_uri, ns.maxAllowedLevel, Literal(0.15, datatype=XSD.float)))
        elif chemical == 'CopperSulfate':
            g.add((chem_uri, ns.maxAllowedLevel, Literal(0.20, datatype=XSD.float)))

    for e in entries:
        product = URIRef(ns + e['product'])
        category = URIRef(ns + e['category'])
        sample = URIRef(ns + "Sample_" + e['product'] + "_" + e['id'])
        chemical = URIRef(ns + e['chemical'])
        
        # Add product type
        g.add((product, RDF.type, ns.Product))
        
        # Add product category
        g.add((product, ns.hasCategory, category))
        
        # Add sample data
        g.add((product, ns.hasSample, sample))
        g.add((sample, ns.hasChemical, chemical))
        g.add((sample, ns.hasValue, Literal(e['value'], datatype=XSD.float)))
        
        # Add production date (using current date for demonstration)
        g.add((product, ns.hasProductionDate, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    # Save to file first
    try:
        os.makedirs('data', exist_ok=True)  # Create data directory if it doesn't exist
        g.serialize(destination='data/farm_data.ttl', format='turtle')
        print(f"{Fore.GREEN}💾 Données sauvegardées dans data/farm_data.ttl{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors de la sauvegarde du fichier: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}Stack trace: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

    # Clear existing data first
    if not clear_existing_data():
        return False

    # Load data to Fuseki
    turtle_data = g.serialize(format='turtle')
    if not load_data_to_fuseki(turtle_data):
        return False

    print(f"{Fore.GREEN}✅ Import terminé: {len(entries)} lectures capteurs traitées{Style.RESET_ALL}")
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        exit(1)