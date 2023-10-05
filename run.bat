@echo off
chcp 65001

set config=.\settings.toml

set host=0.0.0.0
set port=22334

set BLREC_DEFAULT_LOG_DIR=.\log
set BLREC_DEFAULT_OUT_DIR=.\Videos

start cmd /K "python main.py" 

blrec -c %config% --open --host %host% --port %port% -o %BLREC_DEFAULT_OUT_DIR% --log-dir %BLREC_DEFAULT_LOG_DIR%

pause

