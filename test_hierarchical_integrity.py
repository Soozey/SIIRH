#!/usr/bin/env python3
"""
Property-Based Tests for Hierarchical Organizational Structure Integrity

**Feature: hierarchical-organizational-structure, Property 1: Hierarchical Integrity**
**Validates: Requirements 1.5, 6.6**

Tests that the parent-child relationships form a valid tree without cycles or orphaned nodes.
"""

import unittest
import psycopg2
import psycopg2.extras
from hypothesis import given, strategies as st, settings, example
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import sys
import os

# Add the app directory to the path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from test_db_config import get_psycopg2_config

# We don't actually need to import the models for these tests
# from models import OrganizationalUnit


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


class HierarchicalIntegrityTests(unittest.TestCase):
    """Property-based tests for hierarchical integrity"""
    
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
    
    def build_hierarchy_graph(self, units: List[TestOrganizationalUnit]) -> Dict[int, List[int]]:
        """Build a graph representation of the hierarchy (parent -> children)"""
        graph = {}
        for unit in units:
            if unit.parent_id not in graph:
                graph[unit.parent_id] = []
            graph[unit.parent_id].append(unit.id)
            
            # Ensure all nodes exist in the graph
            if unit.id not in graph:
                graph[unit.id] = []
        
        return graph
    
    def has_cycles(self, graph: Dict[int, List[int]], start_node: int, visited: Set[int] = None, rec_stack: Set[int] = None) -> bool:
        """Check if the graph has cycles using DFS"""
        if visited is None:
            visited = set()
        if rec_stack is None:
            rec_stack = set()
        
        visited.add(start_node)
        rec_stack.add(start_node)
        
        # Check all children
        for child in graph.get(start_node, []):
            if child not in visited:
                if self.has_cycles(graph, child, visited, rec_stack):
                    return True
            elif child in rec_stack:
                return True
        
        rec_stack.remove(start_node)
        return False
    
    def find_orphaned_nodes(self, units: List[TestOrganizationalUnit]) -> List[TestOrganizationalUnit]:
        """Find nodes that reference non-existent parents"""
        unit_ids = {unit.id for unit in units}
        orphaned = []
        
        for unit in units:
            if unit.parent_id is not None and unit.parent_id not in unit_ids:
                orphaned.append(unit)
        
        return orphaned
    
    def find_roots(self, units: List[TestOrganizationalUnit]) -> List[TestOrganizationalUnit]:
        """Find root nodes (nodes with no parent)"""
        return [unit for unit in units if unit.parent_id is None]
    
    def validate_tree_structure(self, units: List[TestOrganizationalUnit]) -> Tuple[bool, str]:
        """
        Validate that the organizational units form a valid tree structure.
        
        Returns: (is_valid, error_message)
        """
        if not units:
            return True, "Empty structure is valid"
        
        # Check for orphaned nodes
        orphaned = self.find_orphaned_nodes(units)
        if orphaned:
            orphan_names = [f"{unit.name} (ID:{unit.id}, Parent:{unit.parent_id})" for unit in orphaned]
            return False, f"Orphaned nodes found: {orphan_names}"
        
        # Build graph and check for cycles
        graph = self.build_hierarchy_graph(units)
        
        # Check cycles starting from each root
        roots = self.find_roots(units)
        for root in roots:
            if self.has_cycles(graph, root.id):
                return False, f"Cycle detected starting from root: {root.name} (ID:{root.id})"
        
        # Check that all nodes are reachable from some root
        all_reachable = set()
        
        def dfs_collect(node_id: int, visited: Set[int]):
            if node_id in visited:
                return
            visited.add(node_id)
            for child in graph.get(node_id, []):
                dfs_collect(child, visited)
        
        for root in roots:
            dfs_collect(root.id, all_reachable)
        
        all_unit_ids = {unit.id for unit in units}
        unreachable = all_unit_ids - all_reachable
        
        if unreachable:
            unreachable_units = [unit for unit in units if unit.id in unreachable]
            unreachable_names = [f"{unit.name} (ID:{unit.id})" for unit in unreachable_units]
            return False, f"Unreachable nodes found: {unreachable_names}"
        
        return True, "Valid tree structure"
    
    def test_current_database_hierarchy_integrity(self):
        """Test that the current database has valid hierarchical integrity"""
        print("\n🔍 Testing current database hierarchical integrity...")
        
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
                
                is_valid, message = self.validate_tree_structure(units)
                
                if is_valid:
                    print(f"     ✅ {message}")
                else:
                    print(f"     ❌ {message}")
                
                self.assertTrue(is_valid, f"Hierarchical integrity failed for {employer['raison_sociale']}: {message}")
    
    def test_empty_hierarchy_is_valid(self):
        """Test that an empty hierarchy is considered valid"""
        is_valid, message = self.validate_tree_structure([])
        self.assertTrue(is_valid, f"Empty hierarchy should be valid: {message}")
    
    def test_single_root_is_valid(self):
        """Test that a single root node is valid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement', 
                level_order=1, name='Root', code='ROOT'
            )
        ]
        
        is_valid, message = self.validate_tree_structure(units)
        self.assertTrue(is_valid, f"Single root should be valid: {message}")
    
    def test_simple_parent_child_is_valid(self):
        """Test that a simple parent-child relationship is valid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=None, level='etablissement',
                level_order=1, name='Parent', code='PARENT'
            ),
            TestOrganizationalUnit(
                id=2, employer_id=1, parent_id=1, level='departement',
                level_order=2, name='Child', code='CHILD'
            )
        ]
        
        is_valid, message = self.validate_tree_structure(units)
        self.assertTrue(is_valid, f"Simple parent-child should be valid: {message}")
    
    def test_orphaned_node_is_invalid(self):
        """Test that orphaned nodes (referencing non-existent parents) are invalid"""
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=999, level='departement',  # Parent 999 doesn't exist
                level_order=2, name='Orphan', code='ORPHAN'
            )
        ]
        
        is_valid, message = self.validate_tree_structure(units)
        self.assertFalse(is_valid, "Orphaned node should be invalid")
        self.assertIn("Orphaned nodes found", message)
    
    def test_cycle_is_invalid(self):
        """Test that cycles in the hierarchy are invalid"""
        # This test would require creating a cycle in the database, which is complex
        # For now, we test the cycle detection logic with mock data
        
        # Create a simple cycle: A -> B -> A
        units = [
            TestOrganizationalUnit(
                id=1, employer_id=1, parent_id=2, level='etablissement',
                level_order=1, name='A', code='A'
            ),
            TestOrganizationalUnit(
                id=2, employer_id=1, parent_id=1, level='departement',
                level_order=2, name='B', code='B'
            )
        ]
        
        # This should be invalid due to the cycle
        is_valid, message = self.validate_tree_structure(units)
        self.assertFalse(is_valid, "Cycle should be invalid")
    
    @given(st.integers(min_value=1, max_value=2))
    @settings(max_examples=10, deadline=30000)  # Limit examples for database tests
    def test_property_any_employer_hierarchy_is_valid(self, employer_id):
        """
        Property: For any employer in the database, their organizational hierarchy must be valid.
        
        **Feature: hierarchical-organizational-structure, Property 1: Hierarchical Integrity**
        **Validates: Requirements 1.5, 6.6**
        """
        print(f"\n🔬 Property test for employer {employer_id}")
        
        units = self.get_organizational_units(employer_id)
        
        if not units:
            print(f"     No units found for employer {employer_id}")
            return  # Empty hierarchy is valid
        
        is_valid, message = self.validate_tree_structure(units)
        
        print(f"     Units: {len(units)}, Valid: {is_valid}")
        if not is_valid:
            print(f"     Error: {message}")
        
        self.assertTrue(
            is_valid, 
            f"Hierarchical integrity must hold for employer {employer_id}: {message}"
        )
    
    def test_level_consistency_property(self):
        """
        Test that level consistency is maintained in the current database.
        This is a preview of Property 2 (Level Consistency).
        """
        print("\n🔍 Testing level consistency...")
        
        units = self.get_organizational_units()
        
        # Group by employer
        by_employer = {}
        for unit in units:
            if unit.employer_id not in by_employer:
                by_employer[unit.employer_id] = []
            by_employer[unit.employer_id].append(unit)
        
        for employer_id, employer_units in by_employer.items():
            with self.subTest(employer_id=employer_id):
                print(f"  📊 Testing level consistency for employer {employer_id}")
                
                # Check that each child's level_order is exactly parent's level_order + 1
                units_by_id = {unit.id: unit for unit in employer_units}
                
                for unit in employer_units:
                    if unit.parent_id is not None:
                        parent = units_by_id.get(unit.parent_id)
                        if parent:
                            expected_level_order = parent.level_order + 1
                            self.assertEqual(
                                unit.level_order, 
                                expected_level_order,
                                f"Unit {unit.name} (level_order={unit.level_order}) should have level_order={expected_level_order} "
                                f"(parent {parent.name} has level_order={parent.level_order})"
                            )
                
                print(f"     ✅ Level consistency validated for {len(employer_units)} units")


def run_hierarchical_integrity_tests():
    """Run the hierarchical integrity tests"""
    print("🚀 Running Hierarchical Integrity Property Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(HierarchicalIntegrityTests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All hierarchical integrity tests passed!")
        print(f"📊 Tests run: {result.testsRun}")
        return True
    else:
        print("❌ Some hierarchical integrity tests failed!")
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
    success = run_hierarchical_integrity_tests()
    sys.exit(0 if success else 1)
