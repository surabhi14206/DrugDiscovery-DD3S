"""
Test script to demonstrate PDB ID lookup functionality.
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.utils import (
    get_pdb_id_from_smiles,
    get_all_pdb_ids_from_smiles,
    search_pdb_by_target_and_ligand
)

print("=" * 70)
print("TESTING PDB ID LOOKUP SYSTEM")
print("=" * 70)

# Test cases with known molecules
test_cases = [
    {
        "name": "Acetic Acid",
        "smiles": "CC(=O)O",
        "description": "Simple molecule, likely in many structures"
    },
    {
        "name": "Aspirin",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "description": "Common drug molecule"
    },
    {
        "name": "Caffeine",
        "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
        "description": "Well-known stimulant"
    }
]

print("\nTest 1: Single PDB ID Lookup (Exact Match)")
print("-" * 70)

for test in test_cases:
    print(f"\n{test['name']}: {test['smiles']}")
    print(f"  Description: {test['description']}")
    
    try:
        pdb_id = get_pdb_id_from_smiles(test['smiles'], match_type='graph-exact')
        
        if pdb_id:
            print(f"  ✓ Found PDB ID: {pdb_id}")
        else:
            print(f"  ⊘ Not found in PDB (exact match)")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("Test 2: Multiple PDB IDs Lookup")
print("-" * 70)

# Test with aspirin (likely to have multiple structures)
smiles = "CC(=O)Oc1ccccc1C(=O)O"
print(f"\nLooking for all PDB entries containing: {smiles}")

try:
    pdb_ids = get_all_pdb_ids_from_smiles(smiles, match_type='graph-relaxed', limit=5)
    
    if pdb_ids:
        print(f"  ✓ Found {len(pdb_ids)} PDB entries:")
        for pdb_id in pdb_ids:
            print(f"    - {pdb_id}")
    else:
        print(f"  ⊘ No PDB entries found")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
PDB ID Lookup System Features:

1. Single Lookup: get_pdb_id_from_smiles(smiles)
   - Returns first PDB ID found
   - Use for quick lookups

2. Multiple Lookup: get_all_pdb_ids_from_smiles(smiles)
   - Returns list of all matching PDB IDs
   - Use when molecule appears in multiple structures

3. Target-Specific: search_pdb_by_target_and_ligand(target, smiles)
   - Finds structures with both target protein and ligand
   - Most specific search

Match Types:
- 'graph-exact': Exact chemical structure match
- 'graph-relaxed': Similar structures (more results)

Note: Many drug discovery molecules are NOT in the PDB because they
have never been crystallized in a protein structure. This is normal!
""")
