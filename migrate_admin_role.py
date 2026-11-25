

import sqlite3

DATABASE_NAME = "shopnear.db"

connection = sqlite3.connect(DATABASE_NAME)

try:
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("BEGIN TRANSACTION")

    cursor.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('customer', 'shopkeeper', 'admin')
            ),
            created_at TEXT NOT NULL,
            username TEXT UNIQUE
        )
    """)

    cursor.execute("""
        INSERT INTO users_new
        (id, name, email, password_hash, role, created_at, username)
        SELECT id, name, email, password_hash, role, created_at, username
        FROM users
    """)

    cursor.execute("DROP TABLE users")

    cursor.execute("""
        ALTER TABLE users_new RENAME TO users
    """)

    connection.commit()

    print("Database migration successful!")
    print("Customer, shopkeeper and admin roles are now supported.")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)

finally:
    connection.close()
