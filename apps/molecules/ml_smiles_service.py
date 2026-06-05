"""
ML SMILES Generation Service for Django
Integrates the trained LSTM model into the web application
"""
import os
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MLSmilesService:
    """Service to generate SMILES using trained ML model"""
    
    _instance = None
    _model_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.generator = None
        self.model_path = None
        
    def load_model(self, model_path='ml_models/smiles_generator'):
        """Load the trained model"""
        if self._model_loaded:
            return True
        
        try:
            # Import here to avoid issues if tensorflow not installed yet
            from ml_smiles_generator import SmilesGenerator
            
            base_dir = Path(__file__).resolve().parent.parent
            full_path = base_dir / model_path
            
            if not os.path.exists(f'{full_path}_model.h5'):
                logger.warning(f"ML model not found at {full_path}")
                return False
            
            self.generator = SmilesGenerator()
            self.generator.load(str(full_path))
            self._model_loaded = True
            logger.info("ML SMILES Generator loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading ML model: {e}")
            return False
    
    def generate_smiles(self, temperature=0.8, num_attempts=5):
        """
        Generate a SMILES string using ML model
        
        Args:
            temperature: Sampling temperature (0.5-1.5)
            num_attempts: Number of generation attempts
            
        Returns:
            dict: {
                'smiles': generated SMILES string,
                'method': 'ML-LSTM',
                'temperature': temperature used,
                'success': bool
            }
        """
        if not self._model_loaded:
            if not self.load_model():
                return {
                    'smiles': None,
                    'method': 'ML-LSTM',
                    'success': False,
                    'error': 'Model not loaded'
                }
        
        try:
            # Try multiple times to get a valid SMILES
            for attempt in range(num_attempts):
                smiles = self.generator.generate_smiles(temperature=temperature)
                
                # Basic validation
                if smiles and len(smiles) > 3:
                    return {
                        'smiles': smiles,
                        'method': 'ML-LSTM',
                        'temperature': temperature,
                        'success': True,
                        'attempt': attempt + 1
                    }
            
            return {
                'smiles': None,
                'method': 'ML-LSTM',
                'success': False,
                'error': 'Failed to generate valid SMILES after multiple attempts'
            }
            
        except Exception as e:
            logger.error(f"Error generating SMILES: {e}")
            return {
                'smiles': None,
                'method': 'ML-LSTM',
                'success': False,
                'error': str(e)
            }
    
    def generate_batch(self, count=10, temperature=0.8):
        """Generate multiple SMILES strings"""
        results = []
        for i in range(count):
            result = self.generate_smiles(temperature=temperature)
            if result['success']:
                results.append(result['smiles'])
        return results
    
    def is_model_available(self):
        """Check if model is available"""
        return self._model_loaded


# Singleton instance
ml_smiles_service = MLSmilesService()


def generate_ml_smiles(temperature=0.8):
    """
    Convenience function to generate SMILES
    
    Usage:
        from apps.molecules.ml_smiles_service import generate_ml_smiles
        result = generate_ml_smiles(temperature=0.8)
    """
    return ml_smiles_service.generate_smiles(temperature=temperature)
