@echo off
setlocal

echo ============================================
echo  Painel de Alertas - instalar e compilar
echo ============================================

echo.
echo [1/4] Instalando dependencias Python (schedule, pandas, dotenv, pyodbc, pyinstaller)...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

echo.
echo [2/4] Testando o painel via Python antes de compilar...
echo   Uma janela deve abrir com os 11 alertas. Fecha a janela para continuar.
echo   Se der erro no lugar da janela, cancela com Ctrl+C e me manda o erro.
pause
py alertas_gui.py

echo.
echo   Se abriu certinho, aperte qualquer tecla para compilar.
echo   Se deu erro, feche esta janela e me manda o erro ANTES de compilar.
pause

echo.
echo [3/4] Gerando build de teste, com console, para pegar erro se der...
py -m PyInstaller --name PDA --onedir --console alertas_gui.py --noconfirm
copy /Y .env.* "dist\PDA\" >nul 2>&1

echo.
echo [4/4] Build de teste pronto em: dist\PDA\PDA.exe
echo.
echo   Testa esse exe. Se abrir e funcionar igual ao teste em Python, roda os
echo   2 comandos abaixo para gerar a versao final, sem console atras da GUI:
echo.
echo     py -m PyInstaller --name PDA --onedir --windowed alertas_gui.py --noconfirm
echo     copy /Y .env.* "dist\PDA\"
echo.
echo   A pasta dist\PDA inteira (o .exe + a pasta _internal) pode
echo   ser copiada direto para o servidor remoto. Ela nao depende de pip,
echo   alerta_core ou core instalados la - tudo ja vai embutido dentro dela.
echo   So falta colar os .env.* dentro dessa pasta, no servidor.
echo.
pause
