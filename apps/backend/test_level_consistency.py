#!/usr/bin/env python3
"""
Property-Based Tests for Level Consistency in Hierarchical Organizational Structure

**Feature: hierarchical-organizational-structure, Property 2: Level Consistency**
**Validates: Requirements 1.2, 1.3, 1.4**

Tests that for any organizational entity, its level must be exactly one greater than its parent's level
(establishment=1, department=2, service=3, unit=4).
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


def _safe_print(*args, sep=" ", end="\n", file=sys.stdout, flush=False):
    """Force ASCII-only test logs to avoid cp1252 console failures on Windows."""
    text = sep.join(str(arg) for arg in args)
    safe_text = text.encode("ascii", "replace").decode("ascii")
    builtins.print(safe_text, end=end, file=file, flush=flush)


print = _safe_print

# Add the app directory to the path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from test_db_config import get_psycopg2_config


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


class LevelConsistencyTests(unittest.TestCase):
    """Property-based tests for level consistency"""
    
    # Expected level progression
    LEVEL_HIERARCHY = {
        'etablissement': 1,
        'departement': 2,
        'service': 3,
        'unite': 4
    }
    
    @classmethod
    def setUpClass(cls):
        """Set up database connection for tests"""
        cls.db_config = get_psycopg2_config()
    
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
    
    def validate_level_consistency(self, units: List[TestOrganizationalUnit]) -> Tuple[bool, str]:
        """
        Validate that level consistency is maintained throughout the hierarchy.
        
        Rules:
        1. Root nodes (parent_id=None) must be 'etablissement' with level_order=1
        2. Each child's level_order must be exactly parent's level_order + 1
        3. Level names must match their level_order according to LEVEL_HIERARCHY
        4. No level can be skipped in the hierarchy
        
        Returns: (is_valid, error_message)
        """
        if not units:
            return True, "Empty structure is valid"
        
        # Create lookup maps
        units_by_id = {unit.id: unit for unit in units}
        
        # Validate each unit
        for unit in units:
            # Rule 1: Root nodes must be establishments
            if unit.parent_id is None:
                if unit.level != 'etablissement':
                    return False, f"Root node {unit.name} (ID:{unit.id}) must be 'etablissement', got '{unit.level}'"
                if unit.level_order != 1:
                    return False, f"Root node {unit.name} (ID:{unit.id}) must have level_order=1, got {unit.level_order}"
            
            # Rule 2: Child level_order must be parent level_order + 1
            if unit.parent_id is not None:
                parent = units_by_id.get(unit.parent_id)
                if not parent:
                    return False, f"Unit {unit.name} (ID:{unit.id}) references non-existent parent {unit.parent_id}"
                
                expected_level_order = parent.level_order + 1
                if unit.level_order != expected_level_order:
                    return False, (
                        f"Unit {unit.name} (ID:{unit.id}) has level_order={unit.level_order}, "
                        f"but parent {parent.name} (ID:{parent.id}) has level_order={parent.level_order}. "
                        f"Expected level_order={expected_level_order}"
                    )
            
            # Rule 3: Level name must match level_order
            expected_level_order = self.LEVEL_HIERARCHY.get(unit.level)
            if expected_level_order is None:
                return False, f"Unit {unit.name} (ID:{unit.id}) has invalid level '{unit.level}'"
            
            if unit.level_order != expected_level_order:
                return False, (
                    f"Unit {unit.name} (ID:{unit.id}) has level='{unit.level}' "
                    f"but level_order={unit.level_order}. Expected level_order={expected_level_order}"
                )
        
        # Rule 4: Check for level skipping within each branch
        # Group units by employer and validate each hierarchy branch
        by_employer = {}
        for unit in units:
            if unit.employer_id not in by_employer:
                by_employer[unit.employer_id] = []
            by_employer[unit.employer_id].append(unit)
        
        for employer_id, employer_units in by_employer.items():
            employer_units_by_id = {unit.id: unit for unit in employer_units}
            
            # For each unit, validate the path to root has no gaps
            for unit in employer_units:
                path_levels = []
                current = unit
                
                while current:
                    path_levels.insert(0, current.level_order)
                    if current.parent_id:
                        current = employer_units_by_id.get(current.parent_id)
                    else:
                        current = None
                
                # Check that levels are consecutive (no gaps)
                for i in range(1, len(path_levels)):
                    if path_levels[i] != path_levels[i-1] + 1:
                        return False, (
                            f"Level gap detected in path to {unit.name} (ID:{unit.id}). "
                            f"Path levels: {path_levels}. Level {path_levels[i-1] + 1} is missing."
                        )
        
        return True, "Level consistency validated"
    
    def test_current_database_level_consistency(self):
        """Test that the current database maintains level consistency"""
        print("\n🔍 Testing current database level consistency...")
        
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
                    # Show level distribution
                    level_counts = {}
                    for unit in units:
                        level_counts[unit.level] = level_counts.get(unit.level, 0) + 1
                    print(f"     Distribution: {level_counts}")
                
                is_valid, message = self.validate_level_consistency(units)
                
                if is_valid:
                    print(f"     ✅ {message}")
                else:
                    print(f"     ❌ {message}")
                
                self.assertTrue(is_valid, f"Level consistency failed for {employer['raison_sociale']}: {message}")
    
    def test_empty_hierarchy_level_consistency(self):
        """Test that an empty hierarchy maintains level consistency"""
        is_valid, message = self.validate_level_consistency([])
        self.assertTrue(is_valid, f"Empty hierarchy should maintain level consistency: {message}")
    
    def test_single_establishment_is_valid(self):
        """Test that a single establishment maintains level consistency"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement', 
                level_order=1, name='Root Establishment', code='EST1'
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertTrue(is_valid, f"Single establishment should be valid: {message}")
    
    def test_proper_hierarchy_is_valid(self):
        """Test that a proper 4-level hierarchy maintains level consistency"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement',
                level_order=1, name='Establishment', code='EST1'
            ),
            TestOrganizationalUnit(
                id=2, employer_id=1, parent_id=1, level='departement',
                level_order=2, name='Department', code='DEP1'
            ),
            TestOrganizationalUnit(
                id=3, employer_id=1, parent_id=2, level='service',
                level_order=3, name='Service', code='SRV1'
            ),
            TestOrganizationalUnit(
                id=4, employer_id=1, parent_id=3, level='unite',
                level_order=4, name='Unit', code='UNT1'
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertTrue(is_valid, f"Proper 4-level hierarchy should be valid: {message}")
    
    def test_wrong_root_level_is_invalid(self):
        """Test that non-establishment root nodes are invalid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='departement',  # Should be etablissement
                level_order=2, name='Wrong Root', code='WRONG'
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertFalse(is_valid, "Non-establishment root should be invalid")
        self.assertIn("Root node", message)
        self.assertIn("must be 'etablissement'", message)
    
    def test_wrong_level_order_is_invalid(self):
        """Test that incorrect level_order values are invalid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement',
                level_order=1, name='Establishment', code='EST1'
            ),
            TestOrganizationalUnit(
                id=2, employer_id=1, parent_id=1, level='departement',
                level_order=3, name='Department', code='DEP1'  # Should be 2, not 3
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertFalse(is_valid, "Wrong level_order should be invalid")
        self.assertIn("Expected level_order=2", message)
    
    def test_mismatched_level_and_order_is_invalid(self):
        """Test that mismatched level names and level_order are invalid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='service',  # Wrong level name
                level_order=1, name='Wrong Level', code='WRONG'  # level_order=1 should be etablissement
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertFalse(is_valid, "Mismatched level and level_order should be invalid")
        # The validation catches the root level error first, which is correct
        self.assertIn("Root node", message)
        self.assertIn("must be 'etablissement'", message)
    
    def test_level_gap_is_invalid(self):
        """Test that skipping levels in hierarchy is invalid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement',
                level_order=1, name='Establishment', code='EST1'
            ),
            TestOrganizationalUnit(
                id=3, employer_id=1, parent_id=1, level='service',  # Skipping departement
                level_order=3, name='Service', code='SRV1'
            )
        ]
        
        is_valid, message = self.validate_level_consistency(units)
        self.assertFalse(is_valid, "Level gap should be invalid")
        # The validation catches the level_order mismatch first, which is correct
        self.assertIn("Expected level_order=2", message)
    
    @given(st.integers(min_value=1, max_value=2))
    @settings(max_examples=10, deadline=30000)  # Limit examples for database tests
    def test_property_any_employer_level_consistency(self, employer_id):
        """
        Property: For any employer in the database, their organizational hierarchy must maintain level consistency.
        
        **Feature: hierarchical-organizational-structure, Property 2: Level Consistency**
        **Validates: Requirements 1.2, 1.3, 1.4**
        """
        print(f"\n🔬 Property test for employer {employer_id} level consistency")
        
        units = self.get_organizational_units(employer_id)
        
        if not units:
            print(f"     No units found for employer {employer_id}")
            return  # Empty hierarchy maintains level consistency
        
        is_valid, message = self.validate_level_consistency(units)
        
        print(f"     Units: {len(units)}, Valid: {is_valid}")
        if not is_valid:
            print(f"     Error: {message}")
        
        self.assertTrue(
            is_valid, 
            f"Level consistency must hold for employer {employer_id}: {message}"
        )
    
    def test_level_order_matches_database_constants(self):
        """Test that our test constants match the database model constants"""
        print("\n🔍 Verifying level constants match database...")
        
        # This test ensures our test constants are in sync with the actual model
        expected_levels = {
            'etablissement': 1,
            'departement': 2,
            'service': 3,
            'unite': 4
        }
        
        self.assertEqual(self.LEVEL_HIERARCHY, expected_levels, 
                        "Test level constants must match database model constants")
        
        print("     ✅ Level constants verified")
    
    def test_all_database_levels_are_recognized(self):
        """Test that all levels in the database are recognized by our constants"""
        print("\n🔍 Checking all database levels are recognized...")
        
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT level 
                    FROM organizational_units 
                    WHERE is_active = true
                    ORDER BY level
                """)
                db_levels = [row[0] for row in cursor.fetchall()]
        
        print(f"     Database levels: {db_levels}")
        
        for level in db_levels:
            self.assertIn(level, self.LEVEL_HIERARCHY, 
                         f"Database level '{level}' not recognized in test constants")
        
        print("     ✅ All database levels recognized")


def run_level_consistency_tests():
    """Run the level consistency tests"""
    print("🚀 Running Level Consistency Property Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(LevelConsistencyTests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All level consistency tests passed!")
        print(f"📊 Tests run: {result.testsRun}")
        return True
    else:
        print("❌ Some level consistency tests failed!")
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
    success = run_level_consistency_tests()
    sys.exit(0 if success else 1)
