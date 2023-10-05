# pause#!/bin/bash

# 配置文件
export config=./settings.toml

# 不使用代理
export no_proxy=*

# 主机和端口绑定，可以按需修改。
host=0.0.0.0
port=2233

# 设置日志目录
export BLREC_DEFAULT_LOG_DIR=./log
# mkdir -p $BLREC_DEFAULT_LOG_DIR

# 输出目录
export BLREC_DEFAULT_OUT_DIR=./Videos
# mkdir -p $BLREC_DEFAULT_OUT_DIR

nohup blrec -c $config --open --host $host --port $port -o $BLREC_DEFAULT_OUT_DIR --log-dir $BLREC_DEFAULT_LOG_DIR &
nohuo main.py > nohup.log 2>&1 & 
