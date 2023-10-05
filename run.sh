# pause#!/bin/bash

# 配置文件
export config=./settings.toml

# 不使用代理
export no_proxy=*

# 主机和端口绑定，可以按需修改。
host=0.0.0.0
port=2233

# 设置日志目录
export BLREC_DEFAULT_LOG_DIR=./logs
mkdir $BLREC_DEFAULT_LOG_DIR

# 输出目录
export BLREC_DEFAULT_OUT_DIR=./Videos
mkdir $BLREC_DEFAULT_OUT_DIR

nohup blrec -c $config --open --host $host --port $port -o $BLREC_DEFAULT_OUT_DIR --log-dir $BLREC_DEFAULT_LOG_DIR > blrec.log 2>&1 &
echo "blrec run success!"

nohup python main.py > auto_upload.log 2>&1 &
echo "auto_upload run success!"
