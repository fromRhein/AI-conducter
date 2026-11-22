# 瓦格纳《纽伦堡的名歌手》前奏曲

以 Schott 出版社 18469 号原作总谱（39 页历史扫描件）为对象，做可核验的锚点标注与动机分析。这个项目的核心不是"再写一篇赏析"，而是把每条判断落到一个能在谱上找到的位置，并把找不到的部分明确标出来。

## 一、分析框架

全曲的写作逻辑是：公共性主题、歌唱性材料与谐谑性变形，从先后呈示走向自由交织。

```
公共性陈述 ──→ 抒情对比 ──→ 谐谑变形 ──→ 复合对位 ──→ C 大调终结
              （不同句法与时间尺度）  （短促化与模仿接力）  （多主题交织）   （关系与重心确认）
```

A/B/L/P 等是分析用材料标签，不是作曲家编号。对位段落应区分模仿、碎片接力与高潮综合；"三重可转位对位"一类说法尚未逐音证实，报告中不作为结论使用。

## 二、可复核的动机细胞

这些读数来自 Bülow 钢琴缩编谱的 MusicXML，是缩编谱的直接事实，**不证明 Schott 总谱有相同音符或配器**。

| 缩编小节 | 音高与节奏关系 | 判断 |
| --- | --- | --- |
| 89、91 | 相同休止、时值与 C5 重复音；结尾 D5–C5–B4–C5 | 完整细胞复现 |
| 93、95 | 同一节奏与轮廓，整体上移小三度 | 移位变体 |
| 121、150 | 保留 C–D–C–B–C 邻音尾句；前导材料不同 | 局部细胞保留 |

## 三、总谱上的定位锚点

原谱没有可用的符号层，因此锚点是 OCR 可定位的**印刷文字**，高亮只落在文字上，不覆盖整条声部。

| Schott 页 | 印刷文字 | 与缩编谱的关系 |
| --- | --- | --- |
| 13 | Bewegt, doch immer noch etwas breit | 与 m.89 文字完全相同 |
| 14 | Mässig im Hauptzeitmaass | 与 m.97 速度文字接近，不是逐音映射 |
| 19 | Im mässigen Hauptzeitmaass | 与 m.122 相同；m.121 邻音尾句是缩编旁证 |
| 27 | immer bewegter | 速度推进；与 m.166 animato 仅作宽泛对照 |
| 34 | Sehr gewichtig | 与 m.196 pesante 语义相近 |

另标注 p.6 的 rallentando/Tempo、p.18 的 noch bewegter、p.19 的断奏、p.34 的力度文字。原作编制包括短笛、双管木管、四圆号、三小号、三长号、大号、定音鼓、竖琴、三角铁、钹与弦乐；这些提示应比较声部进入、加倍与低音支撑，但 OCR 位置本身不能证明具体音符同时发声。

## 四、交付物

### analysis/

| 文件 | 说明 |
| --- | --- |
| [Wagner_名歌手前奏曲_深度分析.pdf](analysis/Wagner_名歌手前奏曲_深度分析.pdf) | 完整分析报告（6 MB） |
| [Wagner_名歌手前奏曲_深度分析.md](analysis/Wagner_名歌手前奏曲_深度分析.md) | 纯文本版 |
| [original_analysis.md](analysis/original_analysis.md) | 以原作总谱为对象的分析长文（24.7 KB） |
| [Wagner_名歌手前奏曲_导读.html](analysis/Wagner_名歌手前奏曲_导读.html) | 单页导读 |
| [guide_original.md](analysis/guide_original.md) | 导读源稿（含 flow 图与锚点表） |
| [Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf](analysis/Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf) | 在原谱页面上叠加文字锚点与动机旁注的成品 |

### score/ 与 notes/

| 文件 | 说明 |
| --- | --- |
| [Schott_18469_原作总谱.pdf](score/Schott_18469_原作总谱.pdf) | 39 页原作扫描件，全部判断的谱面载体 |
| [original_page_notes.json](notes/original_page_notes.json) | 逐页中文注（78 条），含页码、系统、文字锚点与说明 |
| [annotation_audit.json](notes/annotation_audit.json) | 注释与锚点的一致性审计 |
| [highlight_alignment_check.json](notes/highlight_alignment_check.json) | 高亮框与 OCR 文字框的对齐检查 |
| [cue_score_verification.json](notes/cue_score_verification.json) | 旁注总谱的构建校验 |
| [delivery_verification.json](notes/delivery_verification.json) / [verification.json](notes/verification.json) | 交付级校验记录 |
| [score_page_*.png](notes/) | 6 张关键页（p1/13/19/27/35/39）的谱面快照 |

### research/ 与 scripts/

- [research/sources.md](research/sources.md)：版本、扫描来源与外部核查记录（含未完成项）。
- [research/structural_analysis.md](research/structural_analysis.md)：结构研究笔记。
- [scripts/build_original.py](scripts/build_original.py)：旁注总谱主构建脚本。
- [scripts/build_cue_score.py](scripts/build_cue_score.py)：锚点标注层构建。
- [scripts/create_detailed_annotations.py](scripts/create_detailed_annotations.py) / [scripts/detailed_annotations.json](scripts/detailed_annotations.json)：详细注释数据。
- [scripts/fix_highlight_alignment.py](scripts/fix_highlight_alignment.py) / [scripts/verify_highlight_fix.py](scripts/verify_highlight_fix.py)：高亮错位的检测与修正。
- [scripts/verify_delivery.py](scripts/verify_delivery.py)：交付前校验（页数、注数、锚点数、PDF 可打开性）。
- [scripts/audit_reduction_motif_recurrence.py](scripts/audit_reduction_motif_recurrence.py) / [scripts/audit_reduction_motif_rhythm.py](scripts/audit_reduction_motif_rhythm.py)：缩编谱动机复现与节奏审计。

## 五、复现

```bash
python scripts/build_cue_score.py        # 锚点层
python scripts/build_original.py          # 旁注总谱
python scripts/verify_highlight_fix.py    # 高亮对齐
python scripts/verify_delivery.py         # 交付校验
```

依赖 Python 3、PyMuPDF（页面合成与文字框）、报告构建所需的模板工具。原谱 PDF 与注释放仓库内，脚本不需要联网。

## 六、证据边界

- Schott 18469 是 39 页历史扫描件，**没有可用的符号层**；视觉输入与本地 OMR 工具当时均不可用，因此没有核实原谱音符、绝对小节线与动机音符边界。
- 缩编谱测得的节奏与音高不移植为原作配器结论；两边的对应只到"文字锚点 + 结构位置"这一层。
- 高亮框来自 OCR 文字定位，可能偏移或漏检；`highlight_alignment_check.json` 记录已修正与仍存疑的位置。
- 分析中的"可听作""可理解为"是解释性判断，不冒充作曲家的标记或同时代文献的直接证据。

## 七、版权

原作与扫描件属公有领域作品的历史版本；分析文本、注释数据与构建脚本由本项目作者生成。扫描件的数字来源与其使用条款请参见 [research/sources.md](research/sources.md)。
