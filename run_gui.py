#!/usr/bin/env python
"""
OpenManus GUI 啟動器
這個腳本用於啟動OpenManus的圖形用戶界面
"""

import sys
import os

try:
    from gui import main
except ImportError:
    print("錯誤：無法導入GUI模塊。請確保您在正確的目錄中運行此腳本。")
    sys.exit(1)

if __name__ == "__main__":
    print("啟動OpenManus GUI介面...")
    try:
        main()
    except Exception as e:
        print(f"運行GUI時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按Enter鍵退出...")
