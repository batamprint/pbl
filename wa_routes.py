from flask import Blueprint, request, jsonify, session
import mysql.connector
import random
import requests  # Import requests langsung, bukan dari flask

wa_bp = Blueprint('wa', __name__)

# Konfigurasi WhatsApp API
FONNTE_API_URL = "https://api.fonnte.com/send"
FONNTE_API_KEY = "kR4MEbxk5Z2Pnwt8iXS6"  # Ganti dengan API key Anda

def get_db_connection():
    """Membuat koneksi database"""
    return mysql.connector.connect(
        host='localhost',
        user='votinguser',
        password='votingpass',
        database='voting'
    )

def send_whatsapp_message(phone_number, message):
    """Mengirim pesan WhatsApp menggunakan Fonnte API"""
    try:
        headers = {
            "Authorization": FONNTE_API_KEY
        }
        
        data = {
            'target': phone_number,
            'message': message,
            'countryCode': '62'  # Untuk Indonesia
        }
        
        response = requests.post(FONNTE_API_URL, headers=headers, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('status') == 'success'
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending WhatsApp: {e}")
        return False

@wa_bp.route('/request-code', methods=['POST'])
def request_code():
    """Handle request kode voting via WhatsApp"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Data tidak valid'}), 400
    
    no_wa = data.get('no_wa', '').strip()
    
    if not no_wa:
        return jsonify({'success': False, 'message': 'Nomor WA kosong'}), 400
    
    # Validasi format nomor WhatsApp
    if not no_wa.isdigit() or len(no_wa) < 10:
        return jsonify({'success': False, 'message': 'Format nomor WhatsApp tidak valid'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Cek apakah sudah request dalam 24 jam
        cursor.execute(
            "SELECT * FROM siswa_request WHERE no_wa = %s AND waktu_request > DATE_SUB(NOW(), INTERVAL 1 DAY)",
            (no_wa,)
        )
        existing_request = cursor.fetchone()
        
        if existing_request:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Anda hanya bisa meminta kode 1x dalam 24 jam.'
            }), 400
        
        # Generate kode 6 digit
        kode = str(random.randint(100000, 999999))
        
        # Simpan ke database - gunakan INSERT dengan ON DUPLICATE KEY UPDATE
        cursor.execute(
            """INSERT INTO siswa_request (no_wa, kode, waktu_request, sudah_vote) 
               VALUES (%s, %s, NOW(), 0)
               ON DUPLICATE KEY UPDATE 
               kode = VALUES(kode), 
               waktu_request = VALUES(waktu_request), 
               sudah_vote = VALUES(sudah_vote)""",
            (no_wa, kode)
        )
        
        conn.commit()
        
        # Kirim pesan WhatsApp
        pesan = f"""Halo, ini kode voting kamu:

*KODE: {kode}*

Gunakan kode ini untuk login dan melakukan voting. Kode hanya berlaku sekali."""
        
        # Hapus angka 0 di depan jika ada, karena countryCode sudah +62
        phone_to_send = no_wa[1:] if no_wa.startswith('0') else no_wa
        
        wa_sent = send_whatsapp_message(phone_to_send, pesan)
        
        if wa_sent:
            # Simpan di session untuk verifikasi nanti
            session['pending_wa'] = no_wa
            session['pending_kode'] = kode
            
            return jsonify({
                'success': True, 
                'message': 'Kode telah dikirim ke WhatsApp.'
            })
        else:
            # Jika gagal kirim WA, hapus data dari database
            cursor.execute("DELETE FROM siswa_request WHERE no_wa = %s AND kode = %s", (no_wa, kode))
            conn.commit()
            
            return jsonify({
                'success': False, 
                'message': 'Gagal mengirim kode ke WhatsApp. Silakan coba lagi.'
            }), 500
            
    except mysql.connector.IntegrityError as e:
        return jsonify({
            'success': False, 
            'message': 'Terjadi kesalahan database. Silakan coba lagi.'
        }), 500
    except Exception as e:
        print(f"Error in request_code: {e}")
        return jsonify({
            'success': False, 
            'message': 'Terjadi kesalahan server. Silakan coba lagi.'
        }), 500
    finally:
        cursor.close()
        conn.close()