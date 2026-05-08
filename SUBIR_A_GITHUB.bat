@echo off
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║         SUBIR A GITHUB - BiomecApp Pro                         ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si git está instalado
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Git no está instalado
    echo Descárgalo desde: https://git-scm.com/
    pause
    exit /b 1
)

REM Verificar si estamos en un repositorio git
if not exist .git (
    echo ❌ ERROR: No hay repositorio git
    echo Ejecuta primero: git init
    pause
    exit /b 1
)

echo.
echo 📝 Ingresa la descripción del cambio:
set /p mensaje="Mensaje (ej: Agregar validaciones): "

if "%mensaje%"=="" (
    set mensaje=Update
)

echo.
echo 📦 Agregando archivos...
git add .

echo ✅ Archivos agregados
echo.
echo 💾 Guardando cambios (commit)...
git commit -m "%mensaje%"

echo ✅ Cambios guardados
echo.
echo 🚀 Subiendo a GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║  ✅ ¡LISTO! Cambios subidos a GitHub                          ║
    echo ║                                                                ║
    echo ║  Railway redesplegará automáticamente                         ║
    echo ║  Revisa: https://railway.app/                                 ║
    echo ╚════════════════════════════════════════════════════════════════╝
) else (
    echo.
    echo ❌ ERROR: No se pudo subir a GitHub
    echo Verifica que:
    echo - Tengas conexión a internet
    echo - Hayas configurado git con tu usuario
    echo - El repositorio remoto esté configurado
)

pause
