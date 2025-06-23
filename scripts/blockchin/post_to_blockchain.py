#!/usr/bin/env python3
"""
Post organic certification proofs to blockchain
Stores immutable proofs for verification and audit
"""

import os
import json
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PROOFS_DIR = "proofs"
BLOCKCHAIN_DIR = "blockchain_receipts"

def setup_web3():
    """Setup Web3 connection"""
    rpc_url = os.getenv("RPC_URL", "http://localhost:8545")
    private_key = os.getenv("PRIVATE_KEY")
    
    if not private_key:
        raise ValueError("PRIVATE_KEY not found in environment variables")
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Add PoA middleware for development chains
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to blockchain at {rpc_url}")
    
    # Setup account
    account = Account.from_key(private_key)
    
    print(f"🔗 Connected to blockchain: {rpc_url}")
    print(f"👤 Using account: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    return w3, account

def ensure_blockchain_directory():
    """Create blockchain receipts directory"""
    if not os.path.exists(BLOCKCHAIN_DIR):
        os.makedirs(BLOCKCHAIN_DIR)
        print(f"📁 Created blockchain receipts directory: {BLOCKCHAIN_DIR}")

def load_signatures():
    """Load signatures from proofs directory"""
    signatures_file = os.path.join(PROOFS_DIR, "signatures.json")
    
    if not os.path.exists(signatures_file):
        raise FileNotFoundError(f"Signatures file not found: {signatures_file}")
    
    with open(signatures_file, 'r') as f:
        signatures = json.load(f)
    
    print(f"📦 Loaded {len(signatures)} signatures from {signatures_file}")
    return signatures

def create_certification_contract_data(farm_id, signature_data):
    """Create contract data for certification"""
    
    # Simple data structure for certification
    cert_data = {
        "farm_id": farm_id,
        "rdf_hash": signature_data["rdf_hash"],
        "timestamp": signature_data["timestamp"],
        "regulation": "EU_2018_848"
    }
    
    # Convert to bytes for blockchain storage
    data_json = json.dumps(cert_data, sort_keys=True)
    data_bytes = data_json.encode('utf-8')
    
    return data_bytes, cert_data

def post_certification_to_blockchain(w3, account, farm_id, signature_data):
    """Post a single certification to blockchain"""
    
    try:
        # Create transaction data
        data_bytes, cert_data = create_certification_contract_data(farm_id, signature_data)
        
        # Get transaction parameters
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        # Build transaction
        transaction = {
            'to': account.address,  # Self-transaction with data
            'value': 0,
            'gas': 100000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'data': data_bytes.hex(),
            'chainId': w3.eth.chain_id
        }
        
        # Sign and send transaction
        signed_txn = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        print(f"   📤 Transaction sent for {farm_id}")
        print(f"   🆔 TX Hash: {tx_hash.hex()}")
        
        # Wait for confirmation
        print(f"   ⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"   ✅ Transaction confirmed for {farm_id}")
            print(f"   📦 Block: {receipt.blockNumber}")
            print(f"   ⛽ Gas used: {receipt.gasUsed}")
            
            # Save receipt
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
            print(f"   ❌ Transaction failed for {farm_id}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error posting {farm_id} to blockchain: {e}")
        return None

def save_blockchain_receipts(receipts):
    """Save blockchain receipts to files"""
    
    # Save individual receipts
    for receipt in receipts:
        if receipt:
            receipt_file = os.path.join(BLOCKCHAIN_DIR, f"{receipt['farm_id']}_receipt.json")
            with open(receipt_file, 'w') as f:
                json.dump(receipt, f, indent=2)
    
    # Save combined receipts
    combined_file = os.path.join(BLOCKCHAIN_DIR, "all_receipts.json")
    with open(combined_file, 'w') as f:
        json.dump([r for r in receipts if r], f, indent=2)
    
    print(f"💾 Blockchain receipts saved to {BLOCKCHAIN_DIR}/")

def verify_blockchain_storage(w3, receipts):
    """Verify that data is properly stored on blockchain"""
    print("\n🔍 Verifying blockchain storage...")
    
    verified_count = 0
    for receipt in receipts:
        if not receipt:
            continue
            
        try:
            # Get transaction from blockchain
            tx = w3.eth.get_transaction(receipt['tx_hash'])
            
            # Verify data integrity
            stored_data = bytes.fromhex(tx['input'][2:]).decode('utf-8')  # Remove '0x' prefix
            stored_json = json.loads(stored_data)
            
            if stored_json['farm_id'] == receipt['farm_id']:
                print(f"   ✅ {receipt['farm_id']}: Data verified on blockchain")
                verified_count += 1
            else:
                print(f"   ❌ {receipt['farm_id']}: Data mismatch")
                
        except Exception as e:
            print(f"   ❌ {receipt['farm_id']}: Verification error: {e}")
    
    print(f"📊 Verification complete: {verified_count}/{len([r for r in receipts if r])} farms verified")

def main():
    print("🚀 Posting organic certification proofs to blockchain")
    print("🔗 Creating immutable audit trail\n")
    
    try:
        # Setup
        ensure_blockchain_directory()
        w3, account = setup_web3()
        signatures = load_signatures()
        
        # Post each certification to blockchain
        print(f"\n📤 Posting {len(signatures)} certifications to blockchain...")
        receipts = []
        
        for farm_id, signature_data in signatures.items():
            print(f"\n🏭 Processing {farm_id}...")
            receipt = post_certification_to_blockchain(w3, account, farm_id, signature_data)
            receipts.append(receipt)
            
            # Small delay to avoid nonce issues
            time.sleep(1)
        
        # Save receipts
        print(f"\n💾 Saving blockchain receipts...")
        save_blockchain_receipts(receipts)
        
        # Verify storage
        verify_blockchain_storage(w3, receipts)
        
        # Final summary
        successful_posts = len([r for r in receipts if r])
        print(f"\n📊 Blockchain Posting Summary:")
        print(f"   Total Farms: {len(signatures)}")
        print(f"   Successfully Posted: {successful_posts}")
        print(f"   Failed Posts: {len(signatures) - successful_posts}")
        print(f"   Network: {w3.eth.chain_id}")
        print(f"   Receipts Saved: {BLOCKCHAIN_DIR}/")
        
        if successful_posts == len(signatures):
            print("\n🎉 All certifications successfully posted to blockchain!")
        else:
            print(f"\n⚠️  {len(signatures) - successful_posts} certifications failed to post")
        
        print("🔒 Immutable audit trail created on blockchain")
        
    except Exception as e:
        print(f"❌ Error posting to blockchain: {e}")
        raise

if __name__ == "__main__":
    main()