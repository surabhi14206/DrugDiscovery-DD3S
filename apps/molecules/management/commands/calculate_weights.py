"""
Management command to calculate molecular weights for existing molecules.
Updates all molecules in the database that don't have calculated weights.
"""
from django.core.management.base import BaseCommand
from apps.molecules.models import Molecule
from apps.molecules.utils import get_molecular_weight, get_molecular_formula
from django.db import transaction


class Command(BaseCommand):
    help = 'Calculate and update molecular weights and formulas for all molecules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate even if weight already exists',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of molecules to process',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        
        # Get molecules that need calculation
        if force:
            molecules = Molecule.objects.all()
            self.stdout.write(self.style.WARNING('Force mode: Recalculating ALL molecules'))
        else:
            molecules = Molecule.objects.filter(molecular_weight__isnull=True)
            self.stdout.write(f'Found {molecules.count()} molecules without weights')
        
        if limit:
            molecules = molecules[:limit]
            self.stdout.write(f'Processing first {limit} molecules')
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # Process in batches for efficiency
        batch_size = 100
        total = molecules.count()
        
        self.stdout.write(f'\nProcessing {total} molecules...\n')
        
        for i, molecule in enumerate(molecules, 1):
            try:
                if not molecule.smiles:
                    self.stdout.write(
                        self.style.WARNING(f'  [{i}/{total}] {molecule.name}: No SMILES - SKIPPED')
                    )
                    skipped_count += 1
                    continue
                
                # Calculate weight
                weight = get_molecular_weight(molecule.smiles, remove_salts=True)
                formula = get_molecular_formula(molecule.smiles, remove_salts=True)
                
                if weight is None:
                    self.stdout.write(
                        self.style.ERROR(f'  [{i}/{total}] {molecule.name}: Invalid SMILES - ERROR')
                    )
                    error_count += 1
                    continue
                
                # Update molecule
                molecule.molecular_weight = weight
                if formula:
                    molecule.molecular_formula = formula
                molecule.save(update_fields=['molecular_weight', 'molecular_formula', 'updated_at'])
                
                success_count += 1
                
                # Show progress every 10 molecules
                if i % 10 == 0 or i == total:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  [{i}/{total}] {molecule.name}: '
                            f'MW={weight:.2f} g/mol, Formula={formula or "N/A"}'
                        )
                    )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  [{i}/{total}] {molecule.name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully calculated: {success_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        if skipped_count:
            self.stdout.write(self.style.WARNING(f'⊘ Skipped: {skipped_count}'))
        self.stdout.write(self.style.SUCCESS(f'\nTotal processed: {success_count + error_count + skipped_count}'))
        self.stdout.write('='*70 + '\n')
