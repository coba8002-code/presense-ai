# 승인된 자료의 자동학습

> 현재 제품 범위: **개 전용 MVP**. 고양이 학습·분석은 후속 단계로 보류합니다.

## 구현 범위

`python -m training.autolearn`은 운영자가 등록한 로컬 오디오 작업을 주기적으로
검사하고, 새 입력이면 학습·평가·기존 모델 비교·후보 아티팩트 저장을 수행한다.
현재 학습기는 NumPy spectral softmax이며 PyTorch 사전학습 모델이나 영상 VLM의
자동 fine-tuning이 아니다. 유튜브 다운로드/자막 추출/권리 자동 승인도 수행하지 않는다.

등록된 manifest가 변경되면 다음 주기에 다시 학습한다. 새 WAV를 디렉터리에
넣는 것만으로는 등록되지 않는다. 사람의 라벨 검수와 manifest 등록이 필요하다.
현재 서버의 실시간 녹음은 저장하지 않으며 자동으로 학습에 사용하지 않는다.

## 바로 실행하는 합성 데모

저장소 루트에서 의존성 설치 후 실행한다. 최초 명령의 출력 디렉터리는 새 경로여야 한다.

```sh
python scripts/autolearn_demo.py --output data/autolearn-demo
python -m training.autolearn --inbox data/autolearn-demo/inbox --output artifacts/autolearn-demo
```

반복 실행은 같은 입력의 기존 결과를 반환한다. 지속 감시는 아래 명령으로 시작한다.
Ctrl+C로 종료하며, 서버 재부팅 후에는 명령을 다시 실행하거나 별도 서비스 관리자를 사용한다.
이번 개발 세션에서는 상시 프로세스를 설치하거나 실행해 두지 않았다.

```sh
python -m training.autolearn --inbox data/autolearn-demo/inbox --output artifacts/autolearn-demo --watch --interval 300
```

Linux/POSIX용이며 `fcntl`을 사용한다. 운영 배치에서는 supervisor/systemd 또는 cron으로
단일 실행을 예약할 수 있다. 원격 GPU나 API 키 없이 로컬 CPU에서 실행한다.

## 실제 자료 작업 계약

inbox 안의 JSON은 운영자만 수정할 수 있어야 한다. 공개 업로드 API가 아니다.
경로는 해당 작업 JSON 디렉터리 기준이며 로컬 절대 경로도 허용한다.
URL/임의 명령/미정의 필드는 거부한다. 입력과 결과 저장소에는 접근 제어를 적용한다.

```json
{
  "version": 1,
  "species": "dog",
  "manifest": "../approved/train/manifest.json",
  "benchmark": "../approved/benchmark/manifest.json",
  "registry": "../approved/registry.json",
  "limits": {
    "min_macro_f1": 0.8,
    "min_coverage": 0.5,
    "max_ece": 0.15,
    "min_improvement": 0.01
  }
}
```

기존 모델이 있으면 `incumbent`에 자동학습 결과의 `model.json` 경로를 추가한다.
이전 수동 학습 모델은 전체 학습 개체/촬영 세션/해시 lineage가 없으므로 비교가 거부된다.
증거 없이 lineage를 채우지 말고 자동학습 경로로 기준선을 다시 생성한다.

manifest의 기존 `path`, `animal_id`, `species`, `label`, `dataset`에
`recording_group`(전역적으로 일관된 촬영 세션/원본 영상 ID)을 추가한다.
같은 개체나 같은 원본 영상의 다른 클립을 서로 다른 ID로 만들면 안 된다.
평가 자료는 학습 manifest 전체와 개체·촬영 세션·SHA256이 겹치지 않아야 한다.
학습 내부 train/validation/test 사이에서도 같은 촬영 세션을 허용하지 않는다.

데이터 registry에는 기존 승인 필드와 함께 다음 두 필드가 필수다.

- `acquisition_evidence`: 원본 파일 제공 계약 또는 합법적인 취득 경로의 증빙 위치.
- `label_review`: 누가 어떤 라벨과 장면 정합성을 검수했는지 확인할 수 있는 기록 위치.

문자열의 존재를 검사하는 기능이며 법적 권한이나 전문가 자격을 자동으로 판정하지 않는다.
오디오 규격은 기존 학습기와 동일한 16 kHz PCM WAV다. 데이터셋별 상업 이용/학습 승인과
권리·동의·버전 기록이 필요하다. 합성 표시는 하나라도 있으면 실데이터 후보가 되지 않는다.

## 처리와 결과

1. 매 주기 권한을 재검사한다. 이전에 학습했어도 권한이 철회되면 차단한다.
2. 개체/세션/파일 중복과 클래스 범위를 확인한다. 별도 평가 자료에 최소 5개체가 필요하다.
3. 작업 내용·데이터 해시·권한·학습 코드 해시·NumPy 버전·기존 모델로 실행 ID를 만든다.
4. 출력 디렉터리 단위 잠금으로 중복 작업을 막는다. 입력을 임시 복사하고 해시를 확인한다.
5. 모델을 학습하고 후보와 기존 모델을 **동일한 별도 평가 자료·동일 임계값**으로 평가한다.
6. 완료 직전 원본/권한 변경을 다시 검사하고 결과 디렉터리를 원자적으로 게시한다.
7. 임시 오디오는 정상 종료/예외 시 제거한다. SIGKILL/전원 장애 뒤 `.pending-*` 잔여물은
   프로세스가 종료됐는지 확인한 뒤 운영자가 삭제한다. 남은 임시 결과를 후보로 읽지 않는다.

`artifacts/<output>/<run_id>/`에 model.json, metrics.json, splits.json,
provenance.json, result.json을 저장한다. 원본 오디오는 결과에 보관하지 않는다.
원본 경로/개체/권리 기록은 포함되므로 결과도 비공개 데이터로 관리한다.
기존 `evaluation.evaluate` 명령으로 내부 holdout 결과를 재현할 수 있다.

| decision | 의미 |
|---|---|
| synthetic_only | 합성 자료 포함. 동물 행동 성능/운영 후보로 사용 금지 |
| rejected | 절대 기준 미달 또는 기존 모델 대비 개선/비퇴행 조건 미달 |
| review_required | 기준을 충족했지만 비교할 기존 모델이 없음 |
| candidate | 기준과 기존 모델 비교 통과. 운영 배포 완료를 뜻하지 않음 |

기본 기준은 예제값이며 제품 성능 목표의 검증 결과가 아니다. 후보가 되려면 macro F1이
설정된 폭 이상 개선되고, coverage/각 클래스 F1이 낮아지지 않고 ECE가 증가하지 않아야 한다.
추가 지표로 accuracy, confusion matrix, Brier score, selective accuracy를 기록한다.
반복 사용하는 benchmark는 모델 선택용 acceptance set이며 독립적인 최종 시험 성적으로
보고하지 않는다. 출시 전 별도의 잠긴 실환경 시험 자료와 실제 기기 지연 검증이 필요하다.

자동 배포/활성 모델 변경은 없다. 검토 후 기존 서버 설정에서 승인된 모델 경로를 선택하며,
이전 모델 경로를 유지하면 되돌릴 수 있다. 권한 철회가 과거 모델 파일을 자동 삭제하거나
이미 학습된 영향을 제거하지는 않는다. 데이터/모델 삭제 및 재학습은 별도 운영 절차다.

## 실패·제한

- 작업당 manifest 최대 2,000개 레코드, 학습+평가 원본 합계 최대 256 MiB.
- inbox 최대 20개 작업. 초과 시 조용히 누락하지 않고 오류로 중단한다.
- 최소 감시 간격 60초. 정상 작업은 입력이 같으면 재학습하지 않는다.
- 실패한 작업은 stdout에 `blocked` 사유를 남기고 다음 작업을 처리한다.
  단일 실행에 실패가 있으면 종료 코드 2, 감시 모드에서는 다음 주기에 재시도한다.
- OS CPU/메모리/디스크 quota 및 실행 시간 제한은 운영 서비스에서 적용해야 한다.
- 자동 증분 fine-tuning이 아닌 전체 승인 manifest 재학습이다. 증분 자료만으로
  manifest를 교체하면 과거 행동을 잊을 수 있으므로 승인된 누적 자료를 구성한다.

## 유튜브/방송 연계의 다음 단계

[YouTube 학습 허용 상태 API](https://developers.google.com/youtube/data/video-trainability)는
권한 확인의 보조 근거로 활용할 수 있다. 학습 허용은 해당 회사와 영상의 조건을 확인해야 하며,
영상 취득 권한이나 개인정보 동의를 자동으로 대체하지 않는다. 이번 코드에는 API 호출이나
영상 자동 수집이 없다. 권리자가 제공한 파일 → 음성/영상 시간 정렬 → 전문가 라벨 검수 →
승인 registry/manifest 등록까지의 intake가 먼저 필요하다. 영상 모델 및 지식 검색 자동 갱신은 후속이다.

## 검증 기록

2026-10-17: 신규 자동학습 테스트 12개 포함 전체 Python 테스트 56개 통과.
실제 CLI로 합성 fixture 생성 → 학습 → 별도 평가 → synthetic_only 저장을 실행했다.
평가 fixture에 음량 변화를 넣었을 때 macro F1은 약 0.333으로 낮았다.
이는 기존 단순 모델의 분포 변화 취약성을 보여주는 합성 점검이며 동물 성능이 아니다.
실제 반려동물 학습·YouTube 수집·상시 운영 서비스·배포는 실행하지 않았다.
