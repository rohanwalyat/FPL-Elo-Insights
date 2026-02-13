#!/usr/bin/env python3
"""
Base classes for data ingestion modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
from dataclasses import dataclass, asdict

@dataclass
class IngestionMetadata:
    """Metadata for tracking data ingestion"""
    source: str
    ingestion_timestamp: str
    data_hash: str
    file_size_bytes: int
    record_count: Optional[int] = None
    data_quality_score: Optional[float] = None
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

class BaseIngester(ABC):
    """Abstract base class for all data ingesters"""
    
    def __init__(self, config: Any):
        self.config = config
        
    def calculate_hash(self, data: Any) -> str:
        """Calculate hash of data for change detection"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def save_metadata(self, metadata: IngestionMetadata, file_path: Path):
        """Save ingestion metadata alongside data file"""
        metadata_path = file_path.with_suffix('.metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2, default=str)
            
    @abstractmethod
    def ingest(self, date_partition: Optional[str] = None) -> Dict[str, Path]:
        """Execute the ingestion process"""
        pass
    
    @abstractmethod
    def validate(self, data: Any) -> List[str]:
        """Validate the ingested data"""
        pass
