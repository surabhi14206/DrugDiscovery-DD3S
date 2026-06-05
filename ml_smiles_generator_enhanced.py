"""
Enhanced ML-Based SMILES Generator with Database Integration
Uses character-level LSTM to generate SMILES strings from molecular structures
Integrates PubChem, ChEMBL for high-quality training data
"""
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
import pickle
import os
from collections import Counter
from molecular_database_fetcher import fetch_training_data, MolecularDataset
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmilesGenerator:
    """Character-level LSTM model for SMILES generation with database integration"""
    
    def __init__(self, max_length=100, embedding_dim=128, lstm_units=256):
        self.max_length = max_length
        self.embedding_dim = embedding_dim
        self.lstm_units = lstm_units
        self.model = None
        self.char_to_idx = {}
        self.idx_to_char = {}
        self.vocab_size = 0
        
    def load_data_from_databases(self, count=10000, source='both'):
        """
        Load SMILES data from online databases (PubChem, ChEMBL)
        
        Args:
            count: Number of molecules to fetch
            source: 'pubchem', 'chembl', or 'both'
            
        Returns:
            List of validated SMILES strings
        """
        logger.info(f"Fetching {count} molecules from {source}...")
        smiles_list = fetch_training_data(count=count, source=source, validate=True)
        logger.info(f"Loaded {len(smiles_list)} validated SMILES from databases")
        return smiles_list
    
    def load_data(self, json_files=None, use_databases=True, db_count=10000, db_source='both'):
        """
        Load SMILES data from JSON files and/or online databases
        
        Args:
            json_files: List of JSON files (optional)
            use_databases: Whether to fetch from online databases
            db_count: Number of molecules to fetch from databases
            db_source: 'pubchem', 'chembl', or 'both'
        """
        smiles_list = []
        
        # Load from databases (recommended for high quality data)
        if use_databases:
            try:
                db_smiles = self.load_data_from_databases(count=db_count, source=db_source)
                smiles_list.extend(db_smiles)
                logger.info(f"Loaded {len(db_smiles)} SMILES from databases")
            except Exception as e:
                logger.error(f"Error loading from databases: {e}")
                logger.info("Falling back to JSON files...")
        
        # Load from JSON files (optional/supplementary)
        if json_files:
            for json_file in json_files:
                logger.info(f"Loading {json_file}...")
                try:
                    if os.path.getsize(json_file) > 100 * 1024 * 1024:  # > 100MB
                        # Load in chunks for large files
                        logger.info(f"  Large file detected, loading in chunks...")
                        with open(json_file, 'r') as f:
                            content = f.read()
                            data = json.loads(content)
                            
                            # Limit to 50000 samples for training efficiency
                            data = data[:50000]
                    else:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                    
                    # Extract SMILES from different JSON formats
                    for item in data:
                        if isinstance(item, dict):
                            smiles = item.get('SMILES') or item.get('smiles') or item.get('CanonicalSMILES')
                            if smiles:
                                smiles_list.append(smiles)
                        elif isinstance(item, str):
                            smiles_list.append(item)
                    
                    logger.info(f"  Loaded {len(smiles_list)} SMILES so far")
                    
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")
        
        # Remove duplicates and filter by length
        smiles_list = list(set(smiles_list))
        smiles_list = [s for s in smiles_list if 3 <= len(s) <= self.max_length]
        
        logger.info(f"Total unique valid SMILES: {len(smiles_list)}")
        
        if len(smiles_list) == 0:
            raise ValueError("No SMILES data loaded! Check your data sources.")
        
        # Build vocabulary
        self._build_vocabulary(smiles_list)
        
        return smiles_list
    
    def _build_vocabulary(self, smiles_list):
        """Build character vocabulary from SMILES strings"""
        all_chars = set()
        for smiles in smiles_list:
            all_chars.update(smiles)
        
        # Sort for consistency
        chars = sorted(list(all_chars))
        
        # Add special tokens
        self.char_to_idx = {'<PAD>': 0, '<START>': 1, '<END>': 2}
        for i, char in enumerate(chars, start=3):
            self.char_to_idx[char] = i
        
        self.idx_to_char = {idx: char for char, idx in self.char_to_idx.items()}
        self.vocab_size = len(self.char_to_idx)
        
        logger.info(f"Vocabulary size: {self.vocab_size}")
        logger.info(f"Characters: {chars}")
    
    def prepare_sequences(self, smiles_list):
        """Convert SMILES strings to training sequences"""
        X, y = [], []
        
        for smiles in smiles_list:
            # Encode SMILES
            encoded = [self.char_to_idx['<START>']]
            for char in smiles:
                if char in self.char_to_idx:
                    encoded.append(self.char_to_idx[char])
            encoded.append(self.char_to_idx['<END>'])
            
            # Create input/output pairs
            for i in range(1, len(encoded)):
                X.append(encoded[:i])
                y.append(encoded[i])
        
        # Pad sequences
        X = keras.preprocessing.sequence.pad_sequences(
            X, maxlen=self.max_length, padding='post', value=self.char_to_idx['<PAD>']
        )
        y = keras.utils.to_categorical(y, num_classes=self.vocab_size)
        
        return X, y
    
    def build_model(self):
        """Build LSTM model for SMILES generation"""
        model = keras.Sequential([
            layers.Embedding(
                input_dim=self.vocab_size,
                output_dim=self.embedding_dim,
                mask_zero=True
            ),
            layers.LSTM(self.lstm_units, return_sequences=True),
            layers.Dropout(0.3),
            layers.LSTM(128, return_sequences=False),
            layers.Dropout(0.3),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(self.vocab_size, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        self.model = model
        logger.info("Model built successfully")
        logger.info(f"Total parameters: {model.count_params():,}")
        
        return model
    
    def train(self, smiles_list, epochs=50, batch_size=128, validation_split=0.2):
        """Train the SMILES generator"""
        logger.info("Preparing training data...")
        X, y = self.prepare_sequences(smiles_list)
        
        logger.info(f"Training samples: {len(X)}")
        logger.info(f"Input shape: {X.shape}")
        logger.info(f"Output shape: {y.shape}")
        
        if self.model is None:
            self.build_model()
        
        # Callbacks
        callbacks = [
            keras.callbacks.ModelCheckpoint(
                'ml_models/smiles_generator_best.h5',
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            ),
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=3,
                verbose=1
            )
        ]
        
        logger.info("Starting training...")
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def generate_smiles(self, temperature=0.8, max_length=100):
        """Generate a SMILES string"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        # Start with START token
        sequence = [self.char_to_idx['<START>']]
        
        for _ in range(max_length):
            # Pad sequence
            padded = keras.preprocessing.sequence.pad_sequences(
                [sequence],
                maxlen=self.max_length,
                padding='post',
                value=self.char_to_idx['<PAD>']
            )
            
            # Predict next character
            predictions = self.model.predict(padded, verbose=0)[0]
            
            # Apply temperature
            predictions = np.log(predictions + 1e-7) / temperature
            predictions = np.exp(predictions) / np.sum(np.exp(predictions))
            
            # Sample next character
            next_idx = np.random.choice(len(predictions), p=predictions)
            
            # Stop if END token
            if next_idx == self.char_to_idx['<END>']:
                break
            
            sequence.append(next_idx)
        
        # Decode to SMILES
        smiles = ''.join([
            self.idx_to_char[idx] for idx in sequence[1:]  # Skip START token
            if idx != self.char_to_idx['<PAD>']
        ])
        
        return smiles
    
    def save(self, model_path='ml_models/smiles_generator_model.h5', 
             vocab_path='ml_models/vocabulary.pkl'):
        """Save model and vocabulary"""
        os.makedirs('ml_models', exist_ok=True)
        
        self.model.save(model_path)
        
        with open(vocab_path, 'wb') as f:
            pickle.dump({
                'char_to_idx': self.char_to_idx,
                'idx_to_char': self.idx_to_char,
                'vocab_size': self.vocab_size,
                'max_length': self.max_length
            }, f)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Vocabulary saved to {vocab_path}")
    
    def load(self, model_path='ml_models/smiles_generator_model.h5',
             vocab_path='ml_models/vocabulary.pkl'):
        """Load model and vocabulary"""
        self.model = keras.models.load_model(model_path)
        
        with open(vocab_path, 'rb') as f:
            vocab = pickle.load(f)
            self.char_to_idx = vocab['char_to_idx']
            self.idx_to_char = vocab['idx_to_char']
            self.vocab_size = vocab['vocab_size']
            self.max_length = vocab['max_length']
        
        logger.info(f"Model loaded from {model_path}")
        logger.info(f"Vocabulary loaded from {vocab_path}")


def main():
    """Main training function with database integration"""
    logger.info("=" * 80)
    logger.info("ENHANCED ML-BASED SMILES GENERATOR")
    logger.info("Training with PubChem and ChEMBL databases")
    logger.info("=" * 80)
    
    # Initialize generator
    generator = SmilesGenerator(max_length=100)
    
    # Choose data source
    print("\nData Source Options:")
    print("1. PubChem + ChEMBL (Recommended - High Quality)")
    print("2. PubChem only")
    print("3. ChEMBL only")
    print("4. Local JSON file (ALL_7_Gene_SMILES_isActive.json)")
    print("5. Combination (Databases + JSON)")
    
    choice = input("\nSelect option (1-5) [default: 1]: ").strip() or "1"
    
    if choice == "1":
        # PubChem + ChEMBL
        smiles_data = generator.load_data(use_databases=True, db_count=15000, db_source='both')
    elif choice == "2":
        # PubChem only
        smiles_data = generator.load_data(use_databases=True, db_count=15000, db_source='pubchem')
    elif choice == "3":
        # ChEMBL only
        smiles_data = generator.load_data(use_databases=True, db_count=15000, db_source='chembl')
    elif choice == "4":
        # Local JSON only
        smiles_data = generator.load_data(
            json_files=['ALL_7_Gene_SMILES_isActive.json'],
            use_databases=False
        )
    else:
        # Combination
        smiles_data = generator.load_data(
            json_files=['ALL_7_Gene_SMILES_isActive.json'],
            use_databases=True,
            db_count=10000,
            db_source='both'
        )
    
    # Train model
    logger.info(f"\nTraining on {len(smiles_data)} unique SMILES...")
    history = generator.train(smiles_data, epochs=50, batch_size=128)
    
    # Save model
    generator.save()
    
    # Test generation
    logger.info("\n" + "=" * 80)
    logger.info("Testing SMILES Generation:")
    logger.info("=" * 80)
    
    for temp in [0.5, 0.8, 1.0]:
        logger.info(f"\nTemperature {temp}:")
        for i in range(3):
            smiles = generator.generate_smiles(temperature=temp)
            logger.info(f"  {i+1}. {smiles}")
    
    # Validate with RDKit
    try:
        from rdkit import Chem
        logger.info("\n" + "=" * 80)
        logger.info("RDKit Validation:")
        logger.info("=" * 80)
        
        valid_count = 0
        total_tests = 10
        
        for i in range(total_tests):
            smiles = generator.generate_smiles(temperature=0.8)
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is not None:
                valid_count += 1
                canonical = Chem.MolToSmiles(mol)
                logger.info(f"✓ Valid: {smiles} → {canonical}")
            else:
                logger.info(f"✗ Invalid: {smiles}")
        
        logger.info(f"\nValidity Rate: {valid_count}/{total_tests} ({100*valid_count/total_tests:.1f}%)")
        
    except ImportError:
        logger.warning("RDKit not installed. Skipping validation.")
    
    logger.info("\n" + "=" * 80)
    logger.info("Training Complete!")
    logger.info("=" * 80)
    logger.info("\nModel saved to: ml_models/smiles_generator_model.h5")
    logger.info("Vocabulary saved to: ml_models/vocabulary.pkl")
    logger.info("\nYou can now use the 'Generate ML SMILES' button in the web interface!")


if __name__ == '__main__':
    main()
