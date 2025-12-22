from web3 import Web3
import json

print("="*60)
print("🔍 BLOCKCHAIN VOTING - DEBUG SCRIPT")
print("="*60)

# 1. Test Koneksi Ganache
print("\n1️⃣ Testing Ganache Connection...")
try:
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    
    if w3.is_connected():
        print("✅ Ganache is connected!")
        print(f"   Chain ID: {w3.eth.chain_id}")
        print(f"   Block Number: {w3.eth.block_number}")
    else:
        print("❌ Cannot connect to Ganache!")
        print("   Make sure Ganache is running on http://127.0.0.1:7545")
        exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit(1)

# 2. Test Accounts
print("\n2️⃣ Testing Accounts...")
try:
    accounts = w3.eth.accounts
    print(f"✅ Found {len(accounts)} accounts:")
    for i, acc in enumerate(accounts[:3]):  # Show first 3
        balance = w3.eth.get_balance(acc)
        print(f"   [{i}] {acc} - Balance: {w3.from_wei(balance, 'ether')} ETH")
except Exception as e:
    print(f"❌ Account error: {e}")

# 3. Load ABI
print("\n3️⃣ Loading ABI...")
try:
    with open("blockchain/VotingABI.json") as f:
        VOTING_ABI = json.load(f)
    print(f"✅ ABI loaded! {len(VOTING_ABI)} functions found")
    
    # Tampilkan function names
    func_names = [item['name'] for item in VOTING_ABI if item['type'] == 'function']
    print(f"   Functions: {', '.join(func_names)}")
except Exception as e:
    print(f"❌ ABI error: {e}")
    print("   Make sure VotingABI.json exists in blockchain/ folder")
    exit(1)

# 4. Test Contract Address
print("\n4️⃣ Testing Contract Address...")
CONTRACT_ADDRESS = input("Enter your contract address (or press Enter to skip): ").strip()

if not CONTRACT_ADDRESS:
    print("⚠️  No contract address provided. Please deploy contract first!")
    print("\n📝 To deploy contract, run:")
    print("   python deploy.py")
    exit(0)

# Check if address is valid
if not w3.is_address(CONTRACT_ADDRESS):
    print(f"❌ Invalid contract address: {CONTRACT_ADDRESS}")
    exit(1)

print(f"✅ Valid address: {CONTRACT_ADDRESS}")

# Check if contract exists
try:
    code = w3.eth.get_code(CONTRACT_ADDRESS)
    if code == b'' or code == '0x':
        print("❌ No contract found at this address!")
        print("   The contract might not be deployed or address is wrong.")
        exit(1)
    print(f"✅ Contract code exists! ({len(code)} bytes)")
except Exception as e:
    print(f"❌ Error checking contract: {e}")
    exit(1)

# 5. Initialize Contract
print("\n5️⃣ Initializing Contract...")
try:
    voting_contract = w3.eth.contract(
        address=CONTRACT_ADDRESS,
        abi=VOTING_ABI
    )
    print("✅ Contract initialized!")
except Exception as e:
    print(f"❌ Contract initialization error: {e}")
    exit(1)

# 6. Test Contract Functions
print("\n6️⃣ Testing Contract Functions...")

# Test candidatesCount()
try:
    count = voting_contract.functions.candidatesCount().call()
    print(f"✅ candidatesCount() = {count}")
    
    if count == 0:
        print("⚠️  No candidates in contract!")
        print("   Deploy contract with candidates first.")
        exit(1)
except Exception as e:
    print(f"❌ candidatesCount() error: {e}")
    exit(1)

# Test getCandidate() for each candidate
print("\n7️⃣ Testing Candidates...")
for i in range(count):
    try:
        name, votes = voting_contract.functions.getCandidate(i).call()
        print(f"✅ Candidate[{i}]: {name} - {votes} votes")
    except Exception as e:
        print(f"❌ getCandidate({i}) error: {e}")

# 8. Test Vote Function (DRY RUN)
print("\n8️⃣ Testing Vote Function (Dry Run)...")
GANACHE_ACCOUNT = w3.eth.accounts[0]
print(f"   Using account: {GANACHE_ACCOUNT}")

test_candidate = 0  # Vote untuk kandidat pertama
print(f"   Voting for candidate index: {test_candidate}")

try:
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(GANACHE_ACCOUNT)
    print(f"   Nonce: {nonce}")
    
    txn = voting_contract.functions.vote(test_candidate).build_transaction({
        'from': GANACHE_ACCOUNT,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.to_wei('1', 'gwei')
    })
    
    print("✅ Transaction built successfully!")
    print(f"   Gas: {txn['gas']}")
    print(f"   Gas Price: {txn['gasPrice']}")
    
except Exception as e:
    print(f"❌ Vote transaction error: {e}")
    print("\n🔍 Detailed error:")
    import traceback
    traceback.print_exc()

# 9. Private Key Check
print("\n9️⃣ Checking Private Key...")
private_key = input("Enter Ganache private key (or press Enter to skip): ").strip()

if private_key:
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    try:
        # Test signing
        account = w3.eth.account.from_key(private_key)
        print(f"✅ Private key valid!")
        print(f"   Address: {account.address}")
        
        if account.address.lower() != GANACHE_ACCOUNT.lower():
            print(f"⚠️  WARNING: Private key doesn't match account!")
            print(f"   Expected: {GANACHE_ACCOUNT}")
            print(f"   Got: {account.address}")
    except Exception as e:
        print(f"❌ Invalid private key: {e}")

# Summary
print("\n" + "="*60)
print("📊 SUMMARY")
print("="*60)
print(f"Ganache: ✅ Connected")
print(f"Contract: ✅ Deployed at {CONTRACT_ADDRESS}")
print(f"Candidates: ✅ {count} found")
print(f"Account: {GANACHE_ACCOUNT}")
print("="*60)

print("\n💡 If everything looks good, your app.py should have:")
print(f"   VOTING_CONTRACT_ADDRESS = \"{CONTRACT_ADDRESS}\"")
print(f"   GANACHE_PRIVATE_KEY = \"0x...\" (from Ganache)")
print("\n✅ Debug complete!")