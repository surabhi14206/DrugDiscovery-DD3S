"""
PyTorch-Based SMILES Generator (GPU-Accelerated)
Compatible with Python 3.14+
Uses PyTorch + RNN/LSTM for SMILES generation with automatic GPU detection
"""
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
import pickle
import os
from collections import Counter
from molecular_database_fetcher import fetch_training_data
import logging

# Import device manager for GPU/CPU handling
import sys
sys.path.insert(0, os.path.dirname(__file__))
from apps.neural_networks.device_manager import DeviceManager, get_device, to_device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmilesDataset(Dataset):
    """PyTorch Dataset for SMILES strings"""
    
    def __init__(self, smiles_list, char_to_idx, max_length=100):
        self.smiles_list = smiles_list
        self.char_to_idx = char_to_idx
        self.max_length = max_length
        
    def __len__(self):
        return len(self.smiles_list)
    
    def __getitem__(self, idx):
        smiles = self.smiles_list[idx]
        
        # Encode SMILES
        encoded = [self.char_to_idx['<START>']]
        for char in smiles:
            if char in self.char_to_idx:
                encoded.append(self.char_to_idx[char])
        encoded.append(self.char_to_idx['<END>'])
        
        # Create input/output pairs
        inputs = torch.tensor(encoded[:-1], dtype=torch.long)
        targets = torch.tensor(encoded[1:], dtype=torch.long)
        
        return inputs, targets


def collate_fn(batch):
    """Custom collate function for batching"""
    inputs, targets = zip(*batch)
    
    # Pad sequences
    inputs_padded = pad_sequence(inputs, batch_first=True, padding_value=0)
    targets_padded = pad_sequence(targets, batch_first=True, padding_value=0)
    
    return inputs_padded, targets_padded


class SmilesLSTM(nn.Module):
    """LSTM model for SMILES generation"""
    
    def __init__(self, vocab_size, embedding_dim=128, hidden_dim=256, num_layers=2, dropout=0.3):
        super(SmilesLSTM, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, vocab_size)
        
    def forward(self, x, hidden=None):
        embedded = self.embedding(x)
        lstm_out, hidden = self.lstm(embedded, hidden)
        lstm_out = self.dropout(lstm_out)
        output = self.fc(lstm_out)
        return output, hidden


class SmilesGenerator:
    """PyTorch-based SMILES generator with automatic GPU acceleration"""
    
    def __init__(self, max_length=100, embedding_dim=128, hidden_dim=256):
        self.max_length = max_length
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.model = None
        self.char_to_idx = {}
        self.idx_to_char = {}
        self.vocab_size = 0
        
        # Use DeviceManager for consistent device handling
        self.device = get_device()
        device_info = DeviceManager.get_device_info()
        
        if device_info['is_cuda']:
            logger.info(
                f"🚀 GPU Accelerated: {device_info['device_name']} "
                f"({device_info['vram_gb']} GB VRAM)"
            )
        else:
            logger.warning("⚠️ Running on CPU (slower, consider GPU setup)")
        
    def load_data_from_databases(self, count=10000, source='both'):
        """Load SMILES data from online databases"""
        logger.info(f"Fetching {count} molecules from {source}...")
        smiles_list = fetch_training_data(count=count, source=source, validate=True)
        logger.info(f"Loaded {len(smiles_list)} validated SMILES from databases")
        return smiles_list
    
    def load_data(self, json_files=None, use_databases=True, db_count=10000, db_source='chembl'):
        """Load SMILES data from JSON files and/or online databases"""
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
                        with open(json_file, 'r') as f:
                            content = f.read()
                            data = json.loads(content)
                            data = data[:50000]  # Limit for efficiency
                    else:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                    
                    # Extract SMILES
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
    
    def build_model(self):
        """Build LSTM model"""
        self.model = SmilesLSTM(
            vocab_size=self.vocab_size,
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            num_layers=2,
            dropout=0.3
        ).to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        logger.info("Model built successfully")
        logger.info(f"Total parameters: {total_params:,}")
        
        return self.model
    
    def train(self, smiles_list, epochs=50, batch_size=128, learning_rate=0.001):
        """Train the SMILES generator"""
        logger.info("Preparing training data...")
        
        # Create dataset and dataloader
        dataset = SmilesDataset(smiles_list, self.char_to_idx, self.max_length)
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
        
        logger.info(f"Training samples: {train_size}")
        logger.info(f"Validation samples: {val_size}")
        
        if self.model is None:
            self.build_model()
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3, verbose=True)
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        
        logger.info("Starting training...")
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                
                optimizer.zero_grad()
                outputs, _ = self.model(inputs)
                
                # Reshape for loss calculation
                outputs = outputs.reshape(-1, self.vocab_size)
                targets = targets.reshape(-1)
                
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation
            self.model.eval()
            val_loss = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(self.device)
                    targets = targets.to(self.device)
                    
                    outputs, _ = self.model(inputs)
                    outputs = outputs.reshape(-1, self.vocab_size)
                    targets = targets.reshape(-1)
                    
                    loss = criterion(outputs, targets)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)
            
            logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f}")
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Early stopping and checkpointing
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save(model_path='ml_models/smiles_generator_pytorch_best.pt')
            else:
                patience_counter += 1
                if patience_counter >= 5:
                    logger.info("Early stopping triggered")
                    break
        
        logger.info("Training complete!")
        return self.model
    
    def generate_smiles(self, temperature=0.8, max_length=100):
        """Generate a SMILES string"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        self.model.eval()
        
        with torch.no_grad():
            # Start with START token
            sequence = [self.char_to_idx['<START>']]
            hidden = None
            
            for _ in range(max_length):
                # Convert to tensor
                input_tensor = torch.tensor([sequence[-1]], dtype=torch.long).unsqueeze(0).to(self.device)
                
                # Predict next character
                output, hidden = self.model(input_tensor, hidden)
                predictions = output[0, -1, :].cpu().numpy()
                
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
    
    def save(self, model_path='ml_models/smiles_generator_pytorch.pt', vocab_path='ml_models/vocabulary_pytorch.pkl'):
        """Save model and vocabulary"""
        os.makedirs('ml_models', exist_ok=True)
        
        # Save model
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'embedding_dim': self.embedding_dim,
            'hidden_dim': self.hidden_dim,
            'vocab_size': self.vocab_size,
            'max_length': self.max_length
        }, model_path)
        
        # Save vocabulary
        with open(vocab_path, 'wb') as f:
            pickle.dump({
                'char_to_idx': self.char_to_idx,
                'idx_to_char': self.idx_to_char,
                'vocab_size': self.vocab_size,
                'max_length': self.max_length
            }, f)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Vocabulary saved to {vocab_path}")
    
    def load(self, model_path='ml_models/smiles_generator_pytorch.pt', vocab_path='ml_models/vocabulary_pytorch.pkl'):
        """Load model and vocabulary"""
        # Load vocabulary
        with open(vocab_path, 'rb') as f:
            vocab = pickle.load(f)
            self.char_to_idx = vocab['char_to_idx']
            self.idx_to_char = vocab['idx_to_char']
            self.vocab_size = vocab['vocab_size']
            self.max_length = vocab['max_length']
        
        # Load model
        checkpoint = torch.load(model_path, map_location=self.device)
        self.embedding_dim = checkpoint['embedding_dim']
        self.hidden_dim = checkpoint['hidden_dim']
        
        self.build_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        logger.info(f"Model loaded from {model_path}")
        logger.info(f"Vocabulary loaded from {vocab_path}")


def main():
    """Main training function"""
    logger.info("=" * 80)
    logger.info("PYTORCH-BASED SMILES GENERATOR")
    logger.info("Training with ChEMBL database (Python 3.14+ compatible)")
    logger.info("=" * 80)
    
    # Initialize generator
    generator = SmilesGenerator(max_length=100)
    
    # Load data from ChEMBL (high quality, working perfectly)
    logger.info("\nLoading data from ChEMBL database...")
    smiles_data = generator.load_data(use_databases=True, db_count=10000, db_source='chembl')
    
    # Train model
    logger.info(f"\nTraining on {len(smiles_data)} unique SMILES...")
    generator.train(smiles_data, epochs=50, batch_size=128)
    
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
    logger.info("\nModel saved to: ml_models/smiles_generator_pytorch.pt")
    logger.info("Vocabulary saved to: ml_models/vocabulary_pytorch.pkl")


if __name__ == '__main__':
    main()
