<#
Genera el paquete de la aplicación y su instalador para Windows.

Requisitos previos (una sola vez):
  1. Instalar Python 3.11 o posterior.
  2. Instalar Inno Setup: https://jrsoftware.org/isinfo.php
  3. En la raíz del proyecto: py -m pip install -e .

Ejecutar desde PowerShell en la raíz del proyecto:
  .\scripts\build_instalador_windows.ps1
#>

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pyproject = Get-Content "pyproject.toml" -Raw
if ($pyproject -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
    throw "No se encontró la versión en pyproject.toml."
}
$version = $Matches[1]

if (-not (Get-Command iscc.exe -ErrorAction SilentlyContinue)) {
    throw "No se encontró Inno Setup (iscc.exe). Instálalo y vuelve a abrir PowerShell."
}

Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue
py -m flet pack main.py --name "GestorProductosElBaul" --onedir --add-data "assets;assets" --product-name "Gestor de productos · El Baúl de la Tuna" --product-version $version --file-version "$version.0" --company-name "El Baúl de la Tuna" --file-description "Gestor de productos para WooCommerce"

iscc.exe "/DMyAppVersion=$version" "installer\GestorProductosElBaul.iss"

Write-Host "Instalador creado en installer\output\Instalador-Gestor de productos - El Baúl de la Tuna-$version.exe"
