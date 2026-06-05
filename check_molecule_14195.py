"""
Check SMILES data for molecule 14195
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.models import Molecule

try:
    mol = Molecule.objects.get(pk=14195)
    print(f"Molecule ID: {mol.pk}")
    print(f"Name: {mol.name}")
    print(f"SMILES: '{mol.smiles}'")
    print(f"SMILES length: {len(mol.smiles) if mol.smiles else 0}")
    print(f"SMILES type: {type(mol.smiles)}")
    print(f"Formula: {mol.molecular_formula}")
    print(f"Weight: {mol.molecular_weight}")
    print(f"Is Active: {mol.is_active}")
    print(f"Gene Target: {mol.gene_target}")
    
    # Check if SMILES is empty or just whitespace
    if not mol.smiles or not mol.smiles.strip():
        print("\n⚠️  WARNING: SMILES field is empty or contains only whitespace!")
    else:
        print(f"\n✓ SMILES data exists: {mol.smiles[:50]}...")
        
except Molecule.DoesNotExist:
    print("❌ Molecule with ID 14195 does not exist in the database!")
except Exception as e:
    print(f"❌ Error: {e}")
