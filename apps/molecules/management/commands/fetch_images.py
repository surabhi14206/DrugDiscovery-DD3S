"""
Management command to fetch and save 2D images from PubChem for all molecules.

Usage:
    python manage.py fetch_images
    python manage.py fetch_images --force  # Re-download existing images
    python manage.py fetch_images --limit 10  # Only fetch first 10
"""

import requests
import time
from io import BytesIO
from urllib.parse import quote_plus
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.molecules.models import Molecule


class Command(BaseCommand):
    help = 'Fetch and save 2D images from PubChem for all molecules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-download images that already exist',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of molecules to process',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between requests in seconds (default: 0.5)',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        delay = options['delay']

        # Get molecules to process
        molecules = Molecule.objects.all()
        if not force:
            molecules = molecules.filter(image_2d='')
        if limit:
            molecules = molecules[:limit]

        total = molecules.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No molecules to process'))
            return

        self.stdout.write(self.style.SUCCESS(f'Processing {total} molecule(s)...'))

        success_count = 0
        error_count = 0

        for i, molecule in enumerate(molecules, 1):
            self.stdout.write(f'[{i}/{total}] Processing {molecule.name}...')

            try:
                # Fetch image from PubChem
                smiles_encoded = quote_plus(molecule.smiles)
                url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles_encoded}/PNG?image_size=large'
                
                self.stdout.write(f'  Fetching from: {url}')
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Save image to molecule
                image_name = f'{molecule.name.replace(" ", "_")}_2d.png'
                molecule.image_2d.save(
                    image_name,
                    ContentFile(response.content),
                    save=True
                )

                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Image saved: {image_name}'))

            except requests.exceptions.RequestException as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error fetching image: {e}'))
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Unexpected error: {e}'))

            # Rate limiting
            if i < total:
                time.sleep(delay)

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully fetched: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        self.stdout.write('=' * 50)
