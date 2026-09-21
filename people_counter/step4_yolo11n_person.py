# -*- coding: utf-8 -*-
"""
第 4 步：用 YOLO11n 在录像里找"人"，只保留 person 这一类

运行（三种方式任选）：
  python step4_yolo11n_person.py                              ← 自动找视频（见 VIDEO_DIR）
  python step4_yolo11n_person.py "D:/Datasets/raw_videos/x.mp4" ← 命令行指定视频
  python step4_yolo11n_person.py --no-show                    ← 不弹预览窗，只保存结果文件

输出：data/yolo11n_person_result.mp4（画好框的视频，用播放器打开看）

【和前三个脚本的关系】
step2/step3 练的是 CSV 读写；这一步第一次接触"视频 = 一连串图片（帧）"。
OpenCV 不用单独装：安装 ultralytics 时它会作为依赖一起装进来。

【为什么选 YOLO11n】
n = nano，是 YOLO11 系列最小的模型，权重只有约 5 MB，
CPU 也能跑到每秒几帧，适合先"跑通"；以后要更准再换 s / m / l / x。

【"只识别 person"是怎么做到的】
模型本身其实会输出 80 类东西（人、车、狗……），编号是 COCO 数据集定死的：
person = 0。把 classes=[0] 传给 predict()，ultralytics 就只把"人"的框
留下来，其它类别一律丢弃——模型没变，变的是"哪些结果被保留"。
"""

import sys                      # 标准库：读取命令行参数
import time                     # 标准库：计时，用来算 FPS
from pathlib import Path        # 标准库：跨平台的文件路径处理

import cv2                      # 第三方库（OpenCV）：读视频、写视频、弹窗显示
import torch                    # 第三方库（PyTorch）：YOLO 的底层框架，这里只用来查"有没有显卡"
from ultralytics import YOLO    # 第三方库：加载模型、跑推理都由它包办

# ==========================================================
# 可以自己改的参数（改完保存，重新运行就能看到不同结果）
# ==========================================================
MODEL_PATH = Path("D:/Datasets/models/yolo11n.pt")   # 权重放 Datasets（规范：大文件不进项目文件夹）
VIDEO_DIR = Path("D:/Datasets/raw_videos")           # 你的录像放这里，脚本自动挑第一个
TEST_VIDEO = Path("data/test_bus.mp4")               # 还没有录像时用的测试视频
OUT_PATH = Path("data/yolo11n_person_result.mp4")    # 结果视频保存到这里
CLASSES = [0]        # 只保留哪些类别：COCO 80 类里 person=0。想多认一类就加编号，如 [0, 2]（汽车）
CONF = 0.25          # 置信度门槛：模型"有多确定这是人"低于 0.25 的框直接丢掉。误框多就调大
IMGSZ = 640          # 推理时把画面缩到 640 像素再喂给模型。调小更快、调大更准
SHOW_WINDOW = True   # True = 边跑边弹窗实时预览；远程/无人值守时改 False

# 命令行里写了 --no-show 就临时关掉弹窗（不用改代码）
if "--no-show" in sys.argv:
    SHOW_WINDOW = False

# 算"自动找视频"时认哪些后缀；lower() 统一成小写再比较，避免 .MP4 匹配不上
VIDEO_EXTS = (".mp4", ".avi", ".mkv", ".mov")


def load_model():
    """加载 YOLO11n。权重文件已经下好的直接用；没下就让 ultralytics 自动下载。"""
    if MODEL_PATH.exists():
        return YOLO(str(MODEL_PATH))    # 传入权重路径，返回一个可以直接调用的模型对象
    print(f"没找到 {MODEL_PATH}，改为自动下载官方权重（约 5 MB）……")
    return YOLO("yolo11n.pt")           # ultralytics 检测到本地没有就会自己下载


def find_video():
    """按优先级找要处理的视频：命令行参数 > raw_videos 里的第一个视频 > 测试视频。"""
    # 1) sys.argv 是命令行参数列表：[脚本名, 参数1, ...]，第 1 个元素是脚本名所以取下标 1
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        return Path(sys.argv[1])
    # 2) iterdir() 列出目录内容，sorted() 保证每次挑的是同一个文件
    if VIDEO_DIR.exists():
        for f in sorted(VIDEO_DIR.iterdir()):
            if f.suffix.lower() in VIDEO_EXTS:
                return f
    # 3) 都没有就退回测试视频，保证"第一次运行一定能看到效果"
    return TEST_VIDEO


def main():
    video_path = find_video()
    if not video_path.exists():
        sys.exit(f"找不到视频。请把录像复制到 {VIDEO_DIR}\\ 再运行，或用命令行指定视频路径。")

    # 检测在哪个设备上跑：有 NVIDIA 显卡 + 装了 CUDA 版 PyTorch 就用 GPU，否则 CPU
    device = f"GPU {torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else "CPU"
    print(f"视频文件 : {video_path}")
    print(f"计算设备 : {device}")

    model = load_model()

    cap = cv2.VideoCapture(str(video_path))    # 打开视频文件，之后用 read() 一帧一帧读
    if not cap.isOpened():
        sys.exit("OpenCV 打不开这个视频：文件可能损坏，或编码格式不支持。")

    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30   # 原视频帧率；个别文件读出来是 0，按 30 兜底
    # 输出视频要跟原视频一样大：宽、高都以像素为单位
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    # VideoWriter(路径, 编码器, 帧率, 画面尺寸)：mp4v 是 MP4 通用的编码器
    writer = cv2.VideoWriter(str(OUT_PATH), cv2.VideoWriter_fourcc(*"mp4v"), fps_in, size)

    frame_idx = 0        # 已处理多少帧
    person_total = 0     # 所有帧的人数总和，最后算平均用
    t0 = time.monotonic()   # 单调时钟起点（同 step2：不受系统改时间影响）

    try:
        while True:
            ok, frame = cap.read()     # 读一帧；视频放完时 ok 变成 False
            if not ok:
                break

            # 核心一行：把这一帧交给模型。
            # classes=CLASSES → 只保留 person；conf=CONF → 丢掉低置信度框；
            # verbose=False → 关掉 ultralytics 每帧自带的打印，换成我们自己的进度输出。
            # 返回值是列表（这里只有一帧所以取 [0]）。
            result = model.predict(frame, classes=CLASSES, conf=CONF,
                                   imgsz=IMGSZ, verbose=False)[0]

            n_person = len(result.boxes)   # 过滤后剩下的框数 = 这一帧识别出的人数
            person_total += n_person
            frame_idx += 1

            annotated = result.plot()      # 把检测框和标签画到这一帧上，返回画好的图
            # 在左上角(10,30)写一行绿字(0,255,0)，字号 1、线宽 2，显示这一帧的人数
            cv2.putText(annotated, f"Persons: {n_person}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            writer.write(annotated)        # 把画好的一帧写进输出视频

            if SHOW_WINDOW:
                cv2.imshow("YOLO11n - person (q 退出)", annotated)  # 弹窗实时预览
                # waitKey(1) 等 1 毫秒按键，顺便让窗口刷新；按 q 就提前结束
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_idx % 30 == 0:        # 每 30 帧报一次进度，免得刷屏
                print(f"已处理 {frame_idx:>4} 帧   当前画面人数 {n_person}")

    except KeyboardInterrupt:
        # 按Ctrl+C 时跳到这里：正常收尾退出，不打印一堆红色报错（同 step2 的写法）
        print("\n收到 Ctrl+C，提前结束。")
    finally:
        # 收尾三件事：释放视频、关闭写入器、关掉窗口。
        # writer.release() 尤其重要：不调用它，输出文件的结尾信息没写全，播放器会打不开。
        elapsed = time.monotonic() - t0
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        if frame_idx:
            print(f"\n共处理 {frame_idx} 帧，用时 {elapsed:.1f} 秒（约 {frame_idx / elapsed:.1f} FPS）")
            print(f"平均每帧人数 {person_total / frame_idx:.1f}")
        print(f"结果视频 → {OUT_PATH.resolve()}")
        print("用播放器打开它就能看到只有'人'被框出来。")


if __name__ == "__main__":
    main()
