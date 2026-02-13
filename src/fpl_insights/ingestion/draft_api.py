#!/usr/bin/env python3
"""
FPL Draft API Ingester
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

class DraftApiIngester(BaseIngester):
    """Ingests data from official FPL Draft API endpoints"""
    
    def __init__(self, config, league_id: Optional[str] = None):
        super().__init__(config)
        load_dotenv()
        self.league_id = league_id or os.getenv('DRAFT_LEAGUE_ID', '25029')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Data-Pipeline/1.0'
        })
        
    def validate(self, data: Any) -> List[str]:
        """Validate Draft API data"""
        errors = []
        if not data:
            errors.append("Empty response from API")
        return errors

    def ingest_league_data(self, date_partition: str) -> Dict[str, Path]:
        """Ingest league-specific data"""
        target_path = self.config.get_layer_path(
            DataLayer.BRONZE,
            DataSource.DRAFT_LEAGUE, 
            date_partition
        )
        
        ingested_files = {}
        endpoints = {
            'bootstrap-static': 'https://draft.premierleague.com/api/bootstrap-static',
            'league-details': f'https://draft.premierleague.com/api/league/{self.league_id}/details',
            'element-status': f'https://draft.premierleague.com/api/league/{self.league_id}/element-status'
        }
        
        for endpoint_name, url in endpoints.items():
            try:
                print(f"📥 Ingesting Draft {endpoint_name} for league {self.league_id}...")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                validation_errors = self.validate(data)
                data_hash = self.calculate_hash(data)
                
                metadata = IngestionMetadata(
                    source=f"draft_league_{endpoint_name}",
                    ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
                    data_hash=data_hash,
                    file_size_bytes=len(json.dumps(data)),
                    data_quality_score=1.0 if not validation_errors else 0.6,
                    validation_errors=validation_errors
                )
                
                file_path = target_path / f"{endpoint_name}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                self.save_metadata(metadata, file_path)
                ingested_files[endpoint_name] = file_path
                print(f"✅ Ingested {endpoint_name}")
                
            except Exception as e:
                print(f"❌ Failed to ingest {endpoint_name}: {e}")
                
        return ingested_files

    def ingest(self, date_partition: Optional[str] = None) -> Dict[str, Path]:
        """Execute the ingestion process"""
        if date_partition is None:
            date_partition = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
        # For now, Draft API ingester focuses on league data
        return self.ingest_league_data(date_partition)
