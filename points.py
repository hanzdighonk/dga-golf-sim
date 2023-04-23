import csv
import sqlite3

# Connect to the SQLite database (or create one if it doesn't exist)
conn = sqlite3.connect('golf2.db')
cur = conn.cursor()

# Open the CSV file
with open('FedExPoints.csv', 'r') as csvfile:
    # Read the CSV file using the csv.reader
    csv_reader = csv.reader(csvfile)

    # Skip the header row (if your CSV file has a header)
    next(csv_reader, None)

    # Insert the CSV data into the SQLite table
    for row in csv_reader:
        cur.execute('INSERT INTO Points (Position, Normal, WGC, Major, Minor, Playoff) VALUES (?, ?, ?, ?, ?, ?)', row)

# Commit the changes and close the connection
conn.commit()
conn.close()
