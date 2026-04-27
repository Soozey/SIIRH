#!/usr/bin/env python3
"""
Property-Based Tests for Path Consistency in Hierarchical Organizational Structure

**Feature: hierarchical-organizational-structure, Property 3: Path Consistency**
**Validates: Requirements 7.3**

Tests that for any organizational entity, its path must be the concatenation of all ancestor names 
from root to current entity.
"""

import unittest
import psycopg2
import psycopg2.extras
from hypothesis import given, strategies as st, settings, example
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import builtins
import sys
import os

# Add the app directory to the path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.organizational_structure_service import OrganizationalStructureService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_db_config import get_database_url, get_psycopg2_config


def _safe_print(*args, sep=" ", end="\n", file=sys.stdout, flush=False):
    """Force ASCII-only test logs to avoid cp1252 console failures on Windows."""
    text = sep.join(str(arg) for arg in args)
    safe_text = text.encode("ascii", "replace").decode("ascii")
    builtins.print(safe_text, end=end, file=file, flush=flush)


print = _safe_print


@dataclass
class TestOrganizationalUnit:
    """Test representation of an organizational unit"""
    id: int
    employer_id: int
    parent_id: Optional[int]
    level: str
    level_order: int
    name: str
    code: str


class PathConsistencyTests(unittest.TestCase):
    """Property-based tests for path consistency"""
    
    @classmethod
    def setUpClass(cls):
        """Set up database connection for tests"""
        cls.db_config = get_psycopg2_config()
        
        # Set up service
        cls.database_url = get_database_url()
        cls.engine = create_engine(cls.database_url)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
    
    def get_db_connection(self):
        """Get database connection"""
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = True
        return conn
    
    def get_organizational_units(self, employer_id: int = None) -> List[TestOrganizationalUnit]:
        """Get organizational units from database"""
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                if employer_id:
                    cursor.execute("""
                        SELECT id, employer_id, parent_id, level, level_order, name, code
                        FROM organizational_units
                        WHERE employer_id = %s AND is_active = true
                        ORDER BY level_order, name
                    """, (employer_id,))
                else:
                    cursor.execute("""
                        SELECT id, employer_id, parent_id, level, level_order, name, code
                        FROM organizational_units
                        WHERE is_active = true
                        ORDER BY employer_id, level_order, name
                    """)
                
                rows = cursor.fetchall()
                return [
                    TestOrganizationalUnit(
                        id=row['id'],
                        employer_id=row['employer_id'],
                        parent_id=row['parent_id'],
                        level=row['level'],
                        level_order=row['level_order'],
                        name=row['name'],
                        code=row['code']
                    )
                    for row in rows
                ]
    
    def compute_expected_path(self, unit: TestOrganizationalUnit, units_by_id: Dict[int, TestOrganizationalUnit]) -> str:
        """
        Compute the expected path for a unit by traversing up the hierarchy.
        
        The path should be: "Root / Parent / ... / Current"
        """
        path_parts = []
        current = unit
        visited = set()  # Prevent infinite loops
        
        while current:
            if current.id in visited:
                raise ValueError(f"Circular reference detected involving unit {current.name}")
            
            visited.add(current.id)
            path_parts.insert(0, current.name)
            
            if current.parent_id:
                current = units_by_id.get(current.parent_id)
            else:
                current = None
        
        return " / ".join(path_parts)
    
    def validate_path_consistency(self, units: List[TestOrganizationalUnit]) -> Tuple[bool, str]:
        """
        Validate that all units have consistent paths.
        
        For each unit, compute the expected path by traversing the hierarchy
        and compare it with the path returned by the service.
        
        Returns: (is_valid, error_message)
        """
        if not units:
            return True, "Empty structure has consistent paths"
        
        units_by_id = {unit.id: unit for unit in units}
        
        with self.SessionLocal() as db:
            service = OrganizationalStructureService(db)
            
            for unit in units:
                try:
                    # Get path from service
                    actual_path = service.get_path(unit.id)
                    
                    # Compute expected path
                    expected_path = self.compute_expected_path(unit, units_by_id)
                    
                    if actual_path != expected_path:
                        return False, (
                            f"Path mismatch for unit {unit.name} (ID:{unit.id}). "
                            f"Expected: '{expected_path}', Got: '{actual_path}'"
                        )
                
                except Exception as e:
                    return False, f"Error computing path for unit {unit.name} (ID:{unit.id}): {str(e)}"
        
        return True, f"Path consistency validated for {len(units)} units"
    
    def test_current_database_path_consistency(self):
        """Test that the current database maintains path consistency"""
        print("\n🔍 Testing current database path consistency...")
        
        # Test each employer separately
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT id, raison_sociale FROM employers ORDER BY id")
                employers = cursor.fetchall()
        
        for employer in employers:
            with self.subTest(employer_id=employer['id'], employer_name=employer['raison_sociale']):
                print(f"  📊 Testing {employer['raison_sociale']} (ID: {employer['id']})")
                
                units = self.get_organizational_units(employer['id'])
                print(f"     Units: {len(units)}")
                
                if units:
                    # Show some example paths
                    with self.SessionLocal() as db:
                        service = OrganizationalStructureService(db)
                        for unit in units[:3]:  # Show first 3 units
                            try:
                                path = service.get_path(unit.id)
                                print(f"     - {unit.name} ({unit.level}): {path}")
                            except Exception as e:
                                print(f"     - {unit.name} ({unit.level}): ERROR - {e}")
                
                is_valid, message = self.validate_path_consistency(units)
                
                if is_valid:
                    print(f"     ✅ {message}")
                else:
                    print(f"     ❌ {message}")
                
                self.assertTrue(is_valid, f"Path consistency failed for {employer['raison_sociale']}: {message}")
    
    def test_empty_hierarchy_path_consistency(self):
        """Test that an empty hierarchy maintains path consistency"""
        is_valid, message = self.validate_path_consistency([])
        self.assertTrue(is_valid, f"Empty hierarchy should maintain path consistency: {message}")
    
    def test_single_unit_path(self):
        """Test path consistency for a single unit"""
        print("\n🔍 Testing single unit path...")
        
        # Get a single unit from the database
        units = self.get_organizational_units()
        if units:
            single_unit = [units[0]]
            is_valid, message = self.validate_path_consistency(single_unit)
            
            print(f"     Unit: {single_unit[0].name}")
            if is_valid:
                print(f"     ✅ {message}")
            else:
                print(f"     ❌ {message}")
            
            self.assertTrue(is_valid, f"Single unit path should be consistent: {message}")
        else:
            print("     ⚠️ No units found in database")
    
    def test_root_unit_path_is_just_name(self):
        """Test that root units have paths equal to their names"""
        print("\n🔍 Testing root unit paths...")
        
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, level
                    FROM organizational_units
                    WHERE parent_id IS NULL AND is_active = true
                    LIMIT 5
                """)
                root_units = cursor.fetchall()
        
        with self.SessionLocal() as db:
            service = OrganizationalStructureService(db)
            
            for root_unit in root_units:
                with self.subTest(unit_id=root_unit['id'], unit_name=root_unit['name']):
                    path = service.get_path(root_unit['id'])
                    expected_path = root_unit['name']
                    
                    print(f"     Root unit {root_unit['name']}: '{path}'")
                    
                    self.assertEqual(
                        path, 
                        expected_path,
                        f"Root unit path should be just the unit name. Expected: '{expected_path}', Got: '{path}'"
                    )
    
    def test_child_unit_path_includes_parent(self):
        """Test that child units have paths that include their parent"""
        print("\n🔍 Testing child unit paths...")
        
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT c.id, c.name as child_name, c.level as child_level,
                           p.name as parent_name, p.level as parent_level
                    FROM organizational_units c
                    JOIN organizational_units p ON c.parent_id = p.id
                    WHERE c.is_active = true AND p.is_active = true
                    LIMIT 5
                """)
                child_units = cursor.fetchall()
        
        with self.SessionLocal() as db:
            service = OrganizationalStructureService(db)
            
            for child_unit in child_units:
                with self.subTest(unit_id=child_unit['id'], unit_name=child_unit['child_name']):
                    path = service.get_path(child_unit['id'])
                    
                    print(f"     Child unit {child_unit['child_name']}: '{path}'")
                    
                    # Path should contain both parent and child names
                    self.assertIn(
                        child_unit['parent_name'], 
                        path,
                        f"Child unit path should contain parent name '{child_unit['parent_name']}'"
                    )
                    
                    self.assertIn(
                        child_unit['child_name'], 
                        path,
                        f"Child unit path should contain child name '{child_unit['child_name']}'"
                    )
                    
                    # Parent should come before child in the path
                    parent_pos = path.find(child_unit['parent_name'])
                    child_pos = path.find(child_unit['child_name'])
                    
                    self.assertLess(
                        parent_pos,
                        child_pos,
                        f"Parent '{child_unit['parent_name']}' should come before child '{child_unit['child_name']}' in path"
                    )
    
    def test_path_separator_consistency(self):
        """Test that all paths use consistent separators"""
        print("\n🔍 Testing path separator consistency...")
        
        units = self.get_organizational_units()
        
        with self.SessionLocal() as db:
            service = OrganizationalStructureService(db)
            
            separator = " / "  # Expected separator
            
            for unit in units[:10]:  # Test first 10 units
                path = service.get_path(unit.id)
                
                # If path contains multiple parts, check separator
                if separator in path:
                    parts = path.split(separator)
                    
                    # Verify no empty parts (which would indicate double separators)
                    empty_parts = [i for i, part in enumerate(parts) if not part.strip()]
                    
                    self.assertEqual(
                        len(empty_parts), 
                        0,
                        f"Path '{path}' contains empty parts at positions {empty_parts}"
                    )
                    
                    # Verify path can be reconstructed
                    reconstructed = separator.join(parts)
                    self.assertEqual(
                        path,
                        reconstructed,
                        f"Path reconstruction failed for '{path}'"
                    )
        
        print(f"     ✅ Path separator consistency validated for {min(len(units), 10)} units")
    
    @given(st.integers(min_value=1, max_value=2))
    @settings(max_examples=5, deadline=30000)  # Limit examples for database tests
    def test_property_any_employer_path_consistency(self, employer_id):
        """
        Property: For any employer in the database, all organizational unit paths must be consistent.
        
        **Feature: hierarchical-organizational-structure, Property 3: Path Consistency**
        **Validates: Requirements 7.3**
        """
        print(f"\n🔬 Property test for employer {employer_id} path consistency")
        
        units = self.get_organizational_units(employer_id)
        
        if not units:
            print(f"     No units found for employer {employer_id}")
            return  # Empty hierarchy has consistent paths
        
        is_valid, message = self.validate_path_consistency(units)
        
        print(f"     Units: {len(units)}, Valid: {is_valid}")
        if not is_valid:
            print(f"     Error: {message}")
        
        self.assertTrue(
            is_valid, 
            f"Path consistency must hold for employer {employer_id}: {message}"
        )
    
    def test_path_uniqueness_within_employer(self):
        """Test that all paths are unique within an employer (no duplicates)"""
        print("\n🔍 Testing path uniqueness within employers...")
        
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT id, raison_sociale FROM employers ORDER BY id")
                employers = cursor.fetchall()
        
        for employer in employers:
            with self.subTest(employer_id=employer['id']):
                print(f"  📊 Testing {employer['raison_sociale']} (ID: {employer['id']})")
                
                units = self.get_organizational_units(employer['id'])
                
                if not units:
                    print("     No units to test")
                    continue
                
                paths = []
                
                with self.SessionLocal() as db:
                    service = OrganizationalStructureService(db)
                    
                    for unit in units:
                        path = service.get_path(unit.id)
                        paths.append((unit.id, unit.name, path))
                
                # Check for duplicate paths
                path_counts = {}
                for unit_id, unit_name, path in paths:
                    if path in path_counts:
                        path_counts[path].append((unit_id, unit_name))
                    else:
                        path_counts[path] = [(unit_id, unit_name)]
                
                duplicates = {path: units for path, units in path_counts.items() if len(units) > 1}
                
                if duplicates:
                    duplicate_info = []
                    for path, units in duplicates.items():
                        unit_info = [f"{name} (ID:{uid})" for uid, name in units]
                        duplicate_info.append(f"Path '{path}': {unit_info}")
                    
                    self.fail(f"Duplicate paths found in employer {employer['raison_sociale']}: {duplicate_info}")
                
                print(f"     ✅ All {len(paths)} paths are unique")


def run_path_consistency_tests():
    """Run the path consistency tests"""
    print("🚀 Running Path Consistency Property Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(PathConsistencyTests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All path consistency tests passed!")
        print(f"📊 Tests run: {result.testsRun}")
        return True
    else:
        print("❌ Some path consistency tests failed!")
        print(f"📊 Tests run: {result.testsRun}")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        
        # Print failure details
        for test, traceback in result.failures:
            print(f"\n❌ FAILURE: {test}")
            print(traceback)
        
        for test, traceback in result.errors:
            print(f"\n❌ ERROR: {test}")
            print(traceback)
        
        return False


if __name__ == "__main__":
    success = run_path_consistency_tests()
    sys.exit(0 if success else 1)
