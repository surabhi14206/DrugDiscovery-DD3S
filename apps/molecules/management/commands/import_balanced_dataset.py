"""
Django Management Command to Import Balanced Dataset
Imports molecules from Balanced_7_Gene_200_per_target.json into the database
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.molecules.models import Molecule, ImportStatistics
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import molecules from Balanced_7_Gene_200_per_target.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Balanced_7_Gene_200_per_target.json',
            help='Path to the JSON file to import'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing molecules before import'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for bulk operations (default: 50)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        clear_existing = options['clear']
        batch_size = options['batch_size']
        
        # Check if file exists
        if not Path(file_path).exists():
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        # Clear existing molecules if requested
        if clear_existing:
            count = Molecule.objects.count()
            if count > 0:
                self.stdout.write(self.style.WARNING(f'Clearing {count} existing molecules...'))
                Molecule.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('✓ Cleared existing molecules'))
        
        # Load JSON data
        self.stdout.write(f'Loading data from {file_path}...')
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {len(data)} molecules from JSON'))
        
        # Track statistics
        created_count = 0
        updated_count = 0
        error_count = 0
        skipped_count = 0
        
        # Import molecules in batches
        total = len(data)
        
        for i in range(0, total, batch_size):
            batch = data[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            self.stdout.write(f'\nProcessing batch {batch_num}/{total_batches} ({len(batch)} molecules)...')
            
            for item in batch:
                try:
                    smiles = item.get('SMILES', '').strip()
                    target = item.get('Target', '').strip()
                    is_active = bool(item.get('isActive', 0))
                    
                    if not smiles:
                        self.stdout.write(self.style.WARNING(f'  ⚠ Skipping entry with no SMILES'))
                        skipped_count += 1
                        continue
                    
                    # Create unique name based on target and index
                    name = f"{target.upper()}_{item.get('Unnamed: 0', 'unknown')}"
                    
                    # Check if molecule already exists (by SMILES and target)
                    existing = Molecule.objects.filter(
                        smiles=smiles,
                        gene_target=target
                    ).first()
                    
                    if existing:
                        # Update existing molecule
                        existing.is_active = is_active
                        existing.name = name
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f'  ↻ Updated: {name}')
                    else:
                        # Create new molecule (skip PDB lookup to speed up import)
                        molecule = Molecule(
                            name=name,
                            smiles=smiles,
                            gene_target=target,
                            is_active=is_active,
                            pdb_id=None  # Set explicitly to skip lookup
                        )
                        # Save with skip_pdb_lookup flag (will be handled in model)
                        molecule._skip_pdb_lookup = True
                        molecule.save()
                        created_count += 1
                        
                        # Print progress every 10 molecules
                        if created_count % 10 == 0:
                            self.stdout.write(f'  ✓ Created {created_count} molecules...')
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error processing molecule: {str(e)}')
                    )
                    logger.exception(f"Error importing molecule: {item}")
            
            # Show batch progress
            progress = min(i + batch_size, total)
            percentage = (progress / total) * 100
            self.stdout.write(
                self.style.SUCCESS(f'Progress: {progress}/{total} ({percentage:.1f}%)')
            )
        
        # Create import statistics record
        ImportStatistics.objects.create(
            source_file=file_path,
            total_entries=len(data),
            created_count=created_count,
            updated_count=updated_count,
            error_count=error_count,
            notes=f"Balanced dataset import: {skipped_count} skipped"
        )
        
        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write('='*60)
        self.stdout.write(f'Total entries processed: {len(data)}')
        self.stdout.write(self.style.SUCCESS(f'✓ Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'↻ Updated: {updated_count}'))
        self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        self.stdout.write(f'⊘ Skipped: {skipped_count}')
        self.stdout.write('='*60)
        
        # Show gene target distribution
        self.stdout.write('\nGene Target Distribution:')
        from django.db.models import Count
        targets = Molecule.objects.values('gene_target').annotate(
            count=Count('id')
        ).order_by('gene_target')
        
        for target in targets:
            self.stdout.write(f"  {target['gene_target']:15} - {target['count']} molecules")
        
        self.stdout.write('\n' + self.style.SUCCESS('✓ All molecules imported successfully!'))
        self.stdout.write(f'\nVisit the home page to see {created_count + updated_count} featured molecules!')
