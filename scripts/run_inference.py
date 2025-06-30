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
from colorama import Fore, Style, init

init(autoreset=True)

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
            print(f"{Fore.GREEN}✅ Terminé: {description}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Erreur dans {description}: HTTP {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠️ Réponse: {response.text}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur dans {description}: {e}{Style.RESET_ALL}")
        return False

def run_inference_rules():
    sparql = setup_sparql()
    
    print(f"{Fore.MAGENTA}🧠 Exécution des règles d'inférence sémantique...")
    
    # First, clear any existing classifications and certifications
    clear_query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    DELETE {
        ?product rdf:type :OrganicProduct .
        ?product rdf:type :NonOrganicProduct .
        ?product :hasCertification ?cert .
        ?product :certificationStatus ?status .
        ?product :violatesRegulation ?reg .
        ?product :hasViolationReason ?reason .
    }
    WHERE {
        ?product rdf:type :Product .
        OPTIONAL { ?product rdf:type :OrganicProduct }
        OPTIONAL { ?product rdf:type :NonOrganicProduct }
        OPTIONAL { ?product :hasCertification ?cert }
        OPTIONAL { ?product :certificationStatus ?status }
        OPTIONAL { ?product :violatesRegulation ?reg }
        OPTIONAL { ?product :hasViolationReason ?reason }
    }
    """
    
    execute_sparql_update(clear_query, "Nettoyage des classifications existantes")
    
    # Identify non-organic products due to prohibited chemicals
    inference_query_1 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT {
        ?product rdf:type :NonOrganicProduct .
        ?product :violatesRegulation :EU_2018_848 .
        ?product :hasViolationReason "Contains prohibited chemical" .
        ?product :certificationStatus "REJECTED" .
    }
    WHERE {
        ?product rdf:type :Product .
        ?product :hasSample ?sample .
        ?sample :hasChemical ?chemical .
        ?chemical rdf:type :ProhibitedChemical .
    }
    """
    
    # Identify non-organic products due to excessive chemical levels
    inference_query_2 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    INSERT {
        ?product rdf:type :NonOrganicProduct .
        ?product :violatesRegulation :EU_2018_848 .
        ?product :hasViolationReason ?reason .
        ?product :certificationStatus "REJECTED" .
    }
    WHERE {
        ?product rdf:type :Product .
        ?product :hasSample ?sample .
        ?sample :hasChemical ?chemical .
        ?sample :hasValue ?value .
        ?chemical rdf:type :AllowedChemical .
        ?chemical :maxAllowedLevel ?max .
        
        BIND(CONCAT("Chemical ", STR(?chemical), " exceeds limit of ", STR(?max)) AS ?reason)
        
        FILTER(?value > ?max)
        FILTER NOT EXISTS {
            ?product rdf:type :NonOrganicProduct
        }
    }
    """
    
    # Certify remaining products as organic
    inference_query_3 = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT {
        ?product rdf:type :OrganicProduct .
        ?product :hasCertification :OrganicCertification .
        ?product :certificationStatus "CERTIFIED" .
    }
    WHERE {
        ?product rdf:type :Product .
        
        # Product must not have any prohibited chemicals
        FILTER NOT EXISTS {
            ?product :hasSample ?s1 .
            ?s1 :hasChemical ?c1 .
            ?c1 rdf:type :ProhibitedChemical .
        }
        
        # Product must not have any excessive chemical levels
        FILTER NOT EXISTS {
            ?product :hasSample ?s2 .
            ?s2 :hasChemical ?c2 .
            ?s2 :hasValue ?v2 .
            ?c2 :maxAllowedLevel ?max2 .
            FILTER(?v2 > ?max2)
        }
        
        # Product must not already be classified
        FILTER NOT EXISTS {
            ?product rdf:type :NonOrganicProduct
        }
        FILTER NOT EXISTS {
            ?product rdf:type :OrganicProduct
        }
    }
    """
    
    rules = [
        ("Identification des produits non-bio (pesticides interdits)", inference_query_1),
        ("Vérification des limites de concentration", inference_query_2),
        ("Certification des produits conformes comme bio", inference_query_3)
    ]
    
    for desc, query in rules:
        print(f"{Fore.CYAN}   Exécution: {desc}")
        execute_sparql_update(query, desc)
    
    print(f"{Fore.GREEN}🎉 Inférence sémantique terminée{Style.RESET_ALL}")

def verify_inference_results():
    sparql = setup_sparql()
    
    # Load verification queries from files
    organic_query, non_organic_query = load_verification_queries()
    
    print(f"{Fore.BLUE}\n📊 Résultats de l'inférence:{Style.RESET_ALL}")
    
    sparql.setQuery(organic_query)
    results = sparql.query().convert()
    organic_products = results["results"]["bindings"]
    
    print(f"{Fore.GREEN}🌱 Fermes certifiées bio: {len(organic_products)}{Style.RESET_ALL}")
    for product in organic_products:
        product_name = product["product"]["value"].split("#")[-1]
        status = product.get("status", {}).get("value", "CERTIFIED")
        print(f"{Fore.GREEN}   • {product_name}: {status}{Style.RESET_ALL}")
    
    sparql.setQuery(non_organic_query)
    results = sparql.query().convert()
    non_organic_products = results["results"]["bindings"]
    
    print(f"{Fore.RED}🚫 Fermes non-bio: {len(non_organic_products)}{Style.RESET_ALL}")
    for product in non_organic_products:
        product_name = product["product"]["value"].split("#")[-1]
        reason = product.get("reason", {}).get("value", "Violation de réglementation")
        print(f"{Fore.RED}   • {product_name}: {reason}{Style.RESET_ALL}")
    
    return len(organic_products), len(non_organic_products)

def main():
    print("Démarrage de l'inférence sémantique pour certification bio")
    print("Application des règles de conformité EU 2018/848\n")
    
    try:
        run_inference_rules()

        organic_count, non_organic_count = verify_inference_results()
        
        print(f"{Fore.CYAN}\nRésumé:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   Fermes bio: {organic_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}   Fermes non-bio: {non_organic_count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Total traité: {organic_count + non_organic_count}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}\n🎉 Inférence sémantique terminée avec succès!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors de l'inférence: {e}{Style.RESET_ALL}")
        raise

if __name__ == "__main__":
    main()