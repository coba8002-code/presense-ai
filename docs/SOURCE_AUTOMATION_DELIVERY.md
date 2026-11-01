# 영상 자료 자동화 실행·전달 기록

2026-11-01. 개 전용. 검색 후보, 내용 분석, 독립 검수, 학습을 구분한다.

## 이번에 실제 실행한 범위

- 공개 웹 검색에서 Kikopup 영상 `qPpEpQXTQb4`와 보듬 관련 색인 영상 `7XmubBOQIeA`의 제목/링크 2건을 찾아 로컬 DB에 등록했다. `config/dog-video-index-candidates.json`은 재현용 검색 메타데이터이며 전문 지식·정답·이용권을 부여하지 않는다. 보듬 후보의 근거는 외부 검색 색인이고 공식 소유권을 확인하지 못했다.
- 공식 oEmbed와 YouTube 채널 피드 접근은 이 실행 환경에서 실패했다. 우회 접속·자막/영상 다운로드를 하지 않았다. 피드 테스트는 MockTransport XML을 사용했으며 실제 채널 인증/가동 증거가 아니다.
- 키 없이 실행되는 메타데이터 워커에 간격/일일 한도/중복 방지/조건부 요청/기한 만료를 추가했다. 공식 피드의 채널 ID 일치도 콘텐츠 권리나 전문가 자격을 검증하지 않는다.
- 실제 임시 계정 → `/app` → `/v1/me/research-status` → 읽기 전용 SQLite 조회를 데스크톱/모바일 Chromium 에뮬레이션에서 확인했다. 로그인 전 차단, 세션 변경 시 목록 삭제, 악성 제목의 텍스트 표시, 외부 요청 없음도 검사했다. 실제 휴대폰 검증은 아니다.
- 새 워커에서 기존 로컬 오디오 학습 큐를 실제 실행했고 `synthetic_only` 결과를 받았다. NumPy 기준 모델의 합성 배관 검증이다. YouTube 기반 학습, AST/VLM 추가 학습, 실제 행동 정확도 향상을 뜻하지 않는다. 기존 학습기의 권리/검수/개체·원본 분리/승격 제한을 유지한다.
- Gemini 링크 분석과 Notebook Enterprise 동기화는 실행하지 않았다. 현재 이 환경의 관련 자격증명은 연결되지 않았다. 소비자용 NotebookLM 웹 로그인 자동화가 아니다.

## Linux/WSL에서 재현

저장소 루트에서 기존 가상 환경과 의존성을 사용한다. 아래 명령은 공개 후보 메타데이터만 등록하며 기본 설정의 채널 목록은 비어 있다.

```sh
python -m knowledge.source_automation --config config/source-automation.example.json --db data/source-discovery/knowledge.sqlite3 --seed config/dog-video-index-candidates.json
python -m knowledge.source_automation --config config/source-automation.example.json --db data/source-discovery/knowledge.sqlite3 --status
```

공식 출처를 확인한 뒤 운영자 전용 설정의 `channels`에 canonical `UC` 채널 ID를 넣는다. `--watch`는 설정을 다시 읽으며 DB에 기록한 실행 간격을 지킨다. 피드의 304 응답은 기존 자료의 메타데이터 확인 기한만 연장한다. 메타데이터가 만료/삭제됐다면 조건부 캐시 없이 전체 피드를 다시 요청한다. 실패 요청도 일일 한도에 포함한다. 피드 크기 256KB, 채널 20개, 결과 100개 상한이며 리다이렉트/DTD/외부 엔티티를 허용하지 않는다.

`deploy/petsense-source-discovery.service`는 설치되지 않은 운영 템플릿이다. 국내 PC에 배포/서비스 설치를 했다고 주장하지 않는다. 계정 API 실행 환경의 `PETSENSE_KNOWLEDGE_DB`를 같은 DB의 절대 경로로 연결하면 로그인 후 `/app`의 ‘자료 수집·분석 상태’에서 볼 수 있다. API는 DB가 없으면 생성하지 않고 오류를 표시하며 외부 모델 호출/학습 실행/권리 변경을 하지 않는다. 마지막 실행 기록은 프로세스 생존 확인이 아니다. 원본·키·정책 증거·로컬 작업 이름은 화면에 노출하지 않는다.

## 실제 분석·학습에 남은 입력

1. 공식 YouTube API/Gemini의 안전한 실행 환경 연결과 별도 분석 비용 범위. 채팅에 키를 보내지 않는다. `PETSENSE_ENABLE_KNOWLEDGE=true`와 운영 설정을 사용하며 기본 정책은 전부 비허용이다.
2. 채널별 유효한 `analysis_allowed`/`knowledge_allowed` 정책과 근거·만료. `enable_link_analysis`와 `paid_link_analysis_approved`는 운영자가 실제 승인 범위에 맞춰 명시한다. 토글 자체는 법적 이용권 증거가 아니다. 검색 후보만으로 자동 승인하지 않는다. 기존 knowledge 파이프라인은 자체 공식 검색/메타데이터 검증을 거친다. 색인 후보를 승인된 videos 테이블로 자동 승격하지 않는다.
3. Notebook이 필요한 경우 별도의 Enterprise 프로젝트/노트북/안전한 인증 및 동기화 권한. 선택 사항이며 분석의 선행 조건이 아니다.
4. 가중치 학습에는 별도의 학습 이용권, 허용된 로컬 원본, 개체/가정/원본 식별자, 검토된 정답과 잠금 평가셋이 필요하다. 링크/강사의 해석/보호자 피드백만으로 정답을 생성하지 않는다. `enable_local_training`은 기존 검수된 오디오 작업만 소비하며 모델 자동 배포를 하지 않는다.

지속 작업은 이 클라우드 세션에서 운영 서비스로 설치되지 않았다. 실제 국내 PC 파일/프로세스와 사용자 휴대폰에는 현재 접근하지 못했다. AX 로그인은 필요하지 않다. 실행 코드/원격 CI의 최종 상태는 해당 PR의 HEAD 검사 기록을 참조한다.
