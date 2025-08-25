#!/usr/bin/env python3
import re
import sys
from typing import List


EXPECTED_PATTERN = re.compile(r"^\d+\. (사실형|추론형|대화형|예측형),(긍정|부정|미정),(과거|현재|미래),(확실|불확실)$")


def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def validate_lines(lines: List[str]) -> List[str]:
    errors: List[str] = []

    if not lines:
        errors.append("파일이 비어 있습니다.")
        return errors

    # 번호 증가 검증 및 형식 검증
    expected_idx = 1
    for i, line in enumerate(lines, start=1):
        if not EXPECTED_PATTERN.match(line):
            errors.append(f"{i}행 형식 오류: '{line}'")

        # 번호 검증: '123. ' 프리픽스 확인
        try:
            prefix, rest = line.split(". ", 1)
            num = int(prefix)
            if num != expected_idx:
                errors.append(f"{i}행 번호 불일치: 기대={expected_idx}, 실제={num}")
        except Exception:
            errors.append(f"{i}행 번호 파싱 실패: '{line}'")

        # 공백 검사: 라벨 사이 공백 금지 -> 패턴이 이미 검증하지만 2중 체크
        if ", " in line or " ," in line:
            errors.append(f"{i}행 쉼표 주변 공백 발견: '{line}'")

        expected_idx += 1

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: python tools/validate_outputs.py <output_file>")
        return 2

    output_path = sys.argv[1]
    try:
        lines = read_lines(output_path)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {output_path}")
        return 2

    errors = validate_lines(lines)
    if errors:
        print("검증 실패:")
        for e in errors:
            print("- ", e)
        return 1

    print("검증 성공: 형식 일치 및 번호 연속")
    return 0


if __name__ == "__main__":
    sys.exit(main())


