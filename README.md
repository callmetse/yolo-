# 高铁站房人员感知装置 · 视觉识别与数据采集

用 YOLO 从录像或相机画面统计「区域内可见人数」，并与温湿度、CO₂ 等环境量一起，构成部署在高铁站房的嵌入式感知装置。本仓库是这套装置的**视觉识别与数据采集**部分：代码、评测计划、数据字典与交接设计。

> 本仓库只放**文档与代码**，不含录像、模型权重和逐帧数据 —— 原因见下文「数据与隐私」。

## 现在到哪一步了

| 环节 | 状态 | 依据 |
|---|---|---|
| 电脑端环境（Python 3.12 + 虚拟环境 + 依赖冻结，推理已启用 GPU） | 已完成 | `people_counter/requirements.txt`、`people_counter/环境变更记录.md`、`station-device/requirements-pc.txt` |
| CSV 读写练习（模拟温度，含坏行处理） | 已完成 | `step2_write_csv.py`、`step3_read_plot.py` |
| 录像人员检测（YOLO11n，imgsz 640，conf 0.25） | 已完成 | `step4_yolo11n_person.py` |
| 逐帧人数写 CSV（YOLO11s，imgsz 1280，conf 0.40） | 已完成 | `step5_count_csv.py` |
| 人数曲线与高峰区间 | 已完成 | `step6_person_curve.py` |
| 模拟环境量（温湿度 + CO₂，含缺失值） | 已完成 | `station-device/sensor_demo.py` |
| 统一检测入口、每次运行独立目录与 manifest | 未开始 | 计划 P0 |
| 人工计数对照（100–200 帧）与参数对照表 A–F | 未开始 | 计划 P1 |
| 分钟汇总、数据字典、交接包 | 未开始 | 计划 P2–P3 |
| HTTP 上传与断网补传、树莓派部署 | 未开始 | 计划 P4，待硬件到货 |

**结论的边界**：现有曲线来自公开渠道的测试录像（不是装置实拍机位），而且预览脚本与计数脚本用的还不是同一套参数。因此**这些曲线只说明程序链路已跑通，不代表精度已通过验收**。下一步是固定机位、抽帧人工计数、统一配置，再谈精度。

## 目录结构

```text
.
├─ project.md                跨项目入口：当前主计划与执行顺序
├─ people_counter/           视觉验证区：YOLO 人数统计的脚本与教程
│   ├─ README.md             从零开始的环境与 CSV 教程（含 8 个必答问题）
│   ├─ 环境变更记录.md        开发机环境改动的留痕：GPU 版 torch 安装、验证数据、回退方法
│   ├─ 树莓派移植前YOLO任务清单.md  移植前的全部任务、验收判据与时间预算
│   ├─ step1_env_check.py    环境自检
│   ├─ step2_write_csv.py    每 5 秒写一行模拟温度到 CSV
│   ├─ step3_read_plot.py    读回 CSV、算统计量、画曲线
│   ├─ step4_yolo11n_person.py  录像画框（只保留 person）
│   ├─ step5_count_csv.py    逐帧人数写 CSV
│   ├─ step6_person_curve.py 人数曲线 + 高峰区间
│   └─ step7_prelabel.py     抽帧 + YOLO 预标注（导出标注工具可直接修改的草稿）
└─ station-device/           装置集成主仓库：字段、口径、接口与阶段计划
    ├─ project.md            人员识别、数据采集与交付推进计划（主文档）
    ├─ docs/技术选型与文献清单.md  检测/跟踪/占用估计/边缘部署的选型依据与文献
    ├─ 硬件到货前的清单.md     硬件未到时可做的全部事项
    ├─ sensor_demo.py        模拟温湿度与 CO₂ 的 CSV + 曲线示例
    └─ device/config.json    设备标识、采样周期、上传接口（骨架）
```

## 电脑端快速开始

```bash
cd people_counter

# 1) 建虚拟环境（只能新建，不能复制：里面记的是绝对路径）
python -m venv .venv

# 2) 装依赖（用虚拟环境自己的 pip，避免装到系统 Python 里）
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3) 视频 → 逐帧人数 CSV
./.venv/Scripts/python.exe step5_count_csv.py "路径/你的录像.mp4"

# 4) CSV → 人数曲线图与高峰时段
./.venv/Scripts/python.exe step6_person_curve.py
```

`station-device` 只需三个库（numpy / pandas / matplotlib），装法见该目录的 `README.md`。

## 数据与隐私

- **录像、模型权重、逐帧数据都不进本仓库。** 权重约 5–19 MB 且可按需重新下载；录像涉及场地与人员画面，按计划约定**不随仓库或交接包传播**。
- **模拟数据必须标 `source=simulated`**，它只验证程序流程，不能当装置测量证据。
- **缺失值写 `null`（CSV 用空字段）并标明状态，绝不写 0。** 0 是合法测量值，用它表示缺失会让接收方无法区分。
- **采样时间与上传时间分开保存**，反复上传旧读数时保留原采样时间。

## 接口与交付约定（摘要）

给下游的是**数据包**而不是截图：数据字典、字段单位与缺失规则、分钟聚合特征、质量报告（人工对照误差、覆盖率）、图表（PNG 展示 + SVG 排版）、可复现说明。

- 原始层不改写：去重、排时序、范围与状态校验后生成清洗层，异常跳变先标记复核，不因变化大就删除。
- 分钟特征按 `[start, end)` 窗口聚合，输出时间加权均值、最大值、P95、人·分钟、覆盖率与最长缺口；覆盖率不足的窗口标 `low_coverage`，无有效数据的窗口是 `null` 而不是 0。
- 平均人数可以是小数，**原始人数是非负整数**。

详见 [station-device/project.md](station-device/project.md) 第 4–6 节。
