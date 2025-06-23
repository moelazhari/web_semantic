#!/usr/bin/env python3

import os
import json
import hashlib
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON, RDF
from rdflib import Graph, Namespace, URIRef, RDF as RDF_NS
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# Configuration - use environment variable for Docker compatibility
FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_ENDPOINT = f"{FUSEKI_URL}/organic"
PROOFS_DIR = "proofs"
ns = Namespace("http://example.org/organic#")

def ensure_proofs_directory():
    """Create proofs directory if it doesn't exist"""
    if not os.path.exists(PROOFS_DIR):
        os.makedirs(PROOFS_DIR)
        print(f"📁 Created proofs directory: {PROOFS_DIR}")

def setup_sparql():
    """Setup SPARQL endpoint connection"""
    sparql = SPARQLWrapper(f"{FUSEKI_ENDPOINT}/sparql")
    sparql.setReturnFormat(JSON)
    return sparql

def get_farm_certification_data():
    """Retrieve farm certification data from Fuseki"""
    sparql = setup_sparql()
    
    query = """
    PREFIX : <http://example.org/organic#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?farm ?farmType ?sample ?pesticide ?value ?certStatus WHERE {
        ?farm :hasSoilSample ?sample .
        ?sample :hasPesticide ?pesticide .
        ?sample :hasValue ?value .
        
        OPTIONAL {
            ?farm rdf:type ?farmType .
            FILTER(?farmType IN (:OrganicFarm, :NonOrganicFarm))
        }
        
        OPTIONAL { ?farm :certificationStatus ?certStatus }
    }
    ORDER BY ?farm ?sample
    """
    
    sparql.setQuery(query)
    results = sparql.query().convert()
    
    farms_data = {}
    for result in results["results"]["bindings"]:
        farm_uri = result["farm"]["value"]
        farm_name = farm_uri.split("#")[-1]
        
        if farm_name not in farms_data:
            farms_data[farm_name] = {
                "farm_uri": farm_uri,
                "samples": [],
                "farm_type": "Unknown",
                "certification_status": "PENDING"
            }
        
        sample_data = {
            "sample_uri": result["sample"]["value"],
            "pesticide": result["pesticide"]["value"].split("#")[-1],
            "concentration": float(result["value"]["value"])
        }
        farms_data[farm_name]["samples"].append(sample_data)
        
        if "farmType" in result:
            farm_type = result["farmType"]["value"].split("#")[-1]
            farms_data[farm_name]["farm_type"] = farm_type
            
        if "certStatus" in result:
            farms_data[farm_name]["certification_status"] = result["certStatus"]["value"]
    
    return farms_data

def create_rdf_proof_for_farm(farm_name, farm_data):
    """Create RDF proof for a specific farm"""
    g = Graph()
    g.bind("organic", ns)
    
    farm_uri = ns[farm_name]
    
    if farm_data["farm_type"] == "OrganicFarm":
        g.add((farm_uri, RDF_NS.type, ns.OrganicFarm))
        g.add((farm_uri, ns.certificationStatus, ns.CERTIFIED))
    elif farm_data["farm_type"] == "NonOrganicFarm":
        g.add((farm_uri, RDF_NS.type, ns.NonOrganicFarm))
        g.add((farm_uri, ns.certificationStatus, ns.REJECTED))
    
    for sample in farm_data["samples"]:
        sample_uri = ns[f"Sample_{farm_name}_{len(g)}"]
        g.add((farm_uri, ns.hasSoilSample, sample_uri))
        g.add((sample_uri, ns.hasPesticide, ns[sample["pesticide"]]))
        g.add((sample_uri, ns.hasValue, ns[str(sample["concentration"])]))
    
    g.add((farm_uri, ns.certificationDate, ns[datetime.now().isoformat()]))
    g.add((farm_uri, ns.regulation, ns["EU_2018_848"]))
    

    rdf_data = g.serialize(format='turtle')
    return rdf_data

def generate_cryptographic_proof(farm_name, rdf_data):
    """Generate cryptographic proof for RDF data"""
    
    rdf_hash = hashlib.sha256(rdf_data.encode('utf-8')).hexdigest()
    
    proof = {
        "farm_id": farm_name,
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
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            
            account = Account.from_key(private_key)
            signature = account.signHash(message_hash)
            
            proof["signature"] = {
                "r": signature.r,
                "s": signature.s,
                "v": signature.v,
                "signer_address": account.address
            }
            
            print(f"   🔐 Cryptographic proof signed for {farm_name}")
            
        except Exception as e:
            print(f"   ⚠️  Warning: Could not sign proof for {farm_name}: {e}")
    
    return proof

def save_proofs(proofs):
    """Save all proofs to files"""
    
    for farm_name, proof in proofs.items():
        proof_file = os.path.join(PROOFS_DIR, f"{farm_name}_proof.json")
        with open(proof_file, 'w') as f:
            json.dump(proof, f, indent=2)
        print(f"   📄 Proof saved: {proof_file}")
    
    signatures = {}
    for farm_name, proof in proofs.items():
        signatures[farm_name] = {
            "rdf_hash": proof["rdf_hash"],
            "timestamp": proof["timestamp"],
            "signature": proof.get("signature", {})
        }
    
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    with open(signatures_file, 'w') as f:
        json.dump(signatures, f, indent=2)
    
    print(f"   📦 Combined signatures saved: {signatures_file}")
    return signatures_file

def verify_proof_integrity(proof):
    """Verify the integrity of a proof"""
    try:
        rdf_data = proof["rdf_data"]
        computed_hash = hashlib.sha256(rdf_data.encode('utf-8')).hexdigest()
        
        if computed_hash == proof["rdf_hash"]:
            return True
        else:
            print(f"   ❌ Hash mismatch for {proof['farm_id']}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error verifying proof: {e}")
        return False

def main():
    print("🔐 Generating cryptographic proofs for organic certification")
    print("🏛️  Creating immutable blockchain-ready proofs\n")
    
    ensure_proofs_directory()
    
    try:
        print("1️⃣  Retrieving farm certification data...")
        farms_data = get_farm_certification_data()
        print(f"   Found {len(farms_data)} farms to process")
        
        print("\n2️⃣  Generating RDF proofs...")
        proofs = {}
        
        for farm_name, farm_data in farms_data.items():
            print(f"   Processing {farm_name}...")
            
            rdf_data = create_rdf_proof_for_farm(farm_name, farm_data)
            
            proof = generate_cryptographic_proof(farm_name, rdf_data)
            
            if verify_proof_integrity(proof):
                proofs[farm_name] = proof
                print(f"   ✅ Proof generated and verified for {farm_name}")
            else:
                print(f"   ❌ Proof verification failed for {farm_name}")

        print("\n3️⃣  Saving proofs...")
        signatures_file = save_proofs(proofs)
        
        print(f"\n📊 Proof Generation Summary:")
        print(f"   Total Proofs Generated: {len(proofs)}")
        print(f"   Organic Farms: {len([p for p in proofs.values() if 'OrganicFarm' in p.get('rdf_data', '')])}")
        print(f"   Non-Organic Farms: {len([p for p in proofs.values() if 'NonOrganicFarm' in p.get('rdf_data', '')])}")
        print(f"   Signatures File: {signatures_file}")
        
        print("\n✅ Cryptographic proof generation completed successfully!")
        print("🔗 Ready for blockchain submission")
        
    except Exception as e:
        print(f"❌ Error generating proofs: {e}")
        raise

if __name__ == "__main__":
    main()