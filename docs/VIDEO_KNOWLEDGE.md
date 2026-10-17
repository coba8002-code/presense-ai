# 영상 링크 자동 지식 갱신

YouTube 공식 검색 → 공개 영상 메타데이터 확인 → 채널별 이용 권한 확인 → Gemini URL 분석 → SQLite 출처 검색 → 선택적으로 NotebookLM Enterprise 소스 등록 순서로 실행한다. 국내외 검색어는 `config/knowledge.example.json`에 있다. 검색 결과는 전체 영상 목록을 보장하지 않는다.

이 기능은 모델 가중치 학습이 아니다. 관찰·발언·가설을 분리한 기계 추출 지식을 갱신한다. 검색은 제한된 로컬 키워드 검색이며, 임베딩 검색이나 검증된 행동 상담이 아니다. 영상 파일을 로컬에 내려받지는 않지만 외부 제공자가 영상을 처리한다. URL 사용만으로 상업적 분석·저장·학습 권한이 생기지 않는다.

## 실행

1. 예제 설정을 `config/knowledge.local.json`으로 복사한다.
2. 실제 권한을 확인한 채널 ID를 `policies`에 등록한다. 각 항목에 `analysis_allowed`, `knowledge_allowed`, `notebook_allowed`, 계약 등 실제 `evidence`, 만료 UTC Unix timestamp `expires_at`를 지정한다. 예제의 빈 정책은 모든 분석을 차단한다. 프로그램은 증빙의 법적 유효성을 자동 판정하지 않는다.
3. 비밀 관리 환경에서 `YOUTUBE_API_KEY`, `GEMINI_API_KEY`를 주입하고 `PETSENSE_ENABLE_KNOWLEDGE=true`로 활성화한다. 키를 Git이나 채팅에 넣지 않는다. `.env.example`은 안내이며 자동 로드되지 않는다.
4. 다음 명령을 실행한다.

```bash
python -m knowledge.worker --config config/knowledge.local.json --watch
```

`--watch`를 빼면 한 번 실행한다. 기본 주기는 1시간, 일일 외부 요청 상한은 20회다. 요청 수는 과금액 또는 YouTube quota unit과 같지 않다. 공급자 콘솔에서도 비용·쿼터 제한을 설정한다. 실패 요청도 예산에 포함된다. SQLite 잠금은 같은 DB를 쓰는 worker의 동시 실행을 막는다. 실행 중인 서버나 스케줄 서비스는 이 PR에서 배포하지 않는다.

기존 승인된 로컬 오디오 작업도 같은 주기로 처리하려면 `--audio-inbox data/autolearn/inbox`를 추가한다. 오디오 작업 형식과 학습 검증은 [AUTOLEARN.md](AUTOLEARN.md)를 따른다. 영상의 자동 추출 문장을 오디오 정답 라벨로 사용하지 않는다.

## 출처 검색

```bash
python -m knowledge.worker --config config/knowledge.local.json --query "강아지"
```

서버에서는 `PETSENSE_KNOWLEDGE_CONFIG`, `PETSENSE_KNOWLEDGE_DB`, `PETSENSE_API_TOKEN`을 설정하고 `GET /v1/knowledge/search?q=...`에 Bearer 인증을 보낸다. 이 요청은 외부 API를 호출하지 않는다. 최대 5개 결과에 원본 링크와 초 단위 위치, 추출 유형, 미검수 표시를 반환한다. 낮은 확신도·만료·권한 철회·오래된 메타데이터는 검색에서 제외한다. 확신도는 보정된 정확도가 아니다. 일치 결과가 없으면 답변을 유보한다.

## NotebookLM 연동 범위

개인용 NotebookLM 유료 구독만으로 이 API를 사용할 수 있는 것은 아니다. Google Cloud NotebookLM Enterprise 프로젝트·노트북·IAM 권한이 필요하다. 설정의 `notebook`에 `projects/PROJECT_NUMBER/locations/global/notebooks/NOTEBOOK_ID` 형태의 실제 리소스를 넣고 `notebook_endpoint`를 제공 지역에 맞춘다.

`GOOGLE_ACCESS_TOKEN_FILE` 또는 `GOOGLE_ACCESS_TOKEN`으로 OAuth 액세스 토큰을 공급한다. worker는 파일을 호출마다 다시 읽지만 토큰을 발급·갱신하지 않는다. 상시 실행에는 외부 인증 관리자가 토큰을 갱신해야 한다. 개인용 서비스 쿠키나 비공식 브라우저 자동화를 사용하지 않는다.

공식 Preview API로 YouTube 소스를 등록·삭제한다. 등록 성공은 NotebookLM의 소스 처리가 완료되었다는 뜻이 아니다. NotebookLM 답변 수집·자동 질의·답변을 통한 모델 재학습은 구현 범위에 없다. YouTube 소스 가져오기는 자막 중심이므로 영상 자세 분석은 별도 Gemini 경로가 담당한다.

등록 요청 결과가 불명확하면 `notebook_uncertain` 상태로 남기고 중복 등록하지 않는다. 관리자가 NotebookLM과 DB를 대조해야 한다. 권한 철회 또는 보존기간 만료 시 다음 worker 실행에서 등록 소스 삭제를 시도한다. 인증·예산 부족 시 삭제가 지연될 수 있다. 로컬 검색의 권한 차단은 설정 변경 즉시 적용된다. 메타데이터는 24시간마다 재확인하며 영상 편집 자체를 완벽히 감지하지 못한다.

## 검증 및 운영 전제

MockTransport와 가짜 제공자를 이용해 API 요청 형식, 중복 방지, 일일 상한, 삭제, 권한 철회, 인증, 응답 크기·리다이렉트 차단을 검증한다. 실제 영상 API 호출과 실제 Enterprise 소스 처리는 자격 증명과 권한 있는 소스가 준비된 후 별도로 검증해야 한다. 현재 통합은 실사용 검증 전이다.

- [Gemini 영상 URL 분석](https://ai.google.dev/gemini-api/docs/generate-content/video-understanding)
- [NotebookLM Enterprise 소스 API](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources)
- [YouTube 검색 API](https://developers.google.com/youtube/v3/docs/search/list)
