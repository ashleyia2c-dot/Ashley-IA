@echo off
REM Setup script para el ambiente de training del wake word "Ashley".
REM Ejecutar UNA SOLA VEZ desde la carpeta wake_word_training/.
REM
REM IMPORTANTE: usa Python 3.11 o 3.12 (PyTorch + tensorflow tienen
REM compatibilidad mejor en esos). Si tu Python global es 3.13, instala
REM 3.12 paralelo (winget install Python.Python.3.12) y úsalo aquí.

echo === Ashley Wake Word Training Setup ===
echo.
echo Esto va a:
echo   1. Crear venv Python en wake_word_training/venv/
echo   2. Instalar PyTorch con CUDA (~3 GB descarga)
echo   3. Instalar deps de training (~500 MB)
echo.
echo Total: ~10-15 minutos con conexion buena.
echo.
pause

REM Crear venv si no existe
if not exist venv\Scripts\python.exe (
    echo Creando venv...
    python -m venv venv
) else (
    echo venv ya existe, reusando.
)

REM Activar
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Actualizando pip...
python -m pip install --upgrade pip

REM PyTorch con CUDA — version compatible con CUDA 12.6 (RTX 5060 Blackwell
REM funciona con builds 12.4+). Si CUDA 13.x da problemas, esto es el
REM fallback estable.
echo.
echo Instalando PyTorch con CUDA 12.6...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

REM Verificar CUDA antes de seguir
echo.
echo Verificando CUDA...
python -c "import torch; assert torch.cuda.is_available(), 'CUDA NO DISPONIBLE - revisa drivers'; print('CUDA OK -', torch.cuda.get_device_name(0))"
if errorlevel 1 (
    echo.
    echo ERROR: PyTorch no detecto la GPU. Posibles causas:
    echo   - Driver NVIDIA desactualizado (necesitas 555+)
    echo   - CUDA Toolkit no instalado
    echo   - Version PyTorch incompatible con RTX 5060 Blackwell
    echo Prueba: pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu126
    pause
    exit /b 1
)

REM Resto de deps
echo.
echo Instalando deps de training...
pip install -r requirements.txt

echo.
echo === Setup completo ===
echo Para usar el venv: venv\Scripts\activate
echo Siguiente paso: python scripts\01_generate_positive.py
pause
