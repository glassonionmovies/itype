$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

Write-Host "==> Creating virtual environment" -ForegroundColor Cyan
python -m venv .venv-build-win
$Python = ".\.venv-build-win\Scripts\python.exe"

Write-Host "==> Installing dependencies" -ForegroundColor Cyan
& $Python -m pip install --quiet --upgrade pip
& $Python -m pip install --quiet -r requirements.txt
& $Python -m pip install --quiet pyinstaller pytest pillow

Write-Host "==> Running tests before packaging" -ForegroundColor Cyan
& $Python -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed; not packaging a broken build."
    exit 1
}

Write-Host "==> Generating Windows icon" -ForegroundColor Cyan
& $Python packaging\make_icon.py

Write-Host "==> Building Typing Adventure" -ForegroundColor Cyan
& ".\.venv-build-win\Scripts\pyinstaller.exe" packaging\TypingAdventure.spec --noconfirm --distpath "$Root\dist" --workpath "$Root\build"

Write-Host "==> Creating Zip archive" -ForegroundColor Cyan
if (Test-Path "$Root\dist\TypingAdventure-Windows.zip") {
    Remove-Item "$Root\dist\TypingAdventure-Windows.zip" -Force
}
Compress-Archive -Path "$Root\dist\Typing Adventure" -DestinationPath "$Root\dist\TypingAdventure-Windows.zip"

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  Zip: $Root\dist\TypingAdventure-Windows.zip"
