import sqlite3
import time
from models import get_db_connection

class WorkerProfile:
    @staticmethod
    def create(user_id, skills, experience, daily_rate, location=None, availability=None, tools_owned=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # First check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_profiles'")
            if not cursor.fetchone():
                # Create the table if it doesn't exist
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    skills TEXT NOT NULL,
                    experience TEXT,
                    daily_rate REAL NOT NULL,
                    location TEXT,
                    availability TEXT DEFAULT 'available',
                    tools_owned TEXT,
                    is_approved INTEGER DEFAULT 0,
                    rejection_reason TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                ''')
                conn.commit()
                print("Created worker_profiles table")

            # Insert the worker profile
            cursor.execute(
                '''
                INSERT INTO worker_profiles (
                    user_id, skills, experience, daily_rate,
                    location, availability, tools_owned
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (user_id, skills, experience, daily_rate, location, availability, tools_owned)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_user_id(user_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM worker_profiles WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_id(profile_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wp.*, u.name, u.phone, u.email
                FROM worker_profiles wp
                JOIN users u ON wp.user_id = u.id
                WHERE wp.id = ?
            ''', (profile_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_all(filters=None, limit=20, offset=0):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            query = '''
                SELECT wp.*, u.name, u.phone, u.email
                FROM worker_profiles wp
                JOIN users u ON wp.user_id = u.id
                WHERE 1=1
            '''
            params = []

            if filters:
                if 'skills' in filters and filters['skills']:
                    query += " AND wp.skills LIKE ?"
                    params.append(f"%{filters['skills']}%")

                if 'location' in filters and filters['location']:
                    query += " AND wp.location LIKE ?"
                    params.append(f"%{filters['location']}%")

                if 'max_rate' in filters and filters['max_rate']:
                    query += " AND wp.daily_rate <= ?"
                    params.append(filters['max_rate'])

                if 'tools_owned' in filters and filters['tools_owned']:
                    query += " AND wp.tools_owned LIKE ?"
                    params.append(f"%{filters['tools_owned']}%")

                if 'available_only' in filters and filters['available_only']:
                    query += " AND wp.availability = 'available'"

            query += " ORDER BY wp.daily_rate ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def update(profile_id, data):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Build the update query dynamically based on provided data
            update_fields = []
            params = []

            for key, value in data.items():
                if key in ['skills', 'experience', 'daily_rate', 'tools_owned', 'availability', 'location']:
                    update_fields.append(f"{key} = ?")
                    params.append(value)

            if not update_fields:
                return False

            query = f"UPDATE worker_profiles SET {', '.join(update_fields)} WHERE id = ?"
            params.append(profile_id)

            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

class WorkerHiring:
    @staticmethod
    def create(worker_profile_id, farmer_id, start_date, end_date, total_payment, work_description=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO worker_hirings (
                    worker_profile_id, farmer_id, start_date, end_date,
                    total_payment, status, work_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (worker_profile_id, farmer_id, start_date, end_date, total_payment, 'pending', work_description)
            )

            # Update worker availability
            cursor.execute(
                'UPDATE worker_profiles SET availability = ? WHERE id = ?',
                ('booked', worker_profile_id)
            )

            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_id(hiring_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.*,
                    u1.name as worker_name,
                    u2.name as farmer_name
                FROM worker_hirings h
                JOIN worker_profiles wp ON h.worker_profile_id = wp.id
                JOIN users u1 ON wp.user_id = u1.id
                JOIN users u2 ON h.farmer_id = u2.id
                WHERE h.id = ?
            ''', (hiring_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_worker(worker_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.*, u.name as farmer_name
                FROM worker_hirings h
                JOIN worker_profiles wp ON h.worker_profile_id = wp.id
                JOIN users u ON h.farmer_id = u.id
                WHERE wp.user_id = ?
                ORDER BY h.start_date DESC
            ''', (worker_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def find_by_farmer(farmer_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.*, u.name as worker_name
                FROM worker_hirings h
                JOIN worker_profiles wp ON h.worker_profile_id = wp.id
                JOIN users u ON wp.user_id = u.id
                WHERE h.farmer_id = ?
                ORDER BY h.start_date DESC
            ''', (farmer_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def update_status(hiring_id, status):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Validate status
            valid_statuses = ['pending', 'accepted', 'rejected', 'completed', 'cancelled']
            if status not in valid_statuses:
                return False

            cursor.execute(
                'UPDATE worker_hirings SET status = ? WHERE id = ?',
                (status, hiring_id)
            )

            # If the hiring is cancelled or rejected, update worker availability
            if status in ['rejected', 'cancelled', 'completed']:
                cursor.execute('''
                    UPDATE worker_profiles
                    SET availability = 'available'
                    WHERE id = (
                        SELECT worker_profile_id
                        FROM worker_hirings
                        WHERE id = ?
                    )
                ''', (hiring_id,))

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

class WorkerReview:
    @staticmethod
    def create(worker_profile_id, reviewer_id, rating, comment=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO worker_reviews (
                    worker_profile_id, reviewer_id, rating, comment
                ) VALUES (?, ?, ?, ?)
                ''',
                (worker_profile_id, reviewer_id, rating, comment)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_worker(worker_profile_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, u.name as reviewer_name
                FROM worker_reviews r
                JOIN users u ON r.reviewer_id = u.id
                WHERE r.worker_profile_id = ?
                ORDER BY r.created_at DESC
            ''', (worker_profile_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_average_rating(worker_profile_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT AVG(rating) as average_rating, COUNT(*) as review_count
                FROM worker_reviews
                WHERE worker_profile_id = ?
                ''',
                (worker_profile_id,)
            )
            result = cursor.fetchone()
            return result
        finally:
            conn.close()