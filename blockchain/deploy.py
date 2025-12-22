from solcx import compile_source, install_solc
from web3 import Web3
import json
import mysql.connector

print("="*60)
print("🚀 BLOCKCHAIN VOTING - DEPLOYMENT SCRIPT")
print("="*60)

# 1. Install compiler Solidity
print("\n📦 Installing Solidity compiler v0.8.0...")
install_solc("0.8.0")
print("✅ Compiler installed!")

# 2. Baca smart contract
print("\n📄 Reading Voting.sol...")
with open("blockchain/Voting.sol", "r") as file:
    contract_source_code = file.read()
print("✅ Contract loaded!")

# 3. Koneksi ke MySQL untuk ambil kandidat
print("\n🗄️  Connecting to MySQL database...")
try:
    db = mysql.connector.connect(
        host="localhost",
        user="votinguser",
        password="votingpass",
        database="voting"
    )
    cursor = db.cursor(dictionary=True)
    
    # Ambil semua kandidat dari database, urutkan berdasarkan ID
    cursor.execute("SELECT id, nama FROM kandidat ORDER BY id ASC")
    kandidat_list = cursor.fetchall()
    
    if not kandidat_list:
        print("❌ Tidak ada kandidat di database! Tambahkan kandidat terlebih dahulu.")
        exit(1)
    
    # Buat array nama kandidat untuk constructor
    candidate_names = [k['nama'] for k in kandidat_list]
    
    print(f"✅ Found {len(candidate_names)} kandidat:")
    for i, k in enumerate(kandidat_list):
        print(f"   [{i}] ID {k['id']}: {k['nama']}")
    
    cursor.close()
    db.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")
    print("⚠️  Using default candidates: Kandidat A, B, C")
    candidate_names = ["Kandidat A", "Kandidat B", "Kandidat C"]

# 4. Compile smart contract
print("\n🔨 Compiling smart contract...")
compiled_sol = compile_source(
    contract_source_code,
    output_values=["abi", "bin"],
    solc_version="0.8.0"
)

contract_id, contract_interface = compiled_sol.popitem()

abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

# 5. SIMPAN ABI
print("\n💾 Saving ABI to blockchain/VotingABI.json...")
with open("blockchain/VotingABI.json", "w") as f:
    json.dump(abi, f, indent=2)
print("✅ VotingABI.json created!")

# 6. Koneksi Ganache
print("\n🔗 Connecting to Ganache (http://127.0.0.1:7545)...")
try:
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    
    if not w3.is_connected():
        print("❌ Cannot connect to Ganache! Make sure Ganache is running.")
        exit(1)
    
    print(f"✅ Connected! Network ID: {w3.eth.chain_id}")
    
    w3.eth.default_account = w3.eth.accounts[0]
    print(f"📍 Using account: {w3.eth.default_account}")
    
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit(1)

# 7. Deploy contract
print(f"\n🚀 Deploying contract with {len(candidate_names)} kandidat...")
print(f"   Candidates: {candidate_names}")

try:
    Voting = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    tx_hash = Voting.constructor(candidate_names).transact()
    
    print(f"⏳ Waiting for transaction {tx_hash.hex()}...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    contract_address = tx_receipt.contractAddress
    
    print("\n" + "="*60)
    print("✅ CONTRACT DEPLOYED SUCCESSFULLY!")
    print("="*60)
    print(f"📍 Contract Address: {contract_address}")
    print(f"⛽ Gas Used: {tx_receipt.gasUsed}")
    print(f"🔗 Transaction Hash: {tx_hash.hex()}")
    print("="*60)
    
    # 8. Verifikasi deployment
    print("\n🔍 Verifying deployment...")
    voting_contract = w3.eth.contract(address=contract_address, abi=abi)
    
    candidate_count = voting_contract.functions.candidatesCount().call()
    print(f"✅ Candidates count in blockchain: {candidate_count}")
    
    if candidate_count == len(candidate_names):
        print("✅ Candidate count matches!")
        
        print("\n📋 Verifying each candidate:")
        for i in range(candidate_count):
            name, votes = voting_contract.functions.getCandidate(i).call()
            print(f"   [{i}] {name} - {votes} votes")
    else:
        print("⚠️  Warning: Candidate count mismatch!")
    
    # 9. Instruksi selanjutnya
    print("\n" + "="*60)
    print("📝 NEXT STEPS:")
    print("="*60)
    print("1. Copy contract address di atas")
    print("2. Paste ke app.py pada baris:")
    print("   VOTING_CONTRACT_ADDRESS = \"<address>\"")
    print("")
    print("3. Copy private key dari Ganache account pertama")
    print("4. Paste ke app.py pada baris:")
    print("   GANACHE_PRIVATE_KEY = \"0x...\"")
    print("")
    print("5. Jalankan Flask app:")
    print("   python app.py")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ Deployment failed: {e}")
    exit(1)

print("\n✅ Deployment script completed successfully!")
