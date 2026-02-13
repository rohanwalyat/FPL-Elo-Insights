#!/usr/bin/env python3
"""
Bronze Layer Data Ingestion

Handles raw data ingestion from multiple sources into the bronze layer
with minimal transformation - preserving original format and adding metadata.
"""

import os
import json
import requests
import pandas as pd
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from fpl_insights.core.medallion_config import MedallionConfig, DataSource, DataLayer
from fpl_insights.ingestion import (
    FPLApiIngester, 
    DraftApiIngester, 
    OddsApiIngester, 
    GitHubDataIngester
)

class BronzeIngestionManager:
    """Manages raw data ingestion into bronze layer using modular ingesters"""
    
    def __init__(self, config: MedallionConfig):
        self.config = config
        self.ingesters = {
            DataSource.FPL_API: FPLApiIngester(config),
            DataSource.DRAFT_LEAGUE: DraftApiIngester(config),
            DataSource.BETTING_ODDS: OddsApiIngester(config),
            DataSource.GITHUB_DATA: GitHubDataIngester(config)
        }
        
    def run_full_bronze_ingestion(self, league_id: str = None) -> Dict[str, Dict[str, Path]]:
        """Run complete bronze layer ingestion from all sources"""
        print("🥉 BRONZE LAYER INGESTION STARTED (Modular)")
        print("=" * 50)
        
        # Update league_id if provided
        if league_id:
            self.ingesters[DataSource.DRAFT_LEAGUE].league_id = league_id
            
        results = {}
        date_partition = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        for source, ingester in self.ingesters.items():
            try:
                print(f"\n--- Processing Source: {source.value} ---")
                source_results = ingester.ingest(date_partition=date_partition)
                results[source.value] = source_results
            except Exception as e:
                print(f"❌ Critical error in {source.value} ingester: {e}")
                results[source.value] = {}
        
        print(f"\n✅ Bronze ingestion complete!")
        print(f"Total sources processed: {len(results)}")
        
        return results

def main():
    """Main execution for bronze layer ingestion"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = MedallionConfig()
    ingester = BronzeIngestionManager(config)
    
    # Run ingestion with draft league ID from environment
    league_id = os.getenv('DRAFT_LEAGUE_ID', '25029')
    results = ingester.run_full_bronze_ingestion(league_id=league_id)
    
    print(f"\n📊 INGESTION SUMMARY:")
    for source, files in results.items():
        print(f"  {source}: {len(files)} files ingested")

if __name__ == "__main__":
    main()