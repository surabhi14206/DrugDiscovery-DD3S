"""
Import molecules in batches of 300 per target, avoiding duplicates
Runs 6 batches to add 1,800 molecules per target
"""
import os
import django
import json
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.molecules.models import Molecule
from django.db.models import Q

def get_existing_smiles(target):
    """Get all existing SMILES for a target"""
    return set(
        Molecule.objects.filter(gene_target=target).values_list('smiles', flat=True)
    )

def import_batch(batch_num, molecules_per_target=300):
    """Import one batch of molecules"""
    print(f"\n{'='*60}")
    print(f"BATCH {batch_num}: Importing {molecules_per_target} molecules per target")
    print(f"{'='*60}")
    
    # Load data from original file
    print("Loading data from ALL_7_Gene_SMILES_isActive.json...")
    with open('ALL_7_Gene_SMILES_isActive.json', 'r') as f:
        data = json.load(f)
    
    print(f"Total molecules in file: {len(data)}")
    
    # Group by target
    targets = {}
    for item in data:
        target = item.get('Target', '').strip()
        if target:
            if target not in targets:
                targets[target] = []
            targets[target].append(item)
    
    # Statistics
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for target, molecules in targets.items():
        print(f"\n{target.upper()}:")
        
        # Get existing SMILES for this target
        existing_smiles = get_existing_smiles(target)
        print(f"  Already in database: {len(existing_smiles)} molecules")
        
        # Shuffle to get random selection
        random.shuffle(molecules)
        
        # Find new molecules (not in database)
        new_molecules = []
        for mol in molecules:
            smiles = mol.get('SMILES', '').strip()
            if smiles and smiles not in existing_smiles:
                new_molecules.append(mol)
                if len(new_molecules) >= molecules_per_target:
                    break
        
        print(f"  Found {len(new_molecules)} new unique molecules")
        
        if len(new_molecules) < molecules_per_target:
            print(f"  ⚠ WARNING: Only {len(new_molecules)} unique molecules available (requested {molecules_per_target})")
        
        # Import the new molecules
        batch_created = 0
        for item in new_molecules:
            try:
                smiles = item.get('SMILES', '').strip()
                is_active = bool(item.get('isActive', 0))
                
                if not smiles:
                    skipped_count += 1
                    continue
                
                # Double-check it doesn't exist
                if Molecule.objects.filter(smiles=smiles, gene_target=target).exists():
                    skipped_count += 1
                    continue
                
                # Create molecule
                name = f"{target.upper()}_B{batch_num}_{batch_created}"
                molecule = Molecule(
                    name=name,
                    smiles=smiles,
                    gene_target=target,
                    is_active=is_active,
                    pdb_id=None
                )
                molecule._skip_pdb_lookup = True
                molecule.save()
                
                batch_created += 1
                created_count += 1
                
                if batch_created % 50 == 0:
                    print(f"    Created {batch_created} molecules...")
                
            except Exception as e:
                error_count += 1
                print(f"    ✗ Error: {str(e)}")
        
        print(f"  ✓ Created {batch_created} new molecules for {target}")
    
    return created_count, skipped_count, error_count

def main():
    """Import 6 batches of 300 molecules per target"""
    print("="*60)
    print("MULTI-BATCH IMPORT")
    print("="*60)
    
    # Set random seed for reproducibility
    random.seed(42)
    
    total_created = 0
    total_skipped = 0
    total_errors = 0
    
    num_batches = 6
    molecules_per_batch = 300
    
    for batch_num in range(1, num_batches + 1):
        created, skipped, errors = import_batch(batch_num, molecules_per_batch)
        total_created += created
        total_skipped += skipped
        total_errors += errors
        
        # Show progress
        print(f"\n{'='*60}")
        print(f"BATCH {batch_num} COMPLETE")
        print(f"{'='*60}")
        print(f"Created: {created}, Skipped: {skipped}, Errors: {errors}")
        
        # Check current database state
        from django.db.models import Count
        targets = Molecule.objects.values('gene_target').annotate(
            count=Count('id')
        ).order_by('gene_target')
        
        print("\nCurrent database state:")
        for t in targets:
            print(f"  {t['gene_target']:15} - {t['count']} molecules")
    
    # Final summary
    print(f"\n{'='*60}")
    print("IMPORT COMPLETE - ALL BATCHES")
    print(f"{'='*60}")
    print(f"Total molecules created: {total_created}")
    print(f"Total skipped (duplicates): {total_skipped}")
    print(f"Total errors: {total_errors}")
    print(f"Batches imported: {num_batches}")
    
    # Final duplicate check
    print(f"\n{'='*60}")
    print("FINAL DUPLICATE CHECK")
    print(f"{'='*60}")
    
    all_targets = ['aldh1a1', 'cyp3a4', 'glp1r', 'gmnn', 'mapt', 'poli', 'tdp1']
    for target in all_targets:
        total = Molecule.objects.filter(gene_target=target).count()
        unique = Molecule.objects.filter(gene_target=target).values('smiles').distinct().count()
        duplicates = total - unique
        
        status = "✓" if duplicates == 0 else "✗"
        print(f"{status} {target:15} - Total: {total}, Unique: {unique}, Duplicates: {duplicates}")
    
    total_all = Molecule.objects.count()
    unique_all = Molecule.objects.values('smiles', 'gene_target').distinct().count()
    print(f"\nOverall: {total_all} total, {unique_all} unique, {total_all - unique_all} duplicates")

if __name__ == "__main__":
    main()
