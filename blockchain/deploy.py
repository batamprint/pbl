from solcx import compile_source, install_solc
from web3 import Web3
import json
import mysql.connector
import os

print("=" * 60)
print("🚀 BLOCKCHAIN VOTING - DEPLOYMENT SCRIPT")
print("=" * 60)

# 1. Install compiler
install_solc("0.8.0")

# 2. Load contract
with open("blockchain/Voting.sol", "r") as file:
    contract_source_code = file.read()

# 3. Compile
compiled_sol = compile_source(
    contract_source_code,
    output_values=["abi", "bin"],
    solc_version="0.8.0"
)

_, contract_interface = compiled_sol.popitem()
abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

# 4. Save ABI
with open("blockchain/VotingABI.json", "w") as f:
    json.dump(abi, f, indent=2)

print("✅ ABI saved")

# 5. Connect Ganache
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
assert w3.is_connected(), "❌ Ganache not connected"

account = w3.eth.accounts[0]
w3.eth.default_account = account

print("📍 Using account:", account)

# 6. Deploy contract (TANPA ARGUMEN)
Voting = w3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = Voting.constructor().transact()
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

contract_address = tx_receipt.contractAddress
print("✅ Contract deployed at:", contract_address)

# 7. Save contract address
os.makedirs("blockchain", exist_ok=True)
with open("blockchain/contract.json", "w") as f:
    json.dump({"address": contract_address}, f, indent=2)

print("✅ Contract address saved to blockchain/contract.json")

# 8. Connect DB & fetch candidates
db = mysql.connector.connect(
    host="localhost",
    user="votinguser",
    password="votingpass",
    database="voting"
)
cursor = db.cursor(dictionary=True)
cursor.execute("SELECT nama FROM kandidat ORDER BY id ASC")
kandidat_list = cursor.fetchall()
cursor.close()
db.close()

# 9. Add candidates to blockchain
voting_contract = w3.eth.contract(
    address=contract_address,
    abi=abi
)

nonce = w3.eth.get_transaction_count(account)

for k in kandidat_list:
    tx = voting_contract.functions.addCandidate(k["nama"]).build_transaction({
        "from": account,
        "nonce": nonce,
        "gas": 200000,
        "gasPrice": w3.to_wei("1", "gwei")
    })

    signed_tx = w3.eth.account.sign_transaction(
        tx,
        private_key="0x0e3352cf4a1e1d5609e554a2ea1a504e173b655b2f8d2b748225915033fcc39c"
    )

    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"➕ Kandidat '{k['nama']}' ditambahkan ke blockchain")
    nonce += 1

# 10. Final verification
count = voting_contract.functions.candidatesCount().call()
print(f"🎉 Total kandidat di blockchain: {count}")

print("=" * 60)
print("✅ DEPLOYMENT SELESAI & SIAP DIGUNAKAN")
print("=" * 60)
