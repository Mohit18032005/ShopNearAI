
import sqlite3

DATABASE_NAME = "shopnear.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

        
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('customer', 'shopkeeper', 'admin')
            ),
            created_at TEXT NOT NULL
        )
    """)

    # Add username column to existing databases
    cursor.execute("PRAGMA table_info(users)")
    columns = [column["name"] for column in cursor.fetchall()]

    if "username" not in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN username TEXT
        """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
        ON users(username)
        WHERE username IS NOT NULL
    """)


    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            shop TEXT NOT NULL,
            location TEXT NOT NULL,
            stock INTEGER NOT NULL,
            image TEXT
        )
    """)

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Import existing product categories
    cursor.execute("""
        INSERT OR IGNORE INTO categories (name)
        SELECT DISTINCT TRIM(category)
        FROM products
        WHERE category IS NOT NULL AND TRIM(category) != ''
    """)



    # Add new product columns to existing databases
    cursor.execute("PRAGMA table_info(products)")
    product_columns = [column["name"] for column in cursor.fetchall()]

    if "owner_id" not in product_columns:
        cursor.execute("""
            ALTER TABLE products
            ADD COLUMN owner_id INTEGER REFERENCES users(id)
        """)

    if "description" not in product_columns:
        cursor.execute("""
            ALTER TABLE products
            ADD COLUMN description TEXT
        """)

    # Remove the global UNIQUE restriction from product names
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type = 'table' AND name = 'products'
    """)

    products_table_sql = cursor.fetchone()["sql"].lower()
    products_table_sql = " ".join(products_table_sql.split())

    if "name text unique" in products_table_sql:

        cursor.execute("""
            CREATE TABLE products_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                shop TEXT NOT NULL,
                location TEXT NOT NULL,
                stock INTEGER NOT NULL,
                image TEXT,
                owner_id INTEGER REFERENCES users(id),
                description TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO products_new
            (id, name, category, price, shop, location,
             stock, image, owner_id, description)
            SELECT id, name, category, price, shop, location,
                   stock, image, owner_id, description
            FROM products
        """)

        cursor.execute("DROP TABLE products")

        cursor.execute("""
            ALTER TABLE products_new
            RENAME TO products
        """)


    # Reservations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product TEXT NOT NULL,
            price REAL NOT NULL,
            shop TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

        # Shops table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            shop_name TEXT NOT NULL,
            address TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """)

    # Add map coordinates to existing shops table
    cursor.execute("PRAGMA table_info(shops)")
    shop_columns = [
        column["name"] for column in cursor.fetchall()
    ]

    if "latitude" not in shop_columns:
        cursor.execute("""
                ALTER TABLE shops
                ADD COLUMN latitude REAL
            """)

    if "longitude" not in shop_columns:
        cursor.execute("""
                ALTER TABLE shops
                ADD COLUMN longitude REAL
            """)





        # Add customer ownership to existing reservations
    cursor.execute("PRAGMA table_info(reservations)")
    reservation_columns = [
        column["name"] for column in cursor.fetchall()
    ]

    if "user_id" not in reservation_columns:
        cursor.execute("""
            ALTER TABLE reservations
            ADD COLUMN user_id INTEGER REFERENCES users(id)
        """)

    # Add user_id column to existing reservations table
    cursor.execute("PRAGMA table_info(reservations)")
    reservation_columns = [
        column["name"] for column in cursor.fetchall()
    ]

    if "user_id" not in reservation_columns:
        cursor.execute("""
            ALTER TABLE reservations
            ADD COLUMN user_id INTEGER REFERENCES users(id)
        """)

    # Insert initial products only if the table is empty
        # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'shopkeeper')),
            created_at TEXT NOT NULL
        )
    """)

    # Add username column if it does not already exist
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column["name"] for column in cursor.fetchall()]

    if "username" not in user_columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN username TEXT
        """)
    # Ensure every username is unique
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
        ON users(username)
    """)

    cursor.execute("SELECT COUNT(*) FROM products")

    if cursor.fetchone()[0] == 0:

        initial_products = [
            ("Wireless Mouse", "Electronics", 599,
             "Tech World", "Kolkata", 12, "mouse.jpg"),

            ("Mechanical Keyboard", "Electronics", 1499,
             "Computer Hub", "Kolkata", 5, None),

            ("Cotton T-Shirt", "Fashion", 399,
             "Fashion Point", "Kolkata", 20, None),

            ("Notebook", "Stationery", 60,
             "Student Stationers", "Kolkata", 30, None),

            ("Football", "Sports", 799,
             "Sports Corner", "Kolkata", 8, None)
        ]

        cursor.executemany("""
            INSERT INTO products
            (name, category, price, shop, location, stock, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, initial_products)

    # Bargaining requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bargaining_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            shopkeeper_id INTEGER NOT NULL,
            offered_price REAL NOT NULL,
            counter_price REAL,
            message TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (shopkeeper_id) REFERENCES users(id)
        )
    """)


        # Add counter_price to existing bargaining tables if missing
    cursor.execute("PRAGMA table_info(bargaining_requests)")
    columns = [column[1] for column in cursor.fetchall()]

    if "counter_price" not in columns:
        cursor.execute("""
            ALTER TABLE bargaining_requests
            ADD COLUMN counter_price REAL
        """)


    connection.commit()
    connection.close()
