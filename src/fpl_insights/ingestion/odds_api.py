#!/usr/bin/env python3
"""
The Odds API Ingester
"""

import json
import requests
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from .base import BaseIngester, IngestionMetadata
from fpl_insights.core.medallion_config import DataLayer, DataSource

class OddsApiIngester(BaseIngester):
    """Ingests data from The Odds API"""
    
    def __init__(self, config):
        super().__init__(config)
        load_dotenv()
        self.api_key = os.getenv('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"
        self.session = requests.Session()
        
    def validate(self, data: Any) -> List[str]:
        """Validate Odds API data"""
        errors = []
        if not self.api_key:
            errors.append("ODDS_API_KEY not found in environment")
        if not data:
            errors.append("Empty response from API")
        return errors

    def ingest(self, date_partition: Optional[str] = None) -> Dict[str, Path]:
        """Execute the ingestion process"""
        if date_partition is None:
            date_partition = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
        if not self.api_key:
            print("❌ ODDS_API_KEY missing. Skipping Odds API ingestion.")
            return {}
            
        target_path = self.config.get_layer_path(
            DataLayer.BRONZE,
            DataSource.BETTING_ODDS,
            date_partition
        )
        
        ingested_files = {}
        
        # Ingest H2H and Totals markets
        markets = ['h2h', 'totals']
        
        for market in markets:
            try:
                print(f"📥 Ingesting {market} odds from The Odds API...")
                url = f"{self.base_url}/sports/{self.sport}/odds"
                params = {
                    'api_key': self.api_key,
                    'regions': 'uk',
                    'markets': market,
                    'oddsFormat': 'decimal'
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                validation_errors = self.validate(data)
                data_hash = self.calculate_hash(data)
                
                metadata = IngestionMetadata(
                    source=f"odds_api_{market}",
                    ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
                    data_hash=data_hash,
                    file_size_bytes=len(json.dumps(data)),
                    record_count=len(data) if isinstance(data, list) else 0,
                    data_quality_score=1.0 if not validation_errors else 0.8,
                    validation_errors=validation_errors
                )
                
                file_path = target_path / f"{market}_odds.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                self.save_metadata(metadata, file_path)
                ingested_files[market] = file_path
                print(f"✅ Ingested {market} odds")
                
            except Exception as e:
                print(f"❌ Failed to ingest {market} odds: {e}")
                
        return ingested_files
