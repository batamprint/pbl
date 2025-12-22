from web3 import Web3
import json
import mysql.connector

print("="*60)
print("🔍 CHECK SYNC: MySQL vs Blockchain")
print("="*60)

# Setup Web3
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

with open("blockchain/VotingABI.json") as f:
    VOTING_ABI = json.load(f)

VOTING_CONTRACT_ADDRESS = "0x549EF15BE0f55Ca268e73543Be02985fCb9d4fb7"

voting_contract = w3.eth.contract(
    address=VOTING_CONTRACT_ADDRESS,
    abi=VOTING_ABI
)

# Get candidates from blockchain
print("\n📊 Candidates in BLOCKCHAIN:")
candidate_count = voting_contract.functions.candidatesCount().call()
blockchain_candidates = []
for i in range(candidate_count):
    name, votes = voting_contract.functions.getCandidate(i).call()
    blockchain_candidates.append({
        'index': i,
        'name': name,
        'votes': votes
    })
    print(f"   Index [{i}] = {name} ({votes} votes)")

# Get candidates from MySQL
print("\n📊 Candidates in MYSQL:")
try:
    db = mysql.connector.connect(
        host="localhost",
        user="votinguser",
        password="votingpass",
        database="voting"
    )
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kandidat ORDER BY id")
    mysql_candidates = cursor.fetchall()
    
    for k in mysql_candidates:
        print(f"   ID [{k['id']}] = {k['nama']}")
    
    cursor.close()
    db.close()
except Exception as e:
    print(f"❌ MySQL error: {e}")
    exit(1)

# Check mapping
print("\n🔗 ID MAPPING:")
print("   MySQL ID → Blockchain Index → Name")
print("   " + "-"*50)

all_match = True
for mysql_k in mysql_candidates:
    mysql_id = mysql_k['id']
    mysql_name = mysql_k['nama']
    blockchain_index = mysql_id - 1  # Convert ID to index
    
    if blockchain_index < len(blockchain_candidates):
        blockchain_name = blockchain_candidates[blockchain_index]['name']
        
        match = "✅" if mysql_name == blockchain_name else "❌"
        print(f"   {match} ID {mysql_id} → Index {blockchain_index} → {blockchain_name}")
        
        if mysql_name != blockchain_name:
            print(f"      ⚠️  MySQL: {mysql_name} ≠ Blockchain: {blockchain_name}")
            all_match = False
    else:
        print(f"   ❌ ID {mysql_id} → Index {blockchain_index} → NOT FOUND")
        all_match = False

print("\n" + "="*60)
if all_match and len(mysql_candidates) == len(blockchain_candidates):
    print("✅ SYNC OK! MySQL dan Blockchain cocok!")
else:
    print("❌ SYNC ERROR! Ada ketidakcocokan!")
    print("\n💡 Solusi:")
    print("   1. Hapus semua kandidat di MySQL")
    print("   2. Tambahkan kandidat sesuai urutan blockchain")
    print("   3. ATAU deploy ulang contract dengan data MySQL")
print("="*60)

# Test conversion
print("\n🧪 TEST CONVERSION:")
print("   MySQL ID → Blockchain Index")
for i in range(1, min(len(mysql_candidates) + 1, 6)):
    blockchain_idx = i - 1
    print(f"   ID {i} → Index {blockchain_idx}")