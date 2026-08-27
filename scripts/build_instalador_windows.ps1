<#
Genera el paquete de la aplicación y su instalador para Windows.

Requisitos previos (una sola vez):
  1. Instalar Python 3.11 o posterior.
  2. Instalar Inno Setup: https://jrsoftware.org/isinfo.php
  3. En la raíz del proyecto: py -m venv .venv
  4. En la raíz del proyecto: .\.venv\Scripts\python.exe -m pip install -e ".[build]"

Ejecutar desde PowerShell en la raíz del proyecto:
  .\scripts\build_instalador_windows.ps1
#>

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$flet = Join-Path $projectRoot ".venv\Scripts\flet.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No se encontró el entorno virtual. Créalo con: py -m venv .venv"
}
if (-not (Test-Path -LiteralPath $flet)) {
    throw 'No se encontró Flet en el entorno virtual. Instala las dependencias con: .\.venv\Scripts\python.exe -m pip install -e ".[build]"'
}

$pyproject = Get-Content "pyproject.toml" -Raw
if ($pyproject -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
    throw "No se encontró la versión en pyproject.toml."
}
$version = $Matches[1]

$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @(
        "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
        "C:\\Program Files\\Inno Setup 6\\ISCC.exe",
        "C:\\Program Files\\Inno Setup 7\\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\\Inno Setup 6\\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\\Inno Setup 7\\ISCC.exe")
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $iscc) {
    throw "No se encontró Inno Setup (iscc.exe). Instálalo y vuelve a abrir PowerShell."
}

Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue
& $flet pack main.py --yes --name "GestorProductosElBaul" --onedir --add-data "assets;assets" --product-name "Gestor de productos · El Baúl de la Tuna" --product-version $version --file-version "$version.0" --company-name "El Baúl de la Tuna" --file-description "Gestor de productos para WooCommerce"
if ($LASTEXITCODE -ne 0) {
    throw "Flet no pudo empaquetar la aplicación."
}

& $iscc "/DMyAppVersion=$version" "installer\GestorProductosElBaul.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup no pudo crear el instalador."
}

Write-Host "Instalador creado en installer\output\Instalador-Gestor de productos - El Baúl de la Tuna-$version.exe"
