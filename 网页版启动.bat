@echo off
REM 激活 conda 环境
call conda activate open_manus

REM 运行 Python 脚本
python run_web.py

REM 保持窗口打开以便查看输出
pause