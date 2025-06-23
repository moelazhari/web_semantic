#!/usr/bin/env python3
"""
Semantic inference engine for organic agriculture certification
Implements EU 2018/848 regulation compliance checking
"""

import requests
import json
import os
import base64
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL
from rdflib.namespace import XSD

# Configuration - use environment variable for Docker compatibility
FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
FUSEKI_USER = os.getenv('FUSEKI_USER', 'admin')
FUSEKI_PASSWORD = os.getenv('FUSEKI_PASSWORD', 'admin123')
ns = Namespace("http://example.org/organic#")

def setup_sparql():
    """Setup SPARQL endpoint connection"""
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    
    # Add authentication
    credentials = f"{FUSEKI_USER}:{FUSEKI_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    sparql.addCustomHttpHeader('Authorization', f'Basic {encoded_credentials}')
    
    return sparql

def execute_sparql_update(query, description):
    """Execute SPARQL UPDATE query with proper formatting"""
    try:
        # Use requests directly for better control over the request
        url = f"{FUSEKI_ENDPOINT}/update"
        headers = {
            'Content-Type': 'application/sparql-update',
            'Authorization': f'Basic {base64.b64encode(f"{FUSEKI_USER}:{FUSEKI_PASSWORD}".encode()).decode()}'
        }
        
        response = requests.post(url, data=query, headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ {description} completed")
            return True
        else:
            print(f"   ❌ Error in {description}: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error in {description}: {e}")
        return False

def run_inference_rules():
    """Run semantic inference rules for organic certification"""
    sparql = setup_sparql()
    
    print("🧠 Running semantic inference rules...")
    
    # Rule 1: Mark farms as non-organic if they have prohibited pesticides
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
        
        # Prohibited pesticides (not in allowed list)
        FILTER(?pesticide NOT IN (:Glyphosate, :Pyrethrin))
    }
    """
    
    # Rule 2: Mark farms as non-organic if pesticide levels exceed limits
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
        
        # Even allowed pesticides have limits
        FILTER((?pesticide = :Glyphosate && ?value > 0.25) || 
               (?pesticide = :Pyrethrin && ?value > 0.15))
    }
    """
    
    # Rule 3: Certify farms as organic if they pass all tests
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
        
        # Farm exists but is not marked as non-organic
        FILTER NOT EXISTS {
            ?farm rdf:type :NonOrganicFarm .
        }
        
        BIND(NOW() as ?date)
    }
    """
    
    # Execute inference rules
    rules = [
        ("Identifying non-organic farms (prohibited pesticides)", inference_query_1),
        ("Checking pesticide concentration limits", inference_query_2),
        ("Certifying compliant farms as organic", inference_query_3)
    ]
    
    for desc, query in rules:
        print(f"   Executing: {desc}")
        execute_sparql_update(query, desc)
    
    print("✅ Semantic inference completed")

def verify_inference_results():
    """Verify the results of semantic inference"""
    sparql = setup_sparql()
    
    # Check organic farms
    organic_query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?status WHERE {
        ?farm rdf:type :OrganicFarm .
        OPTIONAL { ?farm :certificationStatus ?status }
    }
    """
    
    # Check non-organic farms
    non_organic_query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?reason WHERE {
        ?farm rdf:type :NonOrganicFarm .
        OPTIONAL { ?farm :hasViolationReason ?reason }
    }
    """
    
    print("\n📊 Inference Results:")
    
    # Organic farms
    sparql.setQuery(organic_query)
    results = sparql.query().convert()
    organic_farms = results["results"]["bindings"]
    
    print(f"✅ Organic Certified Farms: {len(organic_farms)}")
    for farm in organic_farms:
        farm_name = farm["farm"]["value"].split("#")[-1]
        status = farm.get("status", {}).get("value", "CERTIFIED")
        print(f"   • {farm_name}: {status}")
    
    # Non-organic farms
    sparql.setQuery(non_organic_query)
    results = sparql.query().convert()
    non_organic_farms = results["results"]["bindings"]
    
    print(f"❌ Non-Organic Farms: {len(non_organic_farms)}")
    for farm in non_organic_farms:
        farm_name = farm["farm"]["value"].split("#")[-1]
        reason = farm.get("reason", {}).get("value", "Regulation violation")
        print(f"   • {farm_name}: {reason}")
    
    return len(organic_farms), len(non_organic_farms)

def main():
    print("🚀 Starting Semantic Inference for Organic Certification")
    print("📋 Implementing EU Regulation 2018/848 compliance rules\n")
    
    try:
        # Run inference rules
        run_inference_rules()
        
        # Verify results
        organic_count, non_organic_count = verify_inference_results()
        
        print(f"\n📈 Summary:")
        print(f"   Organic Farms: {organic_count}")
        print(f"   Non-Organic Farms: {non_organic_count}")
        print(f"   Total Processed: {organic_count + non_organic_count}")
        
        print("\n✅ Semantic inference completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during inference: {e}")
        raise

if __name__ == "__main__":
    main()