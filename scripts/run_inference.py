#!/usr/bin/env python3
import requests
import json
import os
import base64
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'queries'))

from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL
from rdflib.namespace import XSD
from query_loader import load_verification_queries, load_swrl_rules

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
FUSEKI_USER = os.getenv('FUSEKI_USER', 'admin')
FUSEKI_PASSWORD = os.getenv('FUSEKI_PASSWORD', 'admin123')
ns = Namespace("http://example.org/organic#")

def setup_sparql():
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    
    credentials = f"{FUSEKI_USER}:{FUSEKI_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    sparql.addCustomHttpHeader('Authorization', f'Basic {encoded_credentials}')
    
    return sparql

def execute_sparql_update(query, description):
    try:
        url = f"{FUSEKI_ENDPOINT}/update"
        headers = {
            'Content-Type': 'application/sparql-update',
            'Authorization': f'Basic {base64.b64encode(f"{FUSEKI_USER}:{FUSEKI_PASSWORD}".encode()).decode()}'
        }
        
        response = requests.post(url, data=query, headers=headers)
        
        if response.status_code == 200:
            print(f"   Terminé: {description}")
            return True
        else:
            print(f"   Erreur dans {description}: HTTP {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"   Erreur dans {description}: {e}")
        return False

def run_inference_rules():
    sparql = setup_sparql()
    
    print("Exécution des règles d'inférence sémantique...")
    
    try:
        swrl_rules = load_swrl_rules()
        print("   Règles SWRL chargées pour le raisonnement")
        print("   Application des règles via SPARQL updates...")
        
    except Exception as e:
        print(f"   Erreur lors du chargement des règles SWRL: {e}")
        print("   Utilisation des règles SPARQL de fallback...")
    
    inference_query_1 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT {
        ?farm rdf:type :NonOrganicFarm .
        ?farm :violatesRegulation :EU_2018_848 .
        ?farm :hasViolationReason ?pesticide .
    }
    WHERE {
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        
        FILTER(?pesticide NOT IN (:Glyphosate, :Pyrethrin))
    }
    """
    
    inference_query_2 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT {
        ?farm rdf:type :NonOrganicFarm .
        ?farm :violatesRegulation :EU_2018_848 .
        ?farm :hasViolationReason "Pesticide level exceeds organic limits" .
    }
    WHERE {
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        
        FILTER((?pesticide = :Glyphosate && ?value > 0.25) || 
               (?pesticide = :Pyrethrin && ?value > 0.15))
    }
    """
    
    inference_query_3 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT {
        ?farm rdf:type :OrganicFarm .
        ?farm :hasCertification :OrganicCertification .
        ?farm :certificationDate ?date .
        ?farm :certificationStatus "CERTIFIED" .
    }
    WHERE {
        ?farm :hasSoilSample ?sample .
        
        FILTER NOT EXISTS {
            ?farm rdf:type :NonOrganicFarm .
        }
        
        BIND(NOW() as ?date)
    }
    """
    
    rules = [
        ("Identification des fermes non-bio (pesticides interdits)", inference_query_1),
        ("Vérification des limites de concentration", inference_query_2),
        ("Certification des fermes conformes comme bio", inference_query_3)
    ]
    
    for desc, query in rules:
        print(f"   Exécution: {desc}")
        execute_sparql_update(query, desc)
    
    print("Inférence sémantique terminée")

def verify_inference_results():
    sparql = setup_sparql()
    
    # Load verification queries from files
    organic_query, non_organic_query = load_verification_queries()
    
    print("\nRésultats de l'inférence:")
    
    sparql.setQuery(organic_query)
    results = sparql.query().convert()
    organic_farms = results["results"]["bindings"]
    
    print(f"Fermes certifiées bio: {len(organic_farms)}")
    for farm in organic_farms:
        farm_name = farm["farm"]["value"].split("#")[-1]
        status = farm.get("status", {}).get("value", "CERTIFIED")
        print(f"   • {farm_name}: {status}")
    
    sparql.setQuery(non_organic_query)
    results = sparql.query().convert()
    non_organic_farms = results["results"]["bindings"]
    
    print(f"Fermes non-bio: {len(non_organic_farms)}")
    for farm in non_organic_farms:
        farm_name = farm["farm"]["value"].split("#")[-1]
        reason = farm.get("reason", {}).get("value", "Violation de réglementation")
        print(f"   • {farm_name}: {reason}")
    
    return len(organic_farms), len(non_organic_farms)

def main():
    print("Démarrage de l'inférence sémantique pour certification bio")
    print("Application des règles de conformité EU 2018/848\n")
    
    try:
        run_inference_rules()

        organic_count, non_organic_count = verify_inference_results()
        
        print(f"\nRésumé:")
        print(f"   Fermes bio: {organic_count}")
        print(f"   Fermes non-bio: {non_organic_count}")
        print(f"   Total traité: {organic_count + non_organic_count}")
        
        print("\nInférence sémantique terminée avec succès!")
        
    except Exception as e:
        print(f"Erreur lors de l'inférence: {e}")
        raise

if __name__ == "__main__":
    main()