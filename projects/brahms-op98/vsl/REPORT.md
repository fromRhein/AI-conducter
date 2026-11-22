# VSL Synchron Prime 状态配置只读分析

执行范围：读取指定播放器/音色卷及 D:/tools/proj/Flute.RPP、vln1.RPP；所有产物只在 render_work/vsl_probe。未启动 REAPER，未操作 GUI，未修改原工程或全局设置。computer-use 技能按要求尝试加载，返回 `source must be a string`；任务本身采用文件读取工具和 Python 3.15 标准库，未依赖视觉。没有进行激活或许可证相关操作。

## 已证实结论

- 工厂预设并非安装目录中的散装文件，目录位于六个 Prime `.syvolume` 容器。完整实际 preset/patch 路径在 `factory_catalog.json`；每种乐器推荐 `01 VelXF sus - MOD` 路径清单在 `factory_presets.md`。同时存在 `$FLOW_PRIME`、`02 VelXF - MOD`、`03 Velocity` 版本，选用传统 Synchron Player preset 与现有工程一致。
- 核心资源容器：`C:/ProgramData/VSL/Vienna Synchron Player/Volumes/at.co.vsl.synchronplayer.syvolume`。它提供默认状态及图标等，并非 Prime 全部乐器预设。
- 容器头偏移20（little-endian uint32）指向公开目录块。此块先有4字节压缩长度，其后zstd JSON目录树，叶子整数为entryIndex。脚本只解出目录，未进一步解析音色内容块，也未宣称已拿到所有乐器完整预设状态。
- 两份 RPP 的 `<VST ...>` Base64逐行分别解码后拼接，在偏移220有zstd帧。内容是 JSON，不是XML。早期探测文件 `.xml` 扩展名只是初始猜测，正式结果为 `Flute.state.json` / `vln1.state.json`。
- Flute压缩帧9964字节，解压130824字节；vln1压缩10345字节，解压158004字节。状态根为 `{data:{custom,meta,parameters},version:...}`。
- `custom.sampler.rootNode` 是完整发音树；叶子 `patchEntry` 是实际音色引用，例 `vol://at.co.vsl.sy.prime.ww:public/patches/02 Woodwinds/02 Flute 1/11P FL1 Long noVib.vsynpatch`。`lastPresetPath` 只是已选预设的记录，单改此字段不足以切换乐器。

## 可操作的程序配置路径

1. 最稳妥：lead在插件内加载相应工厂预设一次，保存各乐器模板RPP，然后程序整体移植该 `<VST>` 块，保留状态内部发音树、调音、混音、范围、元数据一致。这一方法可覆盖目录中所有乐器。
2. 完全离线：对已知同构乐器修改每个叶子的 `patchEntry` 和名称，再重编码状态。已生成 Flute1→Flute2 示例，20个引用（12个独立patch，部分重复用于XF）均在实际安装目录索引存在。这里保留Flute1混音定位及音域，故不是完整Flute2工厂预设的逐字副本，需宿主验听。
3. 不同家族不要机械替换名称：单簧管无vibrato分支、打击乐映射和弦乐奏法都不同。完整官方预设加载/保存后再复用状态更可靠。JSON路径引用可用于自建单奏法节点，但采样范围、输出矩阵、legato模式需按该乐器实际模板校验。
4. 已生成 `Flute_with_existing_Violins_state.RPP`：Flute工程副本的插件块换成现有vln1完整块，逐字节验证与vln1一致，音符保持Flute原曲，只是加载示范，不是完成的编配。

`build_examples.py` 包含可导入 `encode(block,state)`：JSON序列化→zstd→修改长度字段→Base64重编码。针对这两份相同包装模板，压缩长度N对应：偏移192 uint32=N+24，偏移204=N+8，偏移216=N；偏移212为ASCII `Size`，220开始压缩数据，帧后所有宿主尾部原样保留。不同插件/不同I/O包装应重新识别偏移，勿把220当通用VST3标准。REAPER插件ID保持 `{E2666DCD0106481DAD2F37AE8191168A}`。

## 已从实际状态确认的MIDI映射

|功能|来源|
|---|---|
|VelXF|CC1|
|Expression|CC11|
|Master volume|CC7|
|VelXF enabled|CC28|
|Vibrato XF / nodeXFade2|CC20|
|Attack / Release|CC22 / CC23|
|Timbre adjust|CC8|
|Dynamic range|CC30|
|Humanize delay / pitch / amount|CC25 / CC26 / CC27|
|Legato blur|CC33|
|Reverb return0 volume|CC5|
|Reverb enabled / level|CC15 / CC14|
|Room-Mix / Close volume|CC41 / CC42|

Flute现状 `velXFadeEnabled=1`，`velXFade≈0.63025`，expression=1，masterVolume≈0.56234。`VelXF sus`模板短奏叶子 `velXFadeMode=1`，长音/连奏为0，说明不能只凭全局开关推断短奏动态；需同时发送合理note velocity与CC1。初始CC11建议明确发送，避免沿用历史控制器。

## Articulation / keyswitch

- 两现成模板的根 `switchControl=25`、第二层=37，第三层vibrato XF节点=259。它们是内部枚举值，不应直接当成MIDI CC25/37/259。
- 数字25/37很可能编码为从MIDI24/36起的连续keyswitch（C0/C1的具体八度名称取决于宿主），但本次未进行GUI/实机确认，因此应由lead在键盘映射处核实真正MIDI note number后再批量发送。不得把推测写成已测结果。
- 可避免枚举歧义：离线设置树 `currentNodeIndex`（零基）明确默认奏法，再重编码。Flute根0短音、1长音、2连奏、3sfz、4自定义。短音次级0staccato、1agile、2portato、3portato agile；长音/连奏次级0无颤音、1有颤音、2颤音XF，第三项才由CC20进行XF。
- vln1根0staccato、1长音、2legato、3sfz、4tremolo、5pizzicato、6portamento、7自定义。完整树（所有次级、patch、音域、模式）分别在 `Flute.articulations.json` 与 `vln1.articulations.json`。
- 若尚未核实keyswitch，可分奏法轨道，每轨固定currentNodeIndex，音符分配到相应轨道。这样避免整曲演奏被错误keyswitch静默改变。

## Brahms 所需乐器入口

Factory / SYNCHRON Prime Orchestra 下：
- 01 Strings + Harp：大编制 01 1st Violins-14、02 2nd Violins-10、03 Violas-8、04 Violoncellos-8、05 Double basses-6。小编制对应11..15；Harp为00。
- 02 Woodwinds：02 Flute1、03 Flute2、11/12 Oboe1/2 (French)、21/22 Clarinet Bb1/2、31/32 Bassoon1/2、33 Contrabassoon；另有Piccolo、English horn、Bass clarinet。选实际完整路径见清单。
- 03 Brass：11/12 Horn1/2（可独立多实例作四圆号，区别MIDI声部/轻量humanize）；01/02 Trumpet1/2；21 Tenor trombone、22 Bass trombone、23 Trombones4；31 Bass tuba。多重独奏实例与组奏预设音色密度不同，不宜重复同一tutti叠成超编制。
- 04 Percussion：01 Timpani - VelXF sus。其余打击乐及竖琴均已列入目录，不必为本曲添加无谱声部。

## 复验与剩余验证

复现命令依次 `python render_work/vsl_probe/probe_state.py`、`probe_index.py`、`build_examples.py`。Python使用 `from compression import zstd`，无需pip依赖。

自动验证已通过：原工程SHA256前后相同；完整vln1移植字节相同；Flute2所有叶子patch路径都存在；新状态压缩后解压得到完全相同JSON；Base64写出再读回字节相同。详见 `verification.json`。

运行时验证交由lead：打开副本后确认名称/采样加载完成、无missing sample；发送单音和CC1/11变化；核实音域与各奏法切换；保存再解码对比patchEntry仍为目标乐器；短音频试听和峰值检查通过后再大规模复制。此次结构校验不等于已证实插件成功发声。
