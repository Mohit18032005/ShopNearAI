
import sqlite3
from getpass import getpass
from werkzeug.security import generate_password_hash

connection = sqlite3.connect("shopnear.db")
cursor = connection.cursor()

username = "SOUMYA"
new_password = input("Enter your new admin password: ")

if len(new_password) < 8:
    print("Password must contain at least 8 characters.")
else:
    cursor.execute("""
        UPDATE users
        SET password_hash = ?
        WHERE username = ? AND role = 'admin'
    """, (generate_password_hash(new_password), username))

    connection.commit()

    if cursor.rowcount == 1:
        print("Admin password updated successfully!")
    else:
        print("Admin account not found.")

connection.close()
