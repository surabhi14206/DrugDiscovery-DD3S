"""
Script to validate and fix SMILES strings in the database
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.utils import validate_smiles, sanitize_smiles
from apps.molecules.models import Molecule
from rdkit import Chem

print("=" * 70)
print("VALIDATING SMILES STRINGS IN DATABASE")
print("=" * 70)

# Common invalid SMILES patterns and their fixes
invalid_patterns = {
    'cccccc1(c)': 'c1ccccc1',  # Benzene - fixed ring closure
    'cccccc1': 'c1ccccc1',     # Benzene - missing ring closure
}

def fix_invalid_smiles(smiles):
    """Fix common invalid SMILES patterns"""
    if smiles in invalid_patterns:
        return invalid_patterns[smiles]
    
    # Try to parse and canonicalize
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        # Check if it's a partial ring closure issue
        if '1' in smiles and smiles.count('1') == 1:
            # Add missing ring closure
            return smiles + '1'
    return smiles

# Check all molecules
invalid_count = 0
fixed_count = 0
total_count = Molecule.objects.count()

print(f"\nChecking {total_count} molecules...\n")

for molecule in Molecule.objects.all():
    validation = validate_smiles(molecule.smiles)
    
    if not validation['valid']:
        invalid_count += 1
        print(f"❌ Invalid SMILES found:")
        print(f"   ID: {molecule.id}")
        print(f"   Name: {molecule.name}")
        print(f"   SMILES: {molecule.smiles}")
        print(f"   Error: {validation['error']}")
        
        # Try to fix
        fixed_smiles = fix_invalid_smiles(molecule.smiles)
        if fixed_smiles != molecule.smiles:
            fixed_validation = validate_smiles(fixed_smiles)
            if fixed_validation['valid']:
                print(f"   ✓ Fixed to: {fixed_smiles}")
                # Uncomment to apply fix:
                # molecule.smiles = fixed_smiles
                # molecule.save()
                # fixed_count += 1
            else:
                print(f"   ❌ Could not fix automatically")
        print()

print("=" * 70)
print(f"VALIDATION COMPLETE")
print(f"Total molecules: {total_count}")
print(f"Invalid SMILES: {invalid_count}")
print(f"Fixed: {fixed_count}")
print("=" * 70)

if invalid_count > 0:
    print("\n⚠️  To apply fixes, uncomment the molecule.save() line in the script")
