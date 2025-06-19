import sqlite3
import time
from models import get_db_connection

class Equipment:
    @staticmethod
    def check_duplicate(owner_id, name, category):
        """
        Check if the user already has equipment with the same name and category.
        Returns the duplicate equipment if found, None otherwise.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT e.*, u.name as owner_name
                FROM equipment e
                JOIN users u ON e.owner_id = u.id
                WHERE e.owner_id = ? AND LOWER(e.name) = LOWER(?) AND LOWER(e.category) = LOWER(?)
                ''',
                (owner_id, name, category)
            )
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def create(owner_id, name, category, description, price_per_day, location=None, image_url=None):
        # First check for duplicates
        duplicate = Equipment.check_duplicate(owner_id, name, category)
        if duplicate:
            return None, "duplicate"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO equipment (
                    owner_id, name, category, description,
                    price_per_day, location, image_url, availability_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (owner_id, name, category, description, price_per_day, location, image_url, 'available')
            )
            conn.commit()
            return cursor.lastrowid, None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None, "database_error"
        finally:
            conn.close()

    @staticmethod
    def find_by_id(equipment_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, u.name as owner_name
                FROM equipment e
                JOIN users u ON e.owner_id = u.id
                WHERE e.id = ?
            ''', (equipment_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_all(filters=None, limit=20, offset=0):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            query = '''
                SELECT e.*, u.name as owner_name
                FROM equipment e
                JOIN users u ON e.owner_id = u.id
                WHERE 1=1
            '''
            params = []

            if filters:
                if 'category' in filters and filters['category']:
                    query += " AND e.category = ?"
                    params.append(filters['category'])

                if 'location' in filters and filters['location']:
                    query += " AND e.location LIKE ?"
                    params.append(f"%{filters['location']}%")

                if 'max_price' in filters and filters['max_price']:
                    query += " AND e.price_per_day <= ?"
                    params.append(filters['max_price'])

                if 'available_only' in filters and filters['available_only']:
                    query += " AND e.availability_status = 'available'"

                if 'search' in filters and filters['search']:
                    query += " AND (e.name LIKE ? OR e.description LIKE ?)"
                    search_term = f"%{filters['search']}%"
                    params.append(search_term)
                    params.append(search_term)

            query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def find_by_owner(owner_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            print(f"Finding equipment for owner ID: {owner_id}")
            cursor.execute(
                'SELECT * FROM equipment WHERE owner_id = ? ORDER BY created_at DESC',
                (owner_id,)
            )
            results = cursor.fetchall()
            print(f"Found {len(results)} equipment items for owner ID: {owner_id}")
            return results
        finally:
            conn.close()

    @staticmethod
    def update(equipment_id, data):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Build the update query dynamically based on provided data
            update_fields = []
            params = []

            for key, value in data.items():
                if key in ['name', 'category', 'description', 'price_per_day', 'location', 'image_url', 'availability_status']:
                    update_fields.append(f"{key} = ?")
                    params.append(value)

            if not update_fields:
                return False

            query = f"UPDATE equipment SET {', '.join(update_fields)} WHERE id = ?"
            params.append(equipment_id)

            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(equipment_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM equipment WHERE id = ?', (equipment_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_categories():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM equipment_categories ORDER BY name')
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def find_rented_by_user(user_id):
        """Find equipment rented by a specific user with active bookings"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Get current date in YYYY-MM-DD format
            current_date = time.strftime('%Y-%m-%d')

            print(f"Fetching rented equipment for user_id: {user_id}, current_date: {current_date}")

            cursor.execute(
                '''
                SELECT e.*, u.name as owner_name, b.start_date, b.end_date, b.status, b.id as booking_id
                FROM equipment e
                JOIN users u ON e.owner_id = u.id
                JOIN equipment_bookings b ON e.id = b.equipment_id
                WHERE b.renter_id = ?
                AND b.status = 'confirmed'
                AND b.end_date >= ?
                ORDER BY b.end_date ASC
                ''',
                (user_id, current_date)
            )
            results = cursor.fetchall()
            print(f"Found {len(results)} rented equipment items for user_id: {user_id}")
            return results
        finally:
            conn.close()


class Booking:
    @staticmethod
    def create(equipment_id, renter_id, start_date, end_date, total_price, notes=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO equipment_bookings (
                    equipment_id, renter_id, start_date, end_date,
                    total_price, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (equipment_id, renter_id, start_date, end_date, total_price, 'pending', notes)
            )

            # Update equipment availability
            cursor.execute(
                'UPDATE equipment SET availability_status = ? WHERE id = ?',
                ('booked', equipment_id)
            )

            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_id(booking_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, e.name as equipment_name, u.name as renter_name
                FROM equipment_bookings b
                JOIN equipment e ON b.equipment_id = e.id
                JOIN users u ON b.renter_id = u.id
                WHERE b.id = ?
            ''', (booking_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_renter(renter_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, e.name as equipment_name, u.name as owner_name
                FROM equipment_bookings b
                JOIN equipment e ON b.equipment_id = e.id
                JOIN users u ON e.owner_id = u.id
                WHERE b.renter_id = ?
                ORDER BY b.created_at DESC
            ''', (renter_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def find_by_owner(owner_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, e.name as equipment_name, u.name as renter_name
                FROM equipment_bookings b
                JOIN equipment e ON b.equipment_id = e.id
                JOIN users u ON b.renter_id = u.id
                WHERE e.owner_id = ?
                ORDER BY b.created_at DESC
            ''', (owner_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def update_status(booking_id, status):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Get the booking and equipment details
            cursor.execute('SELECT * FROM equipment_bookings WHERE id = ?', (booking_id,))
            booking = cursor.fetchone()

            if not booking:
                return False

            # Update booking status
            cursor.execute(
                'UPDATE equipment_bookings SET status = ? WHERE id = ?',
                (status, booking_id)
            )

            # Update equipment availability based on booking status
            equipment_id = booking['equipment_id']
            equipment_status = 'available'

            if status in ['pending', 'confirmed', 'ongoing']:
                equipment_status = 'booked'

            cursor.execute(
                'UPDATE equipment SET availability_status = ? WHERE id = ?',
                (equipment_status, equipment_id)
            )

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(booking_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Get the booking details first
            cursor.execute('SELECT equipment_id FROM equipment_bookings WHERE id = ?', (booking_id,))
            booking = cursor.fetchone()

            if not booking:
                return False

            # Delete the booking
            cursor.execute('DELETE FROM equipment_bookings WHERE id = ?', (booking_id,))

            # Update equipment availability to available
            cursor.execute(
                'UPDATE equipment SET availability_status = ? WHERE id = ?',
                ('available', booking['equipment_id'])
            )

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()


class Review:
    @staticmethod
    def create(equipment_id, reviewer_id, rating, comment=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO equipment_reviews (
                    equipment_id, reviewer_id, rating, comment
                ) VALUES (?, ?, ?, ?)
                ''',
                (equipment_id, reviewer_id, rating, comment)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_equipment(equipment_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, u.name as reviewer_name
                FROM equipment_reviews r
                JOIN users u ON r.reviewer_id = u.id
                WHERE r.equipment_id = ?
                ORDER BY r.created_at DESC
            ''', (equipment_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_average_rating(equipment_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT AVG(rating) as avg_rating FROM equipment_reviews WHERE equipment_id = ?',
                (equipment_id,)
            )
            result = cursor.fetchone()
            return result['avg_rating'] if result and result['avg_rating'] else 0
        finally:
            conn.close()