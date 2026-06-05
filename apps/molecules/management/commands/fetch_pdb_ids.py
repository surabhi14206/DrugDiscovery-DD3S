"""
Management command to fetch PDB IDs for molecules from RCSB PDB database.
Queries the PDB API using SMILES strings to find matching crystal structures.
"""
from django.core.management.base import BaseCommand
from apps.molecules.models import Molecule
from apps.molecules.utils import get_pdb_id_from_smiles, get_all_pdb_ids_from_smiles
import time


class Command(BaseCommand):
    help = 'Fetch PDB IDs from RCSB PDB for molecules using their SMILES'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Refetch PDB IDs even if already set',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of molecules to process',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between API calls in seconds (default: 0.5)',
        )
        parser.add_argument(
            '--relaxed',
            action='store_true',
            help='Use relaxed matching (finds similar structures)',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Show all PDB IDs found (not just first match)',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        delay = options['delay']
        relaxed = options['relaxed']
        show_all = options['show_all']
        
        match_type = 'graph-relaxed' if relaxed else 'graph-exact'
        
        # Get molecules that need PDB ID lookup
        if force:
            molecules = Molecule.objects.all()
            self.stdout.write(self.style.WARNING('Force mode: Checking ALL molecules'))
        else:
            molecules = Molecule.objects.filter(pdb_id__isnull=True)
            self.stdout.write(f'Found {molecules.count()} molecules without PDB IDs')
        
        if limit:
            molecules = molecules[:limit]
            self.stdout.write(f'Processing first {limit} molecules')
        
        success_count = 0
        not_found_count = 0
        error_count = 0
        skipped_count = 0
        
        total = molecules.count()
        
        self.stdout.write(f'\nQuerying RCSB PDB ({match_type} matching)...\n')
        self.stdout.write(f'Delay between requests: {delay}s\n')
        
        for i, molecule in enumerate(molecules, 1):
            try:
                if not molecule.smiles:
                    self.stdout.write(
                        self.style.WARNING(f'  [{i}/{total}] {molecule.name}: No SMILES - SKIPPED')
                    )
                    skipped_count += 1
                    continue
                
                # Show all PDB IDs or just fetch first one
                if show_all:
                    pdb_ids = get_all_pdb_ids_from_smiles(
                        molecule.smiles,
                        match_type=match_type,
                        limit=10
                    )
                    
                    if pdb_ids:
                        pdb_id = pdb_ids[0]  # Use first for database
                        molecule.pdb_id = pdb_id
                        molecule.save(update_fields=['pdb_id', 'updated_at'])
                        success_count += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [{i}/{total}] {molecule.name}: Found {len(pdb_ids)} entries'
                            )
                        )
                        self.stdout.write(f'    Primary: {pdb_id}')
                        if len(pdb_ids) > 1:
                            self.stdout.write(f'    Others: {", ".join(pdb_ids[1:])}')
                    else:
                        not_found_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{i}/{total}] {molecule.name}: Not found in PDB'
                            )
                        )
                else:
                    # Just fetch first match
                    pdb_id = get_pdb_id_from_smiles(
                        molecule.smiles,
                        match_type=match_type
                    )
                    
                    if pdb_id:
                        molecule.pdb_id = pdb_id
                        molecule.save(update_fields=['pdb_id', 'updated_at'])
                        success_count += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [{i}/{total}] {molecule.name}: PDB ID = {pdb_id}'
                            )
                        )
                    else:
                        not_found_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{i}/{total}] {molecule.name}: Not found in PDB'
                            )
                        )
                
                # Rate limiting - be nice to RCSB servers
                if i < total:
                    time.sleep(delay)
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  [{i}/{total}] {molecule.name}: ERROR - {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully found PDB IDs: {success_count}'))
        if not_found_count:
            self.stdout.write(self.style.WARNING(f'⊘ Not found in PDB: {not_found_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        if skipped_count:
            self.stdout.write(self.style.WARNING(f'⊘ Skipped (no SMILES): {skipped_count}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal processed: {success_count + not_found_count + error_count + skipped_count}'))
        
        if not_found_count > 0:
            self.stdout.write('\n' + self.style.WARNING('Note:'))
            self.stdout.write('  Molecules not found in PDB may be:')
            self.stdout.write('  - Novel compounds not yet crystallized')
            self.stdout.write('  - Library compounds without structural data')
            self.stdout.write('  - Try --relaxed flag for similar structures')
        
        self.stdout.write('='*70 + '\n')
