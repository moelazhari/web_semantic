#!/usr/bin/env python3

import os
import json
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv
from colorama import Fore, Style, init

load_dotenv()

GANACHE_URL = os.getenv('GANACHE_URL', 'http://localhost:8545')
PROOFS_DIR = "proofs"
RECEIPTS_DIR = "blockchain_receipts"

init(autoreset=True)

def ensure_receipts_directory():
    """Create blockchain receipts directory if it doesn't exist"""
    if not os.path.exists(RECEIPTS_DIR):
        os.makedirs(RECEIPTS_DIR)
        print("✅ Dossier créé:", RECEIPTS_DIR)

def connect_to_blockchain():
    """Connect to blockchain network"""
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    
    if not w3.is_connected():
        raise Exception("Impossible de se connecter à la blockchain")
    
    print("⛓️ Connecté à la blockchain:", GANACHE_URL)
    return w3

def load_account(w3):
    """Load blockchain account"""
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise Exception("Clé privée non trouvée")
    
    account = Account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    
    print("💰 Compte utilisé:", account.address)
    print("💸 Solde:", w3.from_wei(balance, 'ether'), "ETH")
    
    return account

def load_signatures():
    """Load cryptographic signatures"""
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    
    if not os.path.exists(signatures_file):
        raise Exception("Fichier signatures non trouvé")
    
    with open(signatures_file) as f:
        signatures = json.load(f)
    
    print("🔏 Chargement de", len(signatures), "signatures depuis", signatures_file)
    return signatures

def create_certification_contract_data(product_id, signature_data):
    """Create contract data for product certification"""
    cert_data = {
        "product_id": product_id,
        "rdf_hash": signature_data["rdf_hash"],
        "timestamp": signature_data["timestamp"],
        "regulation": "EU_2018_848"
    }
    data_json = json.dumps(cert_data, sort_keys=True)
    data_bytes = data_json.encode('utf-8')
    
    return data_bytes, cert_data

def post_to_blockchain(w3, account, signatures):
    """Post certification data to blockchain"""
    nonce = w3.eth.get_transaction_count(account.address)
    receipts = {}
    
    for product_id, signature_data in signatures.items():
        try:
            data_bytes, cert_data = create_certification_contract_data(product_id, signature_data)
            
            # Create transaction
            transaction = {
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'to': account.address,  # Self-transaction for data storage
                'value': 0,
                'data': data_bytes,
                'chainId': w3.eth.chain_id
            }
            
            # Sign and send transaction
            signed_txn = account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            receipts[product_id] = {
                "transaction_hash": receipt["transactionHash"].hex(),
                "block_number": receipt["blockNumber"],
                "certification_data": cert_data,
                "status": "success" if receipt["status"] == 1 else "failed"
            }
            
            print(f"✅ Certification publiée pour {product_id}")
            nonce += 1
            
        except Exception as e:
            print(f"❌ Erreur lors de la publication pour {product_id}:", str(e))
            receipts[product_id] = {
                "error": str(e),
                "certification_data": cert_data,
                "status": "failed"
            }
    
    return receipts

def save_receipts(receipts):
    """Save blockchain transaction receipts"""
    receipts_file = os.path.join(RECEIPTS_DIR, "all_receipts.json")
    
    with open(receipts_file, 'w') as f:
        json.dump(receipts, f, indent=2)
    
    print("✅ Reçus blockchain sauvegardés dans", RECEIPTS_DIR)
    return receipts_file

def verify_blockchain_storage(w3, receipts):
    """Verify data storage on blockchain"""
    print("\nVérification du stockage blockchain...")
    
    success = 0
    total = len(receipts)
    
    for product_id, receipt in receipts.items():
        if receipt["status"] == "success":
            try:
                tx_hash = receipt["transaction_hash"]
                tx = w3.eth.get_transaction(tx_hash)
                
                if tx and tx["blockNumber"] == receipt["block_number"]:
                    success += 1
                else:
                    print(f"❌ Transaction introuvable pour {product_id}")
            except Exception as e:
                print(f"❌ Erreur de vérification pour {product_id}:", str(e))
    
    print(f"Vérification terminée: {success}/{total} produits vérifiés")
    return success, total

def main():
    print("Publication des preuves de certification bio sur blockchain")
    print("Création d'une piste d'audit immuable\n")
    
    ensure_receipts_directory()
    
    try:
        # Connect to blockchain
        w3 = connect_to_blockchain()
        account = load_account(w3)
        
        print("\n1. Chargement des signatures...")
        signatures = load_signatures()
        
        print("\n2. Publication sur blockchain...")
        receipts = post_to_blockchain(w3, account, signatures)
        
        print("\n3. Sauvegarde des reçus...")
        save_receipts(receipts)
        
        print("\n4. Vérification du stockage...")
        success, total = verify_blockchain_storage(w3, receipts)
        
        print("\nRésumé:")
        print("   Publications réussies:", success)
        print("   Publications échouées:", total - success)
        print("   Total traité:", total)
        
        print("\nPublication blockchain terminée avec succès!")
        print("Preuves stockées de manière immuable pour vérification")
        
    except Exception as e:
        print("❌ Erreur lors de la publication blockchain:", str(e))
        raise

if __name__ == '__main__':
    main()