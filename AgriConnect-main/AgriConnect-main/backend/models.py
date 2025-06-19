import sqlite3
import bcrypt
import time
from config import DATABASE_PATH

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class User:
    @staticmethod
    def create(name, phone, email, password, role):
        # Double-check for existing users with the same phone or email
        # This helps prevent race conditions between checking and inserting
        if phone:
            existing_user = User.find_by_phone(phone)
            if existing_user:
                return {'error': 'phone_exists'}

        if email:
            existing_user = User.find_by_email(email)
            if existing_user:
                return {'error': 'email_exists'}

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO users (name, phone, email, password, role)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (name, phone, email, hashed_password, role)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            # Handle unique constraint violations
            error_msg = str(e).lower()
            if 'unique constraint' in error_msg:
                if 'phone' in error_msg:
                    return {'error': 'phone_exists'}
                elif 'email' in error_msg:
                    return {'error': 'email_exists'}
            print(f"Integrity error: {e}")
            return {'error': 'integrity_error'}
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {'error': 'database_error'}
        finally:
            conn.close()

    @staticmethod
    def find_by_phone(phone):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_email(email):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_id(user_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def verify_password(stored_password, provided_password):
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def update(user_id, update_data):
        if not update_data:
            return True  # Nothing to update

        # Build the SQL query dynamically based on the fields to update
        fields = []
        values = []

        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)

        # Add user_id to values for the WHERE clause
        values.append(user_id)

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""UPDATE users SET {', '.join(fields)} WHERE id = ?""",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

# OTP model for phone/email verification
class OTP:
    @staticmethod
    def create(contact, otp_code, contact_type='phone'):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Create OTP table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact TEXT NOT NULL,
                contact_type TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expiry INTEGER NOT NULL
            )
            ''')

            # Generate expiry timestamp
            expiry = int(time.time()) + 300  # 5 minutes from now

            # First delete any existing OTPs for this contact
            cursor.execute('DELETE FROM otps WHERE contact = ? AND contact_type = ?',
                          (contact, contact_type))

            # Insert new OTP
            cursor.execute(
                'INSERT INTO otps (contact, contact_type, otp_code, expiry) VALUES (?, ?, ?, ?)',
                (contact, contact_type, otp_code, expiry)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def verify(contact, otp_code, contact_type='phone'):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM otps WHERE contact = ? AND contact_type = ? AND otp_code = ?',
                (contact, contact_type, otp_code)
            )
            otp_record = cursor.fetchone()

            if not otp_record:
                return False

            # Check if OTP has expired
            current_time = int(time.time())
            if current_time > otp_record['expiry']:
                # Delete expired OTP
                cursor.execute('DELETE FROM otps WHERE id = ?', (otp_record['id'],))
                conn.commit()
                return False

            # OTP is valid, delete it to prevent reuse
            cursor.execute('DELETE FROM otps WHERE id = ?', (otp_record['id'],))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()