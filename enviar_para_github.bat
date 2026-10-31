@echo off
title Enviar Ponto Eletronico para o GitHub
cd /d "%~dp0"
echo ==================================================
echo   ENVIANDO PONTO ELETRONICO PARA O GITHUB
echo ==================================================
echo.
echo Executando git push para main e master...
echo.
git push -u origin main
git push origin main:master
echo.
echo ==================================================
echo   CONCLUIDO! Se deu sucesso, pode fechar esta tela.
echo ==================================================
echo.
pause
