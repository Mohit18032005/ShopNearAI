
import sqlite3
from datetime import datetime
from getpass import getpass
from werkzeug.security import generate_password_hash

DATABASE_NAME = "shopnear.db"

print("\n--- ShopNear AI Admin Account Setup ---")

name = input("Enter admin name: ").strip()
username = input("Enter admin username: ").strip()
email = input("Enter admin email: ").strip().lower()
password = getpass("Enter admin password: ")

if not name or not username or not email or not password:
    print("All fields are required.")
    raise SystemExit

if len(password) < 8:
    print("Password must contain at least 8 characters.")
    raise SystemExit

connection = sqlite3.connect(DATABASE_NAME)
cursor = connection.cursor()

try:
    cursor.execute("""
        INSERT INTO users
        (name, username, email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        username,
        email,
        generate_password_hash(password),
        "admin",
        datetime.now().strftime("%d-%m-%Y %I:%M %p")
    ))

    connection.commit()
    print("\nAdmin account created successfully!")

except sqlite3.IntegrityError as error:

    print("\nDatabase error:", error)

    cursor.execute("""
        SELECT id, name, username, email, role
        FROM users
    """)

    existing_accounts = cursor.fetchall()

    print("\nAll registered accounts:")

    for account in existing_accounts:
        print(account)
