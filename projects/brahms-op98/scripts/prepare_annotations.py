from pathlib import Path
import re,json
BASE=Path(__file__).resolve().parent
notes=[]
extras={
1:{0:'音列B—G—E—C—A—F♯—D♯—B按音级形成下降三度链；实际音区包含上行六度。',9:'旋律C—B—C—A与低音D♯—E—F—F♯相互分离：保持旋律身份而改变和声。',19:'先听中提琴，再听木管接力；模仿不等于所有声部齐奏，也不必称作赋格。',57:'大提琴F♯—E｜E—F♯—E—D｜G—F♯。歌唱旋律与短促背景形成不同发音层。',91:'保持二二拍的大拍；上方附点型与低弦三连音同时存在。',145:'这里制造开头重复的错觉，后续却进入新的发展。不要误认作真正再现。',246:'B—G—E—C、A—F♯—D♯—B被增值并插入弦乐句，主题回归早于其身份被听清。',301:'B—A｜A—B—A—G｜C—B对应呈示副题，调性回归与配器重分配同时发生。',394:'主题的领导权转至低弦；上层错位应答，使熟悉的三度链获得压迫感。',427:'末和弦保留G自然与E低音；第一乐章也没有以大调第三音收尾。'},
2:{1:'E附近的F自然产生降二级色彩。只把开头称为弗里几亚色彩，不把全乐章判成古调式。',5:'G♯—A—B｜G♯—F♯—E保留原型轮廓，同时改变音级功能。连奏与拨奏彼此衔接。',41:'大提琴B—C♯—D♯—E—D♯—C♯构成副题识别基准。上层弦乐承担细分伴奏。',64:'回归不仅是旋律回来；拨奏发音、低音准备与内声部运动共同建立熟悉感。',88:'E—F♯—G♯—A—G♯—F♯对应m41，B大调副题在E大调解决。',113:'圆号回忆E—F—G原型，最终和声仍落在含G♯的E大调。记忆与终止并存。'},
3:{1:'二四拍的强奏开头具有谐谑功能，不能据此套用三拍子谐谑曲加三声中部。',181:'速度与织体的局部减压属于持续发展的内部对照，需与前后材料一起理解。',199:'回归从对应原m10的材料进入，省略开头块状宣告，改变句法重量。',247:'副题从G调方向转回C调，提供奏鸣性调性解决的直接证据。'},
4:{1:'八音E—F♯—G—A—A♯—B—B—E。长号在开头已参与；主题不始终位于最低声部。',97:'这是变奏12，仍为小调／一升号。中提琴与圆号的E脉冲托住长笛独白。',105:'E大调到此才确立。应区别m97长笛独奏与随后大调音色展开两个过程。',113:'“圣咏”描述宽阔和声节奏与音色，不等于已经识别某首教会旋律引文。',129:'长笛恢复开头八音，但低音改变：具有再现功能，绝非照抄原先八小节。',249:'8+30×8+4+59=311。可把这四小节计作广义尾声，或第30变奏的扩展。',253:'Più Allegro后不再强行每八小节编号。m309—310属至主、m311再击，终止坚持e小调。'}
}
for m in range(1,5):
 text=(BASE/f'reports/movement{m}.md').read_text(encoding='utf-8-sig')
 # Choose the first substantial table; movement IV's first table is its complete variation map.
 tables=[];current=[]
 for line in text.splitlines()+['']:
  if line.strip().startswith('|'):current.append(line)
  elif current:tables.append(current);current=[]
 table=max(tables,key=len) if m==4 else tables[0]
 for line in table:
  c=[x.strip() for x in line.strip().strip('|').split('|')]
  loc=c[1] if m==4 else c[0]
  nums=re.findall(r'\d+',loc)
  if not nums:continue
  start=0 if '弱起' in loc else int(nums[0]);end=int(nums[-1])
  if m==1:title=c[2];body=c[3]
  elif m in [2,3]:title=c[1];body='；'.join(c[2:])
  else:title='主题' if c[0]=='主题' else '第'+c[0]+'变奏' if c[0].isdigit() else c[0];body=' '.join(c[2:])
  if start in extras[m]:body+=' '+extras[m][start]
  kind='form' if any(s in title for s in ['尾声','回接','再现','扩展','连接','展开']) else 'theme'
  if m==4 and start in [41,57,65,97,113,161,169,217,225]:kind='orchestration'
  if m==2 and start in [1,41,88,113]:kind='harmony'
  notes.append({'movement':m,'start':start,'end':end,'kind':kind,'title':re.sub(r'\*','',title),'text':re.sub(r'\*','',body)})
(BASE/'annotations.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding='utf8')
print('Annotations',len(notes),{m:sum(n['movement']==m for n in notes) for m in range(1,5)})
