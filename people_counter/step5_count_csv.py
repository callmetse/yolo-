# -*- coding: utf-8 -*-
"""
第 5 步：把每一帧的人数写进 CSV —— "视频进，数字出"

运行（三种方式任选，同 step4）：
  python step5_count_csv.py                        ← 自动找视频
  python step5_count_csv.py "D:/xxx/视频.mp4"       ← 命令行指定视频
  python step5_count_csv.py --show                 ← 想边跑边看预览窗（默认不弹）

输出：data/person_counts.csv，每帧一行：帧号、这帧在视频里的第几秒、人数

【和 step4 的关系】
step4 其实已经在数每帧人数了：
    n_person = len(result.boxes)   ← 这一帧"人"框的个数 = 这一帧的人数
只是数完只累加求了平均。本步只多做一件事：把每个数连同帧号、时间写进 CSV。
画框的视频 step4 已经会了，这里不再写结果视频，跑得更快。

【为什么值得做】
数字只在屏幕上刷过只能"看"，存进 CSV 才能算：平均人数、第几秒人最多、
和温度数据按时间对齐……这正是 step2/step3 练的读写能力第一次真正上岗。
"""

import csv                       # 标准库：写 CSV（step2 用过，这次不用装任何新库）
import sys                       # 标准库：读命令行参数
import time                      # 标准库：计时
from pathlib import Path         # 标准库：文件路径处理

import cv2                       # 第三方库（OpenCV）：打开视频、逐帧读
import torch                     # 第三方库（PyTorch）：这里只用来查有没有显卡
from ultralytics import YOLO     # 第三方库：加载模型、跑推理

# ==========================================================
# 可以自己改的参数（改完保存重跑即可）
# ==========================================================
# 权重按顺序找：列表里第一个真实存在的文件就用它
# s 型号比 n 准不少（夜间视频实测置信度普遍高 0.1+），慢一倍多（4.4 vs 10.4 FPS）；
# 离线数数求准，所以 s 排第一。想快就把它俩顺序对调。
MODEL_CANDIDATES = [
    Path("D:/Datasets/models/yolo11s.pt"),    # 主力：更准（约 2 倍参数量）
    Path("D:/Datasets/models/yolo11n.pt"),    # 备用：s 不在时用 n
]
VIDEO_DIR = Path("D:/Datasets/raw_videos")      # 自动找视频时第一优先扫这里
CSV_PATH = Path("data/person_counts.csv")       # 每帧人数写到这里
CLASSES = [0]      # 只数人（COCO 80 类里 person=0），想数车就加 2：[0, 2]
CONF = 0.40        # 置信度门槛：0.25 太宽松，垃圾框多、人数虚高；0.4 干净很多（夜间视频实测）
IMGSZ = 1280       # 推理尺寸：手机竖屏 720x1280 用 640 会把远处的人压得太小；1280 明显更准
SHOW_WINDOW = False  # 默认不弹预览：数数要快，弹窗会拖慢；想看画框请用 step4
PROGRESS_EVERY = 30  # 每 30 帧在终端报一次进度

if "--show" in sys.argv:      # 命令行写了 --show 就临时打开预览（不用改代码）
    SHOW_WINDOW = True

VIDEO_EXTS = (".mp4", ".avi", ".mkv", ".mov")   # 自动找视频认哪些后缀


def load_model():
    """按候选顺序找权重；一个都没有就让 ultralytics 自动下载 yolo11n.pt。"""
    for p in MODEL_CANDIDATES:        # 依次检查候选清单
        if p.exists():                # 第一个真实存在的就用它
            print(f"使用权重 : {p}")
            return YOLO(str(p))       # 传入权重路径，返回模型对象
    print("没找到本地权重，自动下载 yolo11n.pt（约 5 MB）……")
    return YOLO("yolo11n.pt")


def find_video():
    """找要处理的视频：命令行参数 > raw_videos 第一个 > 项目 data 里的测试视频。"""
    # 1) sys.argv[1] 是命令行里第一个参数（下标 0 是脚本名自己）
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        return Path(sys.argv[1])
    # 2) 扫 raw_videos，sorted() 保证每次挑到的是同一个文件
    if VIDEO_DIR.exists():
        for f in sorted(VIDEO_DIR.iterdir()):
            if f.suffix.lower() in VIDEO_EXTS:
                return f
    # 3) 退回项目 data 里的测试视频（有你自己传的就先用你的）
    for name in ("data/test-1.mp4", "data/test_bus.mp4"):
        if Path(name).exists():
            return Path(name)
    return None          # 哪儿都找不到视频


def main():
    video_path = find_video()
    if video_path is None or not video_path.exists():
        sys.exit(f"找不到视频。把录像复制到 {VIDEO_DIR} 或在命令行指定路径。")

    device = f"GPU {torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else "CPU"
    print(f"视频文件 : {video_path}")
    print(f"计算设备 : {device}")

    model = load_model()

    cap = cv2.VideoCapture(str(video_path))    # 打开视频，之后 read() 一帧帧读
    if not cap.isOpened():
        sys.exit("OpenCV 打不开这个视频：文件可能损坏或编码不支持。")

    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30   # 原视频帧率；个别文件读出 0 就按 30 兜底
    frame_idx = 0          # 帧号，从 0 开始累加
    person_total = 0       # 人数总和，收尾算平均用
    t0 = time.monotonic()  # 单调时钟起点（同 step2/step4：不怕系统自动校时）

    try:
        # with 块包住整个循环：无论跑完还是中途 Ctrl+C，文件都会正确关闭（同 step2）
        # "w"=覆盖重写（每次运行得到干净数据）；utf-8-sig=Excel 打开中文不乱码
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            # 表头三列。以后想加列，必须表头和下面 writerow 同时改，否则错位
            writer.writerow(["frame_idx", "video_s", "person_count"])

            while True:
                ok, frame = cap.read()       # 读一帧；视频放完 ok 变 False
                if not ok:
                    break

                # 核心一行：这一帧交给模型。classes 只留人，verbose=False 关掉
                # ultralytics 每帧自带的打印——数字我们自己存 CSV，比刷屏有用
                result = model.predict(frame, classes=CLASSES, conf=CONF,
                                       imgsz=IMGSZ, verbose=False)[0]

                n_person = len(result.boxes)   # 核心：这一帧"人"框的个数 = 人数
                person_total += n_person
                frame_idx += 1
                video_s = frame_idx / fps_in   # 这帧在视频里的第几秒（帧号 ÷ 帧率）

                # 一行写三列，顺序必须和上面表头一致
                writer.writerow([frame_idx, round(video_s, 2), n_person])

                if frame_idx % PROGRESS_EVERY == 0:   # 每 30 帧报一次进度
                    f.flush()   # 落一次盘：中途被强杀，已写的行也不丢（step2 的 f.flush 教训）
                    print(f"已处理 {frame_idx:>4} 帧   当前人数 {n_person}")

                if SHOW_WINDOW:                        # 预览模式才执行（默认关）
                    annotated = result.plot()          # 把框画到这一帧上
                    cv2.putText(annotated, f"Persons: {n_person}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("step5 counting (q 退出)", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

    except KeyboardInterrupt:
        # Ctrl+C 时到这里正常收尾，不打印一片红字（同 step2/step4 的写法）
        print("\n收到 Ctrl+C，提前结束。")
    finally:
        elapsed = time.monotonic() - t0
        cap.release()                    # 释放视频
        cv2.destroyAllWindows()          # 关掉预览窗（如果有）
        if frame_idx:
            print(f"\n共 {frame_idx} 帧，用时 {elapsed:.1f} 秒（{frame_idx / elapsed:.1f} FPS）")
            print(f"平均每帧人数 {person_total / frame_idx:.1f}")
            print(f"人数明细 → {CSV_PATH.resolve()}")
        print("用 Excel 打开它，就能看到人数随时间变化的每一行。")


if __name__ == "__main__":
    main()
