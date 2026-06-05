from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from .utils import get_molecular_weight, get_molecular_formula, get_pdb_id_from_smiles
import logging
import io

logger = logging.getLogger(__name__)


class Molecule(models.Model):
    """Store compound/molecule data"""
    
    pdb_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    smiles = models.TextField()
    molecular_formula = models.CharField(max_length=255, blank=True)
    molecular_weight = models.FloatField(null=True, blank=True)
    
    # Files
    structure_file = models.FileField(upload_to='structures/', null=True, blank=True)
    image_2d = models.ImageField(upload_to='molecule_images/', null=True, blank=True)
    
    # Properties from JSON
    is_active = models.BooleanField(default=False)
    gene_target = models.CharField(max_length=100, blank=True)
    
    # Predicted properties
    toxicity_score = models.FloatField(null=True, blank=True)
    solubility = models.FloatField(null=True, blank=True)
    radioactivity = models.CharField(max_length=50, null=True, blank=True)
    bioavailability = models.FloatField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    def save(self, *args, **kwargs):
        """
        Automatically calculate molecular weight and formula from SMILES.
        Also attempts to fetch PDB ID if not already set.
        
        This follows the standard chemistry workflow:
        1. Remove salts/solvents (anything after dots in SMILES)
        2. Parse SMILES and add implicit hydrogens
        3. Calculate weight using standard atomic masses
        4. Query RCSB PDB for matching structures
        5. Generate 2D structure image
        """
        if self.smiles:
            # Calculate molecular weight if not already set or if SMILES changed
            if not self.molecular_weight or self._state.adding:
                try:
                    # Calculate weight with salt removal enabled
                    self.molecular_weight = get_molecular_weight(
                        self.smiles, 
                        remove_salts=True
                    )
                    if self.molecular_weight:
                        logger.info(f"Calculated MW for {self.name}: {self.molecular_weight} g/mol")
                except Exception as e:
                    logger.error(f"Failed to calculate MW for {self.name}: {e}")
            
            # Calculate molecular formula if not set
            if not self.molecular_formula or self._state.adding:
                try:
                    self.molecular_formula = get_molecular_formula(
                        self.smiles,
                        remove_salts=True
                    )
                    if self.molecular_formula:
                        logger.info(f"Calculated formula for {self.name}: {self.molecular_formula}")
                except Exception as e:
                    logger.error(f"Failed to calculate formula for {self.name}: {e}")
            
            # Generate 2D image if not already set
            if not self.image_2d or self._state.adding:
                try:
                    from rdkit import Chem
                    from rdkit.Chem import AllChem, Draw
                except ImportError:
                    Chem = None
                    AllChem = None
                    Draw = None
                    
                try:
                    mol = Chem.MolFromSmiles(self.smiles) if Chem else None
                    if mol and AllChem and Draw:
                        AllChem.Compute2DCoords(mol)
                        img = Draw.MolToImage(mol, size=(400, 400))
                        
                        # Save to BytesIO buffer
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        buffer.seek(0)
                        
                        # Save to ImageField
                        filename = f"{self.name.replace(' ', '_')}_2d.png"
                        self.image_2d.save(filename, ContentFile(buffer.read()), save=False)
                        logger.info(f"Generated 2D image for {self.name}")
                except Exception as e:
                    logger.error(f"Failed to generate 2D image for {self.name}: {e}")
            
            # Fetch PDB ID if not set (only on new molecules to avoid repeated API calls)
            # Skip PDB lookup if _skip_pdb_lookup flag is set (for bulk imports)
            skip_lookup = getattr(self, '_skip_pdb_lookup', False)
            if (not self.pdb_id or self.pdb_id == "N/A") and self._state.adding and not skip_lookup:
                try:
                    pdb_id = get_pdb_id_from_smiles(self.smiles)
                    if pdb_id:
                        self.pdb_id = pdb_id
                        logger.info(f"Found PDB ID {pdb_id} for {self.name}")
                    else:
                        self.pdb_id = None  # Set to None instead of "N/A" for proper null handling
                        logger.info(f"No PDB ID found for {self.name}")
                except Exception as e:
                    logger.error(f"Failed to fetch PDB ID for {self.name}: {e}")
                    self.pdb_id = None
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.pdb_id or 'Custom'})"
    
    def get_esol_solubility(self):
        """Get ESOL solubility calculation for this molecule"""
        try:
            from .drug_properties import calculate_esol_solubility
            return calculate_esol_solubility(self.smiles)
        except Exception as e:
            logger.error(f"Error calculating ESOL solubility for {self.name}: {e}")
            return None
    
    def get_structural_alerts(self):
        """Get structural alerts (PAINS/Brenk) for this molecule"""
        try:
            from .drug_properties import check_structural_alerts
            return check_structural_alerts(self.smiles)
        except Exception as e:
            logger.error(f"Error checking structural alerts for {self.name}: {e}")
            return None
    
    def get_lipinski_profile(self):
        """Get Lipinski's Rule of 5 profile for this molecule"""
        try:
            from .drug_properties import check_lipinski_rule_of_5
            return check_lipinski_rule_of_5(self.smiles)
        except Exception as e:
            logger.error(f"Error checking Lipinski profile for {self.name}: {e}")
            return None
    
    def get_comprehensive_profile(self):
        """Get comprehensive drug properties profile"""
        try:
            from .drug_properties import get_comprehensive_drug_profile
            return get_comprehensive_drug_profile(self.smiles)
        except Exception as e:
            logger.error(f"Error getting comprehensive profile for {self.name}: {e}")
            return None
    
    class Meta:
        db_table = 'molecules'
        verbose_name = 'Molecule'
        verbose_name_plural = 'Molecules'
        ordering = ['-created_at']


class MoleculeProperty(models.Model):
    """Detailed molecular properties"""
    
    molecule = models.ForeignKey(
        Molecule,
        on_delete=models.CASCADE,
        related_name='properties'
    )
    property_name = models.CharField(max_length=100)
    property_value = models.TextField()
    confidence_score = models.FloatField(null=True, blank=True)
    predicted = models.BooleanField(default=False)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.molecule.name} - {self.property_name}"
    
    class Meta:
        db_table = 'molecule_properties'
        verbose_name = 'Molecule Property'
        verbose_name_plural = 'Molecule Properties'
        unique_together = ['molecule', 'property_name']


class ImportStatistics(models.Model):
    """Track molecule import statistics"""
    
    source_file = models.CharField(max_length=255)
    total_entries = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    import_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Import from {self.source_file} on {self.import_date.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        db_table = 'import_statistics'
        verbose_name = 'Import Statistic'
        verbose_name_plural = 'Import Statistics'
        ordering = ['-import_date']

