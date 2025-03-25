import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, PhotoImage
import sys
from io import StringIO
import queue
import os

from app.agent.manus import Manus
from app.agent.mcp import MCPAgent
from app.logger import logger


class TextRedirector:
    """重定向標準輸出到Tkinter文本小部件"""
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass


class SplashScreen:
    """啟動畫面類"""
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # 移除標題欄

        # 獲取屏幕尺寸以居中顯示
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        width = 400
        height = 300
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # 使用框架填充
        frame = ttk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        # 添加標誌（如果存在）
        try:
            logo_path = os.path.join("assets", "logo.jpg")
            if os.path.exists(logo_path):
                logo = PhotoImage(file=logo_path)
                logo_label = ttk.Label(frame, image=logo)
                logo_label.image = logo  # 保持引用
                logo_label.pack(pady=20)
        except Exception:
            # 如果加載圖像失敗，使用文本替代
            title_label = ttk.Label(
                frame,
                text="OpenManus",
                font=("Helvetica", 24, "bold")
            )
            title_label.pack(pady=30)

        # 添加載入提示
        loading_label = ttk.Label(
            frame,
            text="啟動中，請稍候...",
            font=("Helvetica", 12)
        )
        loading_label.pack(pady=10)

        # 添加進度條
        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            length=300,
            mode="indeterminate"
        )
        self.progress.pack(pady=20, padx=30)
        self.progress.start()

        # 版權信息
        copyright_label = ttk.Label(
            frame,
            text="© 2025 OpenManus Team",
            font=("Helvetica", 8)
        )
        copyright_label.pack(side=tk.BOTTOM, pady=10)


class OpenManusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenManus AI 助手")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        self.output_queue = queue.Queue()

        # 嘗試設置圖標
        try:
            logo_path = os.path.join("assets", "logo.jpg")
            if os.path.exists(logo_path):
                self.root.iconphoto(True, PhotoImage(file=logo_path))
        except Exception:
            pass  # 如果設置圖標失敗，繼續執行

        self.setup_ui()

        # 創建定時器以檢查輸出佇列
        self.check_output_queue()

    def setup_ui(self):
        # 設置主題風格
        self.set_theme()

        # 設置框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 標題框架
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=5)

        # 標題標籤
        title_label = ttk.Label(
            title_frame,
            text="OpenManus AI 助手",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # 嘗試添加小徽標
        try:
            logo_path = os.path.join("assets", "logo.jpg")
            if os.path.exists(logo_path):
                logo = PhotoImage(file=logo_path)
                # 調整大小
                logo = logo.subsample(8, 8)  # 縮小8倍
                logo_label = ttk.Label(title_frame, image=logo)
                logo_label.image = logo  # 保持引用
                logo_label.pack(side=tk.RIGHT, padx=10)
        except Exception:
            pass  # 如果加載失敗則跳過

        # 分隔線
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)

        # 介紹標籤
        intro_label = ttk.Label(
            main_frame,
            text="請在下方輸入您的問題或指令，AI將為您提供幫助",
            font=("Helvetica", 10)
        )
        intro_label.pack(pady=5)

        # 模式選擇框架
        mode_frame = ttk.LabelFrame(main_frame, text="運行模式")
        mode_frame.pack(fill=tk.X, padx=10, pady=5)

        self.mode_var = tk.StringVar(value="standard")
        standard_radio = ttk.Radiobutton(
            mode_frame,
            text="標準模式 (基本問答)",
            variable=self.mode_var,
            value="standard"
        )
        mcp_radio = ttk.Radiobutton(
            mode_frame,
            text="MCP工具模式 (瀏覽器和工具使用)",
            variable=self.mode_var,
            value="mcp"
        )

        standard_radio.pack(side=tk.LEFT, padx=20, pady=5)
        mcp_radio.pack(side=tk.LEFT, padx=20, pady=5)

        # 輸入框架
        input_frame = ttk.LabelFrame(main_frame, text="您的問題")
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        # 輸入文本框
        self.prompt_entry = scrolledtext.ScrolledText(input_frame, height=4)
        self.prompt_entry.pack(fill=tk.X, padx=5, pady=5)

        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        # 提交按鈕
        self.submit_button = ttk.Button(
            button_frame,
            text="提交問題",
            command=self.submit_prompt
        )
        self.submit_button.pack(side=tk.LEFT, padx=10)

        # 清除按鈕
        clear_button = ttk.Button(
            button_frame,
            text="清除",
            command=self.clear_fields
        )
        clear_button.pack(side=tk.LEFT, padx=10)

        # 停止按鈕
        self.stop_button = ttk.Button(
            button_frame,
            text="停止",
            command=self.stop_processing,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.RIGHT, padx=10)

        # 輸出框架
        output_frame = ttk.LabelFrame(main_frame, text="AI 回應")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 輸出文本框
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            height=15,
            wrap=tk.WORD,
            background="#ffffff"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 狀態列
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 初始化成員變數
        self.processing_thread = None
        self.stop_event = threading.Event()

    def set_theme(self):
        """設置現代化主題"""
        style = ttk.Style()

        # 使用內置主題 (clam, alt, default, classic)
        style.theme_use('clam')

        # 自定義顏色
        bg_color = "#f5f5f5"
        accent_color = "#3a7ebf"

        # 配置元素樣式
        style.configure(
            "TFrame",
            background=bg_color
        )
        style.configure(
            "TButton",
            font=("Helvetica", 10),
            background=accent_color,
            foreground="white"
        )
        style.configure(
            "TLabel",
            font=("Helvetica", 10),
            background=bg_color
        )
        style.configure(
            "TLabelframe",
            font=("Helvetica", 10, "bold"),
            background=bg_color
        )
        style.configure(
            "TLabelframe.Label",
            font=("Helvetica", 10, "bold"),
            background=bg_color
        )

    def check_output_queue(self):
        """檢查並處理輸出佇列中的消息"""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.output_text.insert(tk.END, message)
                self.output_text.see(tk.END)
                self.output_queue.task_done()
        except queue.Empty:
            # 佇列為空時，在100毫秒後再次檢查
            self.root.after(100, self.check_output_queue)

    def submit_prompt(self):
        """提交提示並處理"""
        prompt = self.prompt_entry.get("1.0", tk.END).strip()
        if not prompt:
            self.status_var.set("錯誤: 請輸入問題")
            return

        # 禁用提交按鈕，啟用停止按鈕
        self.submit_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_var.set("處理中...")
        self.stop_event.clear()

        # 清除輸出區域
        self.output_text.delete("1.0", tk.END)

        # 重定向標準輸出
        original_stdout = sys.stdout
        sys.stdout = TextRedirector(self.output_text, self.output_queue)

        # 開始處理線程
        mode = self.mode_var.get()
        self.processing_thread = threading.Thread(
            target=self.run_agent,
            args=(prompt, mode, self.stop_event)
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def run_agent(self, prompt, mode, stop_event):
        """在單獨的線程中運行代理"""
        try:
            if mode == "standard":
                asyncio.run(self.run_standard_agent(prompt, stop_event))
            else:  # mcp mode
                asyncio.run(self.run_mcp_agent(prompt, stop_event))
        except Exception as e:
            self.output_queue.put(f"\n錯誤: {str(e)}")
        finally:
            # 恢復標準輸出
            sys.stdout = sys.__stdout__

            # 更新UI元素狀態
            self.root.after(0, self.reset_ui_state)

    async def run_standard_agent(self, prompt, stop_event):
        """運行標準代理"""
        agent = Manus()
        try:
            self.output_queue.put(f"處理您的請求: {prompt}\n\n")
            await agent.run(prompt)
            if not stop_event.is_set():
                self.output_queue.put("\n處理完成")
        except Exception as e:
            self.output_queue.put(f"\n運行過程中出現錯誤: {str(e)}")

    async def run_mcp_agent(self, prompt, stop_event):
        """運行MCP代理"""
        agent = MCPAgent()
        try:
            self.output_queue.put(f"使用MCP工具處理您的請求: {prompt}\n\n")
            await agent.initialize(connection_type="stdio")
            response = await agent.run(prompt)
            if not stop_event.is_set():
                self.output_queue.put(f"\n回應: {response}")
            await agent.cleanup()
        except Exception as e:
            self.output_queue.put(f"\n運行過程中出現錯誤: {str(e)}")

    def stop_processing(self):
        """停止處理"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_event.set()
            self.status_var.set("正在停止...")
            # 停止後的UI更新會在線程完成時自動進行

    def reset_ui_state(self):
        """重置UI狀態"""
        self.submit_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_var.set("就緒")

    def clear_fields(self):
        """清除輸入和輸出字段"""
        self.prompt_entry.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)


def main():
    # 創建根窗口
    root = tk.Tk()

    # 顯示啟動畫面
    splash = SplashScreen(tk.Toplevel(root))

    # 隱藏主窗口直到加載完成
    root.withdraw()

    # 模擬載入過程
    root.after(2000, lambda: load_main_app(root, splash))

    root.mainloop()


def load_main_app(root, splash):
    """載入主應用程序並關閉啟動畫面"""
    # 創建主應用
    app = OpenManusGUI(root)

    # 顯示主窗口
    root.deiconify()

    # 關閉啟動畫面
    splash.root.destroy()


if __name__ == "__main__":
    main()
