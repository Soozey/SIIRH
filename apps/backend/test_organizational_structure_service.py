#!/usr/bin/env python3
"""
Test script for OrganizationalStructureService

Tests the basic functionality of the hierarchical organizational structure service.
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.organizational_structure_service import OrganizationalStructureService
from app.schemas import CreateOrganizationalUnitRequest, UpdateOrganizationalUnitRequest
from app.models import Base
from test_db_config import get_database_url

DATABASE_URL = get_database_url()

def test_organizational_structure_service():
    """Test the OrganizationalStructureService"""
    print("🚀 Testing OrganizationalStructureService")
    print("=" * 60)
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        service = OrganizationalStructureService(db)
        
        # Test 1: Get tree for existing employer
        print("\n📊 Test 1: Get organizational tree")
        try:
            tree = service.get_tree(employer_id=1)  # Karibo Services
            print(f"✅ Tree retrieved: {tree['total_units']} units")
            print(f"   Levels present: {tree['levels_present']}")
            
            if tree['tree']:
                print("   Tree structure:")
                for root in tree['tree']:
                    print(f"   - {root['name']} ({root['level']}) - {root['worker_count']} workers")
                    for child in root.get('children', []):
                        print(f"     - {child['name']} ({child['level']}) - {child['worker_count']} workers")
                        for grandchild in child.get('children', []):
                            print(f"       - {grandchild['name']} ({grandchild['level']}) - {grandchild['worker_count']} workers")
        except Exception as e:
            print(f"❌ Error getting tree: {e}")
        
        # Test 2: Get children of a root unit
        print("\n📊 Test 2: Get children")
        try:
            children = service.get_children(parent_id=None, employer_id=1)
            print(f"✅ Root units found: {len(children)}")
            for child in children:
                print(f"   - {child.name} ({child.level})")
        except Exception as e:
            print(f"❌ Error getting children: {e}")
        
        # Test 3: Validate hierarchy
        print("\n📊 Test 3: Validate hierarchy")
        try:
            result = service.validate_hierarchy(employer_id=1)
            if result.is_valid:
                print(f"✅ {result.message}")
            else:
                print(f"❌ {result.message}")
        except Exception as e:
            print(f"❌ Error validating hierarchy: {e}")
        
        # Test 4: Get path for a unit
        print("\n📊 Test 4: Get path")
        try:
            # Get first unit to test path
            children = service.get_children(parent_id=None, employer_id=1)
            if children:
                unit = children[0]
                path = service.get_path(unit.id)
                print(f"✅ Path for {unit.name}: {path}")
        except Exception as e:
            print(f"❌ Error getting path: {e}")
        
        # Test 5: Get available choices
        print("\n📊 Test 5: Get available choices")
        try:
            # Get establishments
            establishments = service.get_available_choices(
                parent_id=None, 
                level='etablissement', 
                employer_id=1
            )
            print(f"✅ Establishments available: {len(establishments)}")
            for est in establishments:
                print(f"   - {est['name']} (workers: {est['worker_count']})")
            
            # Get departments for first establishment
            if establishments:
                departments = service.get_available_choices(
                    parent_id=establishments[0]['id'],
                    level='departement',
                    employer_id=1
                )
                print(f"✅ Departments for {establishments[0]['name']}: {len(departments)}")
                for dept in departments:
                    print(f"   - {dept['name']} (workers: {dept['worker_count']})")
        except Exception as e:
            print(f"❌ Error getting available choices: {e}")
        
        # Test 6: Validate combination
        print("\n📊 Test 6: Validate combination")
        try:
            # Test with existing units
            establishments = service.get_available_choices(
                parent_id=None, 
                level='etablissement', 
                employer_id=1
            )
            
            if establishments:
                est_id = establishments[0]['id']
                departments = service.get_available_choices(
                    parent_id=est_id,
                    level='departement',
                    employer_id=1
                )
                
                if departments:
                    dept_id = departments[0]['id']
                    result = service.validate_combination(
                        employer_id=1,
                        establishment_id=est_id,
                        department_id=dept_id
                    )
                    
                    if result.is_valid:
                        print(f"✅ {result.message}")
                    else:
                        print(f"❌ {result.message}")
                else:
                    print("⚠️ No departments found for testing combination")
            else:
                print("⚠️ No establishments found for testing combination")
        except Exception as e:
            print(f"❌ Error validating combination: {e}")
    
    print("\n" + "=" * 60)
    print("✅ OrganizationalStructureService tests completed!")


if __name__ == "__main__":
    test_organizational_structure_service()
