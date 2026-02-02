# 内置GUI库，无需额外安装，打包兼容性最好
import tkinter as tk
from tkinter import messagebox

# 隐藏主窗口，只弹提示框
root = tk.Tk()
root.withdraw()

# 弹出提示框，可自由修改标题和文字
messagebox.showinfo(
    title="测试完成",
    message="你是傻逼吗"
)