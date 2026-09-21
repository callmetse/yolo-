# -*- coding: utf-8 -*-
"""
第 1 步：环境自检

目的：确认三件事
  1) 你运行的是哪一个 Python（电脑里可能装了不止一个）
  2) 当前是不是在项目自己的虚拟环境 .venv 里
  3) 画图要用的第三方库装好没有

运行：python step1_env_check.py
"""

import os        # 标准库：读取环境变量、操作路径
import platform  # 标准库：读取操作系统信息
import sys       # 标准库：读取解释器（python.exe）自身的信息


def main():
    # sys.version_info 是一个"元组"，例如 (3, 12, 4)，可以和另一个元组比大小
    v = sys.version_info
    print("=" * 52)
    print("Python 版本 :", f"{v.major}.{v.minor}.{v.micro}")
    print("解释器路径  :", sys.executable)  # 关键：跟 .venv 里的路径一致才算选对
    print("操作系统    :", platform.system(), platform.release())
    print("=" * 52)

    # 条件判断：版本低于 3.9 时给出警告（后面用到的写法要求 3.9 以上）
    if v < (3, 9):
        print("[警告] Python 版本过低，请升级到 3.9 以上再继续")
    else:
        print("[OK] Python 版本满足要求")

    # 列表 + 循环：把要检查的库名放进列表，逐个检查，避免复制粘贴重复代码
    for name in ("matplotlib", "numpy"):
        try:
            # __import__ 能用字符串名字导入模块，等价于 import matplotlib
            module = __import__(name)
            version = getattr(module, "__version__", "未知版本")
            print(f"[OK]   {name} 已安装，版本 {version}")
        except ImportError:
            # 只有导入失败时才走到这里
            print(f"[缺少] {name} 未安装，请运行： python -m pip install {name}")

    # 判断是否在虚拟环境里，最可靠的方法是比较这两个属性：
    #   sys.base_prefix = 安装 Python 的原始目录
    #   sys.prefix      = 当前实际生效的目录
    # 两者不相等，说明当前解释器来自虚拟环境。
    if sys.prefix != sys.base_prefix:
        print("[OK]   正在虚拟环境中运行：", sys.prefix)
    else:
        print("[提示] 当前不在虚拟环境中（用的是系统 Python）。")
        print("       请按 README 第 2 步建立 .venv，或确认 VS Code 右下角选的是 .venv")

    print("\n自检结束：上面全是 [OK]，就可以进入第 2 步（写 CSV）。")


# 这行的意思是：本文件被"直接运行"时才执行 main()；
# 被别的文件 import 时不会自动执行。这是 Python 里最常见的写法之一。
if __name__ == "__main__":
    main()
