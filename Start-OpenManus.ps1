# Starte OpenManus in dieser venv
$ErrorActionPreference = "Stop"
Set-Location "D:\Tools\InstallOpenManus\OpenManus"
.\.venv\Scripts\Activate.ps1
python .\main.py
Read-Host "
Druecke Enter zum Beenden ..."
