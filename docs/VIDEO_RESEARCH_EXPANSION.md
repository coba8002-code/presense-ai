# 국내외 개 행동·발성 영상 조사 확장

2026-10-30 KST. 이번 변경은 검색 계획·순환 탐색·사례 후보 처리 코드다. 새 YouTube 영상을 시청/분석하거나 모델을 추가 학습한 결과는 아니다.

## 검색 범위
config/dog-video-sources.json의12개 검색 대상명에 행동·발성 검색어24개를 정의했다. 대상명은 검색의 출발점이며 공식 채널 확인·콘텐츠 품질 보증·이용 허락을 뜻하지 않는다. 채널 ID를 추측해서 승인하지 않았다.

|지역|검색 대상명|
|---|---|
|국내|강형욱·보듬TV, EBS 세상에 나쁜 개는 없다, KBS 개는 훌륭하다, 설채현 관련 개 행동 교육|
|해외|Kikopup, Dogs Trust, RSPCA, Battersea, Victoria Stilwell Positively, Karen Pryor Clicker Training, Fear Free Happy Homes, Zak George Dog Training|

발성: 짖음·낑낑거림·하울링·으르렁거림. 행동/맥락: 몸짓·산책/목줄·분리 상황·거리 변화. 검색어에 ‘분리불안’이 포함돼도 검색 결과를 확정 진단 정답으로 라벨링하지 않는다. 특정 프로그램이나 심각한 문제 행동에만 편중하지 않도록 정상 행동과 가정 관찰 자료를 별도 확보해야 한다.

## 실제 접속·문헌 조사 결과
현재 실행 환경의 기본 네트워크 연결은 Operation not permitted였고, 해당 명령에 네트워크 권한을 추가한 YouTube 공개 검색도 Tunnel connection failed:403 Forbidden으로 실패했다. 브라우저 도구와 YOUTUBE_API_KEY/GEMINI_API_KEY는 연결되지 않았다. 제한을 다른 중계 사이트나 다운로드 도구로 우회하지 않았다. 따라서 새로 확인한 영상 ID·제목·시간 구간·행동 라벨은0개다.

GitHub 검색에서는 DogSpeak 공식 README를 다시 확인했다: https://github.com/Lekhak123/DogSpeak-A-Canine-Vocalization-Classification-Dataset . 온라인 영상에서 추출한77,202개 발성 시퀀스·156마리와 개체 ID를 제공하지만 CC BY-NC-SA4.0이다. 현재 상업 서비스 학습용으로 새 승인하지 않았다. dog_7a/dog_7b는 동일 dog_7의 디렉터리 분할이며 다른 개로 분리하면 안 된다. CATVD와 개체가 겹칠 수 있다는 원문 경고도 유지한다. 논문·데이터 카드의 재확인이며 파일 수령/학습은 아니다. 검색에서 나온 무관한 로봇 저장소와 README404 후보는 적용하지 않았다.

## 적용한 기능
1. `python -m knowledge.research_plan --output-dir artifacts/research-new`로 국내/해외 검색 계획과 최대4검색어씩6개 설정을 만든다. 기본 카탈로그 기준12대상/24검색어다. 출력에는 검색 URL만 있으며 발견한 영상처럼 표시하지 않는다. 기존 디렉터리를 덮어쓰지 않고 정책은 비워 두며 Notebook은 끈다.
2. 기존 공식 YouTube Data API 탐색기에 `--research-catalog`를 연결했다. `--discover-only`에서만 허용하고 SQLite에 배치 순서를 저장한다. 같은 DB의 일일 요청 한도를 공유하며 할당량이 없어 실제 요청을 못 한 배치는 건너뛰지 않는다. 기존 운영자의 명시적 정책/모델/예산을 보존한다. 여러 watcher의 중복 실행은 권장하지 않으며 기존 cycle lock을 따른다.
3. `--case-cards`로 기존 허용된 분석 DB에서 시간/출처가 연결된 사례 후보를 내보낸다. observation/speaker_statement/hypothesis를 별도 배열로 보존한다. 발언자를 자동으로 강형욱/전문가라고 확정하지 않는다. 교정 효과·후속 결과·개체 ID·음악/더빙 여부는 확인 전 null/unknown이다.
4. 정책 철회·만료·낡은/미래 메타데이터·다른 모델·비개·유효 관찰 구간 없음은 카드에서 제외한다. 사례 ID는 분석/메타데이터 지문에 묶인다. 모든 카드는 ground_truth=false, training_ready=false다. 독립 검수와 허용된 원본 연결 없이 기존 학습 큐에 자동 승격하지 않는다.
5. 후보 상태의 expert_review_required를 independent_review_required로 조정했다. 일반 관찰 검수를 활용할 수 있으며 전문가는 기준·불일치·표본에 집중한다.

## 실제 실행 경로
YouTube 접근과 공식 API 키가 설정된 환경에서 프로젝트 루트 기준으로 실행한다. 키는 환경의 비밀 저장소에 설정하며 채팅·GitHub·명령 인자에 적지 않는다. 이 문서 작성만으로 호출을 시작하지 않는다. knowledge.pipeline은 fcntl을 사용하므로 현재 watcher는 Linux/WSL 환경을 기준으로 한다. Windows native 실행 완료를 주장하지 않는다.

```
python -m knowledge.worker --config config/knowledge.example.json \
  --db data/knowledge.sqlite3 --discover-only \
  --research-catalog config/dog-video-sources.json --watch
```
PETSENSE_ENABLE_KNOWLEDGE=true와 YOUTUBE_API_KEY가 필요하다. 위 명령은 Gemini/Notebook 호출이나 영상 다운로드·가중치 학습을 하지 않는다. 실제 메타데이터를 받아 공식 채널·영상별 이용조건을 검토한 다음, 허용 범위의 지식 분석을 별도 활성화한다. 공개 라이선스/정당한 이용 근거로 가능한 범위와 별도 허락이 필요한 범위를 구분하고 확인 근거를 남긴다. 소유자의 프로젝트 상업 학습 승인은 제3자 원본의 이용권한과 다르다.

기존 분석 DB의 사례 후보는 네트워크 호출 없이 확인한다.
```
python -m knowledge.worker --config config/knowledge.example.json \
  --db data/knowledge.sqlite3 --case-cards
```
실제 허용 정책이 들어 있는 운영자 로컬 설정을 사용해야 한다. 예제의 빈 policies에서는 사례를 내보내지 않는다. 후보를 승인 데이터라고 자동 표시하지 않는다.

## 학습으로 넘어가는 조건
영상 링크의 지식 검색과 모델 가중치 학습은 다른 단계다. 짧은 출처 기반 설명을 RAG에 쓰는 범위, 원본/자막을 복제하는 범위, 모델 학습용 원본을 수집하는 범위의 권한과 플랫폼 이용조건을 각각 확인한다. 강의 해설·배경음·자막이 섞인 자료를 자연 개 발성 정답으로 쓰지 않는다. 영상/소리/자막을 분리하고 재편집·동일 개체·가정·회차를 같은 split에 묶는다.
기존 training.video_review→training.video_media→독립 평가 계약을 통과한 실제 자료부터 후보 실험에 쓴다. 방송 해설과 AI가 만든 라벨만으로 모델 정확도/교정 효과를 주장하지 않는다. 범용 행동 분석이나 ‘개의 언어 번역’ 완성을 이번 검색 설정의 결과로 표현하지 않는다.
