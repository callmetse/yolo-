# -*- coding: utf-8 -*-
"""
第 2 步（练习 A）：每 5 秒向 CSV 写入一行"时间 + 模拟温度"

运行：python step2_write_csv.py
输出：data/temp_log.csv

【一条必须记住的规则】
这里的数据是程序"编"出来的，所以 source 列固定写 simulated。
它只用来验证程序流程，不能当作真实的环境测量结果。
真实传感器到货后：把 source 改成 sensor，并把 simulate_temperature()
换成读取传感器的函数，其余逻辑不用动。
"""

import csv    # 标准库：读写 CSV 文件
import math   # 标准库：三角函数，用来做周期性波动
import random  # 标准库：随机数，用来加噪声
import time   # 标准库：计时、暂停
from datetime import datetime   # 标准库：取得当前日期时间
from pathlib import Path        # 标准库：跨平台的文件路径

# ==========================================================
# 可以自己改的参数（改完保存，重新运行就能看到不同结果）
# ==========================================================
INTERVAL_S = 5     # 采样间隔：每 5 秒一行
DURATION_S = 30    # 总共记录 30 秒（改大一点，曲线会更完整）
CSV_PATH = Path("data") / "temp_log.csv"   # 输出文件（相对当前项目目录）
CSV_HEADER = ["timestamp", "elapsed_s", "temperature_c", "source"]


def simulate_temperature(elapsed_s):
    """根据"已经过去多少秒"生成一个模拟温度值。

    返回值是浮点数（小数）。整个函数里没有任何真实测量，纯属模拟。
    波动由三部分叠加：基准值 + 周期波动 + 随机噪声。
    """
    base = 24.0                    # 基准温度 24℃
    period_s = 60                  # 波动周期：60 秒完成一个完整上下
    wave = 1.5 * math.sin(2 * math.pi * elapsed_s / period_s)  # ±1.5℃ 的正弦波动
    noise = random.uniform(-0.2, 0.2)                          # ±0.2℃ 随机噪声
    return round(base + wave + noise, 2)   # round(x, 2)：保留两位小数


def main():
    # 1) 确保输出目录存在。parents=True 表示父目录也一起建；
    #    exist_ok=True 表示"这个目录已经存在"不要报错。
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 2) 打开文件准备写入。
    #    with ... as f: 的意思是"这一段结束后自动关闭文件"，不用手动 f.close()。
    #    newline=""          → Windows 上必须写，否则每行之间会多出空行
    #    encoding="utf-8-sig" → 让 Excel 双击打开时中文表头不乱码
    #    "w" = 覆盖写（每次运行都从头开始）；想追加用 "a"
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)          # 用 writer 按"行"写，自动处理逗号、引号
        writer.writerow(CSV_HEADER)     # 第一行写表头

        start = time.monotonic()   # 单调时钟：只往前走，不受系统改时间影响
        rows = 0                   # 计数器：写了多少行数据

        try:
            while True:                                 # 一直循环，靠下面的 break 退出
                elapsed = time.monotonic() - start      # 已经过去的秒数
                if elapsed > DURATION_S:                # 条件成立就跳出循环
                    break

                now = datetime.now()                    # 当前时间（年月日时分秒）
                temp = simulate_temperature(elapsed)

                # 一行写入四列，顺序必须和 CSV_HEADER 一致
                # isoformat(timespec="seconds") 得到 "2026-09-18T15:04:05"
                writer.writerow([
                    now.isoformat(timespec="seconds"),
                    round(elapsed, 1),
                    temp,
                    "simulated",
                ])
                f.flush()   # 立刻写入磁盘：万一程序被强制关掉，已写的数据也不会丢

                rows += 1   # 等价于 rows = rows + 1
                # f-string：{now:%H:%M:%S} 表示按"时:分:秒"格式化时间
                # {temp:5.2f} 表示占 5 个字符宽、保留 2 位小数
                print(f"第 {rows:>2} 行   {now:%H:%M:%S}   {temp:5.2f} ℃")

                time.sleep(INTERVAL_S)   # 暂停 5 秒，再去写下一行

        except KeyboardInterrupt:
            # 你在终端按 Ctrl+C 时会跳到这里。捕获它，程序就不会打印一堆红色报错。
            print("\n收到 Ctrl+C，提前结束记录。")

        finally:
            # 不管上面是正常结束还是被 Ctrl+C 打断，finally 里的代码都会执行。
            # 这类"收尾工作"放在这里最合适。
            print(f"共写入 {rows} 行数据 → {CSV_PATH.resolve()}")

    print("\n完成。接下来运行： python step3_read_plot.py")


if __name__ == "__main__":
    main()
