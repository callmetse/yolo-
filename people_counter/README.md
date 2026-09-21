# 任务 1：搭好 Python 环境，并让程序保存一份 CSV

> 2026-09-19 进度更新：本项目已经增加录像人员检测、逐帧人数 CSV 和人数曲线，下面保留的是最初的环境/CSV 教程。下一阶段请看 [人员识别、数据采集与交付推进计划](../station-device/project.md)。
>
> 当前 step4 使用 YOLO11n / 640 / conf=0.25；step5 优先使用 YOLO11s / 1280 / conf=0.40，两者尚未统一配置。下一步先建立人工对照、统一配置和可追溯输出，再决定模型微调。现有曲线不代表精度已经验收。
>
> 2026-09-21：torch 已换成 CUDA 版，推理改由本机 RTX 3050 承担（只影响速度、不影响精度结论）。改了什么、怎么验证、怎么退回 CPU 版，见 [环境变更记录.md](环境变更记录.md)。
>
> 2026-09-21：移植树莓派前要完成的第一步到第五步、以及"移植就绪"的判据，见 [树莓派移植前YOLO任务清单.md](树莓派移植前YOLO任务清单.md)。
>
> 2026-09-21：新增 [step7_prelabel.py](step7_prelabel.py)：从视频按帧号/间隔/数量抽帧，并用 YOLO 预标注导出 YOLO 格式（同名 `.txt` + `classes.txt`），供标注工具修改定稿 —— 这是任务清单阶段 2 的起手工具。它同时输出"未核对"的人数草稿和一份记录视频/权重指纹的 manifest。

这一天**不碰视频、不碰摄像头**。目标只有一个：

> 让一个 Python 程序把数据写进 CSV 文件，并且你能解释其中每一行代码的作用。

完成标志（导师验收时就看这三条）：

1. 能独立运行 `step2_write_csv.py`，看到终端每 5 秒打印一行温度；
2. 能打开 `data/temp_log.csv`，看懂每一列；
3. 能自己改一个参数（比如把记录时间从 30 秒改成 60 秒）并说清为什么结果变了。

---

## 0. 你电脑上的现状（已实测）

| 项目 | 实际情况 |
|---|---|
| Python | 3.12.4，安装在 `D:\software-code\Python\` |
| VS Code | 1.133.0，`code` 命令可用 |
| 项目位置 | `D:\Projects\people_counter\`（在 D 盘，遵循 `D:\Projects\README.md` 的存放规范） |
| 虚拟环境 | 已经建好：`.venv\`（已装 matplotlib 3.9.2。迁到 D 盘后重建过一次） |

**有一个坑要先知道**：你的电脑里不止一个 Python。`where python` 的输出是

```text
D:\software-code\Python\python.exe                              ← 当前生效的是这个（3.12.4）
C:\Users\jieti\AppData\Local\Microsoft\WindowsApps\python.exe   ← 微软商店的占位程序
D:\software-code\ANACOMDA\python.exe                            ← 另一个 Python
```

三个都在 PATH 里，谁排前面谁生效。这就是为什么**必须用虚拟环境**：虚拟环境不会改变系统的 Python，只在项目里指定"用这一个"，脚本运行时不会再出现"我装的库明明装了却提示找不到"这类问题。

> **关于盘符**：这个项目原来建在 C 盘，现在已经迁到 `D:\Projects\people_counter\`。C 盘只剩不到一半空间，而后面要处理的录像和数据集都是 GB 级文件，所以代码项目统一放 D 盘。
>
> 有一点必须注意：**虚拟环境没有跟着复制过来，而是在 D 盘重新建了一次。** `.venv` 内部记录的是绝对路径，复制到别的目录一定用不了——这也是"虚拟环境不能复制"这条规矩的原因。

---

## 1. 先搞清三个概念（各一句话）

- **Python 解释器**：真正执行 `.py` 文件的程序。你的电脑里可以有好几个版本。
- **虚拟环境（venv）**：项目专用的一个文件夹（这里是 `.venv\`），里面装的是"这个项目要用的库"。项目之间互不干扰，删掉 `.venv\` 也不会影响系统 Python。
- **第三个库 vs 标准库**：`csv`、`datetime`、`math`、`random` 是 Python 自带的**标准库**，直接 `import` 就能用；`matplotlib`（画图）是**第三方库**，必须先用 `pip` 安装。

**记住一条**：虚拟环境不能从 Windows 直接复制到树莓派。到货后要在树莓派上用同样的命令重新建一次。

---

## 2. 建立虚拟环境（已帮你建好，但请自己验证一遍）

下面是**从零开始**的完整命令。以后在树莓派上、或者换电脑时，就是照这个来：

```bash
# ① 进入项目目录
cd /d/Projects/people_counter

# ② 建立虚拟环境，-m venv 是标准写法；生成的 .venv 就是虚拟环境文件夹
python -m venv .venv

# ③ 用虚拟环境里的 pip 安装依赖（注意路径是 .venv/Scripts/python.exe）
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# ④ 验证：打印出来的路径里必须包含 .venv
./.venv/Scripts/python.exe -c "import sys; print(sys.executable)"
```

第 ④ 步的期望输出：

```text
D:\Projects\people_counter\.venv\Scripts\python.exe
```

路径里出现 `.venv` 就对了。如果打印的是 `D:\software-code\Python\python.exe`，说明你用的是系统 Python，**后面装的库不会出现在项目里**。

> 为什么第 ③ 步不直接写 `pip install`？因为在 Windows 上直接敲 `pip` 有可能装到别的 Python 里去。写成 `.venv\Scripts\python.exe -m pip` 是**最不会出错**的做法：明确指定"用哪个 Python 的 pip 去装"。

---

## 3. 在 VS Code 里打开项目

```bash
code "D:/Projects/people_counter"
```

然后在 VS Code 里做两件事：

1. **选解释器**：按 `Ctrl+Shift+P` → 输入 `Python: Select Interpreter` → 选择那条带 `.venv` 的（显示为 `Python 3.12.4 ('.venv': venv)`）。
   选好后，VS Code 右下角（或状态栏）会显示 `.venv`。
2. **确认路径没选错**：新建终端（`` Ctrl+` ``），终端提示符前面应该出现 `(.venv)`。

`.vscode\settings.json` 里我已经把解释器写死到 `.venv` 了，正常打开就会自动选对。项目里还配好了三个调试配置：**按 `F5` 就能直接运行当前脚本**，不用手敲命令。

如果 `F5` 弹出"选择调试配置"，就选名字对应的那一项（`1 环境自检` / `2 写 CSV` / `3 读 CSV 并画曲线`）。

---

## 4. 依次运行三个脚本

### 第 1 个：`step1_env_check.py` —— 环境自检

```bash
./.venv/Scripts/python.exe step1_env_check.py
```

正常输出（我在你电脑上跑出来的实物）：

```text
Python 版本 : 3.12.4
解释器路径  : D:\...\people_counter\.venv\Scripts\python.exe
操作系统    : Windows 11
[OK] Python 版本满足要求
[OK]   matplotlib 已安装，版本 3.9.2
[OK]   numpy 已安装，版本 2.5.3
[OK]   正在虚拟环境中运行： D:\...\people_counter\.venv
```

**看什么**：只要"解释器路径"里有 `.venv`，后面的事都不会因为环境问题出错。

### 第 2 个：`step2_write_csv.py` —— 练习 A（今天的重点）

```bash
./.venv/Scripts/python.exe step2_write_csv.py
```

它会每 5 秒写一行，共跑 30 秒，输出长这样：

```text
第  1 行   10:45:05   24.14 ℃
第  2 行   10:45:10   24.62 ℃
...
共写入 7 行数据 → D:\...\people_counter\data\temp_log.csv
```

**看什么**：时间间隔是不是 5 秒；数字有没有在小范围波动（这是模拟的"温度"）。

跑的过程中可以按 `Ctrl+C` 试试——程序不会崩，会打印"收到 Ctrl+C，提前结束记录"，然后正常收尾。这是 `try / except / finally` 在起作用。

### 第 3 个：`step3_read_plot.py` —— 练习 B

```bash
./.venv/Scripts/python.exe step3_read_plot.py
```

输出：

```text
数据点 : 7 个（跳过 0 个坏行）
时间范围: 10:45:05 ~ 10:45:35
温度    : 平均 24.81 ℃，最低 23.97 ℃，最高 25.65 ℃
图片已保存 → D:\...\people_counter\data\temp_plot.png
```

同时会弹出曲线窗口，并生成 `data\temp_plot.png`。**这就是你今天的成果物**：一份 CSV + 一张曲线图。

> `data\temp_log.csv` 里目前是我测试时产生的 7 行样例数据。你自己重新跑一次 `step2` 会覆盖它，这是正常的（写入用 `"w"` 模式）。

---

## 5. 必须能解释的 8 个问题

跑通不算完成，**能回答这 8 个问题**才算完成。代码里对应的位置都有中文注释。

1. `with open(...) as f:` 跟直接 `f = open(...)` 有什么区别？
   → `with` 会在代码块结束时**自动关闭文件**，即使中途报错也会关。不用手写 `f.close()`。
2. 为什么打开文件要写 `newline=""`？
   → Windows 的换行是 `\r\n`、CSV 标准的换行是 `\n`。不写这个参数，每行数据之间会多出一个空行。
3. 为什么 `encoding` 要用 `utf-8-sig`？
   → Excel 双击打开 CSV 时靠开头的 BOM 判断编码，不写就会中文乱码。
4. 写入用 `"w"`、追加用 `"a"`，这次为什么用 `"w"`？
   → `"w"` 是覆盖（每次运行从头开始，数据干净）；`"a"` 是追加（保留旧数据）。做实验记录通常用 `"a"`。
5. `f.flush()` 是干什么的？
   → 把缓冲区里的数据立刻写进磁盘。平时 Python 会攒一批再写，加了 `flush` 之后程序被强制关闭也不至于丢数据。
6. 为什么用 `time.monotonic()` 而不是 `time.time()`？
   → 单调时钟只会往前走，不受系统自动校时影响；`time.time()` 可能因为校时而跳变，算出来的时间间隔会变成负数。
7. 读 CSV 时为什么必须写 `float(row["temperature_c"])`？
   → CSV 里读出来的**全是字符串**。不转换的话，`"24.14"` 没法参与加减，`max()` 也会按字符串比较（结果会错）。
8. `if __name__ == "__main__":` 是什么意思？
   → 只有这个文件被**直接运行**时才执行下面的代码；被别的文件 `import` 时不会自动跑。这样脚本既能单跑，也能被将来的主程序复用。

---

## 6. 今天的练习（改代码，不是重新抄）

做完下面 5 个改动，任务 1 才算真的过关。每改一个**先猜结果，再运行验证**。

| # | 改哪里 | 怎么改 | 你会观察到 |
|---|---|---|---|
| 1 | `step2` 的 `DURATION_S` | 30 → 60 | 行数从 7 变成 13，曲线更完整 |
| 2 | `step2` 的 `INTERVAL_S` | 5 → 1 | 采样更密，但 `elapsed_s` 列不再是整齐的 0/1/2 |
| 3 | `simulate_temperature` | `period_s` 60 → 15 | 曲线上下摆动明显变快 |
| 4 | `CSV_HEADER` + `writer.writerow` | 加一列湿度 `humidity_pct` | CSV 多一列；**注意表头和数据必须同时改**，否则列会错位 |
| 5 | `step3` 的 `SHOW_WINDOW` | `True` → `False` | 不弹窗，只生成图片（树莓派远程登录时就是这么用） |

第 2 项是个**重要发现**：`elapsed_s` 会变成 1.0、2.1、3.2 这样带小数的值。原因是每轮循环除了 `sleep`，还有打印和写文件的开销，这部分时间会累积。真实系统里这叫**采样漂移**，需要专门处理——现在只要观察到它、记住它。

**第 4 项必须真正动手做**，因为下一步（录像人数统计）的核心就是：表头和数据列一一对应。这一步练熟，后面存 `people_visible` 才不会出错。

---

## 7. 自测题（先自己答，再看答案）

1. 怎么确认当前终端里的 `python` 就是项目 `.venv` 里的那一个？
2. `data\temp_log.csv` 里 `source` 这一列为什么必须写 `simulated`？
3. 如果 CSV 某一行被人手动改坏了（比如温度写成 `abc`），`step3` 会怎样？
4. `elapsed_s` 是 30.0 表示什么？它和 `timestamp` 是什么关系？
5. 为什么温度值不能用来证明"环境信息能估计人数"？

<details>
<summary>点击看答案</summary>

1. 运行 `python -c "import sys; print(sys.executable)"`，路径里必须含 `.venv`。或者看终端提示符前是否有 `(.venv)`。
2. 因为这个数据是程序编出来的，不是真实测量。写 `simulated` 是为了让任何人（包括几个月后的你自己）一眼看出数据来源，避免把模拟数据当成实验结果去汇报。
3. 不会崩溃。`read_rows` 里的 `try/except` 会捕获错误、打印"[跳过] 第 N 行无法解析"、`bad` 计数加 1，然后 `continue` 继续读下一行。
4. `elapsed_s` 是"从程序开始记录到现在过了多少秒"；`timestamp` 是那一刻的真实绝对时间。两者一起存，才能既做相对时间分析（画曲线），又和别的设备数据对齐。
5. 因为这批温度是我用正弦函数生成的，它和画面里的人数**没有任何因果关系**。用模拟数据只能验证"程序流程走得通"，不能得到任何关于人数与环境关系的结论。
</details>

---

## 8. 排错表

| 现象 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'matplotlib'` | 用的是系统 Python，不是 `.venv` 里的 | 用 `./.venv/Scripts/python.exe xxx.py` 运行；或在 VS Code 里重选解释器 |
| 终端里敲 `python` 弹出微软应用商店 | PATH 里有微软商店的占位程序 | 别用 `python`，用 `./.venv/Scripts/python.exe`；或到"设置→应用→应用执行别名"里关掉 python |
| Excel 打开 CSV 中文乱码 | 写入时没写 `utf-8-sig` | 检查 `open(...)` 的 `encoding` 参数 |
| CSV 每行之间多一个空行 | 写入时没写 `newline=""` | 补上 `newline=""` |
| 图片里中文变成方框 `□□□` | matplotlib 没找到中文字体 | 代码里已设置 `Microsoft YaHei`；若仍不行，改成 `SimHei` |
| PowerShell 里 `Activate.ps1` 报"禁止运行脚本" | PowerShell 执行策略限制 | 不用激活脚本，直接用 `.venv\Scripts\python.exe`；或在 Git Bash 里 `source .venv/Scripts/activate` |
| 程序卡住不动 | `step2` 正常会等 5 秒才发现没输出；`step3` 弹窗后要关掉窗口才结束 | 关掉图窗，或按 `Ctrl+C` |
| 树莓派上运行图片不显示 | SSH 没有图形界面 | 设 `SHOW_WINDOW = False`，或运行前加环境变量 `MPLBACKEND=Agg` |

---

## 9. 完成标志自查清单

- [ ] `step1` 输出的解释器路径里含 `.venv`
- [ ] `step2` 能跑完，终端按 5 秒间隔打印温度
- [ ] 跑 `step2` 时按 `Ctrl+C`，程序能正常收尾而不是报一大片红字
- [ ] 能用 Excel 或记事本打开 `data\temp_log.csv`，中文表头不乱码、没有多余空行
- [ ] `step3` 能弹出曲线窗口，并生成 `data\temp_plot.png` 且中文正常
- [ ] 上面第 8 节的 8 个问题能不看注释讲出来
- [ ] 第 6 节的 5 个改动全部亲手做过，特别是第 4 项（加一列）

---

## 10. 项目文件说明

```text
people_counter/
├─ step1_env_check.py     环境自检：确认用的是哪个 Python、库装全没有
├─ step2_write_csv.py     练习 A：每 5 秒写一行"时间+模拟温度"到 CSV
├─ step3_read_plot.py     练习 B：读回 CSV，算统计量并画曲线
├─ requirements.txt       依赖清单（现在只装 matplotlib）
├─ data/                  程序产生的数据：temp_log.csv、temp_plot.png
├─ .vscode/               VS Code 配置：解释器路径 + 三个 F5 运行配置
└─ .venv/                 虚拟环境（不要提交、不要复制到树莓派）
```

**下一步（任务 2）**只需往这个项目里加一个 `step4_read_video.py`：用 OpenCV 打开一段手机拍的录像，逐帧显示。到那时要装的库是 `opencv-python`——现在先别装，等今天的 CSV 练熟了再加。
