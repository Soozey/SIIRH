#!/usr/bin/env python3
"""
Test script for OrganizationalMigrationService

Tests the migration functionality from flat organizational structure to hierarchical.
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.organizational_migration_service import OrganizationalMigrationService
from app.models import Base
from test_db_config import get_database_url

DATABASE_URL = get_database_url()

def test_migration_service():
    """Test the OrganizationalMigrationService"""
    print("🚀 Testing OrganizationalMigrationService")
    print("=" * 60)
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        service = OrganizationalMigrationService(db)
        
        # Test 1: Analyze existing data
        print("\n📊 Test 1: Analyze existing data")
        try:
            for employer_id in [1, 2]:  # Test both employers
                print(f"\n  Analyzing employer {employer_id}:")
                analysis = service.analyze_existing_data(employer_id)
                
                print(f"  ✅ Analysis completed for {analysis.employer_name}")
                print(f"     Total workers: {analysis.total_workers}")
                print(f"     Unique combinations: {analysis.unique_combinations}")
                print(f"     Conflicts: {len(analysis.conflicts)}")
                print(f"     Migration feasible: {analysis.migration_feasible}")
                
                if analysis.conflicts:
                    print("     Conflicts detected:")
                    for conflict in analysis.conflicts[:3]:  # Show first 3
                        print(f"       - {conflict['type']}: {conflict['message']}")
                
                print(f"     Proposed hierarchy nodes: {analysis.proposed_hierarchy.get('total_nodes', 0)}")
                print(f"     Max depth: {analysis.proposed_hierarchy.get('max_depth', 0)}")
                
                print("     Recommendations:")
                for rec in analysis.recommendations[:3]:  # Show first 3
                    print(f"       {rec}")
        
        except Exception as e:
            print(f"❌ Error analyzing data: {e}")
        
        # Test 2: Dry run hierarchy creation
        print("\n📊 Test 2: Dry run hierarchy creation")
        try:
            for employer_id in [1, 2]:
                print(f"\n  Dry run for employer {employer_id}:")
                result = service.create_hierarchy_from_workers(employer_id, dry_run=True)
                
                if result.success:
                    print(f"  ✅ Dry run successful")
                    print(f"     Units would be created: {result.units_created}")
                    print(f"     Workers to migrate: {result.workers_migrated}")
                else:
                    print(f"  ❌ Dry run failed")
                    for error in result.errors:
                        print(f"       Error: {error}")
                
                if result.warnings:
                    print("     Warnings:")
                    for warning in result.warnings[:3]:
                        print(f"       - {warning}")
        
        except Exception as e:
            print(f"❌ Error in dry run: {e}")
        
        # Test 3: Validate current migration state
        print("\n📊 Test 3: Validate current migration state")
        try:
            for employer_id in [1, 2]:
                print(f"\n  Validating employer {employer_id}:")
                validation = service.validate_migration(employer_id)
                
                if validation.is_valid:
                    print(f"  ✅ {validation.message}")
                else:
                    print(f"  ❌ {validation.message}")
        
        except Exception as e:
            print(f"❌ Error validating migration: {e}")
        
        # Test 4: Test worker reference migration (dry run)
        print("\n📊 Test 4: Test worker reference migration (dry run)")
        try:
            for employer_id in [1, 2]:
                print(f"\n  Worker migration dry run for employer {employer_id}:")
                result = service.migrate_worker_references(employer_id, dry_run=True)
                
                if result.success:
                    print(f"  ✅ Worker migration dry run successful")
                    print(f"     Workers would be migrated: {result.workers_migrated}")
                else:
                    print(f"  ❌ Worker migration dry run failed")
                    for error in result.errors:
                        print(f"       Error: {error}")
                
                if result.warnings:
                    print("     Warnings:")
                    for warning in result.warnings[:3]:
                        print(f"       - {warning}")
        
        except Exception as e:
            print(f"❌ Error in worker migration dry run: {e}")
    
    print("\n" + "=" * 60)
    print("✅ OrganizationalMigrationService tests completed!")


if __name__ == "__main__":
    test_migration_service()
