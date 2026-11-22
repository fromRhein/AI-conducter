# 勃拉姆斯《第四交响曲》Op.98

从全曲分析到第四乐章 E→终曲的采样渲染，再到谱面同步视频。三件事共用一套曲式数据与时间表，所以分析里的小节号、音频里的第 113 小节、播放器里的当前系统指向同一处。

## 一、作品与阅读框架

四个乐章的调性路线是 e 小调 → E 大调 → C 大调 → e 小调。中间两个乐章的明亮不是结局的预告，而是把最终回归的距离拉大。全曲的统一性来自对极短材料的持续加工：第一乐章把三度细胞发展为长线条，第二乐章让同一音高中心容纳调式与调性两种听觉，第三乐章用节奏与音色制造反差，终乐章把八小节骨架变成 30 段变奏加扩展尾声。

| 乐章 | 速度/拍号 | 结构 | 关键位置 |
| --- | --- | --- | --- |
| I | Allegro non troppo，2/2 | 奏鸣曲式 + 发展变奏 | 开头 B–G–E–C–A–F♯–D♯–B；m145 假再现；m246 木管增值重述；m394 低弦接替 |
| II | Andante moderato，6/8 | 调式引句与奏鸣性回归 | 圆号 E–F–G 的降二级；m113 召回调式原型 |
| III | Allegro giocoso，2/4 | 节奏冲击与奏鸣性组织 | m181 Poco meno presto；m199 Tempo I；m247 副题移高纯四度 |
| IV | Allegro energico e passionato，3/4（中段 3/2） | 主题 + 30 变奏 + 尾声 | m246 再现增值；m249 C 和弦插句；m253 Più Allegro |

小节计数有一个容易踩的坑：第一乐章 XML 有 441 个 `Measure` 节点，其中第一个是四分音符弱起，所以是"弱起 + 440 个完整小节"。XML 顺序号不能直接当印刷小节号用。

## 二、交付物

### analysis/ — 读谱

| 文件 | 说明 |
| --- | --- |
| [Brahms_Op98_全曲注释总谱.pdf](analysis/Brahms_Op98_全曲注释总谱.pdf) | 98 页，保留原始谱面，页边放中文旁注；黄/青透明带是声部观察带，不是逐音和声归属 |
| [Brahms_Op98_全曲深度分析.pdf](analysis/Brahms_Op98_全曲深度分析.pdf) | 四乐章完整报告，含曲式表与关键小节 |
| [Brahms_Op98_全曲深度分析.md](analysis/Brahms_Op98_全曲深度分析.md) | 同内容的纯文本版，便于检索与 diff |
| [Brahms_Op98_分析导读.html](analysis/Brahms_Op98_分析导读.html) | 单页导读，适合先看全局再看细节 |
| [movements/](analysis/movements/) | 四个乐章的独立分报告 |
| [assets/](analysis/assets/) | 6 张谱例（excerpt-01/30/42/68/75/78），取自原谱实际页面 |
| [annotation_audit.json](analysis/annotation_audit.json) | 旁注与谱面锚点的审计记录 |

PDF 页码与原印页码相差 246（PDF 第 1 页 = 印刷页 247）；乐章起点在 PDF 第 1、30、42、68 页；四乐章各自重新起算小节号。

### performance/ — 演奏

范围：排练字母 **E（第 113 小节）至第 311 小节**，共 199 小节，成品 5:29。E 的定位依据是原谱 PDF 第 76 页 / 印刷页 322 第二系统的排练字母，加上 m113 长号圣咏的进入，置信度 0.98。

| 文件 | 说明 |
| --- | --- |
| [audio/Brahms_IV_E_to_End_VSL_48k24.wav](performance/audio/Brahms_IV_E_to_End_VSL_48k24.wav) | 48 kHz / 24 bit 立体声母带（90 MB） |
| [audio/Brahms_IV_E_to_End_VSL.mp3](performance/audio/Brahms_IV_E_to_End_VSL.mp3) | 320 kbps 试听副本，以母带为准 |
| [project/Brahms_IV_E_VSL_Mix.RPP](performance/project/Brahms_IV_E_VSL_Mix.RPP) | 轻量混音工程，读取 `stems/`；仓库未收录分轨，见下文 |
| [midi/performance_midi/](performance/midi/performance_midi/) | 24 条演奏 MIDI，含实际奏法键位，已折算为绝对时序（固定 120 BPM 承载） |
| [midi/midi_tracks/](performance/midi/midi_tracks/) | 16 条按谱表合并的 MIDI，便于对照原谱声部 |
| [midi/Brahms_IV_E_conductor.mid](performance/midi/Brahms_IV_E_conductor.mid) | 指挥轨（速度图与拍点） |
| [render_projects/](performance/render_projects/) | 24 个主声部工程 + 4 个音域补足辅助工程，含真实 VSL 状态与嵌入式 MIDI |
| [manifests/](performance/manifests/) | 演奏/渲染清单、音频校验、辅助音高检查、宿主工程核验 |
| [scripts/articulation_plan.py](performance/scripts/articulation_plan.py) | 由谱面记号推导奏法与键位的规则 |
| [scripts/recombine_auxiliary_stems.py](performance/scripts/recombine_auxiliary_stems.py) | 把辅助实例音频按原时间叠回主声部 |
| [演奏说明.md](performance/演奏说明.md) | 诠释方向、速度选择、实现细节与已知限制（建议先读这份） |

**诠释要点**（详见演奏说明）：

- 113–128 圣咏与悬停：3/2 按大拍呼吸，初始四分音符约 108；128 收束后加约 0.8 秒停顿。
- 129–176 恢复推进：回到 3/4 立即恢复脉动，不把前段减速带入变奏。
- 177–216 累积而非突然膨胀：按谱面发夹线渐变，加很小的八小节句法拱形。
- 217–248 重新组织层次：木管对答略向前，长句保留局部回收。
- 249–252 收紧蓄势；253–311 Più Allegro，入口约四分音符 144，终止附近约 126。
- 所有数值速度与混音决定都是本次诠释，不冒充作曲家的节拍器标记。

**工程实现**：16 个谱表拆成 24 个音频声部；双管、圆号、双长号按已有声部/和弦音分配，单一旋律音不复制成第二个演奏者；四圆号用 Horn 1/2 音色承载两对声部；两条次中音长号同型号但保留独立事件与轻微时间差。CC1 承载音色力度交叉淡化，CC11 补小幅乐句呼吸，音符起点用固定随机种子加约 ±3 ms 偏移。实际采样触发 9077 次，少于源 MIDI 的 9741 个事件，差异主要来自滚奏/持续震音的写法变化。

**两处必须知道的修正**：

1. MuseScore 导出的 MIDI 把定音鼓滚奏写成半音交替颤音。本版按 XML 实际音高、时值与延音线重建定音鼓声部，用 VSL Rolls 演奏。
2. 数字谱里有 1 个圆号 E1 和 8 个长号 B4–C♯5 超出工厂音色默认音域，其中 E1 还与奏法切换键重合。这 9 个音从主实例分离，用 4 个固定弯音的辅助实例补足（圆号 E2 采样降八度；长号 B♭4 采样升 1/2/3 个半音）。固定弯音避免影响同声部其他音与释放尾音。

### synchronized/ — 听与看对齐

| 文件 | 说明 |
| --- | --- |
| [Brahms_IV_E_分析总谱同步播放器.html](synchronized/Brahms_IV_E_分析总谱同步播放器.html) | 单文件播放器（55 MB），音频与 23 张谱图全部内嵌，断网可用 |
| [Brahms_IV_E_分析总谱同步播放_离线包.zip](synchronized/Brahms_IV_E_分析总谱同步播放_离线包.zip) | 同上的压缩分发版 |
| [Brahms_IV_E_分析总谱同步_4K.mp4](synchronized/Brahms_IV_E_分析总谱同步_4K.mp4) | 4K 视频，适合投屏或存档 |
| [播放器预览.png](synchronized/播放器预览.png) | 界面预览 |
| [使用说明.md](synchronized/使用说明.md) | 操作与同步精度说明 |
| [同步时间表.json](synchronized/同步时间表.json) | 页界、系统位置、时间与证据 |
| [MP4同步核验表.json](synchronized/MP4同步核验表.json) / [MP4验证结果.json](synchronized/MP4验证结果.json) / [播放器验证.json](synchronized/播放器验证.json) | 视频与播放器的验证记录、成品 SHA-256 |
| [scripts/](synchronized/scripts/) | 同步表生成、视频渲染、播放器打包与测试脚本 |

同步口径：23 页、27 个系统；p76 = 第 108 小节起，p76 第二系统 = 第 113 小节（E），p77 = 120，…，p98 = 302。播放器按小节显示并按页切换，青色边框指示当前系统；纵向坐标是近似辅助，未做逐音符游标。已在独立 Edge 实例、断网条件下验证 199 个小节跳转与 329.061 秒音频时长。

### sources/ 与 scripts/

- [sources/](sources/)：四乐章 MuseScore 工程（`Brahms Symphony #4 first/second/third/fourth movement.mscx`），分析与 MIDI 的源头。
- [scripts/build_deliverables.py](scripts/build_deliverables.py)：从谱面与分析数据构建 PDF/HTML 交付物。
- [scripts/prepare_annotations.py](scripts/prepare_annotations.py)：生成注释层与锚点。
- [scripts/overview.md](scripts/overview.md)、[scripts/guide.md](scripts/guide.md)：导读正文源稿。

### vsl/ — 采样器状态格式笔记

为了让"程序化加载音色"可复现，对 VSL Synchron Player 的状态封装做了只读逆向：

- [REPORT.md](vsl/REPORT.md)：RPP 内 `<VST>` 块 Base64 → 偏移 220 起为 zstd 帧 → 解压为 JSON 状态（`{data:{custom,meta,parameters},version}`），叶片 `patchEntry` 指向实际 `.vsynpatch`；`lastPresetPath` 只是记录，单改它不足以换乐器。
- [factory_catalog.json](vsl/factory_catalog.json)：六个 Prime `.syvolume` 容器中的完整 preset/patch 路径清单。
- [factory_presets.md](vsl/factory_presets.md)：每种乐器推荐的 `01 VelXF sus - MOD` 路径。
- [build_examples.py](vsl/build_examples.py)：JSON → zstd → 改写长度字段 → Base64 重编码的可导入实现（针对这两份相同包装模板，偏移不可当通用 VST3 标准）。
- MIDI 映射实测：VelXF = CC1，Expression = CC11，Master volume = CC7，VelXF 启停 = CC28，Vibrato XF = CC20，Attack/Release = CC22/CC23，Timbre = CC8，Dynamic range = CC30，Humanize delay/pitch/amount = CC25/26/27，Legato blur = CC33，Reverb return = CC5。
- [factory_extract_REPORT.md](vsl/factory_extract_REPORT.md) 等：容器目录块与既有状态映射的进一步取证。
- [渲染工作记录.md](vsl/渲染工作记录.md)：渲染过程中的试错记录（冷启动采样未就绪、逐轨独奏输出、起音检查等）。
- [install_verify/](vsl/install_verify/)：渲染环境的加载证据截图（Kontakt 音色库已载入、Synchron Solo Strings 单独加载），用于证明上述状态格式结论对应的实际运行环境。

## 三、复现

```bash
# 1. 只看分析：无需依赖
open analysis/Brahms_Op98_全曲深度分析.pdf

# 2. 重建分析交付物（需要 Python 3 + 依赖）
python scripts/prepare_annotations.py
python scripts/build_deliverables.py

# 3. 重渲染某个声部（需要 REAPER 7 + VSL Synchron Prime）
#    打开 render_projects/20_Violins1.RPP，确认采样加载完成后 Render
#    冷启动不要只看进度 100%，要检查起音

# 4. 重建同步表与播放器
python synchronized/scripts/build_sync.py
python synchronized/scripts/package_player.py
```

渲染的两个经验：采样库冷启动时"进度 100%"不等于发音已就绪，建议小组预加载、逐轨独奏输出并做起音检查；重新渲染越界音组件后，先跑 `recombine_auxiliary_stems.py` 更新分轨，再开混音工程导出。

## 四、已知限制

- 分析以数字谱为音高/时值/声部依据，原谱扫描件用于范围与配器定位；**未完成逐音视觉校勘**。页首编号识别不足的页面标为"跨页参考段／页界待核"。
- 数字谱含播放用速度数值、隐藏速度文字与后加的主题/变奏标签，这些不自动具有作曲家原始标记的权威。终乐章 m253 的"variation 31"标签应与"主题 + 30 变奏 + 尾声"的常用编号区别开。
- 双管 a2/divisi 文字与少量混合 arco/pizz 文字未完整人工复核，声部分配遵循保守规则。
- 自动校验覆盖非静音、时长、电平、削波与合成，不等于人工逐段听审。
- 仓库不含 `stems/` 与 `aux_audio/`，所以混音工程打开时会缺媒体；这是体积取舍，不是文件损坏。
