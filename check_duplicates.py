"""Check for duplicate molecules in the database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.models import Molecule
from django.db.models import Count

print("="*60)
print("CHECKING FOR DUPLICATE MOLECULES")
print("="*60)

# Check each gene target
targets = ['aldh1a1', 'cyp3a4', 'glp1r', 'gmnn', 'mapt', 'poli', 'tdp1']

for target in targets:
    total = Molecule.objects.filter(gene_target=target).count()
    
    # Find duplicates (same SMILES, same target)
    duplicates = Molecule.objects.filter(
        gene_target=target
    ).values('smiles').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    print(f"\n{target.upper()}:")
    print(f"  Total molecules: {total}")
    print(f"  Unique SMILES: {Molecule.objects.filter(gene_target=target).values('smiles').distinct().count()}")
    print(f"  Duplicate SMILES: {duplicates.count()}")
    
    if duplicates.count() > 0:
        print(f"  ⚠ WARNING: Found {duplicates.count()} SMILES appearing multiple times")
        for dup in duplicates[:3]:
            print(f"    - {dup['smiles'][:60]}... ({dup['count']} times)")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
total_molecules = Molecule.objects.count()
total_unique_smiles = Molecule.objects.values('smiles', 'gene_target').distinct().count()
print(f"Total molecules in database: {total_molecules}")
print(f"Total unique (SMILES + target) combinations: {total_unique_smiles}")
print(f"Duplicates: {total_molecules - total_unique_smiles}")
