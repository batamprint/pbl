from web3 import Web3
import json

print("="*70)
print("🔍 GANACHE CONTRACT VIEWER")
print("="*70)

# Setup
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

with open("blockchain/VotingABI.json") as f:
    VOTING_ABI = json.load(f)

CONTRACT_ADDRESS = "0x56ab4327098870C4B66eDA2Cc9eB0BFBda97A9f2"

voting_contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=VOTING_ABI
)

print(f"\n📍 Contract Address: {CONTRACT_ADDRESS}")
print(f"🌐 Network: http://127.0.0.1:7545")
print(f"⛓️  Chain ID: {w3.eth.chain_id}")
print(f"📦 Current Block: {w3.eth.block_number}")

# ============================================================
# SECTION 1: CANDIDATES DATA
# ============================================================
print("\n" + "="*70)
print("📋 CANDIDATES DATA (from Ganache)")
print("="*70)

candidate_count = voting_contract.functions.candidatesCount().call()
print(f"\nTotal Candidates: {candidate_count}\n")

for i in range(candidate_count):
    name, votes = voting_contract.functions.getCandidate(i).call()
    
    # Calculate percentage
    total = sum([voting_contract.functions.getCandidate(j).call()[1] for j in range(candidate_count)])
    percentage = (votes / total * 100) if total > 0 else 0
    
    # Visual bar
    bar_length = int(votes * 5) if votes > 0 else 0
    bar = "█" * bar_length
    
    print(f"Index [{i}]")
    print(f"  Name:       {name}")
    print(f"  Votes:      {votes}")
    print(f"  Percentage: {percentage:.1f}%")
    print(f"  Bar:        {bar}")
    print()

# ============================================================
# SECTION 2: ACCOUNTS VOTING STATUS
# ============================================================
print("="*70)
print("👥 ACCOUNTS VOTING STATUS")
print("="*70)

accounts = w3.eth.accounts[:5]  # Show first 5 accounts
print(f"\nChecking first {len(accounts)} Ganache accounts:\n")

for i, account in enumerate(accounts):
    has_voted = voting_contract.functions.hasVoted(account).call()
    balance = w3.eth.get_balance(account)
    balance_eth = w3.from_wei(balance, 'ether')
    
    status = "✅ VOTED" if has_voted else "⬜ NOT VOTED"
    
    print(f"[{i}] {account}")
    print(f"    Status:  {status}")
    print(f"    Balance: {balance_eth:.4f} ETH")
    print()

# ============================================================
# SECTION 3: TRANSACTION HISTORY
# ============================================================
print("="*70)
print("📜 RECENT TRANSACTIONS (Last 10)")
print("="*70)

current_block = w3.eth.block_number
transactions_found = 0
max_transactions = 10

print(f"\nScanning blocks {max(0, current_block - 20)} to {current_block}...\n")

for block_num in range(current_block, max(0, current_block - 20), -1):
    if transactions_found >= max_transactions:
        break
    
    block = w3.eth.get_block(block_num, full_transactions=True)
    
    for tx in block['transactions']:
        if transactions_found >= max_transactions:
            break
        
        # Check if transaction is to our contract
        if tx['to'] and tx['to'].lower() == CONTRACT_ADDRESS.lower():
            receipt = w3.eth.get_transaction_receipt(tx['hash'])
            
            print(f"Transaction #{transactions_found + 1}")
            print(f"  Block:    {block_num}")
            print(f"  Hash:     {tx['hash'].hex()}")
            print(f"  From:     {tx['from']}")
            print(f"  Gas Used: {receipt['gasUsed']}")
            print(f"  Status:   {'✅ Success' if receipt['status'] == 1 else '❌ Failed'}")
            
            # Try to decode input data to see which candidate was voted for
            try:
                # Vote function signature is first 4 bytes
                if len(tx['input']) >= 10:  # 0x + 8 chars (4 bytes)
                    # Parse the input to get candidate ID
                    input_data = tx['input'].hex()
                    if input_data.startswith('0x0121b93f'):  # vote() function signature
                        # Next 64 chars (32 bytes) is the candidate index
                        candidate_index = int(input_data[10:], 16)
                        candidate_name, _ = voting_contract.functions.getCandidate(candidate_index).call()
                        print(f"  Vote For: [{candidate_index}] {candidate_name}")
            except:
                pass
            
            print()
            transactions_found += 1

if transactions_found == 0:
    print("  No transactions found for this contract yet.\n")

# ============================================================
# SECTION 4: SUMMARY
# ============================================================
print("="*70)
print("📊 SUMMARY")
print("="*70)

total_votes = sum([voting_contract.functions.getCandidate(i).call()[1] for i in range(candidate_count)])
voted_accounts = sum([1 for acc in w3.eth.accounts if voting_contract.functions.hasVoted(acc).call()])

print(f"\n  Total Candidates:    {candidate_count}")
print(f"  Total Votes:         {total_votes}")
print(f"  Accounts Voted:      {voted_accounts}/{len(w3.eth.accounts)}")
print(f"  Contract Address:    {CONTRACT_ADDRESS}")
print(f"  Current Block:       {w3.eth.block_number}")

# Winner
if total_votes > 0:
    results = [(voting_contract.functions.getCandidate(i).call()[0], 
                voting_contract.functions.getCandidate(i).call()[1]) 
               for i in range(candidate_count)]
    winner = max(results, key=lambda x: x[1])
    print(f"\n  🏆 WINNER: {winner[0]} ({winner[1]} votes)")

print("\n" + "="*70)
print("✅ View complete!")
print("="*70)