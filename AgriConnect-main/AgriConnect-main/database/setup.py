import sqlite3
import os

def create_database():
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Connect to SQLite DB (will create if it doesn't exist)
    conn = sqlite3.connect('database/agri_connect.db')
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Equipment table with enhanced fields for rental
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price_per_day REAL NOT NULL,
        location TEXT,
        availability_status TEXT DEFAULT 'available',
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    ''')
    
    # Create Equipment Categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    ''')
    
    # Populate default equipment categories
    categories = [
        ('Tractors', 'Farm tractors and tractor accessories'),
        ('Harvesters', 'Harvesting and threshing equipment'),
        ('Seeders', 'Seed planting equipment'),
        ('Irrigation', 'Water pumps and irrigation systems'),
        ('Sprayers', 'Pesticide and fertilizer spraying equipment'),
        ('Hand Tools', 'Manual farming tools'),
        ('Other', 'Miscellaneous equipment')
    ]
    
    for category in categories:
        try:
            cursor.execute('INSERT INTO equipment_categories (name, description) VALUES (?, ?)', category)
        except sqlite3.IntegrityError:
            # Skip if category already exists
            pass
    
    # Create Equipment Rental Bookings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id INTEGER NOT NULL,
        renter_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipment_id) REFERENCES equipment (id),
        FOREIGN KEY (renter_id) REFERENCES users (id)
    )
    ''')
    
    # Create Workers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        skills TEXT,
        experience INTEGER,
        daily_rate REAL,
        availability_status TEXT DEFAULT 'available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create Equipment Reviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipment_id) REFERENCES equipment (id),
        FOREIGN KEY (reviewer_id) REFERENCES users (id)
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database and tables created successfully!")

if __name__ == "__main__":
    create_database() 