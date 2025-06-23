#!/usr/bin/env python3
import os, json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()  # loads RPC_URL & PRIVATE_KEY

RPC = os.getenv("RPC_URL")
KEY = os.getenv("PRIVATE_KEY")
if not RPC or not KEY:
    raise RuntimeError("Set RPC_URL and PRIVATE_KEY in .env")

w3 = Web3(Web3.HTTPProvider(RPC))
account = w3.eth.account.from_key(KEY)
print(f"Using account: {account.address}")

# Load signatures
with open('signatures.json') as f:
    sigs = json.load(f)

# Build and send one tx per farm
for farm, sig in sigs.items():
    # signature as hex data
    data = "0x" + sig  
    nonce = w3.eth.get_transaction_count(account.address)
    tx = {
        "to": account.address,      # sending to self
        "value": 0,                 # no ETH, just data
        "gas": 100000,
        "gasPrice": w3.to_wei('1', 'gwei'),
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "data": data
    }
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"Farm {farm}: tx sent → {tx_hash.hex()}")
