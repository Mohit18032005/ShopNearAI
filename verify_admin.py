
import sqlite3
from getpass import getpass
from werkzeug.security import check_password_hash

connection = sqlite3.connect("shopnear.db")
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""
    SELECT * FROM users
    WHERE username = ? AND role = 'admin'
""", ("SOUMYA",))

user = cursor.fetchone()

if user:
    print("Admin account found.")

    password = input("Enter your new admin password: ")

    if check_password_hash(user["password_hash"], password):
        print("PASSWORD CHECK: SUCCESS")
    else:
        print("PASSWORD CHECK: FAILED")
else:
    print("Admin account not found.")

connection.close()
