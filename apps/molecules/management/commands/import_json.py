import json
from django.core.management.base import BaseCommand
from apps.molecules.models import Molecule, ImportStatistics


class Command(BaseCommand):
    help = 'Import molecules from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='ALL_7_Gene_SMILES_isActive.json',
            help='Path to JSON file'
        )

    def handle(self, *args, **options):
        json_file = options['file']
        
        self.stdout.write(f'Loading data from {json_file}...')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File {json_file} not found!'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON: {e}'))
            return

        self.stdout.write(f'Found {len(data)} entries')
        
        # Process in batches for better performance with large datasets
        batch_size = 1000
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for idx, entry in enumerate(data, 1):
            try:
                smiles = entry.get('SMILES', '').strip()
                target = entry.get('Target', '').strip()
                is_active = entry.get('isActive', 0)
                
                if not smiles:
                    error_count += 1
                    continue
                
                # Try to get or create molecule
                molecule, created = Molecule.objects.get_or_create(
                    smiles=smiles,
                    defaults={
                        'name': f'{target}_{is_active}_{idx}',
                        'is_active': bool(is_active),
                        'gene_target': target,
                        'molecular_formula': '',
                    }
                )
                
                if created:
                    created_count += 1
                    if idx % 1000 == 0:
                        self.stdout.write(f'Processed {idx}/{len(data)}...')
                else:
                    # Update existing
                    if not molecule.gene_target:
                        molecule.gene_target = target
                    molecule.is_active = bool(is_active)
                    molecule.save()
                    updated_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Entry {idx}: Error - {str(e)[:100]}'))
                error_count += 1
                if error_count > 100:
                    self.stdout.write(self.style.ERROR('Too many errors, stopping import'))
                    break
                continue
        
        # Save import statistics to database
        try:
            ImportStatistics.objects.create(
                source_file=json_file,
                total_entries=len(data),
                created_count=created_count,
                updated_count=updated_count,
                error_count=error_count,
                notes=f"Import completed successfully. Found {len(data)} entries."
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed to save import statistics: {e}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nImport complete!\n'
            f'Created: {created_count}\n'
            f'Updated: {updated_count}\n'
            f'Errors: {error_count}'
        ))
