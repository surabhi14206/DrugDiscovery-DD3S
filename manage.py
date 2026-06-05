#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Reconstruct the dataset from parts if missing
    json_path = 'ALL_7_Gene_SMILES_isActive.json'
    if not os.path.exists(json_path):
        part1 = 'ALL_7_Gene_SMILES_isActive_part1.json'
        part2 = 'ALL_7_Gene_SMILES_isActive_part2.json'
        if os.path.exists(part1) and os.path.exists(part2):
            print("Combining dataset parts into ALL_7_Gene_SMILES_isActive.json...")
            try:
                with open(json_path, 'wb') as outfile:
                    with open(part1, 'rb') as infile1:
                        outfile.write(infile1.read())
                    with open(part2, 'rb') as infile2:
                        outfile.write(infile2.read())
                print("Reconstruction complete!")
            except Exception as e:
                print(f"Error reconstructing dataset: {e}")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
