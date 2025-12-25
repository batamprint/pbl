from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import hashlib
import random
import requests
import os
import json
import subprocess
from web3 import Web3

app = Flask(__name__)
app.secret_key = "blockchain_voting_secret"

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'votinguser'
app.config['MYSQL_PASSWORD'] = 'votingpass'
app.config['MYSQL_DB'] = 'voting'

# ================= BLOCKCHAIN (GANACHE) =================

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# Load ABI dari file terpisah
with open("blockchain/VotingABI.json") as f:
    VOTING_ABI = json.load(f)

# 🔥 LOAD CONTRACT ADDRESS OTOMATIS DARI FILE
CONTRACT_PATH = "blockchain/contract.json"

if not os.path.exists(CONTRACT_PATH):
    raise Exception("❌ File blockchain/contract.json tidak ditemukan. Jalankan deploy.py dulu.")

with open(CONTRACT_PATH) as f:
    contract_data = json.load(f)

VOTING_CONTRACT_ADDRESS = contract_data.get("address")

if not VOTING_CONTRACT_ADDRESS:
    raise Exception("❌ Contract address kosong. Jalankan deploy.py ulang.")

print("✅ Menggunakan contract address:", VOTING_CONTRACT_ADDRESS)

# Akun Ganache
GANACHE_ACCOUNT = w3.eth.accounts[0]
GANACHE_PRIVATE_KEY = "0x0e3352cf4a1e1d5609e554a2ea1a504e173b655b2f8d2b748225915033fcc39c"

def get_transactions_history():
    contract = get_voting_contract()
    transactions = []

    rows = fetch_all("""
        SELECT no_wa, tx_hash
        FROM siswa_request
        WHERE tx_hash IS NOT NULL
    """)

    for row in rows:
        try:
            tx_hash = row['tx_hash'].lower()
            no_wa = row['no_wa']

            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash

            tx = w3.eth.get_transaction(tx_hash)
            receipt = w3.eth.get_transaction_receipt(tx_hash)

            # Filter: hanya tx ke contract voting
            if not tx.to or tx.to.lower() != contract.address.lower():
                continue

            transactions.append({
                "hash": tx_hash,
                "from": no_wa,          # 🔥 WA DARI DATABASE
                "status": receipt.status,
                "verified": True
            })

        except Exception as e:
            print("❌ TX history error:", e)

    return transactions

def resequence_kandidat_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Set ulang variabel counter
        cursor.execute("SET @num := 0")

        # Update ID agar berurutan
        cursor.execute("""
            UPDATE kandidat
            SET id = (@num := @num + 1)
            ORDER BY id
        """)

        # Reset auto increment
        cursor.execute("ALTER TABLE kandidat AUTO_INCREMENT = 1")

        conn.commit()
        print("✅ ID kandidat berhasil disejajarkan (1,2,3,...)")

    except Exception as e:
        conn.rollback()
        print("❌ Gagal resequence kandidat:", e)
        raise e

    finally:
        cursor.close()
        conn.close()


def get_voting_contract():
    CONTRACT_PATH = "blockchain/contract.json"

    if not os.path.exists(CONTRACT_PATH):
        raise Exception("❌ contract.json tidak ditemukan, deploy dulu")

    with open(CONTRACT_PATH) as f:
        data = json.load(f)

    address = data.get("address")
    if not address:
        raise Exception("❌ Contract address kosong")

    return w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=VOTING_ABI
    )


def auto_deploy_contract():
    print("🚀 Auto deploying smart contract...")

    result = subprocess.run(
        ["python3", "blockchain/deploy.py"],
        capture_output=True,
        text=True
    )

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)

    if result.returncode != 0:
        raise Exception("❌ Deploy gagal, cek log di atas")

    print("✅ Deploy selesai")


def get_wa_by_tx_hash(tx_hash):
    try:
        result = fetch_all(
            "SELECT no_wa FROM siswa_request WHERE tx_hash = %s LIMIT 1",
            (tx_hash,)
        )
        if result:
            return result[0]['no_wa']
        return None
    except:
        return None

def send_vote_to_blockchain(candidate_id):
    contract = get_voting_contract()

    blockchain_index = int(candidate_id) - 1
    candidate_count = contract.functions.candidatesCount().call()

    if blockchain_index < 0 or blockchain_index >= candidate_count:
        raise Exception("Kandidat tidak valid")

    nonce = w3.eth.get_transaction_count(GANACHE_ACCOUNT)

    txn = contract.functions.vote(blockchain_index).build_transaction({
        "from": GANACHE_ACCOUNT,
        "nonce": nonce,
        "gas": 200000,
        "gasPrice": w3.to_wei("1", "gwei")
    })

    signed_txn = w3.eth.account.sign_transaction(txn, GANACHE_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex()

def get_blockchain_results():
    contract = get_voting_contract()
    results = []

    candidate_count = contract.functions.candidatesCount().call()

    for i in range(candidate_count):
        name, votes = contract.functions.getCandidate(i).call()
        results.append({
            "id": i + 1,
            "blockchain_index": i,
            "nama": name,
            "total": votes
        })

    return results

def get_kandidat_by_id(kandidat_id):
    """Ambil nama kandidat dari database MySQL berdasarkan ID"""
    try:
        result = fetch_all('SELECT nama FROM kandidat WHERE id = %s', (kandidat_id,))
        if result:
            return result[0]['nama']
        return f"Kandidat {kandidat_id}"
    except:
        return f"Kandidat {kandidat_id}"


# Custom flash function dengan tipe
def flash_message(message, category='info'):
    """Custom flash message dengan kategori"""
    if not session.get('_flashes'):
        session['_flashes'] = []
    session['_flashes'].append({'message': message, 'category': category})

# Override flash default
def flash(message, category='info'):
    flash_message(message, category)

# Context processor untuk flash messages
@app.context_processor
def inject_flash_messages():
    messages = []
    if session.get('_flashes'):
        messages = session.pop('_flashes')
    return dict(flash_messages=messages)

def get_db_connection():
    print("🔥 CONNECTING DB: voting")
    return mysql.connector.connect(
        host="localhost",
        user="votinguser",
        password="votingpass",
        database="voting"
    )


def fetch_all(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def execute_query(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("❌ SQL ERROR:", e)   # <=== INI PENTING
        return False
    finally:
        cursor.close()
        conn.close()

def get_admin_password():
    """Ambil password admin dari database"""
    try:
        result = fetch_all("SELECT password FROM admin WHERE username = 'admin' LIMIT 1")
        if result:
            return result[0]['password']
        return None
    except Exception as e:
        print(f"Error getting admin password: {e}")
        return None

# ==================== ROUTES HASIL VOTING ====================

@app.route('/admin/hasil')
def hasil():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    try:
        results = get_blockchain_results()
        total_votes = sum(r['total'] for r in results)
        results.sort(key=lambda x: x['total'], reverse=True)
    except Exception as e:
        flash('Error mengambil hasil voting dari blockchain!', 'error')
        results = []
        total_votes = 0
        print(f"Hasil voting error: {e}")

    return render_template(
        'hasil.html',
        results=results,
        total_votes=total_votes
    )

# ==================== ROUTES VOTING ====================

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if not session.get('voter_allowed'):
        flash('Silakan verifikasi kode terlebih dahulu!', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        try:
            kandidat_list = fetch_all('SELECT * FROM kandidat ORDER BY id')
            return render_template('vote.html', kandidat_list=kandidat_list)
        except Exception as e:
            flash('Error mengambil data kandidat!', 'error')
            print(f"Vote GET error: {e}")
            return redirect(url_for('login'))

    # ================= POST =================
    id_kandidat = request.form.get('id_kandidat')
    voter_wa = session.get('voter_wa')

    if not id_kandidat or not voter_wa:
        flash('Data voting tidak lengkap!', 'error')
        return redirect(url_for('vote'))

    try:
        print(f"🗳️ Voting kandidat ID: {id_kandidat}")
        print(f"📱 WhatsApp voter: {voter_wa}")

        # 1) Panggil blockchain HANYA SEKALI
        tx_hash = send_vote_to_blockchain(id_kandidat)
        if not tx_hash:
            raise Exception("Gagal mendapatkan tx_hash dari blockchain")

        # 2) Normalisasi format tx_hash
        tx_hash = tx_hash.lower()
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        # 3) Simpan tx_hash ke DB (mapping WA ↔ TX)
        ok = execute_query(
            """
            UPDATE siswa_request
            SET tx_hash = %s
            WHERE no_wa = %s
            """,
            (tx_hash, voter_wa)
        )

        if not ok:
            raise Exception("Gagal menyimpan tx_hash ke database")

        print(f"✅ TX HASH {tx_hash} tersimpan untuk WA {voter_wa}")

        session.clear()
        flash('✅ Vote berhasil tercatat di blockchain!', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        error_msg = str(e)

        if "Ganache tidak terhubung" in error_msg:
            flash('❌ Ganache tidak terhubung!', 'error')
        elif "Already voted" in error_msg or "sudah pernah voting" in error_msg:
            flash('❌ Account blockchain ini sudah pernah voting!', 'error')
        elif "Kandidat tidak valid" in error_msg or "Invalid candidate" in error_msg:
            flash('❌ Kandidat tidak valid!', 'error')
        else:
            flash(f'❌ Error: {error_msg}', 'error')

        print(f"Vote POST error: {e}")
        return redirect(url_for('vote'))

@app.route('/admin/hasil-blockchain')
def hasil_blockchain():
    if not session.get('admin'):
        return redirect(url_for('login'))

    contract = get_voting_contract()

    # ===== KANDIDAT =====
    results = []
    total_votes = 0
    candidate_count = contract.functions.candidatesCount().call()

    for i in range(candidate_count):
        name, votes = contract.functions.getCandidate(i).call()
        results.append({
            "index": i,
            "name": name,
            "votes": votes
        })
        total_votes += votes

    # ===== TRANSACTIONS (🔥 FIX UTAMA) =====
    transactions = get_transactions_history()

    print("DEBUG TRANSACTIONS:", transactions)

    return render_template(
        "hasil_blockchain.html",
        contract_address=contract.address,
        chain_id=w3.eth.chain_id,
        results=results,
        total_votes=total_votes,
        transactions=transactions
    )

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    try:
        # ambil data kandidat dari database
        kandidat_list = fetch_all("SELECT * FROM kandidat")
        total_kandidat = len(kandidat_list)

        # ambil kontrak aktif GANACHE
        contract = get_voting_contract()
        candidate_count = contract.functions.candidatesCount().call()

        total_votes = 0
        for i in range(candidate_count):
            name, votes = contract.functions.getCandidate(i).call()
            total_votes += votes

        available_codes = 0  # nanti bisa isi sesuai kebutuhan

        print("🔥 TOTAL KANDIDAT:", total_kandidat)
        print("🔥 TOTAL VOTES (BLOCKCHAIN):", total_votes)

    except Exception as e:
        print("❌ DASHBOARD ERROR:", e)
        total_kandidat = 0
        total_votes = 0
        available_codes = 0
        kandidat_list = []

    return render_template(
        "admin_dashboard.html",
        total_kandidat=total_kandidat,
        total_votes=total_votes,
        available_codes=available_codes,
        kandidat_debug=kandidat_list
    )

@app.route('/admin/add-kandidat', methods=['GET', 'POST'])
def add_kandidat():
    if not session.get('admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        nama = request.form.get('nama')

        if not nama:
            flash('❌ Nama kandidat tidak boleh kosong!', 'error')
            return redirect(url_for('add_kandidat'))

        ok = execute_query(
            'INSERT INTO kandidat (nama) VALUES (%s)',
            (nama,)
        )

        if not ok:
            flash('❌ Gagal insert kandidat!', 'error')
            return redirect(url_for('add_kandidat'))

        # 🔥 PAKSA ID BERURUTAN
        resequence_kandidat_table()

        # 🔥 REDEPLOY BLOCKCHAIN
        auto_deploy_contract()

        flash(
            "✅ Kandidat ditambahkan, ID diselaraskan, contract di-deploy ulang!",
            "success"
        )
        return redirect(url_for('admin_dashboard'))

    return render_template('add_kandidat.html')

@app.route('/admin/kelola-kandidat')
def kelola_kandidat():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    try:
        kandidat_list = fetch_all('SELECT * FROM kandidat ORDER BY id')
    except Exception as e:
        flash('Error mengambil data kandidat!')
        kandidat_list = []
        print(f"Kelola kandidat error: {e}")
    
    return render_template('kelola_kandidat.html', kandidat_list=kandidat_list)

@app.route('/admin/hapus-kandidat/<int:id>')
def hapus_kandidat(id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    try:
        ok = execute_query(
            'DELETE FROM kandidat WHERE id = %s',
            (id,)
        )

        if not ok:
            raise Exception("Gagal hapus kandidat")

        # 🔥 PAKSA ID BERURUTAN
        resequence_kandidat_table()

        # 🔥 REDEPLOY BLOCKCHAIN
        auto_deploy_contract()

        flash(
            "✅ Kandidat dihapus, ID diselaraskan, contract di-deploy ulang!",
            "success"
        )

    except Exception as e:
        print("❌ Hapus kandidat error:", e)
        flash(
            "❌ Gagal hapus kandidat / deploy ulang",
            "error"
        )

    return redirect(url_for('kelola_kandidat'))


# ==================== ROUTES UTAMA ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_type = request.form.get('login_type')
        
        if login_type == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')

            password_md5 = hashlib.md5(password.encode()).hexdigest()
            
            try:
                result = fetch_all(
                    'SELECT * FROM admin WHERE username = %s AND password = %s',
                    (username, password_md5)
                )
                
                if result:
                    admin = result[0]
                    session['admin'] = username
                    session['admin_id'] = admin['id']
                    flash(f'Selamat datang, {username}!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('login') + '?login_error=admin')
            except Exception as e:
                print(f"Admin login error: {e}")
                return redirect(url_for('login') + '?login_error=admin')
                
        elif login_type == 'siswa':
            flash('Silakan gunakan form WhatsApp untuk request kode', 'info')
    
    return render_template('login.html')


@app.route('/request-code', methods=['POST'])
def request_code():
    """Handle request kode voting via WhatsApp"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Data tidak valid'}), 400
    
    no_wa = data.get('no_wa', '').strip()
    
    if not no_wa:
        return jsonify({'success': False, 'message': 'Nomor WA kosong'}), 400
    
    if not no_wa.isdigit() or len(no_wa) < 10:
        return jsonify({'success': False, 'message': 'Format nomor WhatsApp tidak valid'}), 400
    
    try:
        result = fetch_all(
            "SELECT * FROM siswa_request WHERE no_wa = %s AND waktu_request > DATE_SUB(NOW(), INTERVAL 1 DAY)",
            (no_wa,)
        )
        
        if result:
            return jsonify({
                'success': False, 
                'message': 'Anda hanya bisa meminta kode 1x dalam 24 jam.'
            }), 400
        
        kode = str(random.randint(100000, 999999))
        
        db_success = execute_query(
            """INSERT INTO siswa_request (no_wa, kode, waktu_request, sudah_vote) 
               VALUES (%s, %s, NOW(), 0)""",
            (no_wa, kode)
        )
        
        if not db_success:
            return jsonify({
                'success': False, 
                'message': 'Gagal menyimpan ke database.'
            }), 500

        
        # Kirim pesan WhatsApp
        pesan = f"""Halo, ini kode voting kamu:

*KODE: {kode}*

Gunakan kode ini untuk login dan melakukan voting. Kode hanya berlaku sekali."""
        
        # Konfigurasi WhatsApp
        FONNTE_API_KEY = "kR4MEbxk5Z2Pnwt8iXS6"
        headers = {"Authorization": FONNTE_API_KEY}
        
        # Format nomor
        if no_wa.startswith('0'):
            phone_to_send = '62' + no_wa[1:]
        else:
            phone_to_send = no_wa
        
        try:
            wa_response = requests.post(
                "https://api.fonnte.com/send",
                headers=headers,
                data={
                    'target': phone_to_send,
                    'message': pesan,
                    'countryCode': '62'
                },
                timeout=30
            )
            
            if wa_response.status_code == 200:
                session.permanent = True
                session['pending_wa'] = no_wa
                session['pending_kode'] = kode
                
                return jsonify({
                    'success': True, 
                    'message': 'Kode telah dikirim ke WhatsApp.'
                })
            else:
                session['pending_wa'] = no_wa
                session['pending_kode'] = kode
                return jsonify({
                    'success': True, 
                    'message': 'Kode telah dibuat. Silakan cek WhatsApp Anda.'
                })
                
        except Exception as wa_error:
            session['pending_wa'] = no_wa
            session['pending_kode'] = kode
            return jsonify({
                'success': True, 
                'message': 'Kode telah dibuat. Silakan cek WhatsApp Anda.'
            })
            
    except Exception as e:
        print(f"Error in request_code: {e}")
        return jsonify({
            'success': False, 
            'message': 'Terjadi kesalahan server. Silakan coba lagi.'
        }), 500

@app.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    """Verifikasi kode voting"""
    
    if request.method == 'POST':
        kode_input = request.form.get('kode', '').strip()
        no_wa = session.get('pending_wa')
        stored_kode = session.get('pending_kode')
        
        if not no_wa or not kode_input:
            flash('Data tidak lengkap! Silakan request kode lagi.', 'error')
            return redirect(url_for('login'))
        
        try:
            # Verifikasi kode
            result = fetch_all(
                'SELECT * FROM siswa_request WHERE no_wa = %s AND kode = %s AND sudah_vote = 0',
                (no_wa, kode_input)
            )
            
            if result or (stored_kode and kode_input == stored_kode):
                # Update database
                db_success = execute_query(
                    'UPDATE siswa_request SET sudah_vote = 1 WHERE no_wa = %s AND kode = %s',
                    (no_wa, kode_input)
                )
                
                if db_success:
                    # Set session untuk voting
                    session['voter_allowed'] = True
                    session['voter_wa'] = no_wa
                    session.pop('pending_wa', None)
                    session.pop('pending_kode', None)
                    
                    flash('Kode berhasil diverifikasi!', 'success')
                    return redirect(url_for('vote'))
                else:
                    flash('Error update database!', 'error')
            else:
                flash('Kode salah atau sudah digunakan!', 'error')
                    
        except Exception as e:
            flash('Error saat verifikasi kode!', 'error')
            print(f"Verify code error: {e}")
    
    return render_template('verify_code.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)