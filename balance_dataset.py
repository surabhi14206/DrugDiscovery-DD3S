"""
Balance Dataset: Extract 200 molecules per target type
Creates a balanced dataset from ALL_7_Gene_SMILES_isActive.json
"""
import json
import random
from pathlib import Path

def balance_dataset(input_file, output_file, molecules_per_target=200):
    """
    Extract equal number of molecules for each target
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
        molecules_per_target: Number of molecules to extract per target
    """
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"Total molecules loaded: {len(data)}")
    
    # Group molecules by target
    targets = {}
    for item in data:
        target = item['Target']
        if target not in targets:
            targets[target] = []
        targets[target].append(item)
    
    print("\nOriginal distribution:")
    for target, molecules in targets.items():
        print(f"  {target}: {len(molecules)} molecules")
    
    # Balance the dataset
    balanced_data = []
    
    for target, molecules in targets.items():
        # Shuffle to get random selection
        random.shuffle(molecules)
        
        # Take specified number of molecules
        selected = molecules[:molecules_per_target]
        
        # Try to balance active/inactive if possible
        active = [m for m in selected if m['isActive'] == 1]
        inactive = [m for m in selected if m['isActive'] == 0]
        
        print(f"\n{target}:")
        print(f"  Selected: {len(selected)} molecules")
        print(f"  Active: {len(active)}, Inactive: {len(inactive)}")
        
        balanced_data.extend(selected)
    
    # Shuffle the final dataset
    random.shuffle(balanced_data)
    
    # Renumber the indices
    for i, item in enumerate(balanced_data):
        item['Unnamed: 0'] = i
    
    # Save to output file
    print(f"\nSaving balanced dataset to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(balanced_data, f, indent=2)
    
    print(f"\n✓ Balanced dataset created successfully!")
    print(f"  Total molecules: {len(balanced_data)}")
    print(f"  Molecules per target: {molecules_per_target}")
    print(f"  Number of targets: {len(targets)}")
    
    return balanced_data


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    
    # Input and output files
    input_file = "ALL_7_Gene_SMILES_isActive.json"
    output_file = "Balanced_7_Gene_200_per_target.json"
    
    # Balance the dataset
    balanced_data = balance_dataset(
        input_file=input_file,
        output_file=output_file,
        molecules_per_target=200
    )
    
    # Print summary statistics
    print("\n" + "="*60)
    print("DATASET SUMMARY")
    print("="*60)
    
    targets_count = {}
    active_count = {}
    inactive_count = {}
    
    for item in balanced_data:
        target = item['Target']
        targets_count[target] = targets_count.get(target, 0) + 1
        
        if item['isActive'] == 1:
            active_count[target] = active_count.get(target, 0) + 1
        else:
            inactive_count[target] = inactive_count.get(target, 0) + 1
    
    print("\nFinal distribution:")
    for target in sorted(targets_count.keys()):
        print(f"{target:15} - Total: {targets_count[target]:3}, "
              f"Active: {active_count.get(target, 0):3}, "
              f"Inactive: {inactive_count.get(target, 0):3}")
    
    print("\n" + "="*60)
