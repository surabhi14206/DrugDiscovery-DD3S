"""
Management command to generate 2D images for all molecules in the database.
Usage: python manage.py generate_molecule_images
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.molecules.models import Molecule
import io
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate 2D structure images for all molecules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate images even if they already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, Draw
        except ImportError:
            self.stdout.write(self.style.ERROR('RDKit is not installed. Install it with: pip install rdkit'))
            return
        
        molecules = Molecule.objects.all()
        total = molecules.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No molecules found in database'))
            return
        
        self.stdout.write(f'Processing {total} molecules...')
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, molecule in enumerate(molecules, 1):
            # Skip if image already exists and not forcing
            if molecule.image_2d and not force:
                skip_count += 1
                self.stdout.write(f'[{idx}/{total}] Skipping {molecule.name} (image exists)')
                continue
            
            try:
                mol = Chem.MolFromSmiles(molecule.smiles)
                if not mol:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'[{idx}/{total}] Invalid SMILES for {molecule.name}'))
                    continue
                
                # Generate 2D coordinates and image
                AllChem.Compute2DCoords(mol)
                img = Draw.MolToImage(mol, size=(400, 400))
                
                # Save to BytesIO buffer
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Save to ImageField
                filename = f"{molecule.name.replace(' ', '_')}_2d.png"
                molecule.image_2d.save(filename, ContentFile(buffer.read()), save=True)
                
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'[{idx}/{total}] Generated image for {molecule.name}'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'[{idx}/{total}] Error processing {molecule.name}: {str(e)}'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Successfully generated: {success_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skip_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write('='*50)
