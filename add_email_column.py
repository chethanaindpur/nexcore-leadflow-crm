import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN email TEXT")
    print("Email column added successfully")
except:
    print("Email column already exists")

conn.commit()
conn.close()