@echo off
chcp 65001

set config=.\settings.toml

set host=0.0.0.0
set port=22334

set BLREC_DEFAULT_LOG_DIR=.\logs
set BLREC_DEFAULT_OUT_DIR=.\Videos

mkdir %BLREC_DEFAULT_LOG_DIR%
mkdir %BLREC_DEFAULT_OUT_DIR%

start cmd /K "python main.py" 

blrec -c %config% --open --host %host% --port %port% -o %BLREC_DEFAULT_OUT_DIR% --log-dir %BLREC_DEFAULT_LOG_DIR%

pause

