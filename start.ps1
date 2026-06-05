# ============================================================================
# 🚀 PDB CLONE - STARTUP SCRIPT
# ============================================================================
# This script will help you get started with the PDB Clone project quickly
# ============================================================================

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║           🧬 PDB CLONE - Django Project Startup 🧬           ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "✅ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Please create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Check if database exists
if (Test-Path "db.sqlite3") {
    Write-Host "✅ Database found" -ForegroundColor Green
} else {
    Write-Host "⚠️  Database not found - will be created on first run" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  STARTUP OPTIONS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 🚀 Start Development Server" -ForegroundColor White
Write-Host "2. 👤 Create Superuser" -ForegroundColor White
Write-Host "3. 📊 Import JSON Data" -ForegroundColor White
Write-Host "4. 🔍 Check System" -ForegroundColor White
Write-Host "5. 📚 Open Documentation" -ForegroundColor White
Write-Host "6. 🌐 Open in Browser" -ForegroundColor White
Write-Host "7. 🛠️  Django Shell" -ForegroundColor White
Write-Host "8. 📦 Install Requirements" -ForegroundColor White
Write-Host "9. ❌ Exit" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select an option (1-9)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 Starting Development Server..." -ForegroundColor Green
        Write-Host ""
        Write-Host "Server will be available at: http://127.0.0.1:8000/" -ForegroundColor Cyan
        Write-Host "Admin panel: http://127.0.0.1:8000/admin/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
        Write-Host ""
        .\.venv\Scripts\python.exe manage.py runserver
    }
    
    "2" {
        Write-Host ""
        Write-Host "👤 Creating Superuser..." -ForegroundColor Green
        Write-Host ""
        .\.venv\Scripts\python.exe manage.py createsuperuser
        Write-Host ""
        Write-Host "✅ Superuser created! You can now login to /admin/" -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "3" {
        Write-Host ""
        Write-Host "📊 Importing JSON Data..." -ForegroundColor Green
        Write-Host ""
        if (Test-Path "ALL_7_Gene_SMILES_isActive.json") {
            .\.venv\Scripts\python.exe manage.py import_json
            Write-Host ""
            Write-Host "✅ Import complete!" -ForegroundColor Green
        } else {
            Write-Host "❌ JSON file not found!" -ForegroundColor Red
            Write-Host "   Expected: ALL_7_Gene_SMILES_isActive.json" -ForegroundColor Yellow
        }
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "4" {
        Write-Host ""
        Write-Host "🔍 Running System Check..." -ForegroundColor Green
        Write-Host ""
        .\.venv\Scripts\python.exe manage.py check
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "5" {
        Write-Host ""
        Write-Host "📚 Available Documentation:" -ForegroundColor Green
        Write-Host ""
        Write-Host "  - README.md       : Complete project documentation" -ForegroundColor Cyan
        Write-Host "  - QUICKSTART.md   : 5-minute start guide" -ForegroundColor Cyan
        Write-Host "  - APPROACH.txt    : Implementation roadmap" -ForegroundColor Cyan
        Write-Host "  - COMMANDS.md     : Command reference" -ForegroundColor Cyan
        Write-Host "  - STATUS.txt      : Project status" -ForegroundColor Cyan
        Write-Host "  - SUMMARY.md      : Setup summary" -ForegroundColor Cyan
        Write-Host ""
        $doc = Read-Host "Open which file? (README/QUICKSTART/APPROACH/COMMANDS/STATUS/SUMMARY)"
        
        switch ($doc.ToUpper()) {
            "README" { notepad README.md }
            "QUICKSTART" { notepad QUICKSTART.md }
            "APPROACH" { notepad APPROACH.txt }
            "COMMANDS" { notepad COMMANDS.md }
            "STATUS" { notepad STATUS.txt }
            "SUMMARY" { notepad SUMMARY.md }
            default { Write-Host "Invalid choice" -ForegroundColor Red }
        }
    }
    
    "6" {
        Write-Host ""
        Write-Host "🌐 Opening URLs in browser..." -ForegroundColor Green
        Write-Host ""
        Write-Host "  Home:    http://127.0.0.1:8000/" -ForegroundColor Cyan
        Write-Host "  Admin:   http://127.0.0.1:8000/admin/" -ForegroundColor Cyan
        Write-Host "  API:     http://127.0.0.1:8000/api/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "⚠️  Make sure the server is running first!" -ForegroundColor Yellow
        Write-Host ""
        Start-Process "http://127.0.0.1:8000/"
        Write-Host "✅ Browser opened" -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "7" {
        Write-Host ""
        Write-Host "🛠️  Opening Django Shell..." -ForegroundColor Green
        Write-Host ""
        Write-Host "Quick commands:" -ForegroundColor Cyan
        Write-Host "  from apps.molecules.models import Molecule" -ForegroundColor Yellow
        Write-Host "  Molecule.objects.all()" -ForegroundColor Yellow
        Write-Host "  exit()" -ForegroundColor Yellow
        Write-Host ""
        .\.venv\Scripts\python.exe manage.py shell
    }
    
    "8" {
        Write-Host ""
        Write-Host "📦 Installing Requirements..." -ForegroundColor Green
        Write-Host ""
        .\.venv\Scripts\python.exe -m pip install -r requirements.txt
        Write-Host ""
        Write-Host "✅ Installation complete!" -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "9" {
        Write-Host ""
        Write-Host "👋 Goodbye! Happy coding!" -ForegroundColor Green
        Write-Host ""
        exit 0
    }
    
    default {
        Write-Host ""
        Write-Host "❌ Invalid option! Please select 1-9" -ForegroundColor Red
        Write-Host ""
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
