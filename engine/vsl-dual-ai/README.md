# vsl-dual-ai：双 AI 实时演奏（引擎层）

一句话：**模型不弹音符，也不按小节下命令。它们只在结构点递一个"手势"，真正的实时性由本地 4 ms 控制环和两条互相锁定的时钟保证。**

这是本仓库的引擎层，与 `projects/` 下的作品层分工不同：

| 层 | 谁在动 | 时间尺度 | 产物 |
| --- | --- | --- | --- |
| 作品层 `projects/brahms-op98` | 人下判断 + AI 做分析、写谱、渲染、同步 | 一次几十分钟到几天 | PDF / 母带 / 播放器 |
| 引擎层 `engine/vsl-dual-ai` | 两个模型各扮一个演奏者，本地控制环负责每一 tick | 4 ms 一个 tick，8 拍一个手势 | 实时 MIDI 控制流 |

两者的接缝是同一套判断：作品层里写下来的速度图、句法与力度层次，在引擎层变成乐句曲线的参数；引擎层的手势只调"往哪个方向使劲"，不重新生成音符。音色仍是 VSL（Synchron D-274 或乐队音色），所以引擎层可以直接驱动作品层用过的同一批采样库。

用户给的谱子（两条 MIDI 轨）就是全部音符来源。模型做的是演奏者的事：快一点还是慢一点、往前抢还是往后拖、这一句多大力、踏板多长、采样器色彩往哪边推——以及**听见对方之后改自己**。

---

## 1. 为什么不能"一小节一次决策"

早期版本每小节问模型一次，实测就是这样：模型往返 300–1800 ms，而一拍的预算是 714 ms（84 BPM）。等它回来，音符早该响了，于是永远降级。

所以拆成两层：

| 层 | 谁在做 | 时间尺度 | 掉了怎么办 |
| --- | --- | --- | --- |
| 结构点手势 | 模型（A / B 各一个） | 每 8 拍一次 | 220 ms 内没回来 → **丢弃**，继续按现有曲线走 |
| 演奏控制环 | 本地 Python 线程 | **4 ms 一个 tick** | 不会掉：纯本地，无网络 |

听感上的"立刻反应"来自第二层：A 慢下来 20 ms，B 在下一个 tick（≤4 ms）就把自己的速度往上补一点点。模型只负责"往哪个方向使劲"，不负责"每一拍怎么动"。

---

## 2. 两条时钟，互相锁定

每个声部有自己的拍点 `beat`、自己的速度、自己的漂移：

```
beat += dt / (spb / tempo)
tempo = 乐句曲线 × (1 + 个人偏置 + 个人抖动) × PLL 修正
```

- **个人偏置**：A −0.4 %、B +0.3 %（两个人本来就不可能一样快）
- **个人抖动**：一阶低通随机游走 ±0.45 %，时间常数 0.35 s
- **PLL 修正**：`1 + clamp(kp·e + ki·∫e, ±6 %)`，其中 `e` 是**实测**相位差（秒）

误差大时只走比例项（不会积分饱和），进入 20 ms 以内才开始积分，2 ms 以内不动（死区）。另外允许一次性把下一个音提前最多 12 ms——真人也这样，不是靠变速硬追。

`--detune 45` 会把 A 在乐曲中段硬拖 45 ms，然后测量多久重新对上。

---

## 3. 力度与踏板跟着对方走

- `Balance`：把对方最近的平均力度转成 dB 差，超过 2.5 dB 才动，自己按 0.55–1.45 倍缩放，0.15 s 平滑。
- `PedalWatch`：踏板按住时长 = 2 拍 ÷(1+2.2×音符密度) ÷(0.7+0.9×力度)，密度大手就短，句尾自己松开。
- 参数（CC）**每个声部一套**，各自发到自己的通道，没有仲裁、没有抢所有权。

12 个 CC（20–31）在 VSL D-274 面板上 MIDI Learn 到对应旋钮：reverb / dynamic / mic ×4 / width / send / smooth attack / pedal noise / key-release noise / semitone。`config.json` 的 `params` 段就是这张表，含每个参数的 `lo`/`hi`、限速 `rate_ms` 与斜坡 `ramp_ms`。

---

## 4. 读谱（stage 0）

`--read` 让每个模型先把整份谱子读一遍，写一份中文理解，落成 `readings/reading_A.pdf` 与 `reading_B.pdf`（A4，附小节表）。读到的文本再以 "YOUR OWN READING OF THIS SCORE" 的形式常驻两份 system prompt——先有演奏者自己的话说，再谈手势。

仓库里的 `readings/` 是一次真实运行的产物（两人对同一份 8 小节谱给出的不同读法），`notes/reading_digest.txt` 是喂给模型的 digest 原文。

---

## 5. 实测（本机，8 小节示例，null MIDI 输出）

| 指标 | 值 |
| --- | --- |
| tick 抖动 p99 | 2.99 – 3.47 ms |
| MIDI 事件迟到 均值 / 最大 | 0.02 – 2.05 ms / ≤ 11 ms |
| 两声部同拍起音差 p50 / max | 4.0 ms / 4.0 – 8.0 ms |
| 结构点手势 应用 / 超时丢弃 | 8 / 0 |
| `--detune 45` 重新对齐 | **492 ms**，之后残差 4.0 ms，全程只有 1 个音符超过 15 ms |

作为对照：真人室内乐同拍偏差通常 2–10 ms，被拖后重新对齐一般 0.3–1 s。这组数字落在同一个量级。

`notes/run.log` 是其中一次运行的完整统计（24.6 s、5600 ticks、32 个音符、tick p99 4.05 ms、相位差 ±2 ms）。

---

## 6. 跑起来

```bash
cd engine/vsl-dual-ai

# 0) 只看控制环（不需要 MIDI 设备、不需要 API key）
set VSL_NULL_MIDI=1
python conductor.py --bars 8 --demo --no-read
python conductor.py --bars 8 --demo --no-read --detune 45

# 1) 先读谱：每个模型写一份中文理解，落成 readings/reading_A.pdf / reading_B.pdf
python conductor.py --score examples/example_a.mid examples/example_b.mid --read --bars 0

# 2) 真模型 + 真 MIDI（loopMIDI Port 1 → VSL/DAW）
python conductor.py --score examples/example_a.mid examples/example_b.mid --bars 32 --read
```

`config.json` 里换模型：A 默认 DeepSeek（环境变量 `DEEPSEEK_API_KEY`），B 默认本地 Ollama（`http://127.0.0.1:11434/v1`，`LOCAL_API_KEY`）。两个都是 OpenAI 兼容 `/chat/completions`，超时 5 s，超了就用手势降级而不是等。仓库只存环境变量名，不含任何密钥。

依赖：Python 3（无第三方包也能跑控制环与 null MIDI）、`reportlab`（仅读谱出 PDF 时需要）、`sounddevice`（仅 `listen.py` 可选）。MIDI 输出走 `ctypes` + `winmm`，因此实机演奏限 Windows；Windows 下用 loopMIDI 建一个虚拟端口即可接 VSL。

---

## 7. 文件

| 文件 | 作用 |
| --- | --- |
| `conductor.py` | 实时引擎：两条时钟、PLL、排程、手势派发与非阻塞收取 |
| `ensemble.py` | `PLL` / `Balance` / `PedalWatch` / `Reaction` |
| `curves.py` | 乐句曲线、`blend_gesture`（把模型的手势揉进曲线） |
| `reading.py` | 读谱：digest → 模型写解读 → reportlab 出 A4 PDF（附小节表） |
| `score.py` | MIDI → 拍点序列 |
| `agents.py` | 模型客户端 + `Canned` 离线演奏者 |
| `midiwin.py` | ctypes + winmm，无第三方依赖；`VSL_NULL_MIDI=1` 时空输出 |
| `bus.py` | 声部间共享的动作数据（对方刚发出的力度/速度/相位） |
| `perf.py` | 计时与统计（tick 抖动、事件迟到、相位差） |
| `listen.py` | 可选：WASAPI 回环做"听到什么"的特征（缺 sounddevice 时跳过） |
| `config.json` | 速度/边界/增益/CC 表/模型端点 |
| `examples/example_a.mid`, `example_b.mid` | 8 小节示例谱（`make_example_midi.py` 生成） |
| `docs/design.html` | 设计稿：控制环、手势流、PLL 的可视化说明 |
| `readings/` | 一次真实读谱的产物（A/B 两份 md + PDF + 渲染页） |
| `notes/` | `page_draft.md`（设计笔记）、`reading_digest.txt`、`run.log` |
| `tools/` | 早期 VSL 面板自动化探针（截图 / 坐标点击 / 焦点探测），用于把 CC 旋钮 MIDI Learn 到固定位置 |

---

## 8. 边界（说清楚，免得误会）

- 模型**不改谱**：没有任何"生成音符"的路径，音符只来自你的 MIDI。
- 手势只在 8 拍的结构点出现，所以模型能表达的是"这一段怎么走"，不是"这一拍怎么走"。想更密就调小 `boundary_beats`，代价是更多超时丢弃。
- 220 ms 之后到的答案会被丢掉，不排队、不补发——这是刻意的，晚到的建议比没有建议更糟。
- 真实声学闭环（听自己的声音再调整）目前只有 `listen.py` 的骨架，还没接进控制环；现在"听见对方"用的是**动作数据**（对方刚发出去的力度/速度/相位），不是麦克风。
- 实测数据是 null MIDI 下测的控制精度，**不代表**接上 VSL 后听到的音乐质量；音色、踏板与麦克风摆位的听感判断仍是人做的。

---

## 9. 来源

原型于 2026-11-08 在同一个工作区（`deepseek-harness/music`）里写成，与勃拉姆斯 / 瓦格纳两个作品项目同期但不同源：那批会话记录里没有它的痕迹，是独立推进的一条线。归档 AI-conducter 时按"引擎层"定位整合进来，代码与笔记原样保留，只改了目录布局与文档路径。
