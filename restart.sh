#!/bin/bash

PORT=5172  # 你要释放的端口号

# 查找占用端口的进程ID（PID）
PID=$(lsof -t -i :$PORT)

# 检查是否找到进程
if [ -n "$PID" ]; then
    echo "发现进程 $PID 占用端口 $PORT，正在终止..."
    kill -9 $PID
    echo "端口 $PORT 已释放"
else
    echo "端口 $PORT 没有被占用"
fi
python app.py