#!/usr/bin/env python3
"""
Bronze Loader: Loads raw files from the bronze filesystem into PostgreSQL bronze schema.
"""

import os
import json
import pandas as pd
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from fpl_insights.core.medallion_config import MedallionConfig, DataSource, DataLayer

class BronzeLoader:
    def __init__(self, config: MedallionConfig):
        self.config = config
        load_dotenv()
        self.conn_params = {
            'host': os.getenv('PGHOST', 'localhost'),
            'port': os.getenv('PGPORT', '5432'),
            'database': os.getenv('PGDATABASE', 'fpl_elo'),
            'user': os.getenv('PGUSER', 'postgres'),
            'password': os.getenv('PGPASSWORD')
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def create_bronze_schema(self):
        """Create the bronze schema if it doesn't exist"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
                conn.commit()
                print("✅ Bronze schema ready.")

    def load_json_to_postgres(self, file_path: Path, source_prefix: str):
        """Loads a JSON file, splitting keys like 'elements', 'teams' into separate tables"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            # Known FPL API keys to split
            keys_to_split = ['elements', 'teams', 'events', 'fixtures', 'picks', 'managers']
            found_keys = [k for k in keys_to_split if k in data]
            
            if found_keys:
                for key in found_keys:
                    table_name = f"{source_prefix}_{key}"
                    df = pd.DataFrame(data[key])
                    self._process_and_load_df(df, table_name)
                return

            rows = [data] # Single object
        else:
            rows = data # Already a list

        df = pd.DataFrame(rows)
        self._process_and_load_df(df, source_prefix)

    def _process_and_load_df(self, df: pd.DataFrame, table_name: str):
        """Helper to serialize and load DF"""
        if df.empty:
            print(f"⚠️  Skipping empty table bronze.{table_name}")
            return

        # Stringify nested columns
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
                
        self._load_df_to_table(df, table_name)

    def load_csv_to_postgres(self, file_path: Path, table_name: str):
        """Loads a CSV file into a PostgreSQL table in bronze schema"""
        df = pd.read_csv(file_path)
        self._load_df_to_table(df, table_name)

    def _load_df_to_table(self, df: pd.DataFrame, table_name: str):
        """Internal helper to load DataFrame to Postgres"""
        from sqlalchemy import create_engine
        import urllib.parse
        
        user = self.conn_params['user']
        password = urllib.parse.quote_plus(self.conn_params['password'])
        host = self.conn_params['host']
        port = self.conn_params['port']
        db = self.conn_params['database']
        
        engine_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        engine = create_engine(engine_url)
        
        # Load to bronze schema
        df.to_sql(table_name, engine, schema='bronze', if_exists='replace', index=False)
        print(f"✅ Loaded {len(df)} records into bronze.{table_name}")

    def load_latest_bronze_files(self):
        """Discovers and loads latest files for each source from Bronze filesystem"""
        self.create_bronze_schema()
        
        # Discover latest date partition
        bronze_root = self.config.project_root / "data" / "raw"
        if not bronze_root.exists():
            print("❌ Bronze root not found.")
            return

        for source_dir in bronze_root.iterdir():
            if not source_dir.is_dir(): continue
            
            daily_dir = source_dir / "daily"
            if not daily_dir.exists(): continue
            
            # Get latest date partition
            partitions = sorted([d for d in daily_dir.iterdir() if d.is_dir()])
            if not partitions: continue
            
            latest_partition = partitions[-1]
            source_name = source_dir.name
            
            print(f"📦 Loading {source_name} from {latest_partition.name}...")
            
            for f in latest_partition.iterdir():
                if f.suffix == '.json' and not f.name.endswith('.metadata.json'):
                    source_prefix = f"{source_name}_{f.stem}"
                    self.load_json_to_postgres(f, source_prefix)
                elif f.suffix == '.csv' and not f.name.endswith('.metadata.json'):
                    table_name = f"{source_name}_{f.stem}"
                    self.load_csv_to_postgres(f, table_name)

if __name__ == "__main__":
    config = MedallionConfig()
    # Need sqlalchemy for loader
    loader = BronzeLoader(config)
    loader.load_latest_bronze_files()
