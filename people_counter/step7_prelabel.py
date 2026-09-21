# -*- coding: utf-8 -*-
r"""
第 7 步：预标注（给人工标注做"草稿"）——从视频里抽出选定的帧，
        先用 YOLO 框一遍，导出成 YOLO 格式，供标注工具里修改定稿。

运行示例（都用 .venv 里的 python 跑）：
  # 从视频里均匀抽 30 帧
  ./.venv/Scripts/python.exe step7_prelabel.py --video data/test2.mp4 --count 30

  # 指定确切帧号（帧号从 1 开始，和 step5 的 CSV 一致）
  ./.venv/Scripts/python.exe step7_prelabel.py --video data/test2.mp4 --frames 60,150,300

  # 每 50 帧抽一帧，换模型和阈值
  ./.venv/Scripts/python.exe step7_prelabel.py --video data/test2.mp4 --every 50 \
      --model D:/Datasets/models/yolo11n.pt --conf 0.25

  # 图片已经抽好了（只有图，没有标签），只补标注
  ./.venv/Scripts/python.exe step7_prelabel.py --frames-dir D:/Datasets/frames/station/xxx

产出（默认写到 D:\Datasets\frames\station\<视频名>\）：
  frame_000060.jpg          抽出来的帧（图片放数据盘，不进 Git）
  frame_000060.txt          YOLO 标签，每行 "0 cx cy w h"，坐标都是 0~1 的比例
  classes.txt               类别名单（只有一行 person）——标注工具靠它识别类别
  prelabel_manifest.json    这次预标注的来源与参数（谁生成的、什么配置、复核了没有）
  prelabel_counts_unverified.csv  每帧框数，**未经人工核对**，只能当草稿

【为什么要预标注】
阶段 2 要标 20–30 个难帧的 person 框。从空白画框很慢，先用模型框一遍、
人工只做修改，能省很多时间。

【最重要的一条】预标注是**模型猜的，不是真值**。
manifest 里每帧都有 "reviewed": false。人工在标注工具里改完后要把它改成 true
（见文末"复核后怎么标记"）。否则几个月后分不清哪些框是人标的、哪些是模型猜的，
而用它算出来的精度指标就不可信了。

【和前面脚本的关系】
抽帧用 step4/step5 同一套 OpenCV 读帧；检测用同一套 predict 调用和参数。
默认参数与 step5 一致（yolo11s / 1280 / conf 0.40）。与 step4/step5 不同的是：
模型文件不存在时**直接报错退出，不自动下载、不静默回退**——标注数据的来源必须明确。
"""

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2                  # 读视频、写图片
import torch                # 查有没有显卡
from ultralytics import YOLO  # 加载模型、跑推理

# ==========================================================
# 默认值（可以在命令行里覆盖，命令行的写法见文件开头的运行示例）
# ==========================================================
MODEL_PATH = Path("D:/Datasets/models/yolo11s.pt")  # 默认用 step5 的配置
IMGSZ = 1280          # 推理尺寸
CONF = 0.40           # 置信度门槛
IOU = 0.70            # NMS 重叠阈值（显式传，不靠库的默认值）
MAX_DET = 300         # 单帧最多保留多少个框（显式传）
CLASSES = [0]         # COCO 里 person = 0
OUT_ROOT = Path("D:/Datasets/frames/station")   # 帧与标签的根目录（D 盘规范：数据不进项目文件夹）
JPEG_QUALITY = 95     # 抽帧保存质量：标注看细节，别压太狠
LABEL_CLASS_NAME = "person"   # classes.txt 里写什么名字


def parse_args():
    """命令行参数。argparse 是标准库，比手写 sys.argv 判断更清楚也更安全。"""
    ap = argparse.ArgumentParser(
        description="抽帧 + YOLO 预标注（YOLO 格式），供标注工具修改定稿",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # ---- 输入：二选一 ----
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", type=Path, help="视频文件路径（会从里面抽帧）")
    src.add_argument("--frames-dir", type=Path, help="已有的图片目录（只补标注，不抽帧）")

    # ---- 抽哪些帧：三选一（必须显式指定，不许悄悄替用户决定）----
    pick = ap.add_mutually_exclusive_group()
    pick.add_argument("--frames", type=str, help='指定帧号，如 "60,150,300"（从 1 开始）')
    pick.add_argument("--every", type=int, help="每 N 帧抽一帧，如 50")
    pick.add_argument("--count", type=int, help="在整个视频里均匀抽 N 帧，如 30")

    # ---- 检测参数 ----
    ap.add_argument("--model", type=Path, default=MODEL_PATH, help=f"权重路径（默认 {MODEL_PATH}）")
    ap.add_argument("--imgsz", type=int, default=IMGSZ)
    ap.add_argument("--conf", type=float, default=CONF)
    ap.add_argument("--iou", type=float, default=IOU)
    ap.add_argument("--max-det", type=int, default=MAX_DET)
    ap.add_argument("--device", default=None,
                    help='计算设备："0"=第一块显卡、"cpu"=处理器；不写则自动（优先显卡）')

    # ---- 输出 ----
    ap.add_argument("--out", type=Path, default=None,
                    help=f"输出目录（默认 {OUT_ROOT}\\<视频名>）")
    ap.add_argument("--jpeg-quality", type=int, default=JPEG_QUALITY)
    ap.add_argument("--force", action="store_true",
                    help="输出目录已有内容时也继续（默认拒绝，避免覆盖以前的结果）")

    args = ap.parse_args()

    # 抽帧参数必须显式给一个（如果用户只给了图片目录，就不需要）
    if args.video and not (args.frames or args.every or args.count):
        ap.error("从视频抽帧时必须指定 --frames 或 --every 或 --count 之一。"
                 "\n例：--count 30（均匀抽 30 帧）或 --frames 60,150,300（指定帧号）")
    return args


def sha256_of(path, chunk=1 << 20):
    """算文件的 sha256。用来说明"这份结果到底是哪个文件的产物"。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def count_decodable_frames(path):
    """把视频顺序读一遍，数出真正能解码多少帧。

    为什么不用 CAP_PROP_FRAME_COUNT：它只是容器头里写的数字，实测可能和实际
    能读出的帧数不一致。要均匀抽帧就得有个可信的总数，所以必要时真读一遍。
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        sys.exit(f"OpenCV 打不开这个视频：{path}")
    n = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        n += 1
    cap.release()
    return n


def pick_frame_numbers(args, total):
    """把"抽哪些帧"这件事变成一串帧号（从 1 开始，和 step5 的 CSV 一致）。"""
    if args.frames:
        nums = []
        for s in args.frames.split(","):
            s = s.strip()
            if not s:
                continue
            try:
                nums.append(int(s))
            except ValueError:
                sys.exit(f'--frames 里有个看不懂的值："{s}"（应该写成 60,150,300 这样）')
        nums = sorted(set(nums))
        bad = [n for n in nums if n < 1 or (total and n > total)]
        if bad:
            sys.exit(f"这些帧号超出范围（视频共 {total} 帧）：{bad}")
        return nums

    if args.every:
        if args.every < 1:
            sys.exit("--every 必须 ≥ 1")
        return list(range(1, total + 1, args.every))

    if args.count:
        if args.count < 1:
            sys.exit("--count 必须 ≥ 1")
        if args.count >= total:
            return list(range(1, total + 1))
        # 均匀分布：把视频分成 count 段，取每段中间那一帧，避免全落在开头
        step = total / args.count
        return sorted({max(1, min(total, int(round(step * (i + 0.5))))) for i in range(args.count)})

    return []


def boxes_to_yolo_lines(boxes_xyxy, img_w, img_h, cls=0):
    """把像素坐标的框转成 YOLO 格式的行：class cx cy w h（全都是 0~1 的比例）。

    YOLO 用的不是左上/右下角，而是"中心点 + 宽高"，且都除以图片宽高归一化。
    这些行直接写进同名 .txt 就是 YOLO 标签，标注工具（X-AnyLabeling）能直接读。
    """
    lines = []
    for x1, y1, x2, y2 in boxes_xyxy:
        # 先裁剪到画面内，避免模型给出界外的坐标（裁完宽高可能变成 0，下面会跳过）
        x1, x2 = sorted((max(0.0, min(x1, img_w)), max(0.0, min(x2, img_w))))
        y1, y2 = sorted((max(0.0, min(y1, img_h)), max(0.0, min(y2, img_h))))
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            continue
        cx, cy = (x1 + x2) / 2 / img_w, (y1 + y2) / 2 / img_h
        lines.append(f"{cls} {cx:.6f} {cy:.6f} {w / img_w:.6f} {h / img_h:.6f}")
    return lines


def prelabel_from_video(args, out_dir, video_hash, model):
    """从视频里抽帧 + 预标注。"""
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        sys.exit(f"OpenCV 打不开这个视频：{args.video}")

    total_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    if args.count or args.every:
        # 需要可信的总帧数：先看容器头写的数字，读不出就真读一遍
        total = total_meta if total_meta > 0 else count_decodable_frames(args.video)
        if total_meta > 0:
            real = count_decodable_frames(args.video)
            if real != total_meta:
                print(f"[提示] 容器头写着 {total_meta} 帧，实际能解码 {real} 帧，按实际的算。")
                total = real
    else:
        total = total_meta or 0
        if total == 0:
            total = count_decodable_frames(args.video)

    want = set(pick_frame_numbers(args, total))
    print(f"视频      : {args.video}")
    print(f"总帧数    : {total} 帧" + (f"（约 {total / fps:.1f} 秒，{fps:.2f} FPS）" if fps else ""))
    print(f"要抽的帧  : {len(want)} 帧   帧号范围 {min(want)}~{max(want)}" if want else "要抽的帧  : 0 帧")

    # 为什么顺序读、不用 cap.set() 跳帧：实测这个项目的视频上 set() 会读失败，
    # 顺序读能读出全部帧。抽样帧不多时这点开销可以忽略。
    rows = []          # 每帧一条：帧号、秒、框数、图片名
    boxes_total = 0
    decoded = 0
    t0 = time.monotonic()
    r = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        decoded += 1
        if decoded not in want:
            continue

        h, w = frame.shape[:2]
        # 与 step4/step5 完全同一套调用；显式传 iou/max_det，不靠库的默认值
        r = model.predict(frame, classes=CLASSES, conf=args.conf, imgsz=args.imgsz,
                          iou=args.iou, max_det=args.max_det,
                          device=args.device, verbose=False)[0]

        stem = f"frame_{decoded:06d}"          # 帧号补零到 6 位，方便按名字排序
        img_path = out_dir / f"{stem}.jpg"
        cv2.imwrite(str(img_path), frame, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])

        # 模型输出的框是像素坐标 xyxy，转成 YOLO 的归一化 cxcywh
        xyxy = r.boxes.xyxy.cpu().numpy()
        lines = boxes_to_yolo_lines(xyxy, w, h)
        with open(out_dir / f"{stem}.txt", "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        video_s = decoded / fps if fps else ""
        rows.append({"frame_idx": decoded, "video_time_s": video_s,
                     "n_person": len(lines), "image": img_path.name})
        boxes_total += len(lines)
        print(f"  抽到第 {decoded:>5} 帧 → {stem}.jpg   框 {len(lines)} 个")

    elapsed = time.monotonic() - t0
    cap.release()

    if len(rows) < len(want):
        missing = sorted(want - {r_["frame_idx"] for r_ in rows})
        print(f"[提示] 有 {len(missing)} 个指定帧号在视频里不存在（视频提前结束或跳帧）：{missing[:20]}")

    return rows, boxes_total, dict(total_frames=total, decoded_frames=decoded,
                                   fps=fps, elapsed_s=round(elapsed, 1),
                                   device_seen=(str(r.boxes.xyxy.device) if r is not None else None))


def prelabel_from_dir(args, out_dir, model):
    """图片已经抽好了，只是缺标签：逐张跑检测，写同名 txt。"""
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    imgs = sorted(p for p in args.frames_dir.iterdir() if p.suffix.lower() in exts)
    if not imgs:
        sys.exit(f"{args.frames_dir} 里没找到图片（认这些后缀：{exts}）")

    print(f"图片目录  : {args.frames_dir}")
    print(f"图片数量  : {len(imgs)} 张")
    rows = []
    boxes_total = 0
    t0 = time.monotonic()
    r = None

    for i, img_path in enumerate(imgs, start=1):
        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"  [跳过] 读不出来：{img_path.name}")
            continue
        h, w = frame.shape[:2]
        r = model.predict(frame, classes=CLASSES, conf=args.conf, imgsz=args.imgsz,
                          iou=args.iou, max_det=args.max_det,
                          device=args.device, verbose=False)[0]
        lines = boxes_to_yolo_lines(r.boxes.xyxy.cpu().numpy(), w, h)

        # 图片还在原目录，不搬动；标签写到"图片名.txt"（YOLO 的约定）
        txt_path = img_path.with_suffix(".txt")
        with open(txt_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        rows.append({"frame_idx": i, "video_time_s": "", "n_person": len(lines),
                     "image": img_path.name})
        boxes_total += len(lines)
        print(f"  [{i}/{len(imgs)}] {img_path.name}   框 {len(lines)} 个")

    elapsed = time.monotonic() - t0
    return rows, boxes_total, dict(total_frames=len(imgs), decoded_frames=len(imgs),
                                   fps="", elapsed_s=round(elapsed, 1),
                                   device_seen=(str(r.boxes.xyxy.device) if r is not None else None))


def main():
    args = parse_args()

    # ---- 权重：不存在就报错，不自动下载、不静默回退（来源必须明确）----
    if not args.model.exists():
        sys.exit(f"找不到权重文件：{args.model}\n"
                 f"预标注的第一步就是明确用的是哪个模型，所以这里不自动下载。\n"
                 f"请确认路径，或用 --model 指定。")

    # ---- 输出目录 ----
    name = args.video.stem if args.video else args.frames_dir.name
    out_dir = args.out or (OUT_ROOT / name)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        sys.exit(f"输出目录已经有内容：{out_dir}\n"
                 f"为了不覆盖以前的标注，默认拒绝写入。确认要覆盖就加 --force，"
                 f"或者用 --out 换个目录。")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print(f"模型      : {args.model}")
    print(f"检测参数  : imgsz={args.imgsz}  conf={args.conf}  iou={args.iou}  max_det={args.max_det}")
    print(f"输出目录  : {out_dir}")
    print(f"计算设备  : {'自动（优先显卡）' if args.device is None else args.device}"
          + (f"   [torch 报告 CUDA 可用: {torch.cuda.is_available()}]" if args.device is None else ""))
    print("=" * 62)

    model = YOLO(str(args.model))
    model_hash = sha256_of(args.model)          # 记下权重指纹：以后能证明用的是哪份权重

    video_hash = ""
    if args.video:
        if not args.video.exists():
            sys.exit(f"找不到视频：{args.video}")
        print("正在算视频指纹（大文件会慢一点）……")
        video_hash = sha256_of(args.video)
        rows, boxes_total, stats = prelabel_from_video(args, out_dir, video_hash, model)
    else:
        rows, boxes_total, stats = prelabel_from_dir(args, out_dir, model)

    # classes.txt：标注工具靠它把 class_id 显示成名字
    (out_dir / "classes.txt").write_text(LABEL_CLASS_NAME + "\n", encoding="utf-8")

    # 未经核对的人数草稿：文件名里明确写 unverified，防止被当真值用
    csv_path = out_dir / "prelabel_counts_unverified.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["frame_idx", "video_time_s", "n_person", "image"])
        w.writeheader()
        for row in rows:
            w.writerow(row)

    # manifest：这份标注从哪来、用什么参数生成的、复核了没有
    manifest = {
        "schema_version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "purpose": "预标注（模型草稿），供人工在标注工具里修改后定稿",
        "warning": "这是模型预测，不是人工真值。未经复核的框不能用于计算精度指标。",
        "source": {
            "kind": "video_inference" if args.video else "frames_dir_inference",
            "video": str(args.video) if args.video else "",
            "video_sha256": video_hash,
            "frames_dir": str(args.frames_dir) if args.frames_dir else "",
        },
        "model": {"path": str(args.model), "sha256": model_hash,
                  "class_ids": CLASSES, "class_names": [LABEL_CLASS_NAME]},
        "params": {"imgsz": args.imgsz, "conf": args.conf, "iou": args.iou,
                   "max_det": args.max_det, "device": args.device or "auto",
                   "device_actually_used": stats.get("device_seen")},
        "frames": rows,
        "reviewed": False,
        "reviewed_by": "",
        "reviewed_at": "",
        "roi_version": "",          # ROI 和计数规则还没定（见任务清单阶段 0），先留空
        "run_stats": stats,
        "env": {"python": sys.version.split()[0], "torch": torch.__version__,
                "cuda": torch.version.cuda, "opencv": cv2.__version__},
    }
    with open(out_dir / "prelabel_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print()
    print(f"完成：抽帧 {len(rows)} 张，共 {boxes_total} 个框")
    print(f"图片与标签 → {out_dir.resolve()}")
    print(f"每帧框数草稿（未核对）→ {csv_path.name}")
    print(f"来源与参数 → prelabel_manifest.json")
    print()
    print("下一步：用标注工具打开上面这个目录，改框（漏检补上、误检删掉、框歪了调正）。")
    print("改完后把 prelabel_manifest.json 里的 reviewed 改成 true，并填 reviewed_by / reviewed_at ——")
    print("不标这一笔，以后就分不清哪些框是模型猜的、哪些是人标的。")


if __name__ == "__main__":
    main()
