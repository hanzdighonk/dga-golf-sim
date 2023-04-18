import pandas as pd
from numpy import NaN
import requests
import sqlite3

X_API_KEY = "da2-gsrx5bibzbb4njvhl7t37wqyl4"
YEAR = 2023

STAT_IDS = ["120", "142", "143", "144", "02675", "112", "113", "114", "02414" ]

rows = []

for STAT_ID in STAT_IDS:
    payload = {
        "operationName": "StatDetails",
        "variables": {
            "tourCode": "R",
            "statId": STAT_ID,
            "year": YEAR,
            "eventQuery": None
        },
        "query": "query StatDetails($tourCode: TourCode!, $statId: String!, $year: Int, $eventQuery: StatDetailEventQuery) {\n  statDetails(\n    tourCode: $tourCode\n    statId: $statId\n    year: $year\n    eventQuery: $eventQuery\n  ) {\n    tourCode\n    year\n    displaySeason\n    statId\n    statType\n    tournamentPills {\n      tournamentId\n      displayName\n    }\n    yearPills {\n      year\n      displaySeason\n    }\n    statTitle\n    statDescription\n    tourAvg\n    lastProcessed\n    statHeaders\n    statCategories {\n      category\n      displayName\n      subCategories {\n        displayName\n        stats {\n          statId\n          statTitle\n        }\n      }\n    }\n    rows {\n      ... on StatDetailsPlayer {\n        __typename\n        playerId\n        playerName\n        country\n        countryFlag\n        rank\n        rankDiff\n        rankChangeTendency\n        stats {\n          statName\n          statValue\n          color\n        }\n      }\n      ... on StatDetailTourAvg {\n        __typename\n        displayName\n        value\n      }\n    }\n  }\n}"
    }

    page = requests.post("https://orchestrator.pgatour.com/graphql", json=payload, headers={"x-api-key": X_API_KEY})
    page.raise_for_status()

    data = page.json()["data"]["statDetails"]["rows"]
    data = filter(lambda item: item.get("__typename", NaN) == "StatDetailsPlayer", data)

    table = map(lambda item: {
        "STAT_ID": STAT_ID,
        "RANK": item["rank"],
        "PLAYER": item["playerName"],
        "AVERAGE": item["stats"][0]["statValue"],
    }, data)

    rows += table

df = pd.DataFrame(rows)

# Change data types of specified columns
df = df.astype({"STAT_ID": int, "RANK": int, "AVERAGE": float})

print(df)

# create a connection to the database
conn = sqlite3.connect('golf2.db')

# write the DataFrame to a table in the database
df.to_sql(name='PGA_stats', con=conn, if_exists='replace', index=False)

# close the connection to the database
conn.close()