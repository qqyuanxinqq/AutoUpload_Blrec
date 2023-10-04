@echo off
chcp 65001
cd %~dp0
set PATH=.\ffmpeg\bin;.\python;%PATH%

@REM 不使用代理
set no_proxy=*

@REM 主机和端口绑定，可以按需修改。
set host=0.0.0.0
set port=2233

@REM 请自行修改 api key，不要使用默认的 api key。
set api_key=bili2233

python blrec -c settings.toml --open --host %host% --port %port% --api-key %api_key%

pause