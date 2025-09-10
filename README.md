## KT Track2 프롬프트 엔지니어링 운영 저장소

### 목적
- 데이콘 Track2: 프롬프트 엔지니어링 대회(예선 2025-08-25 ~ 2025-09-10) 대응을 위한 운영 저장소입니다.
- GPT‑4o 기반 Custom 모델(beta)에 적용할 시스템 프롬프트를 설계·개선하고, 매일 최대 3회 제출 사이클을 안정적으로 운용합니다.
- 대회 안내: [대회 페이지](https://dacon.io/competitions/official/236552/overview/description)

### 핵심 규칙 요약
- 출력 형식: `번호. 유형,극성,시제,확실` (쉼표만, 공백/추가 텍스트 금지)
- 라벨 셋: 유형(사실형/추론형/대화형/예측형), 극성(긍정/부정/미정), 시제(과거/현재/미래), 확실성(확실/불확실)
- 시스템 프롬프트는 한국어 위주로 작성(한글 비율·길이 가점), 최대 3000자
- 외부 데이터 사용 금지(대회 제공 데이터만 활용)

### 저장소 구조
```
.
├─ prompts/
│  ├─ system_v1_ko.txt            # 기준 시스템 프롬프트
│  ├─ system_v1_variants/         # A/B/C 변형 프롬프트
│  └─ final/                      # 최종 산출물(최고/차선)
├─ outputs/                        # 제출 직전 결과물(원본 보존)
├─ tools/
│  ├─ validate_outputs.py         # 로컬 형식 검증기
│  └─ offline_eval.py             # 규칙 기반 오프라인 추정(참고용)
└─ experiments/
   ├─ experiments.csv             # 제출 로그(점수/길이/한글비율 등)
   └─ notes.md                    # 관찰/가설/교훈 노트
```

### 사용 방법
1) 시스템 프롬프트 등록: `prompts/system_v1_ko.txt` 내용을 커스텀 모델의 시스템 프롬프트로 설정
2) 출력 생성: 대회 플랫폼에서 유저 프롬프트 실행 → 결과를 `outputs/YYYYMMDD_HHMM_run.txt`로 저장
3) 형식 검증:
```
python tools/validate_outputs.py outputs/YYYYMMDD_HHMM_run.txt
```
4) 제출 및 기록: 검증 통과 후 제출 → `experiments/experiments.csv`에 결과(점수/길이/한글비율/변경점) 기록

### 운영 원칙(A/B 실험)
- 하루 3회 제출: 오전 안정판 1회, 오후 A/B 2회
- 한 번에 하나의 가설만 변경(우선순위/트리거/기본값 중 택1) → 승자만 다음날 승격
- 형식 파손 0%를 최우선. 필요 시 검증기/프롬프트의 형식 강제 규칙 강화

### 데이터 안내
- `data/samples.csv`: 예시 16,541개 (문장·라벨)
- `data/datainfo.txt`: 데이터 설명

### 참고 파일
- `PLAN.md`: 일일 운영 계획과 실험 전략
- `개요.md`, `규칙.md`, `평가.md`: 대회 공식 요약 정리

### 라이선스
- 개인 사용 목적의 대회 운영 저장소입니다. 대회 규칙에 따라 외부 공유/재배포는 제한될 수 있습니다.

### 최종 산출물/요약/태그
- 최종 요약: `FINAL_SUMMARY.md`
- 아카이브: `ARCHIVE.md` (최고점 `prompts/final/FINAL_28C.txt`, 차선 `prompts/final/FINAL_06C.txt`)
- 최종 태그: `final-20250910`


