# -*- coding: utf-8 -*-
"""
模拟传感器数据：每 5 秒写一条，写完读回来画图。

运行： python sensor_demo.py
产出： outputs/sensor_demo.csv  和  outputs/sensor_demo.png

数据是程序编出来的（source=simulated），不是真实测量。

字段含义（单位写在名字里）：
  seq                    第几条，从 1 开始
  sample_ts              采样时间
  temperature_c          温度，单位 ℃
  relative_humidity_pct  相对湿度，单位 %
  co2_ppm                CO2 浓度，单位 ppm
  status                 valid 正常 / missing 有读不到的值
  source                 数据来源，simulated = 程序模拟
"""

import csv
import random
import time
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt

# ============ 想改就改这两个数字 ============
INTERVAL_S = 5     # 每隔几秒记一条
COUNT = 6          # 一共记几条（6 条大约跑 30 秒）

OUT_DIR = Path("outputs")
CSV_PATH = OUT_DIR / "sensor_demo.csv"
PNG_PATH = OUT_DIR / "sensor_demo.png"
FIELDS = ["seq", "sample_ts", "temperature_c",
          "relative_humidity_pct", "co2_ppm", "status", "source"]


def make_row(seq, temp, humi, co2):
    """整理成一条记录。哪个值是 None（读不到），status 就标 missing。"""
    missing = None in (temp, humi, co2)
    return {
        "seq": seq,
        "sample_ts": datetime.now().isoformat(timespec="seconds"),
        "temperature_c": temp,
        "relative_humidity_pct": humi,
        "co2_ppm": co2,
        "status": "missing" if missing else "valid",
        "source": "simulated",
    }


def write_data():
    """每 INTERVAL_S 秒写一条到 CSV。"""
    OUT_DIR.mkdir(exist_ok=True)
    temp, humi, co2 = 26.0, 55.0, 800.0

    # newline="" 防止 Windows 上多出空行；utf-8-sig 让 Excel 打开不乱码
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for seq in range(1, COUNT + 1):
            # 数值小幅波动，看起来像真实变化
            temp += random.uniform(-0.3, 0.3)
            humi += random.uniform(-1.0, 1.0)
            co2 += random.uniform(-20, 20)

            # 第 3 条故意让 CO2 读不到，模拟传感器没返回数据
            co2_now = None if seq == 3 else round(co2, 1)
            row = make_row(seq, round(temp, 2), round(humi, 1), co2_now)
            writer.writerow(row)
            f.flush()   # 立刻落盘，中途关掉也不丢已写的数据

            print(f"第 {seq} 条  {row['sample_ts'][11:]}  "
                  f"温度 {row['temperature_c']}  湿度 {row['relative_humidity_pct']}  "
                  f"CO2 {row['co2_ppm']}  {row['status']}")

            if seq < COUNT:
                time.sleep(INTERVAL_S)

    print(f"\n写入完成 → {CSV_PATH.resolve()}")


def read_and_plot():
    """读回 CSV，画图。"""
    def num(v):
        """空字符串 → None（缺失），否则转成数字。"""
        return None if v == "" else float(v)

    with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    seqs = [int(r["seq"]) for r in rows]
    temps = [num(r["temperature_c"]) for r in rows]
    humis = [num(r["relative_humidity_pct"]) for r in rows]
    co2s = [num(r["co2_ppm"]) for r in rows]

    # 检查缺失值有没有被写成 0
    missing = [r["seq"] for r in rows if r["status"] == "missing"]
    print(f"共 {len(rows)} 条记录，其中 {len(missing)} 条有缺失（seq = {missing}）")
    for r in rows:
        if r["status"] == "missing":
            print(f"  seq {r['seq']}: CO2 = {r['co2_ppm']!r}  ← 空值，不是 0")

    # 上下两张图：上面温湿度，下面 CO2
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    ax1.plot(seqs, temps, marker="o", label="温度 ℃")
    ax1.plot(seqs, humis, marker="s", label="湿度 %")
    ax1.set_ylabel("温度 / 湿度")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2.plot(seqs, co2s, marker="^", color="tomato", label="CO2 ppm")
    ax2.set_xlabel("序号 seq")
    ax2.set_ylabel("CO2 / ppm")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.4)

    ax1.set_title("模拟环境数据（source=simulated，非真实测量）")
    fig.tight_layout()
    fig.savefig(PNG_PATH, dpi=130)
    print(f"图片已保存 → {PNG_PATH.resolve()}")


def main():
    write_data()
    read_and_plot()
    plt.show()   # 弹出窗口；关掉窗口程序才结束


if __name__ == "__main__":
    main()
