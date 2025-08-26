#!/usr/bin/env python3
"""
오프라인 규칙 기반 평가기

samples.csv(user_prompt, output)을 읽어, 휴리스틱 분류기로 4개 속성(유형/극성/시제/확실성)을 예측하고
각 속성 정확도 및 평균 정확도를 출력합니다.

사용법 예시:
  python tools/offline_eval.py --variant 26_B --limit 2000
  python tools/offline_eval.py --variant 26_C
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


LABEL_TYPES = ("사실형", "추론형", "대화형", "예측형")
LABEL_POLARITY = ("긍정", "부정", "미정")
LABEL_TENSE = ("과거", "현재", "미래")
LABEL_CERTAINTY = ("확실", "불확실")


# 공통 트리거 사전
CONV_KEYWORDS = [
    "말했다", "물었다", "대답했다", "요청한다", "안내한다", "문의", "답변",
    "회의", "회의에서", "발언했다", "라고 했다",
]

PRED_KEYWORDS_BASE = [
    "예정", "계획", "전망", "목표", "추진", "의도", "검토", "가능성", "예상", "추정",
    "시사", "논의", "협의", "제안", "희망", "될 수 있다", "할 수 있다", "보인다", "듯하다",
]

INFER_KEYWORDS = [
    "때문", "따라", "해석하면", "의미한다", "만약", "이라면", "시사한다", "암시한다",
    "분석", "평가", "정황", "근거", "으로 보인다",
]

FACT_REPORT_KEYWORDS = [
    "밝혔다", "발표했다", "전했다", "판결했다", "확인했다", "공시했다", "발표문", "보도자료", "판결문",
]

TIME_EXPRESSIONS = [
    "내일", "모레", "이번 주", "다음 주", "내달", "다음 달", "내년", "후년", "203", "202", "9월", "10월",
    "하반기", "상반기", "1분기", "2분기", "3분기", "4분기", "연말", "월요일", "화요일", "수요일", "목요일",
    "금요일", "토요일", "일요일", "까지", "부터", "이후", "이내", "이상", "이하",
]

PAST_MARKERS = [
    "했다", "였다", "이었다", "발표했다", "판결했다", "발생했다", "재계약했다", "체결했다", "선정됐다",
    "지난", "앞서", "전날", "어제", "작년", "지난해",
]

PRESENT_MARKERS = [
    "현재", "지금", "이다", "있다", "한다", "중이다", "중", "상태다",
]

FUTURE_MARKERS = [
    "겠다", "할 것이다", "앞두고 있다", "앞둘 것이다", "될 것이다", "예정", "전망", "추진",
]

NEG_WORDS = [
    "감소", "적자", "손실", "하락", "위기", "경고", "논란", "비판", "징계", "실패", "파산",
    "취소", "불승인", "연기", "지연", "부족", "부정적", "악화", "역성장", "적색", "경보",
    "하한", "제재", "벌금", "구금", "문제", "위험",
]

NEG_MORPH = [
    "않", "못", "없", "무", "비", "불", "미", "지 못", "어렵다", "힘들다", "부족하다",
    "취소됐다", "파기됐다", "무산됐다", "철회했다",
]

POS_WORDS = [
    "증가", "호조", "개선", "성장", "확대", "수주", "달성", "수익", "이익", "승인", "합격", "수상",
    "반등", "상향", "회복", "개최", "체결", "확정", "상승",
]

MITIGATION_WORDS = [
    "둔화", "완화", "회복", "반등", "상향", "상승 전환", "감소 폭 축소", "적자 축소", "손실 축소",
    "개선 조짐", "안정세", "진정세", "완화세", "회복세", "반등세", "상향 조정",
]

UNCERTAIN_WORDS = [
    "가능성", "추정", "검토", "논의", "전망", "예상", "관측", "제안", "가정", "미정", "잠정", "초안",
]

CERTAIN_WORDS = [
    "확정", "체결", "승인", "공시", "발표했다", "판결", "계약 체결", "발표문", "판결문",
]


@dataclass
class VariantConfig:
    name: str
    require_time_for_future_tense: bool
    strengthen_negative_polarity: bool
    enable_mitigation_exception: bool


VARIANTS: Dict[str, VariantConfig] = {
    # 26_A: 미래 시제는 명시적 시간표현 필요
    "26_A": VariantConfig(
        name="26_A",
        require_time_for_future_tense=True,
        strengthen_negative_polarity=False,
        enable_mitigation_exception=False,
    ),
    # 26_B: 부정 극성 강화
    "26_B": VariantConfig(
        name="26_B",
        require_time_for_future_tense=False,
        strengthen_negative_polarity=True,
        enable_mitigation_exception=False,
    ),
    # 26_C: 26_B + 미래 시제 조건 + 부정 완화 예외
    "26_C": VariantConfig(
        name="26_C",
        require_time_for_future_tense=True,
        strengthen_negative_polarity=True,
        enable_mitigation_exception=True,
    ),
    # 27_A: 26_C 기반, 완화 예외 시 긍정으로 반전
    "27_A": VariantConfig(
        name="27_A",
        require_time_for_future_tense=True,
        strengthen_negative_polarity=True,
        enable_mitigation_exception=True,
    ),
    # 27_B: 26_C 기반, 완화 예외 시 미정으로만 완화(보수)
    "27_B": VariantConfig(
        name="27_B",
        require_time_for_future_tense=True,
        strengthen_negative_polarity=True,
        enable_mitigation_exception=True,
    ),
}


def contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(k for k in keywords if k and k in text)


def detect_type(text: str) -> str:
    if contains_any(text, CONV_KEYWORDS):
        return "대화형"
    if contains_any(text, PRED_KEYWORDS_BASE):
        return "예측형"
    if contains_any(text, INFER_KEYWORDS):
        return "추론형"
    if contains_any(text, FACT_REPORT_KEYWORDS):
        return "사실형"
    return "사실형"


def detect_tense(text: str, cfg: VariantConfig) -> str:
    # Future if markers + (optionally) time expression
    future_candidate = contains_any(text, FUTURE_MARKERS) or contains_any(text, PRED_KEYWORDS_BASE)
    has_time = contains_any(text, TIME_EXPRESSIONS)
    if future_candidate and (has_time or not cfg.require_time_for_future_tense):
        return "미래"
    if contains_any(text, PAST_MARKERS):
        return "과거"
    if contains_any(text, PRESENT_MARKERS):
        return "현재"
    return "현재"


def detect_certainty(text: str) -> str:
    if contains_any(text, UNCERTAIN_WORDS):
        return "불확실"
    if contains_any(text, CERTAIN_WORDS) or contains_any(text, FACT_REPORT_KEYWORDS):
        return "확실"
    # 숫자 다수 포함 시 확실 가중(보수적으로 미적용)
    return "확실"


def detect_polarity(text: str, cfg: VariantConfig) -> str:
    has_neg = contains_any(text, NEG_WORDS) or contains_any(text, NEG_MORPH)
    has_pos = contains_any(text, POS_WORDS)
    if cfg.strengthen_negative_polarity and has_neg:
        if cfg.enable_mitigation_exception and contains_any(text, MITIGATION_WORDS):
            # 27_A는 긍정으로 반전, 27_B/26_C는 미정으로 완화
            if cfg.name == "27_A":
                return "긍정"
            else:
                return "미정"
        return "부정"
    if has_pos and not has_neg:
        return "긍정"
    if has_neg and not has_pos:
        return "부정"
    return "미정"


def parse_gold(label: str) -> Tuple[str, str, str, str]:
    parts = label.strip().strip('"').split(",")
    if len(parts) != 4:
        raise ValueError(f"잘못된 라벨 형식: {label}")
    return tuple(parts)  # type: ignore


def evaluate(csv_path: str, cfg: VariantConfig, limit: int | None = None) -> Dict[str, float]:
    total = 0
    correct_type = 0
    correct_polarity = 0
    correct_tense = 0
    correct_certainty = 0

    # utf-8-sig로 BOM을 처리해 header가 "\ufeffuser_prompt"로 읽히는 문제를 방지
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("user_prompt") or "").strip()
            gold = (row.get("output") or "").strip()
            if not text or not gold:
                continue

            try:
                g_type, g_pol, g_tense, g_cert = parse_gold(gold)
            except Exception:
                continue

            p_type = detect_type(text)
            p_tense = detect_tense(text, cfg)
            p_cert = detect_certainty(text)
            p_pol = detect_polarity(text, cfg)

            total += 1
            if p_type == g_type:
                correct_type += 1
            if p_pol == g_pol:
                correct_polarity += 1
            if p_tense == g_tense:
                correct_tense += 1
            if p_cert == g_cert:
                correct_certainty += 1

            if limit is not None and total >= limit:
                break

    acc_type = correct_type / total if total else 0.0
    acc_polarity = correct_polarity / total if total else 0.0
    acc_tense = correct_tense / total if total else 0.0
    acc_certainty = correct_certainty / total if total else 0.0
    avg = (acc_type + acc_polarity + acc_tense + acc_certainty) / 4.0

    return {
        "samples": float(total),
        "acc_type": acc_type,
        "acc_polarity": acc_polarity,
        "acc_tense": acc_tense,
        "acc_certainty": acc_certainty,
        "avg": avg,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/samples.csv")
    ap.add_argument("--variant", choices=list(VARIANTS.keys()), default="26_C")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cfg = VARIANTS[args.variant]
    metrics = evaluate(args.csv, cfg, args.limit)
    print(
        f"variant={cfg.name} samples={int(metrics['samples'])} "
        f"type={metrics['acc_type']:.4f} pol={metrics['acc_polarity']:.4f} "
        f"tense={metrics['acc_tense']:.4f} cert={metrics['acc_certainty']:.4f} avg={metrics['avg']:.4f}"
    )


if __name__ == "__main__":
    main()


