from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
import mysql.connector
import hashlib
import random
import requests
from datetime import datetime
import csv
import io
import base64
import os
import json
from web3 import Web3

app = Flask(__name__)
app.secret_key = "blockchain_voting_secret"

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'votinguser'
app.config['MYSQL_PASSWORD'] = 'votingpass'
app.config['MYSQL_DB'] = 'voting'

# ================= BLOCKCHAIN (GANACHE) =================

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

# Load ABI dari file terpisah
with open("blockchain/VotingABI.json") as f:
    VOTING_ABI = json.load(f)

# Address hasil deploy smart contract
VOTING_CONTRACT_ADDRESS = "0xD85F6D40C6c83aD8aD039b2887ba2f2707aCD56f"

# Inisialisasi contract
voting_contract = w3.eth.contract(
    address=VOTING_CONTRACT_ADDRESS,
    abi=VOTING_ABI
)

# Akun Ganache
GANACHE_ACCOUNT = w3.eth.accounts[0]
GANACHE_PRIVATE_KEY = "0xdce76c76ef6bc844360995b93c99dc369844bccb6c7af94c90ccdeeb486f8719"

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
    """
    Kirim vote ke blockchain Ganache
    PENTING: Smart contract menggunakan array index (0, 1, 2, ...)
    Sedangkan database MySQL menggunakan ID (1, 2, 3, ...)
    Jadi kita perlu convert: candidate_id - 1
    """
    try:
        # Convert MySQL ID ke array index blockchain
        blockchain_index = int(candidate_id) - 1
        
        print(f"🗳️ Voting: MySQL ID {candidate_id} → Blockchain Index {blockchain_index}")
        
        # Check if Ganache is connected
        if not w3.is_connected():
            raise Exception("Ganache tidak terhubung! Pastikan Ganache berjalan di http://127.0.0.1:7545")
        
        # Check if candidate index is valid
        candidate_count = voting_contract.functions.candidatesCount().call()
        if blockchain_index >= candidate_count or blockchain_index < 0:
            raise Exception(f"Kandidat tidak valid! Index {blockchain_index} (Total: {candidate_count})")
        
        print(f"✅ Validasi OK. Building transaction...")
        
        nonce = w3.eth.get_transaction_count(GANACHE_ACCOUNT)

        txn = voting_contract.functions.vote(
            blockchain_index  # Gunakan index, bukan ID
        ).build_transaction({
            'from': GANACHE_ACCOUNT,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.to_wei('1', 'gwei')
        })

        print(f"✅ Transaction built. Signing...")

        signed_txn = w3.eth.account.sign_transaction(
            txn, GANACHE_PRIVATE_KEY
        )

        print(f"✅ Transaction signed. Sending...")

        tx_hash = w3.eth.send_raw_transaction(
            signed_txn.raw_transaction
        )

        print(f"⏳ Waiting for receipt...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ Vote berhasil! TX: {tx_hash.hex()}")
        print(f"   Gas used: {receipt['gasUsed']}")
        print(f"   Block: {receipt['blockNumber']}")
        
        return tx_hash.hex()
        
    except Exception as e:
        print(f"❌ Blockchain vote error: {e}")
        import traceback
        traceback.print_exc()
        raise e


def get_blockchain_results():
    """
    Ambil hasil voting dari blockchain
    Return: List of dict dengan format [{id, nama, total}, ...]
    """
    results = []
    try:
        # Ambil jumlah kandidat dari smart contract
        candidate_count = voting_contract.functions.candidatesCount().call()
        print(f"📊 Total kandidat di blockchain: {candidate_count}")
        
        for i in range(candidate_count):
            # Ambil data kandidat menggunakan getCandidate(index)
            name, vote_count = voting_contract.functions.getCandidate(i).call()
            
            # Convert array index ke MySQL ID
            mysql_id = i + 1
            
            results.append({
                "id": mysql_id,  # ID MySQL (1, 2, 3, ...)
                "blockchain_index": i,  # Index blockchain (0, 1, 2, ...)
                "nama": name,
                "total": vote_count
            })
        
        print(f"✅ Hasil blockchain: {results}")
        return results
    except Exception as e:
        print(f"❌ Get blockchain results error: {e}")
        return []


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

# Caesar Cipher Encryption/Decryption
CAESAR_SHIFT = 3

def caesar_encrypt(text, shift=CAESAR_SHIFT):
    """Enkripsi menggunakan Caesar Cipher dengan shift tertentu"""
    encrypted = ""
    for char in text:
        if char.isalpha():
            if char.islower():
                encrypted += chr((ord(char) - ord('a') + shift) % 26 + ord('a'))
            else:
                encrypted += chr((ord(char) - ord('A') + shift) % 26 + ord('A'))
        elif char.isdigit():
            encrypted += chr((ord(char) - ord('0') + shift) % 10 + ord('0'))
        else:
            encrypted += char
    return encrypted

def caesar_decrypt(text, shift=CAESAR_SHIFT):
    """Dekripsi menggunakan Caesar Cipher dengan shift tertentu"""
    decrypted = ""
    for char in text:
        if char.isalpha():
            if char.islower():
                decrypted += chr((ord(char) - ord('a') - shift) % 26 + ord('a'))
            else:
                decrypted += chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
        elif char.isdigit():
            decrypted += chr((ord(char) - ord('0') - shift) % 10 + ord('0'))
        else:
            decrypted += char
    return decrypted

def encrypt_data(data, shift=CAESAR_SHIFT):
    """Enkripsi data menggunakan Caesar Cipher dengan shift tertentu"""
    encrypted_text = caesar_encrypt(data, shift)
    metadata = f"SHIFT:{shift}:"
    return base64.urlsafe_b64encode((metadata + encrypted_text).encode()).decode()

def decrypt_data(encrypted_data, provided_shift=None):
    """Dekripsi data menggunakan Caesar Cipher"""
    try:
        decoded_data = base64.urlsafe_b64decode(encrypted_data).decode()
        
        if decoded_data.startswith("SHIFT:"):
            parts = decoded_data.split(":", 2)
            if len(parts) >= 3:
                stored_shift = int(parts[1])
                encrypted_text = parts[2]
                
                if provided_shift is not None:
                    shift_to_use = provided_shift
                else:
                    shift_to_use = stored_shift
                
                return caesar_decrypt(encrypted_text, shift_to_use)
        
        shift_to_use = provided_shift if provided_shift is not None else CAESAR_SHIFT
        return caesar_decrypt(decoded_data, shift_to_use)
        
    except:
        return None

def get_db_connection():
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
    """Execute INSERT/UPDATE/DELETE query"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Database execute error: {e}")
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
    """Tampilkan hasil voting dari blockchain"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    try:
        # Ambil hasil dari blockchain
        results = get_blockchain_results()
        
        # Hitung total votes
        total_votes = sum(r['total'] for r in results)
        
        # Urutkan berdasarkan vote count (descending)
        results.sort(key=lambda x: x['total'], reverse=True)
        
    except Exception as e:
        flash('Error mengambil hasil voting dari blockchain!', 'error')
        results = []
        total_votes = 0
        print(f"Hasil voting error: {e}")
    
    return render_template('download_hasil.html', results=results, total_votes=total_votes)

@app.route('/admin/download-hasil', methods=['GET', 'POST'])
def download_hasil():
    """Download hasil voting dari blockchain"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password_input = request.form.get('password')
        shift_input = request.form.get('shift', str(CAESAR_SHIFT))
        
        try:
            shift_value = int(shift_input)
            if shift_value < 1 or shift_value > 25:
                flash('Shift harus antara 1 dan 25!', 'error')
                return redirect(url_for('hasil'))
        except ValueError:
            flash('Shift harus berupa angka!', 'error')
            return redirect(url_for('hasil'))
        
        admin_password = get_admin_password()
        
        if not admin_password:
            flash('Error: Password admin tidak ditemukan!', 'error')
            return redirect(url_for('admin_dashboard'))
        
        password_input_md5 = hashlib.md5(password_input.encode()).hexdigest()
        
        try:
            # Ambil hasil dari blockchain
            results = get_blockchain_results()
            results.sort(key=lambda x: x['total'], reverse=True)
            
            # Buat CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Nama Kandidat', 'Total Suara'])
            for result in results:
                writer.writerow([result['id'], result['nama'], result['total']])
            
            csv_data = output.getvalue()
            output.close()
            
            # VERIFIKASI 2FA: PASSWORD + SHIFT HARUS BENAR
            password_correct = (password_input_md5 == admin_password)
            shift_correct = (shift_value == CAESAR_SHIFT)
            
            if password_correct and shift_correct:
                response = make_response(csv_data)
                response.headers["Content-Disposition"] = "attachment; filename=hasil_voting_blockchain.csv"
                response.headers["Content-type"] = "text/csv"
                flash('Download berhasil! Password dan shift benar.', 'success')
                return response
            else:
                encrypted_data = encrypt_data(csv_data, shift_value)
                response = make_response(encrypted_data)
                response.headers["Content-Disposition"] = "attachment; filename=hasil_voting_encrypted.txt"
                response.headers["Content-type"] = "text/plain"
                
                session['last_encryption_shift'] = shift_value
                
                if not password_correct and not shift_correct:
                    flash('Password salah dan shift tidak sesuai sistem! File terenkripsi.', 'warning')
                elif not password_correct:
                    flash('Password salah! File terenkripsi.', 'warning')
                elif not shift_correct:
                    flash(f'Shift tidak sesuai sistem (harus {CAESAR_SHIFT})! File terenkripsi dengan shift={shift_value}.', 'warning')
                
                return response
                
        except Exception as e:
            flash('Error download hasil!', 'error')
            print(f"Download hasil error: {e}")
    
    return render_template('download_hasil.html', default_shift=CAESAR_SHIFT)

@app.route('/admin/dekripsi-hasil', methods=['GET', 'POST'])
def dekripsi_hasil():
    """Halaman untuk mendekripsi file hasil voting"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'encrypted_file' not in request.files:
            flash('Tidak ada file yang diupload!', 'error')
            return redirect(url_for('dekripsi_hasil'))
        
        file = request.files['encrypted_file']
        shift_input = request.form.get('shift', str(CAESAR_SHIFT))
        
        if file.filename == '':
            flash('Tidak ada file yang dipilih!', 'error')
            return redirect(url_for('dekripsi_hasil'))
        
        try:
            shift_value = int(shift_input)
        except ValueError:
            flash('Shift harus berupa angka!', 'error')
            return redirect(url_for('dekripsi_hasil'))
        
        try:
            encrypted_content = file.read().decode('utf-8')
            decrypted_content = decrypt_data(encrypted_content, shift_value)
            
            if decrypted_content is None:
                flash(f'Gagal mendekripsi dengan shift={shift_value}. Coba shift yang berbeda.', 'error')
                return redirect(url_for('dekripsi_hasil'))
            
            if 'Kandidat' in decrypted_content and 'Total Suara' in decrypted_content:
                response = make_response(decrypted_content)
                response.headers["Content-Disposition"] = "attachment; filename=hasil_voting_dekripsi.csv"
                response.headers["Content-type"] = "text/csv"
                
                if shift_value == CAESAR_SHIFT:
                    flash(f'Dekripsi berhasil! Shift {shift_value} sesuai sistem.', 'success')
                else:
                    flash(f'Dekripsi berhasil dengan shift={shift_value}, tapi tidak sesuai sistem (harus {CAESAR_SHIFT}).', 'warning')
                
                return response
            else:
                flash(f'Dekripsi dengan shift={shift_value} tidak menghasilkan file CSV yang valid.', 'error')
                return redirect(url_for('dekripsi_hasil'))
                
        except Exception as e:
            flash(f'Error saat mendekripsi file: {str(e)}', 'error')
            print(f"Dekripsi file error: {e}")
            return redirect(url_for('dekripsi_hasil'))
    
    last_shift = session.get('last_encryption_shift', CAESAR_SHIFT)
    return render_template('dekripsi_hasil.html', default_shift=last_shift)

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

    # ================= KANDIDAT =================
    results = []
    candidate_count = voting_contract.functions.candidatesCount().call()
    total_votes = 0

    for i in range(candidate_count):
        name, votes = voting_contract.functions.getCandidate(i).call()
        results.append({
            'index': i,
            'name': name,
            'votes': votes
        })
        total_votes += votes

    # Hitung persen di backend
    for r in results:
        r['percent'] = round((r['votes'] / total_votes * 100), 1) if total_votes > 0 else 0

    # ================= AKUN GANACHE =================
    accounts_status = []
    for acc in w3.eth.accounts[:5]:
        accounts_status.append({
            'address': acc,
            'balance': float(w3.from_wei(w3.eth.get_balance(acc), 'ether'))
        })

    # ================= TRANSAKSI VOTING (FIX & STABIL) =================
    transactions = []
    current_block = w3.eth.block_number
    max_tx = 10
    found = 0

    for block_num in range(current_block, max(0, current_block - 50), -1):
        if found >= max_tx:
            break

        block = w3.eth.get_block(block_num, full_transactions=True)

        for tx in block.transactions:
            if found >= max_tx:
                break

            # FILTER KETAT: hanya tx ke contract voting + ada input
            if (
                tx.to
                and tx.to.lower() == voting_contract.address.lower()
                and tx.input
                and len(tx.input) >= 10
            ):
                receipt = w3.eth.get_transaction_receipt(tx.hash)
                tx_hash_hex = Web3.to_hex(tx.hash).lower()

                # ===== Decode vote(uint) =====
                vote_for = "-"
                try:
                    input_hex = tx.input.hex()
                    if len(input_hex) >= 74:
                        candidate_index = int(input_hex[-64:], 16)
                        candidate_name, _ = voting_contract.functions.getCandidate(candidate_index).call()
                        vote_for = f"[{candidate_index}] {candidate_name}"
                except:
                    pass

                # ===== HASH CHECKING (VALID GANACHE) =====
                try:
                    w3.eth.get_transaction(tx.hash)
                    verified = True
                except:
                    verified = False

                # ===== FROM: WA ↔ TX HASH =====
                wa_number = get_wa_by_tx_hash(tx_hash_hex)
                from_display = wa_number if wa_number else f"{tx['from'][:12]}...{tx['from'][-6:]}"

                transactions.append({
                    'block': block_num,
                    'hash': tx_hash_hex,
                    'from': from_display,
                    'vote_for': vote_for,
                    'status': receipt.status,
                    'verified': verified
                })

                found += 1

    return render_template(
        'hasil_blockchain.html',
        contract_address=voting_contract.address,
        chain_id=w3.eth.chain_id,
        block_number=w3.eth.block_number,
        results=results,
        total_votes=total_votes,
        accounts_status=accounts_status,
        transactions=transactions
    )

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    try:
        # Hitung statistik
        result_kandidat = fetch_all('SELECT COUNT(*) as total FROM kandidat')
        total_kandidat = result_kandidat[0]['total'] if result_kandidat else 0
        
        # Ambil total votes dari blockchain
        blockchain_results = get_blockchain_results()
        total_votes = sum(r['total'] for r in blockchain_results)
        
        result_codes = fetch_all('SELECT COUNT(*) as total FROM siswa_request WHERE sudah_vote = 0')
        available_codes = result_codes[0]['total'] if result_codes else 0
    except Exception as e:
        flash('Error mengambil data dashboard!')
        total_kandidat = total_votes = available_codes = 0
        print(f"Dashboard error: {e}")
    
    return render_template('admin_dashboard.html', 
                         total_kandidat=total_kandidat,
                         total_votes=total_votes,
                         available_codes=available_codes)

@app.route('/admin/add-kandidat', methods=['GET', 'POST'])
def add_kandidat():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nama = request.form.get('nama')
        
        try:
            execute_query('INSERT INTO kandidat (nama) VALUES (%s)', (nama,))
            flash('⚠️ Kandidat berhasil ditambahkan ke MySQL! Jangan lupa deploy ulang smart contract agar kandidat muncul di blockchain.', 'warning')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash('Error menambah kandidat!', 'error')
            print(f"Add kandidat error: {e}")
    
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
        execute_query('DELETE FROM kandidat WHERE id = %s', (id,))
        flash('⚠️ Kandidat berhasil dihapus dari MySQL! Jangan lupa deploy ulang smart contract.', 'warning')
    except Exception as e:
        flash('Error menghapus kandidat!', 'error')
        print(f"Hapus kandidat error: {e}")
    
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
