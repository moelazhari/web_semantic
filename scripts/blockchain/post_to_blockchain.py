#!/usr/bin/env python3

import os
import json
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()
PROOFS_DIR = "proofs"
BLOCKCHAIN_DIR = "blockchain_receipts"

def setup_web3():
    rpc_url = os.getenv("GANACHE_URL", "http://localhost:8545")
    private_key = os.getenv("PRIVATE_KEY")
    
    if not private_key:
        raise ValueError("PRIVATE_KEY non trouvée dans les variables d'environnement")
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        raise ConnectionError(f"Impossible de se connecter à la blockchain: {rpc_url}")
    
    account = Account.from_key(private_key)
    
    print(f"Connecté à la blockchain: {rpc_url}")
    print(f"Compte utilisé: {account.address}")
    print(f"Solde: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    return w3, account

def ensure_blockchain_directory():
    if not os.path.exists(BLOCKCHAIN_DIR):
        os.makedirs(BLOCKCHAIN_DIR)
        print(f"Dossier créé: {BLOCKCHAIN_DIR}")

def load_signatures():
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    
    if not os.path.exists(signatures_file):
        raise FileNotFoundError(f"Fichier signatures non trouvé: {signatures_file}")
    
    with open(signatures_file, 'r') as f:
        signatures = json.load(f)
    
    print(f"Chargement de {len(signatures)} signatures depuis {signatures_file}")
    return signatures

def create_certification_contract_data(farm_id, signature_data):
    cert_data = {
        "farm_id": farm_id,
        "rdf_hash": signature_data["rdf_hash"],
        "timestamp": signature_data["timestamp"],
        "regulation": "EU_2018_848"
    }
    data_json = json.dumps(cert_data, sort_keys=True)
    data_bytes = data_json.encode('utf-8')
    
    return data_bytes, cert_data

def post_certification_to_blockchain(w3, account, farm_id, signature_data):
    
    try:
        data_bytes, cert_data = create_certification_contract_data(farm_id, signature_data)
    
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        transaction = {
            'to': account.address,
            'value': 0,
            'gas': 100000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'data': data_bytes.hex(),
            'chainId': w3.eth.chain_id
        }
        
        signed_txn = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        print(f"   Transaction envoyée pour {farm_id}")
        print(f"   Hash TX: {tx_hash.hex()}")
        
        print(f"   Attente de confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"   Transaction confirmée pour {farm_id}")
            print(f"   Bloc: {receipt.blockNumber}")
            print(f"   Gas utilisé: {receipt.gasUsed}")
            
            receipt_data = {
                "farm_id": farm_id,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "certification_data": cert_data,
                "blockchain_proof": {
                    "network": "ganache-local",
                    "chain_id": w3.eth.chain_id,
                    "timestamp": time.time(),
                    "status": "confirmed"
                }
            }
            
            return receipt_data
            
        else:
            print(f"   Transaction échouée pour {farm_id}")
            return None
            
    except Exception as e:
        print(f"   Erreur lors de la publication de {farm_id}: {e}")
        return None

def save_blockchain_receipts(receipts):
    for receipt in receipts:
        if receipt:
            receipt_file = os.path.join(BLOCKCHAIN_DIR, f"{receipt['farm_id']}_receipt.json")
            with open(receipt_file, 'w') as f:
                json.dump(receipt, f, indent=2)

    combined_file = os.path.join(BLOCKCHAIN_DIR, "all_receipts.json")
    with open(combined_file, 'w') as f:
        json.dump([r for r in receipts if r], f, indent=2)
    
    print(f"Reçus blockchain sauvegardés dans {BLOCKCHAIN_DIR}/")

def verify_blockchain_storage(w3, receipts):
    print("\nVérification du stockage blockchain...")
    
    verified_count = 0
    for receipt in receipts:
        if not receipt:
            continue
            
        try:
            tx = w3.eth.get_transaction(receipt['tx_hash'])
            
            stored_data = bytes.fromhex(tx['input'][2:]).decode('utf-8')
            stored_json = json.loads(stored_data)
            
            if stored_json['farm_id'] == receipt['farm_id']:
                print(f"   {receipt['farm_id']}: Données vérifiées sur blockchain")
                verified_count += 1
            else:
                print(f"   {receipt['farm_id']}: Incohérence de données")
                
        except Exception as e:
            print(f"   {receipt['farm_id']}: Erreur de vérification: {e}")
    
    print(f"Vérification terminée: {verified_count}/{len([r for r in receipts if r])} fermes vérifiées")

def main():
    print("Publication des preuves de certification bio sur blockchain")
    print("Création d'une piste d'audit immuable\n")
    
    try:
        ensure_blockchain_directory()
        w3, account = setup_web3()
        
        print("\n1. Chargement des signatures...")
        signatures = load_signatures()
        
        print("\n2. Publication sur blockchain...")
        receipts = []
        
        for farm_id, signature_data in signatures.items():
            print(f"   Publication de {farm_id}...")
            receipt = post_certification_to_blockchain(w3, account, farm_id, signature_data)
            receipts.append(receipt)
            
            if receipt:
                print(f"   Succès pour {farm_id}")
            else:
                print(f"   Échec pour {farm_id}")
        
        print("\n3. Sauvegarde des reçus...")
        save_blockchain_receipts(receipts)
        
        print("\n4. Vérification du stockage...")
        verify_blockchain_storage(w3, receipts)
        
        successful_receipts = [r for r in receipts if r]
        print(f"\nRésumé:")
        print(f"   Publications réussies: {len(successful_receipts)}")
        print(f"   Publications échouées: {len(receipts) - len(successful_receipts)}")
        print(f"   Total traité: {len(receipts)}")
        
        print("\nPublication blockchain terminée avec succès!")
        print("Preuves stockées de manière immuable pour vérification")
        
    except Exception as e:
        print(f"Erreur lors de la publication blockchain: {e}")
        raise

if __name__ == "__main__":
    main()