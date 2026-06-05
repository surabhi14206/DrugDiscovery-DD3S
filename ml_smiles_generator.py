"""
ML-Based SMILES Generator
Uses character-level LSTM to generate SMILES strings from molecular structures
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

class SmilesGenerator:
    """Character-level LSTM model for SMILES generation"""
    
    def __init__(self, max_length=100, embedding_dim=128, lstm_units=256):
        self.max_length = max_length
        self.embedding_dim = embedding_dim
        self.lstm_units = lstm_units
        self.model = None
        self.char_to_idx = {}
        self.idx_to_char = {}
        self.vocab_size = 0
        
    def load_data(self, json_files):
        """Load SMILES data from JSON files"""
        smiles_list = []
        
        for json_file in json_files:
            print(f"Loading {json_file}...")
            try:
                if os.path.getsize(json_file) > 100 * 1024 * 1024:  # > 100MB
                    # Load in chunks for large files
                    print(f"  Large file detected, loading in chunks...")
                    with open(json_file, 'r') as f:
                        # Read first part to get structure
                        data = []
                        chunk_size = 10000
                        f.seek(0)
                        content = f.read()
                        data = json.loads(content)
                        
                        # Limit to 50000 samples for training efficiency
                        data = data[:50000]
                else:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                
                # Extract SMILES
                for item in data:
                    if isinstance(item, dict) and 'SMILES' in item:
                        smiles = item['SMILES']
                        if smiles and len(smiles) <= self.max_length:
                            smiles_list.append(smiles)
                            
                print(f"  Loaded {len(smiles_list)} SMILES from {json_file}")
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue
        
        return smiles_list
    
    def build_vocabulary(self, smiles_list):
        """Build character vocabulary from SMILES strings"""
        all_chars = set()
        for smiles in smiles_list:
            all_chars.update(smiles)
        
        # Add special tokens
        all_chars.add('<START>')
        all_chars.add('<END>')
        all_chars.add('<PAD>')
        
        # Create mappings
        self.char_to_idx = {char: idx for idx, char in enumerate(sorted(all_chars))}
        self.idx_to_char = {idx: char for char, idx in self.char_to_idx.items()}
        self.vocab_size = len(self.char_to_idx)
        
        print(f"Vocabulary size: {self.vocab_size}")
        print(f"Characters: {sorted(all_chars)}")
        
    def encode_smiles(self, smiles):
        """Encode SMILES string to indices"""
        encoded = [self.char_to_idx['<START>']]
        for char in smiles:
            if char in self.char_to_idx:
                encoded.append(self.char_to_idx[char])
        encoded.append(self.char_to_idx['<END>'])
        
        # Pad to max_length
        if len(encoded) < self.max_length:
            encoded += [self.char_to_idx['<PAD>']] * (self.max_length - len(encoded))
        else:
            encoded = encoded[:self.max_length]
            
        return encoded
    
    def prepare_sequences(self, smiles_list):
        """Prepare input-output sequences for training"""
        X, y = [], []
        
        for smiles in smiles_list:
            encoded = self.encode_smiles(smiles)
            
            # Create sequences: predict next character
            for i in range(1, len(encoded)):
                X.append(encoded[:i])
                y.append(encoded[i])
        
        # Pad X sequences
        max_seq_len = max(len(seq) for seq in X)
        X_padded = np.zeros((len(X), max_seq_len))
        for i, seq in enumerate(X):
            X_padded[i, :len(seq)] = seq
        
        y = np.array(y)
        
        return X_padded, y
    
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
            layers.LSTM(self.lstm_units // 2),
            layers.Dropout(0.3),
            layers.Dense(self.lstm_units // 2, activation='relu'),
            layers.Dense(self.vocab_size, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        self.model = model
        return model
    
    def train(self, X, y, validation_split=0.2, epochs=50, batch_size=128):
        """Train the model"""
        if self.model is None:
            self.build_model()
        
        # Callbacks
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-6
        )
        
        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        return history
    
    def generate_smiles(self, seed='<START>', max_len=100, temperature=1.0):
        """Generate SMILES string"""
        if self.model is None:
            raise ValueError("Model not trained yet!")
        
        generated = [self.char_to_idx[seed]]
        
        for _ in range(max_len):
            # Prepare input
            x = np.array([generated])
            
            # Predict next character
            preds = self.model.predict(x, verbose=0)[0]
            preds = np.log(preds + 1e-7) / temperature
            preds = np.exp(preds) / np.sum(np.exp(preds))
            
            next_idx = np.random.choice(len(preds), p=preds)
            
            # Stop if END token
            if self.idx_to_char[next_idx] == '<END>':
                break
            
            # Skip PAD token
            if self.idx_to_char[next_idx] == '<PAD>':
                continue
            
            generated.append(next_idx)
        
        # Decode
        smiles = ''.join([
            self.idx_to_char[idx] 
            for idx in generated[1:]  # Skip START token
            if self.idx_to_char[idx] not in ['<START>', '<END>', '<PAD>']
        ])
        
        return smiles
    
    def save(self, base_path='models/smiles_generator'):
        """Save model and vocabulary"""
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        
        # Save model
        self.model.save(f'{base_path}_model.h5')
        
        # Save vocabulary
        vocab_data = {
            'char_to_idx': self.char_to_idx,
            'idx_to_char': self.idx_to_char,
            'vocab_size': self.vocab_size,
            'max_length': self.max_length
        }
        with open(f'{base_path}_vocab.pkl', 'wb') as f:
            pickle.dump(vocab_data, f)
        
        print(f"Model saved to {base_path}")
    
    def load(self, base_path='models/smiles_generator'):
        """Load model and vocabulary"""
        # Load vocabulary
        with open(f'{base_path}_vocab.pkl', 'rb') as f:
            vocab_data = pickle.load(f)
        
        self.char_to_idx = vocab_data['char_to_idx']
        self.idx_to_char = vocab_data['idx_to_char']
        self.vocab_size = vocab_data['vocab_size']
        self.max_length = vocab_data['max_length']
        
        # Load model
        self.model = keras.models.load_model(f'{base_path}_model.h5')
        
        print(f"Model loaded from {base_path}")


def main():
    """Main training pipeline"""
    print("=" * 70)
    print("SMILES GENERATOR - ML MODEL TRAINING")
    print("=" * 70)
    
    # Initialize generator
    generator = SmilesGenerator(max_length=150, embedding_dim=128, lstm_units=256)
    
    # Load data
    json_files = [
        'sample_molecules.json',
        # 'ALL_7_Gene_SMILES_isActive.json'  # Add if you want more data (will limit to 50k)
    ]
    
    smiles_list = generator.load_data(json_files)
    print(f"\nTotal SMILES loaded: {len(smiles_list)}")
    
    # Build vocabulary
    generator.build_vocabulary(smiles_list)
    
    # Prepare training data
    print("\nPreparing sequences...")
    X, y = generator.prepare_sequences(smiles_list)
    print(f"Input shape: {X.shape}")
    print(f"Output shape: {y.shape}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\nTraining samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")
    
    # Build and train model
    print("\nBuilding model...")
    generator.build_model()
    generator.model.summary()
    
    print("\nTraining model...")
    history = generator.train(X_train, y_train, epochs=30, batch_size=64)
    
    # Evaluate
    print("\nEvaluating model...")
    test_loss, test_acc = generator.model.evaluate(X_test, y_test)
    print(f"Test Loss: {test_loss:.4f}")
    print(f"Test Accuracy: {test_acc:.4f}")
    
    # Generate sample SMILES
    print("\n" + "=" * 70)
    print("GENERATING SAMPLE SMILES")
    print("=" * 70)
    
    for i in range(10):
        smiles = generator.generate_smiles(temperature=0.8)
        print(f"{i+1}. {smiles}")
    
    # Save model
    generator.save('ml_models/smiles_generator')
    print("\n✓ Model saved successfully!")
    
    return generator, history


if __name__ == '__main__':
    generator, history = main()
