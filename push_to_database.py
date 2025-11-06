from scrape import *
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()
conn_str = os.getenv("AZURE_POSTGRES_CONNECTION_STRING")

# Create SQLAlchemy engine
engine = create_engine(conn_str)

functions = [
    league_table,
    top_scorers,
    detail_top,
    player_table,
    all_time_table,
    all_time_winner_club,
    top_scorers_seasons,
    goals_per_season
]

for func in functions:
    try:
        df = func()
        if df.empty:
            print(f"⚠️ {func.__name__} returned empty DataFrame, skipping.")
            continue
        table_name = func.__name__
        print(f"📤 Uploading {table_name} to PostgreSQL...")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"✅ {table_name} uploaded successfully!")
    except Exception as e:
        print(f"❌ Error uploading {func.__name__}: {e}")

print("🎉 All uploads completed.")
