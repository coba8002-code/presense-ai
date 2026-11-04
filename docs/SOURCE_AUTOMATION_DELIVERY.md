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

## 후속 실행: 지정 링크 분석과 검수 패키지

같은 날 추가 요청에 따라 EBS 교양의 공개 검색 결과 2건을 더해 후보를 총 4건으로 확장했다. 원본 화면·소리·자막은 보지 못했으며 검색 제목을 행동 정답으로 사용하지 않았다. 새 `config/knowledge-targeted.example.json`은 해당 ID를 고정하고 `targeted_only=true`로 검색 및 다른 저장 영상의 신규 처리를 제한한다. 기존 Notebook 자료의 철회/만료 정리는 계속 적용한다. 채널 정책은 비어 있고 권한을 부여하지 않는다.

- [EBS 후보 1](https://www.youtube.com/watch?v=NpQgmiT1c0Y)
- [EBS 후보 2](https://www.youtube.com/watch?v=xEAX6ixFmyc)
- 해외 교정 지식의 출처 검토 대상으로 [Dogs Trust 행동 관찰 자료](https://www.dogstrust.org.uk/dog-advice/understanding-your-dog/body-language)와 [RSPCA 짖음 안내](https://www.rspca.org.uk/adviceandwelfare/pets/dogs/behaviour/barking)를 확인했다. 링크 참고 자료이며 영상/글을 모델 가중치 학습 데이터로 편입하지 않았다.

새 워커는 현재 유효한 research_links를 공식 메타데이터 검증 대상 ID에 연결한다. 색인 링크만으로 채널·공개 여부·길이·분석 이용권을 확정하지 않는다. 기존 일일 한도·권한/만료·종/시간·모델 검사와 독립 검수 요구를 그대로 거친다. API 설정이 없는 상태에서 공식 워커를 실제 실행했으며, 외부 호출 전에 인증 구성 검사에서 중단됐다. 실제 영상 분석 및 YouTube 가중치 학습은 **0건**이다. 과거 합성 큐 결과를 이번 실제 학습으로 재사용하지 않는다.

```sh
python -m knowledge.worker --config config/knowledge-targeted.example.json --db data/source-discovery/knowledge.sqlite3
python -m knowledge.source_progress --db data/source-discovery/knowledge.sqlite3 --config config/knowledge-targeted.example.json --output artifacts/youtube-review-packet.json
```

두 번째 명령은 네트워크·미디어 접근 없이 검수 패키지를 생성한다. 출력 파일은 새 파일만 허용하고 처음부터 0600으로 생성한다. 실제 로컬 4후보로 실행한 결과는 sources=4, proposals=0, training_ready=false였다. 관찰 시각·검수자·라벨·개체·촬영 그룹을 자동 작성하지 않는다. 실제 승인된 분석이 있을 때만 유효한 관찰 제안을 제시하며, 승인/학습을 대신하지 않는다. 독립 검수 시에는 관찰과 강사 주장 분리, 영상 편집/배경음/더빙, 발성 개체 확인, 전후 맥락, 교정 전후의 다른 조건, 숨겨진 통증·환경 요인을 확인해야 한다.

`/app`은 ‘분석 미실행’ 고정 표시를 제거하고 현재 정책에 따른 메타데이터 미확인·이용 범위 확인·분석 대기·모델 변경·기한 만료·AI 관찰 추출/독립 검수 전을 구분한다. 분석 내용이나 정책 증거는 이 상태 API로 보내지 않는다. `PETSENSE_KNOWLEDGE_CONFIG`에 운영 설정 경로가 연결되지 않으면 승인된 분석으로 표시하지 않는다. 분석 건수와 검수 제안 수는 학습 완료/정확도를 뜻하지 않는다.

검증은 지정 ID 전달/다른 영상 제외/권한 미승격, 현재 정책 철회·분석 기한/모델/무결성, 제안의 미검토 상태, 브라우저의 새 상태 표시·이용 조건 철회 반영을 포함한다. provider-shaped 자료는 합성 테스트이며 실제 YouTube 분석으로 주장하지 않는다. 실제 외부 분석·검수·학습·국내 PC 설치는 앞의 입력/운영 의존성이 여전히 남아 있다.
