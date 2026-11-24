$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $exclude = @('PyQt5','PyQt6','PySide2','PySide6','torch','tensorflow','matplotlib','scipy','IPython','notebook','pytest','pyarrow','numba','llvmlite','dask','distributed','xarray','bokeh','panel','plotly','altair','sphinx','statsmodels','sklearn','skimage','nbconvert','nbformat','jupyter','botocore','boto3','intake','h5py','tables','sympy','seaborn') | ForEach-Object { '--exclude-module'; $_ }
    & .\.check-venv\Scripts\python.exe -m PyInstaller --noconfirm --onedir --name backend --distpath desktop-build --workpath desktop-build/work --paths castorice_backend --collect-data jieba @exclude desktop/backend_entry.py
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed' }
    $pythonBase = & .\.check-venv\Scripts\python.exe -c 'import sys; print(sys.base_prefix)'
    foreach ($dll in @('libssl-3-x64.dll', 'libcrypto-3-x64.dll')) {
        $source = Join-Path $pythonBase "Library\bin\$dll"
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination "desktop-build\backend\_internal\$dll" -Force }
    }
    Push-Location castorice_vue
    try { npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' } } finally { Pop-Location }
    Push-Location desktop
    try { npm.cmd run pack; if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed' } } finally { Pop-Location }
} finally { Pop-Location }
