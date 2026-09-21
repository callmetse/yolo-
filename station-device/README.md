# station-device —— 高铁站房人员与环境感知装置

最新推进计划（2026-09-19）：[project.md](project.md)。其中记录多人检测调优、数据采集与统计、图表/接口交接及阶段验收；跨项目入口在 [D 盘 project.md](../project.md)。

对应文档（在 `C:\Users\jieti\outputs\researchwrite\station-energy-control\`）：

- **实施计划 V3**：`exports\高铁站房嵌入式感知装置实施计划.md` —— 定义交付范围、硬件、模块划分和数据接口
- **软件配置与学习清单**：`exports\装置软件配置与学习清单.md` —— 定义学习顺序和每步该装什么

本仓库是这台装置的**软件部分**。硬件（树莓派 5、Camera Module 3、SHT45、SCD41）到货前，先在 Windows 上用录像和模拟数据把程序跑通。

## 一、开发环境（本机已就绪）

清单第 1 节要求的四项已全部核对：

| 项目 | 版本 | 位置 |
|---|---|---|
| Python | 3.12.4 | `D:\software-code\Python\` |
| Git | 2.55.0.windows.3 | `D:\softwa-code\Git\`（提交身份：TSE） |
| VS Code | 1.133.0 | `code` 命令可用 |
| 虚拟环境 | `.venv\` | 本项目内，解释器见下 |

虚拟环境解释器绝对路径：

```text
D:\Projects\station-device\.venv\Scripts\python.exe
```

**当前已安装**（清单第 1 节指定的三个库）：

| 库 | 版本 | 用途 |
|---|---|---|
| numpy | 2.5.3 | 数值计算 |
| pandas | 3.0.6 | 表格数据处理与 CSV |
| matplotlib | 3.11.2 | 画曲线 |

**故意还没装**——按清单顺序，到第 3 节（录像与人员检测）再装：

```text
opencv-python    → 读取录像、画框、裁区域
ultralytics      → YOLO11n 人员检测（会连带安装 PyTorch，体积较大）
```

## 二、目录结构

```text
station-device\
├─ device\              程序模块（对应实施计划第 5 节的建议结构）
│   └─ config.json      设备编号、区域、采样周期、接收端地址
├─ inputs\              输入视频（test.mp4 放这里，见清单第 3 节）
├─ outputs\             输出：CSV、JSON、检测结果图、本地缓存
├─ requirements-pc.txt  电脑端依赖快照（pip freeze 产物，见清单第 7 节）
│                       既是版本记录，也是重装环境时的依赖来源
├─ 硬件到货前的清单.md   到货前可做的全部事项，按优先顺序排列
├─ README.md            本文件
└─ .venv\               虚拟环境（不提交、不复制到树莓派）
```

实施计划第 5 节规定的模块文件，等对应阶段再逐个建：

```text
device\config.json        已完成（字段骨架）
device\camera_reader.py   相机或录像输入
device\people_counter.py  检测与区域人数
device\sensor_reader.py   温湿度与 CO₂ 读取
device\recorder.py        记录、本地缓存、CSV 导出
device\uploader.py        JSON 传递、重试、补传
device\main.py            组织各模块与日志
```

**每次只加入一个新模块**，便于定位故障——这是实施计划第 2 节的要求。

## 三、常用命令

全部直接调用虚拟环境内的 python.exe，不依赖 PowerShell 激活脚本（清单第 1 节的做法）：

```bash
cd /d/Projects/station-device

# 运行脚本
./.venv/Scripts/python.exe device/main.py

# 装新依赖（例如到第 3 节时）
./.venv/Scripts/python.exe -m pip install opencv-python

# 装完后重新冻结依赖
./.venv/Scripts/python.exe -m pip freeze > requirements-pc.txt
```

从零重建环境（换电脑时用这套）：

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements-pc.txt
```

这里只用 `requirements-pc.txt` 一个文件，不另设"声明依赖"清单。它是 `pip freeze` 的完整快照，包含间接依赖，所以重建出来的环境与当前这台电脑**完全一致**——这正是清单第 7 节要的效果。

代价要知道：升级某个库之后，必须重新执行一次 `pip freeze > requirements-pc.txt`，新版本才会被记录下来。文件里的库也比你直接 `import` 的多（numpy / pandas / matplotlib 会拉进来 pillow、tzdata 等），这是正常的，不要手动删。

## 四、当前进度（2026-09-19 核查）

| 工作 | 状态与证据 |
|---|---|
| 环境与基础 CSV | 已有独立虚拟环境、依赖记录和示例 |
| 模拟温湿度/CO₂ | 本项目 `sensor_demo.py` 已有 CSV、缺失值和曲线，输出标记 simulated；真实探头未据此验收 |
| 录像检测与人数曲线 | `people_counter` 已有 step4/step5/step6 及输出；尚未集成到本仓库 |
| 多人场景精度 | 待人工标注、参数对照和独立片段验证；预览与计数配置目前不同 |
| 统一记录与汇总 | 待补来源、时间、质量、运行版本、分钟特征；现有 config 是骨架 |
| JSON/HTTP 与断网补传 | 待实现；接口地址为空，尚不能视为已具备通信能力 |
| 真实硬件与长期运行 | 待硬件接入和 2h→8h→24h 验证 |

**下一步**：按 [主计划](project.md) 的 P0/P1，在 `people_counter` 统一检测配置、建立人工对照和每次运行独立输出；随后将经验证的逻辑接入本项目，完成本地记录、分钟汇总和交接包。暂不把微调训练或进出计数设为必做前置任务。

前文环境与命令是本仓库最初的准备说明；`device/main.py` 等模块仍待创建，不代表现在可以直接启动完整装置。视频和大数据后续按 `D:\Projects\AGENTS.md` 放入 `D:\Datasets` 对应目录。

## 五、几条必须遵守的规则

来自实施计划第 6 节的数据接口约定：

- **缺失值写 `null` 并标明状态，绝不写 0。** 0 是一个合法测量值，用它表示缺失会让接收方无法区分。
- **采样时间与上传时间分开保存。** 不能只用"写入数据库的时间"代替采集时间。
- **反复上传旧读数时保留原采样时间**，让接收方自己判断是否过期。
- **模拟数据必须明确标记**（`source=simulated`），它只验证程序流程，不能当作装置测量证据。
- **`boot_id` 区分每次启动，`seq` 在该次运行内递增**，与 `device_id` 组合后可识别重传。

## 六、待与导师确认（实施计划第 11 节）

`device\config.json` 里这几项现在是占位值，确认后再填：

- `device_id`、`zone_id` —— 装置编号与安装区域
- `upload_endpoint_url` —— 接收方接口地址；若项目组已有 MQTT，改用其接口，不搭两套
- 采样与上传周期 —— 现在都暂按 5 秒

另外需要确认：人员变化口径是"当前人数趋势"还是"必须含进出次数"（这决定要不要加 ByteTrack）。
