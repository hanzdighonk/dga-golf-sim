import sqlite3

def update_players_table():
    conn = sqlite3.connect("golf2.db")
    c = conn.cursor()

    # Get all players currently in the Players table
    c.execute("SELECT Name FROM Players")
    existing_players = set(row[0] for row in c.fetchall())

    # Get all players in the PGA_Stats table
    c.execute("SELECT STAT_ID, RANK, PLAYER, AVERAGE FROM PGA_Stats")
    pga_stats = c.fetchall()

    # Add new players to the Players table if they don't already exist
    for row in pga_stats:
        stat_id = row[0]
        rank = row[1]
        name = row[2]
        value = row[3]

        if name not in existing_players:
            c.execute("INSERT INTO Players (Name, tour, human) VALUES (?, ?, ?)", (name, 'PGA', 0))
            existing_players.add(name)
            if c.rowcount > 0:
                print(f"Inserted new player {name} into Players table.")

        if stat_id == 120:
            c.execute("UPDATE Players SET ScoringAVG=? WHERE Name=?", (rank, name))
            if c.rowcount > 0:
                print(f"Updated ScoringAVG for player {name} to {rank}.")

        elif stat_id == 2675:
            c.execute("UPDATE Players SET ShotsGained=? WHERE Name=?", (rank, name))
            if c.rowcount > 0:
                print(f"Updated ShotsGained for player {name} to {rank}.")

        elif stat_id == 142:
            c.execute("UPDATE Players SET Par3avg=? WHERE Name=?", (rank, name))
            if c.rowcount > 0:
                print(f"Updated Par3avg for player {name} to {rank}.")

        elif stat_id == 143:
            c.execute("UPDATE Players SET Par4avg=? WHERE Name=?", (rank, name))
            if c.rowcount > 0:
                print(f"Updated Par4avg for player {name} to {rank}.")

        elif stat_id == 144:
            c.execute("UPDATE Players SET Par5avg=? WHERE Name=?", (rank, name))
            if c.rowcount > 0:
                print(f"Updated Par5avg for player {name} to {rank}.")
                
        elif stat_id == 112:
            c.execute("UPDATE Players SET Par3BirdBetter=? WHERE Name=?", (value, name))
            if c.rowcount > 0:
                print(f"Updated Par3BirdBette for player {name} to {value}.")

        elif stat_id == 113:
            c.execute("UPDATE Players SET Par4BirdBetter=? WHERE Name=?", (value, name))
            if c.rowcount > 0:
                print(f"Updated Par4BirdBette for player {name} to {value}.")
                
        elif stat_id == 114:
            c.execute("UPDATE Players SET Par5BirdBetter=? WHERE Name=?", (value, name))
            if c.rowcount > 0:
                print(f"Updated Par5BirdBette for player {name} to {value}.")

        elif stat_id == 2414:
            c.execute("UPDATE Players SET BogeyAvoid=? WHERE Name=?", (value, name))
            if c.rowcount > 0:
                print(f"Updated BogeyAvoid for player {name} to {value}.")
    
    # Compute the Rating column as the sum of the other columns
    c.execute("UPDATE Players SET Rating = ROUND(99 - (ScoringAVG + ShotsGained) / 8)")
    if c.rowcount > 0:
        print("Updated Ratings for all players in Players table.")

    conn.commit()
    conn.close()

update_players_table()
