#!/usr/bin/env python3
"""
Medallion Architecture Orchestrator

Orchestrates the complete medallion data pipeline:
1. Bronze Layer: Raw data ingestion from all sources
2. Silver Layer: Data cleaning, validation, and normalization  
3. Gold Layer: Business logic, aggregations, and analytics

Usage:
    python medallion_orchestrator.py [--layer bronze|silver|gold|all] [--source fpl|github|draft|all]
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from medallion_config import MedallionConfig, DataSource, DataLayer
from bronze_ingestion import BronzeIngestionManager
from silver_transformation import SilverTransformationManager
from gold_aggregation import GoldAggregationManager

class MedallionOrchestrator:
    """Orchestrates the complete medallion data pipeline"""
    
    def __init__(self, config: MedallionConfig = None):
        self.config = config or MedallionConfig()
        self.bronze_manager = BronzeIngestionManager(self.config)
        self.silver_manager = SilverTransformationManager(self.config)
        self.gold_manager = GoldAggregationManager(self.config)
        
        # Pipeline execution tracking
        self.execution_log = []
        self.start_time = None
        self.errors = []
        
    def log_step(self, layer: str, step: str, status: str, details: str = ""):
        """Log pipeline execution step"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'layer': layer,
            'step': step,
            'status': status,
            'details': details
        }
        self.execution_log.append(log_entry)
        
        # Print status
        status_emoji = {"started": "🔄", "success": "✅", "error": "❌", "warning": "⚠️"}
        emoji = status_emoji.get(status, "ℹ️")
        print(f"{emoji} [{layer.upper()}] {step}: {details}")
    
    def run_bronze_layer(self, sources: List[str] = None) -> Dict:
        """Execute bronze layer ingestion"""
        self.log_step("bronze", "ingestion", "started", "Raw data ingestion from all sources")
        
        try:
            if sources is None or 'all' in sources:
                # Run full bronze ingestion
                league_id = os.getenv('DRAFT_LEAGUE_ID', '25029')
                results = self.bronze_manager.run_full_bronze_ingestion(league_id=league_id)
            else:
                # Run selective ingestion
                results = {}
                if 'fpl' in sources:
                    results['fpl_api'] = self.bronze_manager.ingest_fpl_api_data()
                if 'github' in sources:
                    github_data_path = self.config.project_root / "data" / "2025-2026"
                    if github_data_path.exists():
                        results['github_data'] = self.bronze_manager.ingest_github_csv_data(github_data_path)
                if 'draft' in sources:
                    league_id = os.getenv('DRAFT_LEAGUE_ID', '25029')
                    results['draft_league'] = self.bronze_manager.ingest_draft_league_data(league_id)
            
            total_files = sum(len(files) for files in results.values())
            self.log_step("bronze", "ingestion", "success", f"Ingested {total_files} files from {len(results)} sources")
            return results
            
        except Exception as e:
            self.log_step("bronze", "ingestion", "error", str(e))
            self.errors.append(f"Bronze layer error: {e}")
            return {}
    
    def run_silver_layer(self) -> Dict:
        """Execute silver layer transformation"""
        self.log_step("silver", "transformation", "started", "Data cleaning and validation")
        
        try:
            results = self.silver_manager.run_full_silver_transformation()
            
            # Count successful transformations
            success_count = sum(1 for source_results in results.values() 
                              for result in source_results.values() 
                              if result.success)
            total_count = sum(len(source_results) for source_results in results.values())
            
            if success_count == total_count:
                self.log_step("silver", "transformation", "success", 
                            f"All {success_count} transformations completed successfully")
            else:
                self.log_step("silver", "transformation", "warning", 
                            f"{success_count}/{total_count} transformations successful")
            
            # Log any errors
            for source, source_results in results.items():
                for data_type, result in source_results.items():
                    if not result.success:
                        error_msg = f"{source}.{data_type}: {', '.join(result.errors)}"
                        self.errors.append(f"Silver layer error: {error_msg}")
            
            return results
            
        except Exception as e:
            self.log_step("silver", "transformation", "error", str(e))
            self.errors.append(f"Silver layer error: {e}")
            return {}
    
    def run_gold_layer(self) -> Dict:
        """Execute gold layer aggregation"""
        self.log_step("gold", "aggregation", "started", "Business logic and analytics")
        
        try:
            results = self.gold_manager.run_full_gold_aggregation()
            
            self.log_step("gold", "aggregation", "success", 
                        f"Generated {len(results)} analytics datasets")
            return results
            
        except Exception as e:
            self.log_step("gold", "aggregation", "error", str(e))
            self.errors.append(f"Gold layer error: {e}")
            return {}
    
    def run_full_pipeline(self, sources: List[str] = None, skip_layers: List[str] = None) -> Dict:
        """Execute complete medallion pipeline"""
        self.start_time = time.time()
        skip_layers = skip_layers or []
        
        print("🏗️  MEDALLION ARCHITECTURE PIPELINE")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sources: {sources or ['all']}")
        print(f"Skip layers: {skip_layers or ['none']}")
        print()
        
        pipeline_results = {}
        
        # 1. Bronze Layer (Raw Ingestion)
        if 'bronze' not in skip_layers:
            bronze_results = self.run_bronze_layer(sources)
            pipeline_results['bronze'] = bronze_results
            
            if not bronze_results:
                self.log_step("pipeline", "abort", "error", "Bronze layer failed - aborting pipeline")
                return self._generate_final_report(pipeline_results)
        
        # 2. Silver Layer (Cleaning & Validation)  
        if 'silver' not in skip_layers:
            silver_results = self.run_silver_layer()
            pipeline_results['silver'] = silver_results
            
            # Check if we have enough silver data to proceed
            success_count = sum(1 for source_results in silver_results.values() 
                              for result in source_results.values() 
                              if result.success)
            
            if success_count == 0:
                self.log_step("pipeline", "abort", "error", "Silver layer failed - aborting pipeline")
                return self._generate_final_report(pipeline_results)
        
        # 3. Gold Layer (Analytics & Business Logic)
        if 'gold' not in skip_layers:
            gold_results = self.run_gold_layer()
            pipeline_results['gold'] = gold_results
        
        return self._generate_final_report(pipeline_results)
    
    def run_single_layer(self, layer: str, sources: List[str] = None) -> Dict:
        """Execute a single layer of the pipeline"""
        print(f"🎯 RUNNING SINGLE LAYER: {layer.upper()}")
        print("=" * 40)
        
        self.start_time = time.time()
        
        if layer == 'bronze':
            results = {'bronze': self.run_bronze_layer(sources)}
        elif layer == 'silver':
            results = {'silver': self.run_silver_layer()}
        elif layer == 'gold':
            results = {'gold': self.run_gold_layer()}
        else:
            raise ValueError(f"Unknown layer: {layer}")
        
        return self._generate_final_report(results)
    
    def _generate_final_report(self, results: Dict) -> Dict:
        """Generate final execution report"""
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        print()
        print("📊 PIPELINE EXECUTION SUMMARY")
        print("=" * 40)
        print(f"Total execution time: {execution_time:.1f} seconds")
        print(f"Layers executed: {list(results.keys())}")
        print(f"Total errors: {len(self.errors)}")
        
        if self.errors:
            print()
            print("❌ ERRORS ENCOUNTERED:")
            for error in self.errors:
                print(f"  • {error}")
        
        # Layer-specific summaries
        for layer, layer_results in results.items():
            print(f"\n{layer.upper()} LAYER SUMMARY:")
            
            if layer == 'bronze':
                total_files = sum(len(files) for files in layer_results.values() if isinstance(files, dict))
                print(f"  Files ingested: {total_files}")
                print(f"  Sources: {list(layer_results.keys())}")
            
            elif layer == 'silver':
                if layer_results:
                    success_count = sum(1 for source_results in layer_results.values() 
                                      for result in source_results.values() 
                                      if result.success)
                    total_count = sum(len(source_results) for source_results in layer_results.values())
                    print(f"  Transformations: {success_count}/{total_count} successful")
            
            elif layer == 'gold':
                print(f"  Analytics datasets: {len(layer_results)}")
                if layer_results:
                    print(f"  Datasets: {list(layer_results.keys())}")
        
        # Save execution log
        self._save_execution_log()
        
        print(f"\n{'✅ PIPELINE COMPLETED SUCCESSFULLY' if not self.errors else '⚠️  PIPELINE COMPLETED WITH ERRORS'}")
        
        return {
            'results': results,
            'execution_time': execution_time,
            'errors': self.errors,
            'execution_log': self.execution_log
        }
    
    def _save_execution_log(self):
        """Save execution log to file"""
        try:
            import json
            log_dir = self.config.data_root / "logs"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f"medallion_pipeline_{timestamp}.json"
            
            log_data = {
                'execution_time': time.time() - self.start_time if self.start_time else 0,
                'start_time': self.start_time,
                'end_time': time.time(),
                'errors': self.errors,
                'steps': self.execution_log
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
                
            print(f"📝 Execution log saved: {log_file}")
            
        except Exception as e:
            print(f"⚠️  Could not save execution log: {e}")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Medallion Architecture Data Pipeline")
    
    parser.add_argument('--layer', 
                       choices=['bronze', 'silver', 'gold', 'all'], 
                       default='all',
                       help='Which layer(s) to execute')
    
    parser.add_argument('--source',
                       choices=['fpl', 'github', 'draft', 'all'],
                       default='all',
                       help='Which data sources to process (bronze layer only)')
    
    parser.add_argument('--skip-layers',
                       nargs='*',
                       choices=['bronze', 'silver', 'gold'],
                       help='Layers to skip in full pipeline execution')
    
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Show what would be executed without running')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE")
        print(f"Would execute: layer={args.layer}, source={args.source}")
        if args.skip_layers:
            print(f"Would skip layers: {args.skip_layers}")
        return
    
    # Initialize orchestrator
    config = MedallionConfig()
    orchestrator = MedallionOrchestrator(config)
    
    # Execute pipeline
    try:
        sources = [args.source] if args.source != 'all' else None
        
        if args.layer == 'all':
            results = orchestrator.run_full_pipeline(sources=sources, skip_layers=args.skip_layers)
        else:
            results = orchestrator.run_single_layer(args.layer, sources=sources)
        
        # Exit with error code if there were errors
        sys.exit(1 if results['errors'] else 0)
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()