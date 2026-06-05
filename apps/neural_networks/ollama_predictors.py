"""
Ollama-based AI Predictors using Gemma3:4b model
Provides toxicity, solubility, bioavailability and other predictions using local LLM
"""
import logging
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski
except ImportError:
    Chem = None
    Descriptors = None
    Crippen = None
    Lipinski = None

logger = logging.getLogger(__name__)


class OllamaMolecularPredictor:
    """Use Ollama's Gemma3:4b to predict molecular properties"""
    
    def __init__(self, model_name='gemma3:4b'):
        self.model_name = model_name
    
    def _get_molecular_context(self, smiles: str) -> str:
        """Extract molecular features for context"""
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return f"SMILES: {smiles} (Invalid)"
            
            context = f"""SMILES: {smiles}
Molecular Weight: {Descriptors.MolWt(mol):.2f} g/mol
LogP: {Crippen.MolLogP(mol):.2f}
H-Bond Donors: {Descriptors.NumHDonors(mol)}
H-Bond Acceptors: {Descriptors.NumHAcceptors(mol)}
Rotatable Bonds: {Descriptors.NumRotatableBonds(mol)}
Aromatic Rings: {Descriptors.NumAromaticRings(mol)}
TPSA: {Descriptors.TPSA(mol):.2f}"""
            
            return context
        except Exception as e:
            logger.error(f"Error calculating descriptors: {e}")
            return f"SMILES: {smiles}"
    
    def _query_ollama(self, prompt: str) -> dict:
        """Query Ollama model"""
        try:
            import ollama
            
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent predictions
                    'num_predict': 150,
                }
            )
            
            return {
                'success': True,
                'response': response['message']['content']
            }
            
        except ConnectionError as e:
            logger.error(f"Ollama connection error: {e}")
            return {
                'success': False,
                'error': 'Ollama not running. Please start Ollama and run: ollama pull gemma3:4b'
            }
        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg:
                return {
                    'success': False,
                    'error': 'Model not found. Run: ollama pull gemma3:4b'
                }
            logger.error(f"Ollama query error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_toxicity(self, smiles: str) -> dict:
        """Predict toxicity score using AI"""
        context = self._get_molecular_context(smiles)
        
        prompt = f"""Analyze this molecule for toxicity:

{context}

Based on molecular structure and properties, predict toxicity score (0.0 = safe, 1.0 = highly toxic).
Consider: reactive groups, heavy atoms, aromatic systems, molecular weight.

Respond with ONLY a number between 0.0 and 1.0, followed by a brief explanation."""
        
        result = self._query_ollama(prompt)
        
        if not result['success']:
            return {
                'smiles': smiles,
                'toxicity_score': None,
                'prediction': 'unavailable',
                'confidence': 0.0,
                'explanation': result['error'],
                'model': self.model_name
            }
        
        # Parse response to extract score
        response_text = result['response']
        try:
            # Try to extract a number from the response
            import re
            numbers = re.findall(r'0\.\d+|1\.0', response_text)
            score = float(numbers[0]) if numbers else 0.5
        except:
            score = 0.5  # Default to moderate toxicity
        
        return {
            'smiles': smiles,
            'toxicity_score': round(score, 2),
            'prediction': 'toxic' if score > 0.6 else 'moderate' if score > 0.3 else 'safe',
            'confidence': 0.75,
            'explanation': response_text,
            'model': self.model_name
        }
    
    def predict_solubility(self, smiles: str) -> dict:
        """Predict aqueous solubility (LogS) using AI"""
        context = self._get_molecular_context(smiles)
        
        prompt = f"""Analyze this molecule for water solubility:

{context}

Predict LogS (log of solubility in mol/L). Typical range: -10 (insoluble) to 0 (highly soluble).
Consider: molecular weight, LogP, hydrogen bonding, polarity.

Respond with ONLY a LogS value (e.g., -4.5), followed by interpretation."""
        
        result = self._query_ollama(prompt)
        
        if not result['success']:
            return {
                'smiles': smiles,
                'log_solubility': None,
                'prediction': 'unavailable',
                'explanation': result['error'],
                'model': self.model_name
            }
        
        # Parse response to extract LogS value
        response_text = result['response']
        try:
            import re
            # Match negative or positive decimals
            numbers = re.findall(r'-?\d+\.?\d*', response_text)
            log_s = float(numbers[0]) if numbers else -4.0
            # Clamp to reasonable range
            log_s = max(-10.0, min(0.0, log_s))
        except:
            log_s = -4.0  # Default moderate solubility
        
        return {
            'smiles': smiles,
            'log_solubility': round(log_s, 2),
            'prediction': 'soluble' if log_s > -4 else 'moderate' if log_s > -6 else 'insoluble',
            'explanation': response_text,
            'model': self.model_name
        }
    
    def predict_bioavailability(self, smiles: str) -> dict:
        """Predict oral bioavailability using AI"""
        context = self._get_molecular_context(smiles)
        
        prompt = f"""Analyze this molecule for oral bioavailability:

{context}

Predict bioavailability score (0.0 = poor, 1.0 = excellent).
Consider: Lipinski's Rule of Five, molecular weight, LogP, hydrogen bonding, TPSA.

Respond with ONLY a score between 0.0 and 1.0, followed by explanation."""
        
        result = self._query_ollama(prompt)
        
        if not result['success']:
            return {
                'smiles': smiles,
                'bioavailability_score': None,
                'prediction': 'unavailable',
                'explanation': result['error'],
                'model': self.model_name
            }
        
        # Parse response
        response_text = result['response']
        try:
            import re
            numbers = re.findall(r'0\.\d+|1\.0', response_text)
            score = float(numbers[0]) if numbers else 0.5
        except:
            score = 0.5
        
        return {
            'smiles': smiles,
            'bioavailability_score': round(score, 2),
            'prediction': 'good' if score > 0.7 else 'moderate' if score > 0.4 else 'poor',
            'explanation': response_text,
            'model': self.model_name
        }
    
    def predict_all(self, smiles: str) -> dict:
        """Run all predictions at once"""
        return {
            'smiles': smiles,
            'toxicity': self.predict_toxicity(smiles),
            'solubility': self.predict_solubility(smiles),
            'bioavailability': self.predict_bioavailability(smiles),
            'model': self.model_name
        }


# Global instance
ollama_predictor = OllamaMolecularPredictor()
