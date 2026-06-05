# How to Prevent DLL/PYD Application Control Errors

## The Problem
Windows Application Control marks downloaded files (including Python packages) as potentially unsafe, blocking DLL and PYD files from loading.

## Solutions

### Option 1: Run the Unblock Script (Easiest)
After installing any new Python packages:
```powershell
.\unblock_python_deps.ps1
```

### Option 2: One-Line Command
Run this in PowerShell from your project directory:
```powershell
Get-ChildItem -Path ".venv\Lib\site-packages" -Recurse -Include *.dll,*.pyd | Unblock-File
```

### Option 3: Add to Your Workflow
Add this to your `requirements.txt` installation process:
```powershell
pip install -r requirements.txt; Get-ChildItem -Path ".venv\Lib\site-packages" -Recurse -Include *.dll,*.pyd | Unblock-File
```

### Option 4: Automate with Post-Install Script
Create a batch file `install_and_unblock.bat`:
```batch
@echo off
pip install %*
powershell -Command "Get-ChildItem -Path '.venv\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File"
echo All files unblocked!
```

Then use: `install_and_unblock.bat package-name`

## When to Run
- After `pip install` with packages that have binary extensions (rdkit, numpy, scipy, torch, etc.)
- After upgrading packages
- When you see "DLL load failed" errors
- After cloning a project with a pre-built virtual environment

## Common Packages That Need Unblocking
- rdkit
- numpy
- scipy
- pandas (with C extensions)
- torch/tensorflow
- matplotlib
- pillow
- lxml
