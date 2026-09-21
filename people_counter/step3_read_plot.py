# -*- coding: utf-8 -*-
"""
第 3 步（练习 B）：读回 CSV，画出温度随时间变化的曲线

运行：python step3_read_plot.py
输出：data/temp_plot.png（同时在屏幕上弹出窗口）
"""

import csv
from datetime import datetime
from pathlib import Path

import matplotlib

# matplotlib 默认字体里没有中文，不设置的话中文会显示成方框（□□□）
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False   # 让坐标轴上的负号正常显示

import matplotlib.pyplot as plt   # 约定俗成的简写：plt

CSV_PATH = Path("data") / "temp_log.csv"
PNG_PATH = Path("data") / "temp_plot.png"
SHOW_WINDOW = True   # 改成 False 就只保存图片、不弹窗口（树莓派远程登录时很有用）


def read_rows(path):
    """读取 CSV，返回三个东西：(时间列表, 温度列表, 坏行数量)。

    逐行读取，某一行格式不对就跳过并计数，而不是让整个程序崩溃 ——
    这是处理真实数据时的基本习惯。
    """
    times = []    # 空列表，用来按顺序存时间
    temps = []    # 空列表，用来按顺序存温度
    bad = 0       # 坏行计数器

    # 读取时的 encoding 要和写入时保持一致
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        # DictReader 把每一行变成字典：{"timestamp": "...", "temperature_c": "..."}
        # 按列名取值，比按第几列取值更不容易出错
        reader = csv.DictReader(f)
        # enumerate(..., start=2)：同时拿到序号和内容；第 1 行是表头，所以从 2 开始数
        for line_no, row in enumerate(reader, start=2):
            try:
                # CSV 里读出来的全都是字符串，必须自己转成时间 / 数字
                t = datetime.fromisoformat(row["timestamp"])
                temp = float(row["temperature_c"])
            except (ValueError, KeyError, TypeError) as e:
                # 转换失败（空行、写坏的字符、缺列）时走到这里
                bad += 1
                print(f"[跳过] 第 {line_no} 行无法解析：{e}")
                continue     # 跳过这一行，继续下一行（不是退出循环）

            times.append(t)      # 追加到列表末尾
            temps.append(temp)

    return times, temps, bad


def main():
    # 先判断文件在不在，给出人话提示，而不是直接报错
    if not CSV_PATH.exists():
        print(f"找不到数据文件：{CSV_PATH.resolve()}")
        print("请先运行： python step2_write_csv.py")
        return

    times, temps, bad = read_rows(CSV_PATH)   # 一个函数返回多个值，用这种方式接收

    # 列表为空时不能做 max()/sum()，要先拦一下
    if len(temps) == 0:
        print("CSV 里没有可用的数据行，请检查文件内容。")
        return

    # ---- 用纯 Python 算几个统计量（顺便复习循环和内置函数）----
    count = len(temps)                 # 数据点个数
    avg = sum(temps) / count           # 平均值 = 总和 / 个数
    t_max = max(temps)                 # 最大值
    t_min = min(temps)                 # 最小值
    i_max = temps.index(t_max)         # 最大值在列表中的位置（下标）

    print(f"数据点 : {count} 个（跳过 {bad} 个坏行）")
    print(f"时间范围: {times[0]:%H:%M:%S} ~ {times[-1]:%H:%M:%S}")   # [0] 第一个，[-1] 最后一个
    print(f"温度    : 平均 {avg:.2f} ℃，最低 {t_min:.2f} ℃，最高 {t_max:.2f} ℃")

    # ---- 画图 ----
    # 创建"画布"和"坐标轴"。figsize 单位是英寸，(10, 4.5) 比较适合放在文档里
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # plot 画折线：横轴是时间，纵轴是温度
    # marker="o" 在每个数据点画个圆点，"-" 是实线
    ax.plot(times, temps, marker="o", linestyle="-", color="#1f6feb", label="模拟温度")

    # 标出最高点：ax.annotate 会在图上加一段文字和箭头
    ax.annotate(
        f"最高 {t_max:.2f} ℃",
        xy=(times[i_max], t_max),                    # 箭头指向的坐标
        xytext=(times[i_max], t_max + 0.8),          # 文字所在的位置
        arrowprops={"arrowstyle": "->", "color": "gray"},
        ha="center",
    )

    ax.set_title("模拟温度随时间变化（数据来源：程序模拟，非真实测量）")
    ax.set_xlabel("时间")
    ax.set_ylabel("温度 / ℃")
    ax.grid(True, linestyle="--", alpha=0.4)   # 网格线，alpha 是透明度
    ax.legend()                                # 显示图例（label 的内容）

    fig.autofmt_xdate()   # 横轴时间标签太长时自动倾斜，避免互相压住
    fig.tight_layout()    # 自动调整边距，防止标签被裁掉

    # 保存成图片。dpi=150 表示清晰度，数字越大越清晰、文件越大
    fig.savefig(PNG_PATH, dpi=150)
    print(f"图片已保存 → {PNG_PATH.resolve()}")

    # 有些环境没有图形界面（树莓派用 SSH 登录、服务器），弹窗会失败。
    # 所以先问一下 matplotlib 当前用的是哪种后端，再决定要不要弹窗口。
    backend = matplotlib.get_backend().lower()
    if SHOW_WINDOW and backend != "agg":
        plt.show()   # 弹出窗口；关掉窗口程序才真正结束
    else:
        plt.close(fig)   # 不弹窗时手动释放资源
        if SHOW_WINDOW:
            print(f"当前后端是 {backend}（没有图形界面），已跳过弹窗，只保存图片。")


if __name__ == "__main__":
    main()
