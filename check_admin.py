import sqlite3

connection = sqlite3.connect("shopnear.db")
cursor = connection.cursor()

cursor.execute("""
    SELECT id, name, username, email, role
    FROM users
    WHERE role = 'admin'
""")

print("\nADMIN ACCOUNTS:")

for account in cursor.fetchall():
    print(account)

connection.close()