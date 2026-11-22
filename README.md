# AI-conducter

一个 AI 指挥实验：把一部交响曲的总谱读成可核验的分析，再把分析变成一次真实渲染的演奏，最后让演奏与谱面同步。整个流程由人类下判断、AI 执行工程与写作，每一步都留下可复查的中间产物，而不是只交一份"看起来很美"的成品。

仓库分两层：**作品层**把一部交响曲读成可核验的分析，再渲染成演奏、与谱面同步；**引擎层**把同样的判断推进到实时，让两个模型在 4 ms 的控制环上真的"一起演奏"。

| 层 | 目录 | 对象 | 交付物 |
| --- | --- | --- | --- |
| 作品层 | [brahms-op98](projects/brahms-op98/README.md) | 勃拉姆斯《第四交响曲》Op.98 | 全曲分析（98 页注释总谱 + 深度报告）、第四乐章 E→终曲 VSL 渲染（5:29）、同步播放器与 4K 视频 |
| 作品层 | [wagner-meistersinger](projects/wagner-meistersinger/README.md) | 瓦格纳《纽伦堡的名歌手》前奏曲 | Schott 18469 原作 39 页总谱的锚点标注、动机旁注总谱、深度分析 |
| 引擎层 | [vsl-dual-ai](engine/vsl-dual-ai/README.md) | 双 AI 实时演奏 | 8 拍结构点手势 + 4 ms 演奏控制环、双时钟 PLL、读谱 PDF、控制精度实测 |

## 为什么做这件事

指挥不是"跟着谱子打拍子"，而是先把谱面读成一个有层次的判断：哪里是材料的来源，哪里是改写，哪些相似只是气质相似，哪些重复已经换了功能。这个仓库试图把这种判断显式化：

1. **读谱**：从数字谱与原始扫描件出发，标出曲式边界、动机变形、配器功能，并把"文件结构事实"与"解释性判断"分开写。
2. **做谱**：把分析做成可读的注释总谱与导读，而不是散落的段落。
3. **演奏**：把分析转成速度图、奏法键位、动态与声部平衡，在采样库里真实渲染，不用"合成器味道"糊过去。
4. **对位**：让音频、谱页、小节号三者对齐，做成能点的播放器，让判断可以被听见、被核对。

## 两层怎么接上

作品层里写下来的速度图、句法判断与力度层次，在引擎层变成乐句曲线的参数；引擎层的手势只决定"往哪个方向使劲"，不重新生成任何音符。两边用的是同一批 VSL 采样库，所以作品层渲染出来的声音，和引擎层实时推出去的 MIDI，指向同一个音色世界。

## 快速入口

- 想听：[`Brahms_IV_E_to_End_VSL.mp3`](projects/brahms-op98/performance/audio/Brahms_IV_E_to_End_VSL.mp3)（12.6 MB，199 小节，5 分 29 秒）
- 想看谱：[`Brahms_Op98_全曲注释总谱.pdf`](projects/brahms-op98/analysis/Brahms_Op98_全曲注释总谱.pdf)
- 想边听边看谱：[`Brahms_IV_E_分析总谱同步播放器.html`](projects/brahms-op98/synchronized/Brahms_IV_E_分析总谱同步播放器.html)（单文件离线，双击用桌面浏览器打开）
- 想读判断：[`Brahms_Op98_全曲深度分析.pdf`](projects/brahms-op98/analysis/Brahms_Op98_全曲深度分析.pdf) 或 [Markdown 版](projects/brahms-op98/analysis/Brahms_Op98_全曲深度分析.md)
- 瓦格纳：[`Wagner_名歌手前奏曲_深度分析.pdf`](projects/wagner-meistersinger/analysis/Wagner_名歌手前奏曲_深度分析.pdf) 与 [原作锚点旁注总谱](projects/wagner-meistersinger/analysis/Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf)
- 想跑引擎：[vsl-dual-ai](engine/vsl-dual-ai/README.md)——`python conductor.py --bars 8 --demo --no-read`，不需要 MIDI 设备，也不需要 API key

## 仓库结构

```
AI-conducter/
├── README.md
├── .gitattributes
├── projects/                 作品层
│   ├── brahms-op98/
│   │   ├── analysis/         注释总谱、深度报告、导读、乐章分报告、谱例
│   │   ├── performance/      母带 WAV/MP3、混音工程、24 轨 MIDI、渲染工程、校验清单
│   │   ├── synchronized/     同步播放器、离线包、4K 视频、时间表与验证记录
│   │   ├── sources/          四乐章 MuseScore 源工程（.mscx）
│   │   ├── scripts/          曲式标注、注释生成、交付构建脚本
│   │   └── vsl/              VSL Synchron Player 状态格式与工厂预设的逆向笔记
│   └── wagner-meistersinger/
│       ├── score/            Schott 18469 原作总谱（39 页扫描）
│       ├── analysis/         深度分析、导读、旁注总谱
│       ├── notes/            逐页中文注、锚点审计、高亮校验
│       ├── research/         来源核查与结构研究
│       └── scripts/          标注构建、锚点校正、交付校验
└── engine/                   引擎层
    └── vsl-dual-ai/          双 AI 实时演奏
        ├── conductor.py      两条时钟、PLL、排程、手势派发
        ├── ensemble.py       PLL / Balance / PedalWatch / Reaction
        ├── reading.py        读谱 → 模型解读 → A4 PDF
        ├── examples/         8 小节示例谱（A/B 两条轨）
        ├── readings/         一次真实读谱的产物
        ├── notes/            设计笔记与运行统计
        ├── tools/            VSL 面板自动化探针
        └── docs/             控制环与手势流设计稿
```

## 技术链路

- **谱面**：MuseScore 4 工程（`.mscx`）作为可计算的谱面来源；历史扫描件（Wagner Schott 18469）作为配器与文字锚点的依据。
- **渲染**：REAPER 7.23 + Vienna Synchron Player / SYNCHRON Prime Orchestra，24 个音频声部由 16 个谱表拆分，逐轨渲染后合成。
- **分析写作**：Python 生成注释层与谱例，PDF/HTML 由同一份数据构建，报告与导读共享曲式表，避免多处口径不一。
- **同步**：读取实际演奏的速度图生成小节—时间映射，浏览器端按页切换谱图；视频由同一份时间表渲染。
- **实时（引擎层）**：Python 3 单线程控制环（4 ms tick）+ `ctypes`/`winmm` 直出 MIDI，两个 OpenAI 兼容端点只在 8 拍结构点递手势，超时即丢弃；Windows 侧用 loopMIDI 接 VSL。
- **脚本语言**：Python 3（构建/校验/实时引擎）、Node.js（少量打包与二进制处理）、Bash/PowerShell（渲染调度）。

## 复现

各项目 README 给出具体命令与依赖。共通前提：

```bash
git clone https://github.com/fromRhein/AI-conducter.git
cd AI-conducter
```

- 分析类交付（PDF/Markdown/HTML）只依赖仓库内文件，不需要额外安装。
- 渲染类复现需要本机安装 REAPER 与对应 VSL 音色库；`.RPP` 内含插件状态，工程可打开，但采样是否齐全取决于授权与安装。
- 播放器为单文件 HTML，音频与谱图已内嵌，断网可用。
- 引擎层的控制环可脱离硬件验证：`VSL_NULL_MIDI=1 python conductor.py --bars 8 --demo --no-read`，量的是 tick 抖动、事件迟到与两声部相位差，不需要 VSL 授权。

## 关于体积

仓库工作树约 291 MB（`.git` 约 237 MB），其中引擎层不到 1 MB。为了保持"克隆即可用"，母带 WAV、同步播放器、4K 视频与源谱都直接入库；但以下中间产物**不在版本控制内**：

- `performance/stems/`：24 轨原始分轨（约 2.2 GB）
- `performance/aux_audio/`：越界音补足实例的中间音频（约 543 MB）
- REAPER 自动备份与渲染缓存

归档时这两批音频被移入 `projects/brahms-op98/performance/` 并写入 `.gitignore`：本机上 `Brahms_IV_E_VSL_Mix.RPP` 打开即媒体齐全（工程内路径为 `../stems/`、`../aux_audio/`），而从 GitHub 克隆下来的副本不含这些文件，打开工程会提示缺少媒体——此时用 `render_projects/` 里的渲染工程重新渲染即可重建。所有入库文件均低于 GitHub 单文件 100 MB 上限，仓库不使用 Git LFS。

## 证据边界

这个仓库刻意保留"没做到"的部分：

- 勃拉姆斯分析以数字谱为音高/时值/声部依据，原始扫描件用于范围与配器定位；**未完成逐音视觉校勘**，页界不清处标为"跨页参考段"。
- VSL 渲染的自动化校验覆盖逐声部非静音、时长、电平、削波与合成检查，**不等于人工逐段听审**；数字谱中 9 个越界音用固定弯音辅助实例补足，并单独记录。
- 瓦格纳项目的动机细胞来自 Bülow 钢琴缩编谱，Schott 原谱只标注可 OCR 定位的印刷文字锚点；**不把缩编谱的读数移植为原作配器结论**。
- 播放器的同步精度为"按小节显示 + 按页切换"，纵向位置是近似辅助，不是逐音符游标。

把这些边界写清楚，比把成品说得完美更接近指挥这件事本身。

## 来源

本仓库内容由一次完整的 AI 协作会话产出并迁移归档（会话 `session-312b472a-4871-4ce9-b0c3-c7b3dffe08ee`，2026-10-31 至 2026-11-08）。迁移时保留了交付物、工程、脚本与校验记录，剔除了渲染中间音频与不属于本项目的其他工程资产。71 个二进制交付物（PDF/PNG/WAV/MP3/MP4/ZIP/MID/MSCX）在迁移后逐一做了 SHA-256 比对，与源文件一致；同步播放器的哈希也与 `播放器验证.json` 中记录的值相同。

`engine/vsl-dual-ai` 是同一工作区里的另一条线（2026-11-08），不在该会话记录内，归档时按"引擎层"定位独立整合，代码与笔记原样保留。

原始工作区中属于该会话的目录（交付物、渲染工程、同步工程、源谱工作目录、瓦格纳工作目录、报告）在迁移校验通过后已清理，只剩不属于该会话的 Tennstedt / Mahler 研究资产。

## 许可

分析文本、注释、脚本与工程文件由本项目作者生成，供学习与研究使用。所涉乐谱为公有领域作品的历史版本；扫描件与采样库分别受其原始提供方与厂商授权约束，不随本仓库授予任何再分发权。
