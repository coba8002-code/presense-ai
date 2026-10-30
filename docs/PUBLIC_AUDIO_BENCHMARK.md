# 공개 개 소리 기준 평가

이 실험은 ESC-10의 dog40개와 다른9개 소리 범주360개를 구별하는 점수의 순위를 측정한다. 감정/의도/교정/질병 정확도나 새로운 개체에 대한 일반화 평가가 아니다. 실제 결과는 CI artifact의 esc10-report.json에서 확인하며 이 문서에 실행 전 수치를 넣지 않는다.

## 재현 순서
```
python -m scripts.acquire_esc10 --output data/esc10
python local_pc/pc.py prepare-esc10 --input data/esc10 --output data/esc10-16k
python local_pc/pc.py score-esc10 --input data/esc10-16k --output artifacts/esc10-scores --limit 0
python -m evaluation.sound_benchmark --input artifacts/esc10-scores --output artifacts/esc10-report.json
```
공개 소스는 karolpiczak/ESC-50의 revision33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6. 전체 ESC-50의 비상업 조건과 구별하여 CC BY3.0인 ESC-10 부분집합만 받는다. 공식 README와 파일별 출처 LICENSE를 함께 보존한다. scripts/acquire_esc10.py는400개/개40개·PCM형식·길이를 확인하고 입력 SHA256과 source URL을 남긴다. 이 해시는 보존 지문이며 제공자 체크섬 대조를 대신하지 않는다.

## 모델과 지표
AST MIT/ast-finetuned-audioset-10-10-0.4593의 고정 revision과 safetensors를 사용한다. 44.1kHz→16kHz 변환 이력과 입력 해시를 연결하고 7개 원본 dog 사건 점수의 최댓값을 미리 정한 dog-score로 사용한다. 추가 학습이나 임계값 탐색은 없다. 모든 모델 판정은 abstain을 유지한다.
AUROC는 양성 점수가 음성보다 높을 순위 확률이며 동점은0.5로 계산한다. Average Precision은 점수가 같은 항목을 하나의 임계점으로 처리한다. 두 지표 모두 실제 사용 임계값의 precision/recall, 시간당 오탐 또는 사용자의 체감 정확도를 확정하지 않는다.

## 실패 조건
불완전한400개 출력, dog 개수 불일치, 중복 입력 바이트/경로, 다른 모델/revision, 입력 해시 불일치, 보류가 아닌 판정, 누락된7개 사건 라벨, 비정상 점수는 결과 생성을 거절한다. 샘플별 파일을 읽어 실제 추론 결과가 존재하는지 확인하므로 성공 메시지만으로 평가 완료하지 않는다.

## 제한과 후속
개체 ID가 없고 공개 클립의 사전학습 중복도 배제하지 못한다. 따라서 이 실험을 최종 독립 평가셋으로 삼지 않는다. 개체/가정/세션이 검수된 별도 자료에서 학습·검증·테스트를 나누고 배경 TV·사람 말·생활 잡음·품종/나이/거리별 오탐을 확인해야 한다. 영상/음성 융합과 행동 가설은 별도 문제다.

공식 출처 https://github.com/karolpiczak/ESC-50#license
모델 배포 https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593
