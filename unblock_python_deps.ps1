# Unblock Python Dependencies Script
# Run this script after installing packages with native extensions (like rdkit, numpy, etc.)

Write-Host "Unblocking Python dependencies in virtual environment..." -ForegroundColor Cyan

$venvPath = "$PSScriptRoot\.venv\Lib\site-packages"

if (Test-Path $venvPath) {
    $files = Get-ChildItem -Path $venvPath -Recurse -Include *.dll,*.pyd -ErrorAction SilentlyContinue
    
    $count = 0
    foreach ($file in $files) {
        Unblock-File -Path $file.FullName -ErrorAction SilentlyContinue
        $count++
    }
    
    Write-Host "Successfully unblocked $count files" -ForegroundColor Green
    Write-Host "Your Python packages should now work without Application Control errors" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "Make sure you're running this script from your project root directory" -ForegroundColor Yellow
}

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
