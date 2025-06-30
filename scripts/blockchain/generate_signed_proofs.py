#!/usr/bin/env python3

import os
import json
import hashlib
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'queries'))

from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON, RDF
from rdflib import Graph, Namespace, URIRef, RDF as RDF_NS
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
from query_loader import load_query

load_dotenv()

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
PROOFS_DIR = "proofs"
ns = Namespace("http://example.org/organic#")

def ensure_proofs_directory():
    """Create proofs directory if it doesn't exist"""
    if not os.path.exists(PROOFS_DIR):
        os.makedirs(PROOFS_DIR)
        print(f"Dossier créé: {PROOFS_DIR}")

def setup_sparql():
    """Setup SPARQL endpoint connection"""
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    return sparql

def get_product_certification_data():
    """Retrieve product certification data from Fuseki"""
    sparql = setup_sparql()
    
    # Load query from file
    query = load_query("farm_certification_data")
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    products_data = {}
    for result in results["results"]["bindings"]:
        product_uri = result["product"]["value"]
        product_name = product_uri.split("#")[-1]
        
        if product_name not in products_data:
            products_data[product_name] = {
                "product_uri": product_uri,
                "samples": [],
                "product_type": "Inconnu",
                "certification_status": "EN_ATTENTE",
                "category": result["category"]["value"].split("#")[-1]
            }
        
        sample_data = {
            "sample_uri": result["sample"]["value"],
            "chemical": result["chemical"]["value"].split("#")[-1],
            "concentration": float(result["value"]["value"])
        }
        products_data[product_name]["samples"].append(sample_data)
        
        if "productType" in result:
            product_type = result["productType"]["value"].split("#")[-1]
            products_data[product_name]["product_type"] = product_type
            
        if "certStatus" in result:
            products_data[product_name]["certification_status"] = result["certStatus"]["value"]
    
    return products_data

def create_rdf_proof_for_product(product_name, product_data):
    """Create RDF proof for a specific product"""
    g = Graph()
    g.bind("organic", ns)
    
    product_uri = ns[product_name]
    category_uri = ns[product_data["category"]]
    
    g.add((product_uri, ns.hasCategory, category_uri))
    
    if product_data["product_type"] == "OrganicProduct":
        g.add((product_uri, RDF_NS.type, ns.OrganicProduct))
        g.add((product_uri, ns.certificationStatus, ns.CERTIFIED))
    elif product_data["product_type"] == "NonOrganicProduct":
        g.add((product_uri, RDF_NS.type, ns.NonOrganicProduct))
        g.add((product_uri, ns.certificationStatus, ns.REJECTED))
    
    for sample in product_data["samples"]:
        sample_uri = ns[f"Sample_{product_name}_{len(g)}"]
        g.add((product_uri, ns.hasSample, sample_uri))
        g.add((sample_uri, ns.hasChemical, ns[sample["chemical"]]))
        g.add((sample_uri, ns.hasValue, ns[str(sample["concentration"])]))
    
    g.add((product_uri, ns.certificationDate, ns[datetime.now().isoformat()]))
    g.add((product_uri, ns.regulation, ns["EU_2018_848"]))
    
    rdf_data = g.serialize(format='turtle')
    return rdf_data

def generate_cryptographic_proof(product_name, rdf_data):
    """Generate cryptographic proof for RDF data"""
    
    rdf_hash = hashlib.sha256(rdf_data.encode('utf-8')).hexdigest()
    
    proof = {
        "product_id": product_name,
        "timestamp": datetime.now().isoformat(),
        "rdf_hash": rdf_hash,
        "regulation": "EU_2018_848",
        "proof_type": "ORGANIC_CERTIFICATION",
        "rdf_data": rdf_data
    }
    
    private_key = os.getenv("PRIVATE_KEY")
    if private_key:
        try:
            message = json.dumps(proof, sort_keys=True)
            
            # Create account from private key
            account = Account.from_key(private_key)
            
            # Sign the message
            signed_message = Account.sign_message(
                encode_defunct(text=message),
                private_key=private_key
            )
            
            proof["signature"] = {
                "r": signed_message.r,
                "s": signed_message.s,
                "v": signed_message.v,
                "signer_address": account.address
            }
            
            print(f"   Preuve cryptographique signée pour {product_name}")
            
        except Exception as e:
            print(f"   Attention: Impossible de signer la preuve pour {product_name}: {e}")
    
    return proof

def verify_proof_integrity(proof):
    """Verify the integrity of a cryptographic proof"""
    try:
        # Verify RDF data hash
        rdf_hash = hashlib.sha256(proof["rdf_data"].encode('utf-8')).hexdigest()
        if rdf_hash != proof["rdf_hash"]:
            print(f"   Erreur: Hash RDF invalide pour {proof['product_id']}")
            return False
        
        # Verify signature if present
        if "signature" in proof:
            message = json.dumps({k: v for k, v in proof.items() if k != "signature"}, sort_keys=True)
            
            signature = proof["signature"]
            v, r, s = signature["v"], signature["r"], signature["s"]
            
            # Create the Ethereum-specific message
            message_hash = encode_defunct(text=message)
            
            # Recover the signer's address
            signer = Account.recover_message(message_hash, vrs=(v, r, s))
            
            if signer.lower() != signature["signer_address"].lower():
                print(f"   Erreur: Signature invalide pour {proof['product_id']}")
                return False
            
            print(f"   Preuve générée et vérifiée pour {proof['product_id']}")
        
        return True
        
    except Exception as e:
        print(f"   Erreur de vérification pour {proof['product_id']}: {e}")
        return False

def save_proofs(proofs):
    """Save all proofs to files"""
    
    for product_name, proof in proofs.items():
        proof_file = os.path.join(PROOFS_DIR, f"{product_name}_proof.json")
        with open(proof_file, 'w') as f:
            json.dump(proof, f, indent=2)
        print(f"   Preuve sauvegardée: {proof_file}")
    
    signatures = {}
    for product_name, proof in proofs.items():
        signatures[product_name] = {
            "rdf_hash": proof["rdf_hash"],
            "timestamp": proof["timestamp"],
            "signature": proof.get("signature", {})
        }
    
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    with open(signatures_file, 'w') as f:
        json.dump(signatures, f, indent=2)
    
    print(f"   Signatures combinées sauvegardées: {signatures_file}")
    return signatures_file

def main():
    print("Génération des preuves cryptographiques pour certification bio")
    print("Création de preuves immuables pour blockchain\n")
    
    ensure_proofs_directory()
    
    try:
        print("1. Récupération des données de certification...")
        products_data = get_product_certification_data()
        print(f"   {len(products_data)} produits trouvés")
        
        print("\n2. Génération des preuves RDF...")
        proofs = {}
        
        for product_name, product_data in products_data.items():
            print(f"   Traitement de {product_name}...")
            
            rdf_data = create_rdf_proof_for_product(product_name, product_data)
            proof = generate_cryptographic_proof(product_name, rdf_data)
            
            if verify_proof_integrity(proof):
                proofs[product_name] = proof
                print(f"   Preuve générée et vérifiée pour {product_name}")
            else:
                print(f"   Erreur de vérification pour {product_name}")
        
        print("\n3. Sauvegarde des preuves...")
        signatures_file = save_proofs(proofs)
        
        # print(f"\nRésumé de génération:")
        # print(f"   Preuves générées: {len(proofs)}")
        # print(f"   Produits bio: {len([p for p in proofs.values() if 'OrganicProduct' in p['rdf_data']])}")
        # print(f"   Produits non-bio: {len([p for p in proofs.values() if 'NonOrganicProduct' in p['rdf_data']])}")
        # print(f"   Fichier signatures: {signatures_file}")
        
        print("\nGénération des preuves cryptographiques terminée!")
        print("Prêt pour soumission blockchain")
        
    except Exception as e:
        print(f"Erreur lors de la génération des preuves: {e}")
        raise

if __name__ == '__main__':
    main()