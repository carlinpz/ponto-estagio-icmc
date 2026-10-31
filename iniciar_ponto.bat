@echo off
title Ponto Eletronico - Estagio
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw launcher.pyw) || (start "" pyw launcher.pyw)
