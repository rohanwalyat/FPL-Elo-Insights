#!/usr/bin/env python3
"""
Official FPL API Ingester
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from .base import BaseIngester, IngestionMetadata
from fpl_insights.core.medallion_config import DataLayer, DataSource

class FPLApiIngester(BaseIngester):
    """Ingests data from official FPL API endpoints"""
    
    def __init__(self, config):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Data-Pipeline/1.0'
        })
        self.endpoints = {
            'bootstrap-static': 'https://fantasy.premierleague.com/api/bootstrap-static/',
            'fixtures': 'https://fantasy.premierleague.com/api/fixtures/'
        }

    def validate(self, data: Dict) -> List[str]:
        """Validate FPL API data structure"""
        errors = []
        
        # Validation for bootstrap-static
        if 'elements' in data and 'teams' in data:
            if not isinstance(data['elements'], list):
                errors.append("'elements' should be a list")
            elif len(data['elements']) < 500:
                errors.append(f"Too few players: {len(data['elements'])}")
        
        return errors

    def ingest(self, date_partition: Optional[str] = None) -> Dict[str, Path]:
        """Ingest data from FPL API"""
        if date_partition is None:
            date_partition = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
        target_path = self.config.get_layer_path(
            DataLayer.BRONZE, 
            DataSource.FPL_API, 
            date_partition
        )
        
        ingested_files = {}
        
        for endpoint_name, url in self.endpoints.items():
            try:
                print(f"📥 Ingesting {endpoint_name} from FPL API...")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                validation_errors = self.validate(data)
                data_hash = self.calculate_hash(data)
                
                # record_count logic varies by endpoint
                record_count = 0
                if isinstance(data, list):
                    record_count = len(data)
                elif isinstance(data, dict):
                    record_count = len(data.get('elements', data.get('teams', [])))
                
                metadata = IngestionMetadata(
                    source=f"fpl_api_{endpoint_name}",
                    ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
                    data_hash=data_hash,
                    file_size_bytes=len(json.dumps(data)),
                    record_count=record_count,
                    data_quality_score=1.0 if not validation_errors else 0.5,
                    validation_errors=validation_errors
                )
                
                file_path = target_path / f"{endpoint_name}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                self.save_metadata(metadata, file_path)
                ingested_files[endpoint_name] = file_path
                print(f"✅ Ingested {endpoint_name}: {record_count} records")
                
            except Exception as e:
                print(f"❌ Failed to ingest {endpoint_name}: {e}")
                
        return ingested_files
