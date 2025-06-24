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
PROOFS_DIR = "proofs"
BLOCKCHAIN_DIR = "blockchain_receipts"

init(autoreset=True)

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
    
    print(f"{Fore.YELLOW}⛓️ Connecté à la blockchain: {rpc_url}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}💰 Compte utilisé: {account.address}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}💸 Solde: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH{Style.RESET_ALL}")
    
    return w3, account

def ensure_blockchain_directory():
    if not os.path.exists(BLOCKCHAIN_DIR):
        os.makedirs(BLOCKCHAIN_DIR)
        print(f"{Fore.GREEN}✅ Dossier créé: {BLOCKCHAIN_DIR}{Style.RESET_ALL}")

def load_signatures():
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    
    if not os.path.exists(signatures_file):
        raise FileNotFoundError(f"Fichier signatures non trouvé: {signatures_file}")
    
    with open(signatures_file, 'r') as f:
        signatures = json.load(f)
    
    print(f"{Fore.CYAN}🔏 Chargement de {len(signatures)} signatures depuis {signatures_file}{Style.RESET_ALL}")
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
        
        print(f"{Fore.CYAN}🔗 Transaction envoyée pour {farm_id}{Style.RESET_ALL}")
        print(f"   Hash TX: {tx_hash.hex()}")
        
        print(f"{Fore.YELLOW}⏳ Attente de confirmation...{Style.RESET_ALL}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"{Fore.GREEN}✅ Transaction confirmée pour {farm_id}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Bloc: {receipt.blockNumber}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Gas utilisé: {receipt.gasUsed}{Style.RESET_ALL}")
            
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
            print(f"{Fore.RED}❌ Transaction échouée pour {farm_id}{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors de la publication de {farm_id}: {e}{Style.RESET_ALL}")
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
    
    print(f"{Fore.GREEN}✅ Reçus blockchain sauvegardés dans {BLOCKCHAIN_DIR}/{Style.RESET_ALL}")

def verify_blockchain_storage(w3, receipts):
    print(f"{Fore.CYAN}\nVérification du stockage blockchain...{Style.RESET_ALL}")
    
    verified_count = 0
    for receipt in receipts:
        if not receipt:
            continue
            
        try:
            tx = w3.eth.get_transaction(receipt['tx_hash'])
            
            stored_data = bytes.fromhex(tx['input'][2:]).decode('utf-8')
            stored_json = json.loads(stored_data)
            
            if stored_json['farm_id'] == receipt['farm_id']:
                print(f"{Fore.GREEN}   {receipt['farm_id']}: Données vérifiées sur blockchain{Style.RESET_ALL}")
                verified_count += 1
            else:
                print(f"{Fore.RED}   {receipt['farm_id']}: Incohérence de données{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}   {receipt['farm_id']}: Erreur de vérification: {e}{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}Vérification terminée: {verified_count}/{len([r for r in receipts if r])} fermes vérifiées{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}Publication des preuves de certification bio sur blockchain{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Création d'une piste d'audit immuable\n{Style.RESET_ALL}")
    
    try:
        ensure_blockchain_directory()
        w3, account = setup_web3()
        
        print(f"{Fore.CYAN}\n1. Chargement des signatures...{Style.RESET_ALL}")
        signatures = load_signatures()
        
        print(f"{Fore.CYAN}\n2. Publication sur blockchain...{Style.RESET_ALL}")
        receipts = []
        
        for farm_id, signature_data in signatures.items():
            print(f"{Fore.CYAN}   Publication de {farm_id}...{Style.RESET_ALL}")
            receipt = post_certification_to_blockchain(w3, account, farm_id, signature_data)
            receipts.append(receipt)
            
            if receipt:
                print(f"{Fore.GREEN}   Succès pour {farm_id}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}   Échec pour {farm_id}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}\n3. Sauvegarde des reçus...{Style.RESET_ALL}")
        save_blockchain_receipts(receipts)
        
        print(f"{Fore.CYAN}\n4. Vérification du stockage...{Style.RESET_ALL}")
        verify_blockchain_storage(w3, receipts)
        
        successful_receipts = [r for r in receipts if r]
        print(f"{Fore.CYAN}\nRésumé:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   Publications réussies: {len(successful_receipts)}{Style.RESET_ALL}")
        print(f"{Fore.RED}   Publications échouées: {len(receipts) - len(successful_receipts)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Total traité: {len(receipts)}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}\nPublication blockchain terminée avec succès!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Preuves stockées de manière immuable pour vérification{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Erreur lors de la publication blockchain: {e}{Style.RESET_ALL}")
        raise

if __name__ == "__main__":
    main()