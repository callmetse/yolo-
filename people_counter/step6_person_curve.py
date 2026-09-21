# -*- coding: utf-8 -*-
"""
第 6 步：读 step5 的每帧人数 CSV，画出"人数随时间变化"曲线，并找出高峰时段

运行：python step6_person_curve.py
输出：data/person_curve.png（同时在屏幕上弹出窗口）

【和 step3 的关系】
骨架完全一样：读 CSV → 算统计量 → 画曲线 → 存图。
只有三处不同：
  1. 数据源换成 person_counts.csv（step5 的产出），横轴是"视频第几秒"而不是真实时间；
  2. 纵轴是人数，人数只能是整数，所以 y 轴刻度强制取整；
  3. 多了一步"找高峰"：把人数等于最大值的那些帧，归并成几段连续的时间区间。
"""

import csv
from pathlib import Path

import matplotlib

# matplotlib 默认字体里没有中文，不设置的话中文会显示成方框（□□□）——同 step3
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False   # 让坐标轴上的负号正常显示

import matplotlib.pyplot as plt        # 约定俗成的简写：plt
from matplotlib.ticker import MaxNLocator   # 用来强制 y 轴刻度取整（人数没有半个人）

CSV_PATH = Path("data") / "person_counts.csv"
PNG_PATH = Path("data") / "person_curve.png"
SHOW_WINDOW = True   # 改成 False 就只保存图片、不弹窗口（远程/无人值守时用）


def read_rows(path):
    """读取 step5 的 CSV，返回三个对齐的列表：(帧号列表, 秒列表, 人数列表) 加坏行数。

    三个列表长度永远一样：第 i 个帧号、第 i 个秒数、第 i 个人数说的是同一帧。
    某一行坏了就整行跳过并计数，不让程序崩溃 —— 习惯同 step3。
    """
    frames = []    # 帧号
    seconds = []   # 这帧在视频里的第几秒
    counts = []    # 这一帧识别出的人数
    bad = 0

    # 编码要和 step5 写入时一致：utf-8-sig
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)   # 按列名取值：row["frame_idx"]、row["video_s"]、row["person_count"]
        for line_no, row in enumerate(reader, start=2):   # 第 1 行是表头，行号从 2 数起
            try:
                # CSV 读出来全是字符串，必须自己转数字
                frame = int(row["frame_idx"])
                sec = float(row["video_s"])
                n = int(row["person_count"])
            except (ValueError, KeyError, TypeError) as e:
                bad += 1
                print(f"[跳过] 第 {line_no} 行无法解析：{e}")
                continue

            frames.append(frame)
            seconds.append(sec)
            counts.append(n)

    return frames, seconds, counts, bad


def merge_peak_ranges(indices, seconds):
    """把"人数等于最大值"的那些帧下标，归并成连续的时间区间。

    例如最大值出现在第 58,59,60,81,82 帧 → 归并成两段：58~60 帧、81~82 帧。
    做法：从头往后走，只要下一个下标恰好等于上一个 +1 就算同一段；
    断开了就收尾开新段 —— 和 step2 里数采样间隔是同一种"遍历+分组"思路。
    """
    ranges = []                 # 收集结果：每个元素是 (起始下标, 结束下标)
    start = prev = indices[0]   # 当前段的起点和上一个小标，都从第一处高峰开始
    for i in indices[1:]:       # 从第二处高峰开始往后看
        if i == prev + 1:       # 和上一处紧挨着 → 还是同一段
            prev = i
        else:                   # 断开了 → 当前段收尾，开新段
            ranges.append((start, prev))
            start = prev = i
    ranges.append((start, prev))    # 别忘了最后一段（循环里没人替它收尾）
    return ranges


def main():
    if not CSV_PATH.exists():
        print(f"找不到数据文件：{CSV_PATH.resolve()}")
        print("请先运行： python step5_count_csv.py")
        return

    frames, seconds, counts, bad = read_rows(CSV_PATH)

    if len(counts) == 0:
        print("CSV 里没有可用的数据行，请检查文件内容。")
        return

    # ---- 统计量：和 step3 同一套套路，只是对象从温度换成了人数 ----
    total = len(counts)                # 数据点个数 = 处理的帧数
    avg = sum(counts) / total          # 平均每帧人数
    n_max = max(counts)                # 最多的一帧有多少人
    n_min = min(counts)                # 最少的一帧有多少人

    print(f"数据点 : {total} 帧（跳过 {bad} 个坏行）")
    print(f"时长   : {seconds[0]:.1f} ~ {seconds[-1]:.1f} 秒")
    print(f"人数   : 平均 {avg:.2f} 人，最少 {n_min} 人，最多 {n_max} 人")

    # ---- 找高峰：所有达到最大值的帧 → 归并成时间段 ----
    peak_idx = [i for i, c in enumerate(counts) if c == n_max]   # 列表推导式：挑出所有高峰帧的下标
    ranges = merge_peak_ranges(peak_idx, seconds)
    parts = [f"{seconds[a]:.1f}~{seconds[b]:.1f} 秒（第 {frames[a]}~{frames[b]} 帧）"
             for a, b in ranges]        # 每段生成一句人话描述
    print(f"高峰   : 人数最多（{n_max} 人）出现在 {'、'.join(parts)}")

    # ---- 画图：同 step3 的画法，换数据、加一条平均线 ----
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # 240 个点很密，画圆点会糊成一片，所以只画线不画点（step3 只有 7 个点才用的 marker）
    ax.plot(seconds, counts, linestyle="-", linewidth=1.5, color="#1f6feb", label="每帧人数")

    # 平均线：axhline 是"横贯整张图的水平线"，一眼看出哪些时段高于平均
    ax.axhline(avg, linestyle="--", color="orange", label=f"平均 {avg:.2f} 人")

    # 标出第一个高峰：箭头指向它，文字里带上时间段
    first = peak_idx[0]
    ax.annotate(
        f"高峰 {n_max} 人\n({seconds[peak_idx[0]]:.1f}~{seconds[peak_idx[-1]]:.1f} 秒)",
        xy=(seconds[first], n_max),                 # 箭头指向的坐标
        xytext=(seconds[first], n_max + 0.6),       # 文字位置：比峰顶再高一点
        arrowprops={"arrowstyle": "->", "color": "gray"},
        ha="center",
    )

    ax.set_title("视频人数随时间变化（数据来源：YOLO 逐帧识别，非模拟）")
    ax.set_xlabel("视频时间 / 秒")
    ax.set_ylabel("人数 / 人")
    # 人数只能是整数，强制 y 轴刻度取整，不然会出现 4.5 这种没意义的刻度
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(bottom=0)                 # 人数最小是 0，y 轴从 0 起比较符合直觉
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    fig.tight_layout()

    fig.savefig(PNG_PATH, dpi=150)
    print(f"图片已保存 → {PNG_PATH.resolve()}")

    # 弹窗前先看有没有图形界面 —— 处理方式同 step3
    backend = matplotlib.get_backend().lower()
    if SHOW_WINDOW and backend != "agg":
        plt.show()
    else:
        plt.close(fig)
        if SHOW_WINDOW:
            print(f"当前后端是 {backend}（没有图形界面），已跳过弹窗，只保存图片。")


if __name__ == "__main__":
    main()
