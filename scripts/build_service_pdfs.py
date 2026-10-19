"""Build Korean service brochure and scope proposal; requires PyMuPDF and Noto CJK."""
from pathlib import Path
import textwrap
import fitz
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/documents'
REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
INK = (0.09, .16, .22)
TEAL = (.0, .43, .43)
MUTED = (.37, .43, .48)
BG = (.95, .97, .97)
WHITE = (1,1,1)
# Extract the Korean face from CJK collections for portable embedded fonts.
for weight, source in [('Regular', REG), ('Bold', BOLD)]:
 target = Path('/tmp') / ('PetSenseNotoSansKR-' + weight + '.ttf')
 font = TTFont(source, fontNumber=1)
 sub = subset.Subsetter()
 sub.populate(text=Path(__file__).read_text() + ''.join(chr(i) for i in range(32,127)))
 sub.subset(font)
 glyphset = font.getGlyphSet()
 glyphs = {}
 for name in font.getGlyphOrder():
  pen = TTGlyphPen(None)
  glyphset[name].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
  glyphs[name] = pen.glyph()
 builder = FontBuilder(font['head'].unitsPerEm, isTTF=True)
 builder.setupGlyphOrder(font.getGlyphOrder())
 builder.setupCharacterMap(font.getBestCmap())
 builder.setupGlyf(glyphs)
 builder.setupHorizontalMetrics(font['hmtx'].metrics)
 builder.setupHorizontalHeader(ascent=font['hhea'].ascent, descent=font['hhea'].descent)
 builder.setupNameTable({'familyName':'PetSense Noto KR','styleName':weight,'uniqueFontIdentifier':'PetSenseNotoKR'+weight,'fullName':'PetSense Noto KR '+weight,'psName':'PetSenseNotoKR-'+weight})
 builder.setupOS2(sTypoAscender=font['hhea'].ascent,sTypoDescender=font['hhea'].descent,usWinAscent=font['hhea'].ascent,usWinDescent=abs(font['hhea'].descent))
 builder.setupPost()
 builder.setupMaxp()
 builder.save(target)
REG = '/tmp/PetSenseNotoSansKR-Regular.ttf'
BOLD = '/tmp/PetSenseNotoSansKR-Bold.ttf'
FONT = fitz.Font(fontfile=REG)
BFONT = fitz.Font(fontfile=BOLD)
LINKS = [
 ('개발 PR', 'https://github.com/coba8002-code/presense-ai/pull/2'),
 ('음향 모델 실행 검증', 'https://github.com/coba8002-code/presense-ai/actions/runs/39213061875'),
 ('경량 VLM 실행 검증', 'https://github.com/coba8002-code/presense-ai/actions/runs/39128173508'),
 ('개 전문 자료 조사', 'https://github.com/coba8002-code/presense-ai/blob/codex/sprint02-bootstrap-audio-vlm/docs/DOG_RESEARCH_EXPANSION.md')]

class PDF:
 def __init__(self, title):
  self.doc = fitz.open(); self.title = title; self.page = None; self.y = 0
 def text(self, text, x=44, y=None, size=11, width=507, bold=False, color=INK, leading=1.65):
  if y is None: y = self.y
  font = BFONT if bold else FONT
  for paragraph in text.split('\n'):
   line = ''
   for ch in paragraph:
    if line and font.text_length(line+ch, fontsize=size)>width:
     self.page.insert_text((x,y),line,fontname='KB' if bold else 'KR',fontsize=size,color=color)
     y += size*leading; line = ''
    line += ch
   self.page.insert_text((x,y),line,fontname='KB' if bold else 'KR',fontsize=size,color=color)
   y += size*leading
  self.y = y
  if y > 770: raise ValueError(f'Page overflow {len(self.doc)}: {y}')
  return y
 def new(self, kicker, title, subtitle=''):
  self.page = self.doc.new_page(width=595,height=842)
  self.page.insert_font(fontname='KR',fontfile=REG)
  self.page.insert_font(fontname='KB',fontfile=BOLD)
  self.page.draw_rect(fitz.Rect(0,0,595,10),color=TEAL,fill=TEAL)
  self.text('PetSense AI  /  '+kicker,y=43,size=10,bold=True,color=TEAL)
  self.text(title,y=94,size=25,bold=True,leading=1.35)
  if subtitle: self.text(subtitle,y=self.y+8,size=10,color=MUTED)
  self.y += 20
  self.page.insert_text((44,811),'PetSense AI · '+self.title+' · 2026.10.19 KST',fontname='KR',fontsize=8,color=MUTED)
  self.page.insert_text((530,811),str(len(self.doc)),fontname='KR',fontsize=9,color=MUTED)
 def section(self,title,body):
  self.text(title,y=self.y+7,size=14,bold=True,color=TEAL)
  self.text(body,y=self.y+4,size=11)
  self.y += 12
 def box(self,title,body):
  y=self.y
  # Draw background first, size estimated from width-aware wrapping.
  lines=0
  for paragraph in body.split('\n'):
   w=0; lines+=1
   for ch in paragraph:
    cw=FONT.text_length(ch,fontsize=10.5)
    if w+cw>467: lines+=1; w=0
    w+=cw
  h=51+lines*17
  self.page.draw_rect(fitz.Rect(44,y,551,y+h),color=BG,fill=BG)
  self.text(title,x=60,y=y+23,size=12,bold=True,color=TEAL,width=467)
  self.text(body,x=60,y=y+46,size=10.5,width=467,leading=1.6)
  self.y=y+h+16
  if self.y>770: raise ValueError('Box overflow')
 def link(self,title,url):
  y=self.y
  self.text(title+'  ↗',size=10,color=TEAL)
  self.page.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(44,y-12,540,y+5),'uri':url})
 def save(self,name):
  self.doc.set_metadata({'title':self.title,'author':'PetSense AI','subject':'Dog-only MVP; current status and planned scope','keywords':'PetSense AI, 개, 행동 분석, 기획'})
  self.doc.embfile_add('FONT_LICENSE.txt', Path('/usr/share/doc/fonts-noto-cjk/copyright').read_bytes(), desc='Noto CJK font copyright and license; embedded subset converted to TrueType')
  # Fonts were subset before embedding to preserve Korean glyphs.
  self.doc.save(OUT/name,garbage=4,deflate=True)


def brochure():
 p=PDF('서비스 소개 브로셔')
 p.new('SERVICE BROCHURE','우리 개의 행동을,\n근거와 함께 이해하다','개 전용 AI 행동 관찰 서비스 · 개발 중인 MVP 소개')
 p.section('PetSense AI는 어떤 서비스인가요?', '개의 소리와 짧은 영상을 분석해 눈에 보이고 귀에 들리는 행동을 정리하고, 검토된 자료를 바탕으로 보호자가 상황을 이해하도록 돕는 서비스를 만들고 있습니다.')
 p.box('소리에서 단서를 찾습니다','짖음·하울링·으르렁·낑낑거림 등 소리 유형을 분석합니다. 현재는 실제 사전학습 음향 모델을 연결한 개발용 추론 도구가 있습니다.')
 p.box('영상에서 행동을 살펴봅니다','서기·앉기·눕기 같은 자세와 주변 상황을 관찰하는 기능을 개발합니다. 개의 감정이나 의도를 단정하지 않고 불확실한 부분을 구분합니다.')
 p.box('설명에 출처를 연결합니다','행동학 지침과 전문가 사례를 검토해 관련 근거를 찾아주는 기능을 계획합니다. 강형욱 출연 영상 등은 권한과 내용을 확인할 사례 후보입니다.')
 p.text('목표 사용자: 자기 개의 특정 행동을 이해하고 기록하려는 보호자',size=10,bold=True)
 p.new('HOW IT WORKS','어떻게 사용하게 되나요?','아래 흐름은 목표 사용자 경험이며, 완성된 모바일 앱 화면은 아닙니다.')
 p.section('01  궁금한 장면을 선택합니다','보호자가 개의 짧은 영상이나 소리를 선택합니다. 상시 녹화보다 필요한 장면을 분석하는 방식으로 시작합니다.')
 p.section('02  관찰 결과와 불확실성을 확인합니다','소리 유형과 자세를 정리하고, 가림·잡음·맥락 부족으로 판단하기 어려운 부분을 표시합니다. 실제 앱 연결과 결과 화면은 후속 개발 범위입니다.')
 p.section('03  관련 근거를 읽고 기록합니다','검수된 자료의 출처를 살펴보고 보호자가 상황을 추가 기록하도록 설계합니다. 개별 사례에 맞지 않는 조언을 확정적으로 제시하지 않습니다.')
 p.box('현재 확인된 성과','개발 테스트 112개 통과. 실제 AST 가중치로 음향 파일 추론 성공. SmolVLM2의 합성 이미지 LoRA 학습·저장·재로딩 검증 성공. 이 결과는 실제 개 행동 정확도 검증과는 다릅니다.')
 p.box('개발 중인 기능과 서비스의 한계','실제 개 데이터 평가, 영상·음성 결합, 모바일 앱, 운영 배포는 미완료입니다. 개의 말을 사람 언어로 번역하거나 질병을 진단하지 않습니다. 급격한 이상 행동은 수의사 등 전문가의 평가가 필요할 수 있습니다.')
 for title,url in LINKS[:2]: p.link(title,url)
 p.save('PetSense_AI_Brochure.pdf')


def proposal():
 p=PDF('제품 기획서 및 작업 범위')
 p.new('PRODUCT PROPOSAL','PetSense AI\n제품 기획서 및 작업 범위','문서 버전 1.0 · 개 전용 MVP · 기준일 2026.10.19 KST')
 p.section('기획 목적','보호자가 개의 행동을 이해할 때 소리, 자세, 상황을 함께 살펴보고 출처가 있는 설명을 얻도록 돕는다. 관찰 사실과 해석을 구분하고, 판단할 근거가 부족하면 결과를 보류한다.')
 p.section('핵심 사용자와 해결할 문제','첫 사용자는 반려견 보호자다. 특정 장면의 짖음이나 자세가 궁금하지만 정보가 흩어져 있고 일반적인 조언을 자기 개에 적용하기 어렵다는 문제를 다룬다. 이 문제와 사용 의향은 향후 사용자 인터뷰로 검증해야 한다.')
 p.box('제품의 핵심 질문','“이 장면에서 우리 개가 무엇을 하고 있으며, 어떤 단서를 확인할 수 있고, 무엇은 아직 알 수 없는가?”')
 p.section('핵심 가치','소리와 영상의 관찰 정보를 함께 제공한다. 전문가의 설명은 출처와 적용 조건을 보존한다. 개인정보와 학습 동의를 구분하고, 오류를 검수할 수 있는 기록을 남긴다.')
 p.section('이 문서의 상태','완료된 개발 기능과 목표 제품 범위를 구분하는 실행 기획서다. 시장성·매출·정확도·출시일이 검증되었다는 뜻은 아니다. 개발 내역은 PR #2와 연결 문서를 기준으로 추적한다.')
 p.new('CURRENT STATUS','현재 구현 수준','실행 가능한 연구·개발 프로토타입. 제품 출시와 실제 개 성능 검증은 미완료.')
 p.section('구현 및 실행 검증 완료','FastAPI 개발 서버, 오디오 전처리와 기초 학습 파이프라인, 브라우저 음성 입력, 로컬 영상 검수 도구가 있다. 데이터 권리·개체 분리·파일 변조 검사를 구현했다.')
 p.section('음향 AI: 이번에 추가한 기능','AST AudioSet 사전학습 모델을 고정 버전으로 불러 로컬 WAV를 분석한다. 개 관련 원본 라벨 7개의 독립 점수를 반환한다. 실제 가중치의 합성 음성 추론과 독립 CLI 실행이 CI에서 성공했다.')
 p.section('영상 AI: 현재 확인한 범위','SmolVLM2 256M의 LoRA 학습·저장·재로딩·추론을 합성 이미지로 검증했다. 정지 자세용 실험 경로와 외부 VLM 연동 코드가 있다. 실제 개 자세 학습이나 연속 동작 성능 검증은 완료되지 않았다.')
 p.box('완료로 표시하면 안 되는 항목','개 행동 정확도, 감정·의도 해석, Dog2vec/AVES 실제 연결, 영상·음성 결합 평가, Flutter 앱, 운영 인증·배포, 지속적인 실데이터 자동학습은 미완료다. 음향 점수는 보정되지 않았으며 현재 결정은 보류한다.')
 p.section('검증 증거','로컬 테스트 112개 통과. 음향 CI 39213061875 성공. 백엔드·브라우저 CI 39213065678 성공. 테스트 통과는 코드의 작동 증거이며, 실제 개 인식 정확도의 증거는 아니다.')
 p.new('USER EXPERIENCE','사용 흐름과 MVP 경계','단일 개의 짧은 장면을 분석하는 흐름부터 완성한다.')
 p.section('목표 사용 흐름','개 프로필 등록 → 영상/음성 선택 → 분석 및 학습 동의 구분 → 처리 상태 확인 → 관찰 결과·불확실성 확인 → 근거 자료 보기 → 보호자 피드백·삭제.')
 p.section('초기 입력 범위','앱 영상은 10~20초 권장, 최대 30초·20 MB를 초기 설계값으로 제안한다. 이는 현재 구현된 업로드 제한이 아니다. 현재 AST CLI 입력은 16 kHz PCM16 WAV, 0.1~10초, mono/stereo, 2 MB 이하로 제한된다.')
 p.section('초기 출력 범위','음향은 짖음·하울링·으르렁·개 낑낑거림 등 원본 라벨 점수다. 영상은 서기·앉기·눕기·판단 보류부터 시작한다. 걷기 등 시간적 행동은 시퀀스 입력과 별도 평가가 필요하다.')
 p.box('초기 서비스 범위에서 제외','고양이 지원, 개 언어 번역, 질병 진단, 교정 성공 보장, 다중 동물 추적, 상시 서버 전송, 스마트폰 대형 VLM 상시 실행은 MVP 범위에서 제외한다.')
 p.section('피드백 설계','보호자가 결과에 동의하지 않거나 맥락을 추가할 수 있게 한다. 보호자의 피드백은 검수 후보로 저장하고 자동으로 학습 정답으로 확정하지 않는다. 삭제와 학습 사용 철회를 처리할 정책이 필요하다.')
 p.new('WORK PACKAGES','작업 범위와 완료 기준','각 작업은 실행 증거가 있어야 완료 처리한다. 일정은 데이터·인력 확보 후 산정한다.')
 p.section('WP1  음향 모델 연결 · 일부 완료','AST 파일 추론과 CI 검증 완료. Dog2vec/AVES는 가중치 이용 조건 확인 후 진행한다. 완료 기준: 정확한 버전·입력·출력 라벨·오류 처리·재현 가능한 추론. 실제 개 성능 평가는 WP2에서 수행한다.')
 p.section('WP2  실제 데이터와 독립 평가 · 미완료','권한과 라벨을 검토한 개 녹음·영상 및 잡음 대조군을 확보한다. 개체·가정·세션·원본 기준으로 분리한다. 완료 기준: 출처/권리 기록, 검수된 manifest, 누수 감사, 기본 모델 평가 보고서.')
 p.section('WP3  영상·멀티모달 모델 · 일부 기반 완료','현재 정지 자세 LoRA 기반을 실제 데이터로 평가하고, 이후 시간적 행동과 음향 결합을 구현한다. 완료 기준: 영상만/음성만/결합 모델을 동일한 독립 표본으로 비교하고 실패 사례를 기록한다.')
 p.section('WP4  전문가 근거와 검색 설명 · 일부 기반 완료','공식 영상·행동학 문서의 후보 수집, 출처·관찰·해석·개입·결과 분리, 사람 검수, 승인 근거 검색을 구현한다. 완료 기준: 답변에서 원문 시간 구간과 검수 상태를 추적하고 철회된 자료를 제외한다.')
 p.section('WP5  앱·서버·운영 · 미완료','사용자 인증, 개인 미디어 업로드, 비동기 작업, 비용 한도, 결과·피드백·삭제 API, Flutter 흐름을 연결한다. 완료 기준: 실제 기기 전체 흐름, 접근 통제, 삭제, 실패·재시도·비용 상한 검증.')
 p.new('DATA & KNOWLEDGE','학습 자료와 전문가 영상','영상의 정보 가치를 살리면서 관찰과 해석을 구분한다.')
 p.section('모델·데이터 도입 기준','공식 코드·가중치·데이터 라이선스를 각각 확인한다. DogSpeak와 DigiDogs는 확인된 비상업 조건 때문에 상업 학습을 보류한다. 공개 링크나 저장소의 존재를 학습 허락으로 해석하지 않는다.')
 p.section('강형욱 출연 영상의 활용','실제 행동, 보호자의 설명, 전문가 해석과 개입 후 반응이 함께 있어 사례 자료로 유용하다. 원본 URL·회차·시간 구간·권한·검토자를 기록하고, 사례별 판단을 다른 개에 대한 확정 진단으로 일반화하지 않는다.')
 p.box('사례 카드에 담을 정보','출처와 시간 구간 / 행동 전 상황 / 직접 관찰 / 전문가 해석과 적용 조건 / 개입 절차 / 이후 반응과 관찰 기간 / 편집·더빙·가림 / 권한 및 검수 상태. 신규 사례 카드 확장 필드는 설계 단계다.')
 p.section('검색과 학습은 별도 경로','승인된 자료를 답변 근거로 검색하는 기능과 모델 가중치를 학습하는 기능은 구분한다. NotebookLM은 선택적 자료 정리 도구이며, 연결만으로 모델이 자동 학습되지는 않는다.')
 p.section('데이터 품질 관리','같은 개와 재편집 영상을 평가셋에서 분리한다. 해설·음악·효과음 오염을 기록한다. 자막 없이도 행동을 인식하는지 확인하고, 정상 행동·다양한 가정·여러 전문가 자료를 함께 평가한다.')
 p.new('ARCHITECTURE & GATES','시스템 구성과 출시 검증','폰의 입력 기능과 서버 분석을 결합하는 하이브리드 방식을 우선한다.')
 p.section('권장 시스템 구성','Flutter 앱에서 선택한 장면을 인증된 API로 전송한다. 비공개 저장소와 작업 큐를 통해 오디오·영상 모델을 호출하고, 검수된 근거를 검색해 결과를 구성한다. 결과·동의·모델 버전·삭제 이력을 관리한다. 이 운영 구성은 목표 설계다.')
 p.section('폰과 서버의 역할','초기 폰은 촬영·선택·전송·결과 표시를 담당한다. 서버는 모델 실행·권한·비용·버전을 통제한다. 폰의 경량 소리/움직임 감지와 양자화 모델은 실제 기기 성능을 확인한 뒤 도입한다. API 키는 앱에 넣지 않는다.')
 p.section('성능과 품질 검증','개체 분리 accuracy·macro F1·클래스별 recall, 시간당 오탐, 판단 보류 비율과 보류하지 않은 결과의 정확도를 보고한다. 확률 보정, 가림·잡음·비개체 오류, 전체 응답 지연·메모리·비용도 측정한다.')
 p.box('기존 설계의 제안 목표 · 달성 수치 아님','행동 macro F1 ≥ 0.80, 클래스별 recall ≥ 0.65, 선택적 정확도 ≥ 0.90, coverage ≥ 0.70, 업로드 후 응답 p95 ≤ 30초. 평가 계약에서 재검토할 제안값이며 현재 성능 주장이 아니다.')
 p.section('출시 전 필수 확인','실제 개 독립 평가, 데이터 삭제·동의 철회, 비용 한도, 운영 인증, 모델 버전 회귀·롤백, 실제 기기 흐름을 확인한다. 임계값은 validation에서 정하고 최종 test로 선택을 반복하지 않는다.')
 p.new('DELIVERY PLAN','진행 순서와 산출물','코드와 문서의 완료 상태를 함께 관리한다.')
 p.section('다음 진행 순서','① 권한 확인된 실제 개 데이터와 평가 계약 확보\n② AST 기준 성능 측정 및 Dog2vec/AVES 조건 검토\n③ 실제 자세 튜닝과 영상·음성 결합 비교\n④ 전문가 근거 검색 흐름 완성\n⑤ 인증·미디어 처리·Flutter 연결 후 제한된 사용자 검증')
 p.section('필요 역할과 비용 산정','개발, ML 평가, 개 행동 검수, 데이터 권리·운영 담당 역할이 필요하다. 한 사람이 여러 역할을 맡을 수 있다. 비용은 VLM 호출량·미디어 보관량·모델 실행 자원·검수 시간을 기준으로 측정한다. 현재 인력·사용량·단가가 정해지지 않아 예산과 출시일은 확정하지 않는다.')
 p.section('산출물과 인수 기준','소스와 테스트, 모델 버전·이용 조건 기록, 데이터 manifest, 독립 평가 보고서, 사례 검수 기록, API·앱 사용 흐름, 개인정보·운영 절차가 산출물이다. 수치가 없는 성능 주장과 문서만 있는 기능은 완료로 인정하지 않는다.')
 p.section('연결 자료','아래 링크에서 실제 코드와 실행 증거, 조사 자료를 확인할 수 있다.')
 for title,url in LINKS: p.link(title,url)
 p.section('문서 관리','이 기획서는 현재 범위의 요약 기준이다. 상세 진행은 tasks/todo.md, 구현 지시는 docs/WORK_ORDER.md, 아키텍처는 docs/DOG_MVP_ARCHITECTURE.md를 함께 관리한다. 브로셔에 적힌 목표 기능도 같은 검증 기준을 적용한다.')
 p.save('PetSense_AI_Project_Proposal.pdf')

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 brochure(); proposal()
 for path in OUT.glob('*.pdf'):
  doc=fitz.open(path)
  assert all(len(page.get_text().strip())>100 for page in doc)
  print(path.name, len(doc), 'pages', path.stat().st_size, 'bytes')
