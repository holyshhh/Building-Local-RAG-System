#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이전 RAG 버전과 현재 RAG 버전을 동일한 10개 질문으로 실행하고,
답변 완전성, 근거 적중률, 평균 응답시간을 비교하여 보고서를 생성

실행 파일 경로
----------------
project/
├── 02_rag_faq.py                 # 현재 버전
├── versions/
│   └── 02_rag_faq_previous.py    # 이전 버전
├── data/
│   └── 개인통관고유부호 발급 시스템이용 FAQ.pdf
├── models/
└── 03_test.py

실행 예시
---------
python 03_test.py \
  --baseline-script ./versions/02_rag_faq_previous.py \
  --current-script ./02_rag_faq.py \
  --pdf "./data/개인통관고유부호 발급 시스템이용 FAQ.pdf" \
  --model-dir ./models \
  --output-dir ./evaluation_outputs

평가 정의
---------
1. 답변 완전성 (answer completeness)
   질문별 필수 정보 단위(requirement group) 중 답변에 포함된 비율.

2. 근거 적중률 (evidence hit rate)
   정답 근거 단위별로 기대 페이지와 핵심 표현이 실제 evidence에 함께 등장한 비율.

3. 평균 응답시간 (average response time)
   인덱스 생성과 모델 최초 로딩을 제외하고 answer_question() 한 건의 wall-clock 시간 평균.

주의
----
- 두 버전의 공정한 비교를 위해 동일 PDF, 동일 질문, 동일 n_ctx, 동일 reranker 설정 사용.
- 기본값은 이전 코드와 현재 코드 모두에서 사용 가능한 Qwen2.5-7B 계열을 기준으로 함.
- 소스 코드는 평가용 작업 디렉터리에 복사한 뒤, 문제 세트와 시간 계측 코드만 자동 삽입.
  원본 파일은 변경하지 않음.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


# -----------------------------------------------------------------------------
# 1. 평가 질문과 정답 기준
# -----------------------------------------------------------------------------

TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": "t01",
        "question": "개인통관고유부호는 무엇이며, 번호 형식과 사용 기간은 어떻게 되나요?",
        "answer_requirements": [
            {"label": "주민등록번호 대신 사용하는 개인 식별 부호", "aliases": ["주민등록번호 대신", "개인 식별", "개인식별"]},
            {"label": "P로 시작하는 13자리", "aliases": ["p로 시작하는 13자리", "p+숫자12자리", "p + 숫자 12자리"]},
            {"label": "한번 발급받으면 계속 사용", "aliases": ["계속 사용할 수", "계속 사용", "지속 사용", "재사용"]},
        ],
        "evidence_requirements": [
            {"pages": [3], "aliases": ["주민등록번호 대신", "개인 식별"]},
            {"pages": [3], "aliases": ["p로 시작하는 13자리", "p+숫자12자리"]},
            {"pages": [3], "aliases": ["계속 사용할 수", "한번 부여받은"]},
        ],
    },
    {
        "id": "t02",
        "question": "개인통관고유부호는 신청 후 언제 발급되며, 신청 가능한 시간은 어떻게 되나요?",
        "answer_requirements": [
            {"label": "신청 즉시 자동 발급", "aliases": ["신청한 즉시", "즉시 자동", "즉시 발급"]},
            {"label": "24시간 신청 가능", "aliases": ["24시간", "24 시간"]},
        ],
        "evidence_requirements": [
            {"pages": [3], "aliases": ["신청한 즉시", "즉시 자동"]},
            {"pages": [3], "aliases": ["24시간 신청 가능", "24시간"]},
        ],
    },
    {
        "id": "t03",
        "question": "모바일 앱으로 발급하려면 어떤 앱을 어디에서 설치하고, 설치 후 어떤 메뉴를 선택해야 하나요?",
        "answer_requirements": [
            {"label": "모바일 관세청 앱", "aliases": ["모바일 관세청", "모바일관세청"]},
            {"label": "Play Store 또는 App Store", "aliases": ["play store", "플레이 스토어", "app store", "앱 스토어"]},
            {"label": "개인통관고유부호 메뉴", "aliases": ["개인통관고유부호 메뉴", "[개인통관고유부호]", "개인통관고유부호 선택"]},
        ],
        "evidence_requirements": [
            {"pages": [4], "aliases": ["모바일 관세청", "모바일관세청"]},
            {"pages": [4], "aliases": ["play store", "플레이 스토어", "app store", "앱 스토어"]},
            {"pages": [4], "aliases": ["개인통관고유부호 메뉴", "개인통관고유부호 선택"]},
        ],
    },
    {
        "id": "t04",
        "question": "PC에서 개인통관고유부호를 신규 발급할 때 선택할 수 있는 본인인증 방법을 모두 나열하세요.",
        "answer_requirements": [
            {"label": "휴대폰 인증", "aliases": ["휴대폰인증", "휴대폰 인증"]},
            {"label": "공동/금융인증서 인증", "aliases": ["공동/금융인증서", "공동인증서", "금융인증서"]},
            {"label": "간편인증", "aliases": ["간편인증", "간편 인증"]},
        ],
        "evidence_requirements": [
            {"pages": [9, 10, 11], "aliases": ["휴대폰인증", "휴대폰 인증"]},
            {"pages": [9, 10, 11], "aliases": ["공동/금융인증서", "공동인증서", "금융인증서"]},
            {"pages": [9, 10, 11], "aliases": ["간편인증", "간편 인증"]},
        ],
    },
    {
        "id": "t05",
        "question": "개인통관고유부호 발급 시 주소는 어디에서 어떻게 검색하나요?",
        "answer_requirements": [
            {"label": "주소 항목 우측 돋보기", "aliases": ["주소 항목 우측 돋보기", "돋보기 버튼", "주소 우측 돋보기"]},
            {"label": "도로명주소 안내시스템", "aliases": ["도로명주소 안내시스템", "juso.go.kr"]},
            {"label": "상세주소 입력 후 주소 입력 버튼", "aliases": ["상세주소 입력", "주소 입력 버튼", "[주소 입력]"]},
        ],
        "evidence_requirements": [
            {"pages": [12], "aliases": ["돋보기 버튼", "주소 항목 우측"]},
            {"pages": [12], "aliases": ["도로명주소 안내시스템", "juso.go.kr"]},
            {"pages": [12], "aliases": ["상세주소 입력", "주소 입력"]},
        ],
    },
    {
        "id": "t06",
        "question": "본인 명의 휴대전화가 없을 때 개인통관고유부호를 발급받을 수 있는 대안을 모두 설명하세요.",
        "answer_requirements": [
            {"label": "공동/금융인증서로 인증", "aliases": ["공동/금융인증서", "공동인증서", "금융인증서"]},
            {"label": "신분증을 지참해 세관 방문", "aliases": ["신분증 지참", "세관 방문", "가까운 세관"]},
            {"label": "금융인증서는 PC만 가능", "aliases": ["금융인증서 인증은 현재 pc", "금융인증서는 pc", "pc를 통한 발급만"]},
        ],
        "evidence_requirements": [
            {"pages": [13], "aliases": ["공동/금융인증서", "공동인증서"]},
            {"pages": [13], "aliases": ["신분증 지참", "세관 방문"]},
            {"pages": [13], "aliases": ["금융인증서 인증은 현재 pc", "pc를 통한 발급만"]},
        ],
    },
    {
        "id": "t07",
        "question": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
        "answer_requirements": [
            {"label": "모바일 앱", "aliases": ["모바일 앱", "앱(app)", "모바일관세청 앱"]},
            {"label": "모바일 웹", "aliases": ["모바일 웹", "웹(web)", "모바일웹"]},
            {"label": "PC", "aliases": ["pc 이용", "pc에서", "pc로"]},
        ],
        "evidence_requirements": [
            {"pages": [13], "aliases": ["모바일 앱", "앱(app)"]},
            {"pages": [13], "aliases": ["모바일 웹", "웹(web)"]},
            {"pages": [13], "aliases": ["pc 이용", "pc에서"]},
        ],
    },
    {
        "id": "t08",
        "question": "개인통관고유부호를 재발급하면 기존 부호는 어떻게 되며, 재발급 횟수 제한은 얼마인가요?",
        "answer_requirements": [
            {"label": "기존 부호 자동 미사용 처리", "aliases": ["자동으로 미사용", "자동 미사용", "기존 개인통관고유부호는 자동"]},
            {"label": "새 부호만 통관 가능", "aliases": ["신규 발급된 부호로만", "새로운 부호로만", "신규 부호로만"]},
            {"label": "연간 5회 제한", "aliases": ["연간 5회", "1년에 5회"]},
            {"label": "미사용 부호는 다시 사용 불가", "aliases": ["다시 사용 처리 불가", "다시 사용할 수 없", "미사용 처리된 부호"]},
        ],
        "evidence_requirements": [
            {"pages": [14], "aliases": ["자동으로 미사용", "자동 미사용"]},
            {"pages": [14], "aliases": ["신규 발급된 부호로만", "신규 부호로만"]},
            {"pages": [14], "aliases": ["연간 5회"]},
            {"pages": [14], "aliases": ["다시 사용 처리 불가", "미사용 처리된 부호"]},
        ],
    },
    {
        "id": "t09",
        "question": "개인통관고유부호의 주소나 전화번호를 수정할 수 있는 이용 경로와 마지막 저장 동작을 각각 설명하세요.",
        "answer_requirements": [
            {"label": "모바일 앱", "aliases": ["모바일 앱", "앱(app)", "모바일관세청 앱"]},
            {"label": "앱에서는 등록 버튼", "aliases": ["등록 버튼", "[등록]"]},
            {"label": "모바일 웹", "aliases": ["모바일 웹", "웹(web)", "모바일웹"]},
            {"label": "PC", "aliases": ["pc 이용", "pc에서", "pc로"]},
            {"label": "웹과 PC에서는 저장 버튼", "aliases": ["저장 버튼", "[저장]"]},
        ],
        "evidence_requirements": [
            {"pages": [14], "aliases": ["모바일 앱", "앱(app)"]},
            {"pages": [14], "aliases": ["등록 버튼", "[등록]"]},
            {"pages": [14], "aliases": ["모바일 웹", "웹(web)"]},
            {"pages": [14], "aliases": ["pc 이용", "pc에서"]},
            {"pages": [14], "aliases": ["저장 버튼", "[저장]"]},
        ],
    },
    {
        "id": "t10",
        "question": "개인통관고유부호로 해외 직구 이력을 조회할 수 있는 두 가지 방법을 모두 나열하고, 각 방법의 주요 차이를 설명하세요.",
        "answer_requirements": [
            {"label": "개인통관고유부호 발급 시스템", "aliases": ["개인통관고유부호 발급 시스템", "개인통관고유부호 발급사이트"]},
            {"label": "관세청 홈페이지 해외직구 여기로", "aliases": ["해외직구 여기로", "관세청 홈페이지"]},
            {"label": "발급 시스템은 사용 상태 부호 이력", "aliases": ["사용 상태", "‘사용’ 상태", "사용 상태의 개인통관고유부호"]},
            {"label": "관세청 홈페이지는 미사용 상태 이력도 조회", "aliases": ["미사용 상태", "‘미사용’ 상태", "미사용 상태의 개인통관고유부호"]},
            {"label": "모바일 앱은 수입신고 이력만", "aliases": ["수입신고 이력만", "앱에서는 수입신고"]},
        ],
        "evidence_requirements": [
            {"pages": [17, 18], "aliases": ["개인통관고유부호 발급 시스템", "발급사이트"]},
            {"pages": [17, 18], "aliases": ["해외직구 여기로", "관세청 홈페이지"]},
            {"pages": [17, 18], "aliases": ["사용 상태", "‘사용’ 상태"]},
            {"pages": [17, 18], "aliases": ["미사용 상태", "‘미사용’ 상태"]},
            {"pages": [17], "aliases": ["수입신고 이력만"]},
        ],
    },
]


@dataclass
class VersionRun:
    name: str
    source_script: Path
    work_dir: Path
    staged_script: Path
    command: List[str]
    return_code: int
    wall_time_sec: float
    stdout_log: Path
    stderr_log: Path
    answers_path: Optional[Path]
    results: List[Dict[str, Any]]
    error: Optional[str] = None


# -----------------------------------------------------------------------------
# 2. 문자열 및 페이지 처리
# -----------------------------------------------------------------------------

def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("·", " ").replace("ㆍ", " ")
    text = re.sub(r"[\[\](){}<>‘’'\"`*_#|,:;.!?→⇨/\\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def alias_hit(text: str, aliases: Sequence[str]) -> bool:
    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")
    for alias in aliases:
        a = normalize_text(alias)
        if not a:
            continue
        if a in normalized or a.replace(" ", "") in compact:
            return True
    return False


def parse_page_spec(value: Any) -> Set[int]:
    """'p.4-8', '4', 'p.13' 등의 표현에서 페이지 집합을 추출"""
    text = str(value or "")
    pages: Set[int] = set()
    for start, end in re.findall(r"(?:p\.?\s*)?(\d+)\s*[-~]\s*(?:p\.?\s*)?(\d+)", text, flags=re.I):
        a, b = int(start), int(end)
        if a <= b and b - a <= 100:
            pages.update(range(a, b + 1))
    text_without_ranges = re.sub(r"(?:p\.?\s*)?\d+\s*[-~]\s*(?:p\.?\s*)?\d+", " ", text, flags=re.I)
    for token in re.findall(r"(?:p\.?\s*)?(\d+)", text_without_ranges, flags=re.I):
        pages.add(int(token))
    return pages


def evidence_text_and_pages(evidence: Sequence[Dict[str, Any]]) -> Tuple[str, Set[int]]:
    texts: List[str] = []
    pages: Set[int] = set()
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        texts.extend([
            str(item.get("quote", "")),
            str(item.get("title", "")),
            str(item.get("locator", "")),
        ])
        pages.update(parse_page_spec(item.get("page", "")))
        pages.update(parse_page_spec(item.get("locator", "")))
    return "\n".join(texts), pages


# -----------------------------------------------------------------------------
# 3. 소스 코드 평가용 패치
# -----------------------------------------------------------------------------

def replace_problem_set(source: str, cases: Sequence[Dict[str, Any]]) -> str:
    marker = "PROBLEM_SET"
    start = source.find(marker)
    if start < 0:
        raise RuntimeError("소스에서 PROBLEM_SET을 찾지 못했습니다.")
    eq = source.find("=", start)
    open_idx = source.find("[", eq)
    if eq < 0 or open_idx < 0:
        raise RuntimeError("PROBLEM_SET 리스트 시작점을 찾지 못했습니다.")

    depth = 0
    in_string: Optional[str] = None
    escape = False
    close_idx = -1
    for i in range(open_idx, len(source)):
        ch = source[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx < 0:
        raise RuntimeError("PROBLEM_SET 리스트 끝점을 찾지 못했습니다.")

    compact_cases = [{"id": c["id"], "question": c["question"]} for c in cases]
    replacement = "PROBLEM_SET = " + repr(compact_cases)
    return source[:start] + replacement + source[close_idx + 1 :]


def inject_timing(source: str) -> str:
    """run_problem_set 루프 안 answer_question 호출 전후에 시간 측정을 삽입"""
    if "import time\n" not in source:
        insert_at = 0
        # __future__ import가 있다면 그 뒤에 삽입
        future_match = re.search(r"^from __future__ import .*?$", source, flags=re.M)
        if future_match:
            insert_at = future_match.end() + 1
        source = source[:insert_at] + "import time\n" + source[insert_at:]

    loop_pos = source.find("for item in PROBLEM_SET:")
    if loop_pos < 0:
        raise RuntimeError("run_problem_set의 문제 반복문을 찾지 못했습니다.")

    call_match = re.search(
        r"(?P<indent>^[ \t]*)answer_obj\s*,\s*context_items\s*,\s*diagnostics\s*=\s*answer_question\(",
        source[loop_pos:],
        flags=re.M,
    )
    if not call_match:
        raise RuntimeError("answer_question 호출을 찾지 못했습니다.")

    absolute_call = loop_pos + call_match.start()
    indent = call_match.group("indent")
    source = source[:absolute_call] + f"{indent}_eval_t0 = time.perf_counter()\n" + source[absolute_call:]

    # 삽입 후 호출 괄호의 끝을 찾아 elapsed 계산 추가
    call_start = source.find("answer_question(", absolute_call)
    paren_start = source.find("(", call_start)
    depth = 0
    in_string: Optional[str] = None
    escape = False
    call_end = -1
    for i in range(paren_start, len(source)):
        ch = source[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                call_end = i + 1
                break
    if call_end < 0:
        raise RuntimeError("answer_question 호출 끝을 찾지 못했습니다.")

    source = source[:call_end] + f"\n{indent}_eval_elapsed = time.perf_counter() - _eval_t0" + source[call_end:]

    # 현재 loop 내부의 all_results.append 딕셔너리에 response_time_sec를 삽입
    append_pos = source.find("all_results.append", call_end)
    if append_pos < 0:
        raise RuntimeError("all_results.append를 찾지 못했습니다.")
    question_key = source.find('"question": question,', append_pos)
    if question_key < 0:
        question_key = source.find("'question': question,", append_pos)
    if question_key < 0:
        raise RuntimeError("결과 딕셔너리의 question 필드를 찾지 못했습니다.")
    line_end = source.find("\n", question_key)
    key_indent = re.match(r"[ \t]*", source[source.rfind("\n", 0, question_key) + 1 : question_key]).group(0)
    source = source[: line_end + 1] + f'{key_indent}"response_time_sec": _eval_elapsed,\n' + source[line_end + 1 :]
    return source


def stage_version(
    name: str,
    source_script: Path,
    root: Path,
    model_dir: Path,
    pdf_path: Path,
) -> Tuple[Path, Path]:
    work_dir = root / name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    source = source_script.read_text(encoding="utf-8")
    source = replace_problem_set(source, TEST_CASES)
    source = inject_timing(source)
    staged_script = work_dir / "02_rag_faq.py"
    staged_script.write_text(source, encoding="utf-8")

    # 원본 모델을 복제하지 않고 심볼릭 링크로 공유
    model_link = work_dir / "models"
    try:
        model_link.symlink_to(model_dir.resolve(), target_is_directory=True)
    except OSError as exc:
        raise RuntimeError(f"모델 디렉터리 심볼릭 링크 생성 실패: {exc}") from exc

    data_dir = work_dir / "data"
    data_dir.mkdir(exist_ok=True)
    pdf_link = data_dir / pdf_path.name
    try:
        pdf_link.symlink_to(pdf_path.resolve())
    except OSError:
        shutil.copy2(pdf_path, pdf_link)

    # 패치된 파일 문법 확인
    check = subprocess.run(
        [sys.executable, "-m", "py_compile", str(staged_script)],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        raise RuntimeError(f"{name} 평가용 소스 문법 오류:\n{check.stderr}")
    return work_dir, staged_script


def get_supported_options(script: Path, cwd: Path, timeout: int = 120) -> Set[str]:
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    help_text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return set(re.findall(r"--[a-zA-Z0-9_-]+", help_text))


def append_if_supported(cmd: List[str], supported: Set[str], flag: str, value: Optional[Any] = None) -> bool:
    if flag not in supported:
        return False
    cmd.append(flag)
    if value is not None:
        cmd.append(str(value))
    return True


def append_first_supported(
    cmd: List[str],
    supported: Set[str],
    flags: Sequence[str],
    value: Optional[Any] = None,
) -> Optional[str]:
    """여러 버전에서 이름이 달라진 CLI 옵션 중 실제 지원되는 첫 옵션을 추가"""
    for flag in flags:
        if append_if_supported(cmd, supported, flag, value):
            return flag
    return None


def build_run_command(
    script: Path,
    work_dir: Path,
    pdf_path: Path,
    args: argparse.Namespace,
) -> List[str]:
    supported = get_supported_options(script, work_dir)
    cmd = [sys.executable, str(script)]
    append_first_supported(cmd, supported, ["--pdf", "--pdf-path", "--pdf_path"], str(pdf_path))
    append_first_supported(cmd, supported, ["--rebuild", "--build-index", "--build_index"])
    if not args.no_ocr:
        append_first_supported(cmd, supported, ["--ocr", "--use-ocr", "--use_ocr"])

    run_flag = append_first_supported(
        cmd,
        supported,
        [
            "--run_problem_set",
            "--run-problem-set",
            "--run_questions",
            "--run-questions",
            "--evaluate",
        ],
    )
    if run_flag is None:
        raise RuntimeError(
            "평가 대상 코드에서 문제 세트 실행 옵션을 찾지 못했습니다. "
            f"지원 옵션: {sorted(supported)}"
        )

    # 공정 비교를 위한 공통 실행 조건
    append_if_supported(cmd, supported, "--n_ctx", args.n_ctx)
    append_if_supported(cmd, supported, "--n_gpu_layers", args.n_gpu_layers)
    append_if_supported(cmd, supported, "--dense_k", args.dense_k)
    append_if_supported(cmd, supported, "--bm25_k", args.bm25_k)
    append_if_supported(cmd, supported, "--candidate_k", args.candidate_k)
    append_if_supported(cmd, supported, "--top_k", args.top_k)
    append_if_supported(cmd, supported, "--max_context_chunks", args.max_context_chunks)
    append_if_supported(cmd, supported, "--unit_cross_top_n", args.unit_cross_top_n)
    append_if_supported(cmd, supported, "--max_answer_units", args.max_answer_units)

    # 현재 버전에서만 존재할 수 있는 옵션은 지원 여부를 확인한 뒤 적용
    append_if_supported(cmd, supported, "--llm_model", args.llm_model)
    append_if_supported(cmd, supported, "--answer_mode", "grounded")
    append_if_supported(cmd, supported, "--reranker_mode", "on")
    append_if_supported(cmd, supported, "--llm_backend", "subprocess")
    append_if_supported(cmd, supported, "--llm_force_cpu")
    append_if_supported(cmd, supported, "--llm_timeout", args.llm_timeout)
    append_if_supported(cmd, supported, "--llm_n_batch", args.llm_n_batch)
    append_if_supported(cmd, supported, "--llm_n_ubatch", args.llm_n_ubatch)
    append_if_supported(cmd, supported, "--num_retrieval_queries", args.num_retrieval_queries)
    append_if_supported(cmd, supported, "--query_planner", args.query_planner)
    append_if_supported(cmd, supported, "--rerank_pool_k", args.rerank_pool_k)
    append_if_supported(cmd, supported, "--composer_token_budget", args.composer_token_budget)
    append_if_supported(cmd, supported, "--composer_max_tokens", args.composer_max_tokens)
    append_if_supported(cmd, supported, "--composer_safety_margin", args.composer_safety_margin)
    append_if_supported(cmd, supported, "--max_composer_evidence", args.max_composer_evidence)
    append_if_supported(cmd, supported, "--max_composer_sections", args.max_composer_sections)
    append_if_supported(cmd, supported, "--max_chars_per_composer_evidence", args.max_chars_per_composer_evidence)
    append_if_supported(cmd, supported, "--composer_max_attempts", args.composer_max_attempts)
    return cmd


# -----------------------------------------------------------------------------
# 4. 버전 실행 및 결과 로딩
# -----------------------------------------------------------------------------

def discover_answers_json(work_dir: Path, stdout_text: str = "") -> Optional[Path]:
    """
    버전별로 달라질 수 있는 답변 JSON 경로를 폭넓게 탐색
    
    1) 표준 outputs 경로
    2) stdout에 출력된 JSON 경로
    3) 작업 디렉터리 전체 재귀 검색
    """
    output_dirs = [work_dir / "outputs", work_dir / "output", work_dir / "results"]
    preferred_names = [
        "answers.json",
        "answers_qwen2_5-7b_reranker_on.json",
        "answers_qwen3-4b_reranker_on.json",
        "results.json",
        "evaluation_results.json",
    ]

    for directory in output_dirs:
        for name in preferred_names:
            path = directory / name
            if path.exists() and path.is_file():
                return path

    # 실행 로그에 출력된 경로가 있으면 우선 확인
    for token in re.findall(r"(?:^|[\s'\"])([^\s'\"]+\.json)(?=$|[\s'\"])", stdout_text or ""):
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = work_dir / candidate
        if candidate.exists() and candidate.is_file() and "answer" in candidate.name.lower():
            return candidate

    candidates: List[Path] = []
    for pattern in ("answers*.json", "*answer*.json", "results*.json", "*result*.json"):
        candidates.extend(work_dir.rglob(pattern))

    # cache/index JSON은 제외하고 최신 결과 파일을 선택
    filtered = [
        p for p in candidates
        if p.is_file()
        and "cache" not in {part.lower() for part in p.parts}
        and "chunk" not in p.name.lower()
        and "compare" not in p.name.lower()
    ]
    filtered = sorted(set(filtered), key=lambda p: p.stat().st_mtime, reverse=True)
    return filtered[0] if filtered else None


def normalize_result_row(row: Dict[str, Any]) -> Dict[str, Any]:
    answer_obj = row.get("answer")
    if isinstance(answer_obj, dict):
        answer_text = answer_obj.get("final_answer") or answer_obj.get("answer") or ""
        evidence = answer_obj.get("evidence", row.get("evidence", []))
    else:
        answer_text = row.get("answer", "")
        evidence = row.get("evidence", [])
    return {
        **row,
        "answer": str(answer_text or ""),
        "evidence": evidence if isinstance(evidence, list) else [],
        "response_time_sec": safe_float(row.get("response_time_sec")),
    }


def safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_version(
    name: str,
    source_script: Path,
    eval_root: Path,
    model_dir: Path,
    pdf_path: Path,
    args: argparse.Namespace,
) -> VersionRun:
    work_dir, staged_script = stage_version(name, source_script, eval_root, model_dir, pdf_path)
    staged_pdf = work_dir / "data" / pdf_path.name
    cmd = build_run_command(staged_script, work_dir, staged_pdf, args)

    stdout_log = work_dir / "run_stdout.log"
    stderr_log = work_dir / "run_stderr.log"
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=args.version_timeout,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        elapsed = time.perf_counter() - started
        stdout_log.write_text(proc.stdout or "", encoding="utf-8")
        stderr_log.write_text(proc.stderr or "", encoding="utf-8")
        answers_path = discover_answers_json(work_dir, proc.stdout or "")
        results: List[Dict[str, Any]] = []
        error: Optional[str] = None
        if answers_path and answers_path.exists():
            loaded = json.loads(answers_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                # 비교 출력 형태가 들어온 경우 첫 리스트를 선택
                list_values = [v for v in loaded.values() if isinstance(v, list)]
                loaded = list_values[0] if list_values else []
            if isinstance(loaded, list):
                results = [normalize_result_row(r) for r in loaded if isinstance(r, dict)]
        if proc.returncode != 0:
            error = f"프로세스 종료 코드 {proc.returncode}. stderr 로그를 확인하세요."
        elif not answers_path:
            stdout_tail = "\n".join((proc.stdout or "").splitlines()[-20:])
            stderr_tail = "\n".join((proc.stderr or "").splitlines()[-20:])
            error = (
                "answers JSON을 찾지 못했습니다. "
                "프로세스는 정상 종료했지만 문제 세트가 실행되지 않았거나, "
                "이전 버전이 다른 경로/형식으로 결과를 저장했을 가능성이 큽니다.\n"
                f"실행 명령: {' '.join(cmd)}\n"
                f"stdout 마지막 20줄:\n{stdout_tail or '(비어 있음)'}\n"
                f"stderr 마지막 20줄:\n{stderr_tail or '(비어 있음)'}"
            )
        elif not results:
            error = (
                f"답변 JSON은 찾았지만 평가 결과 행이 없습니다: {answers_path}. "
                "JSON 구조가 버전별로 다를 수 있으므로 파일 내용을 확인하세요."
            )
        return VersionRun(
            name=name,
            source_script=source_script,
            work_dir=work_dir,
            staged_script=staged_script,
            command=cmd,
            return_code=proc.returncode,
            wall_time_sec=elapsed,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            answers_path=answers_path,
            results=results,
            error=error,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        stdout_log.write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8")
        stderr_log.write_text((exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8")
        return VersionRun(
            name=name,
            source_script=source_script,
            work_dir=work_dir,
            staged_script=staged_script,
            command=cmd,
            return_code=124,
            wall_time_sec=elapsed,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            answers_path=None,
            results=[],
            error=f"{args.version_timeout}초 제한시간을 초과했습니다.",
        )


# -----------------------------------------------------------------------------
# 5. 정량지표 계산
# -----------------------------------------------------------------------------

def compute_answer_completeness(answer: str, requirements: Sequence[Dict[str, Any]]) -> Tuple[float, List[bool]]:
    hits = [alias_hit(answer, req.get("aliases", [])) for req in requirements]
    score = (sum(hits) / len(hits) * 100.0) if hits else 0.0
    return score, hits


def compute_evidence_hit_rate(
    evidence: Sequence[Dict[str, Any]],
    requirements: Sequence[Dict[str, Any]],
) -> Tuple[float, List[bool]]:
    evidence_text, evidence_pages = evidence_text_and_pages(evidence)
    hits: List[bool] = []
    for req in requirements:
        expected_pages = set(int(p) for p in req.get("pages", []))
        page_ok = not expected_pages or bool(expected_pages & evidence_pages)
        keyword_ok = alias_hit(evidence_text, req.get("aliases", []))
        hits.append(page_ok and keyword_ok)
    score = (sum(hits) / len(hits) * 100.0) if hits else 0.0
    return score, hits


def evaluate_version(run: VersionRun) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows_by_id = {str(r.get("id")): r for r in run.results}
    detail: List[Dict[str, Any]] = []

    for case in TEST_CASES:
        result = rows_by_id.get(case["id"], {})
        answer = str(result.get("answer", ""))
        evidence = result.get("evidence", []) if isinstance(result.get("evidence", []), list) else []
        completeness, answer_hits = compute_answer_completeness(answer, case["answer_requirements"])
        evidence_rate, evidence_hits = compute_evidence_hit_rate(evidence, case["evidence_requirements"])
        latency = safe_float(result.get("response_time_sec"))

        missing_answer = [
            req["label"]
            for req, hit in zip(case["answer_requirements"], answer_hits)
            if not hit
        ]
        missing_evidence = [
            f"pages={req.get('pages', [])}, aliases={req.get('aliases', [])}"
            for req, hit in zip(case["evidence_requirements"], evidence_hits)
            if not hit
        ]
        detail.append({
            "version": run.name,
            "id": case["id"],
            "question": case["question"],
            "answer": answer,
            "answer_completeness_pct": round(completeness, 2),
            "evidence_hit_rate_pct": round(evidence_rate, 2),
            "response_time_sec": round(latency, 3) if latency is not None else None,
            "missing_answer_requirements": missing_answer,
            "missing_evidence_requirements": missing_evidence,
            "evidence": evidence,
        })

    valid_latencies = [r["response_time_sec"] for r in detail if r["response_time_sec"] is not None]
    summary = {
        "version": run.name,
        "n_test_cases": len(TEST_CASES),
        "n_answered": sum(bool(r["answer"].strip()) for r in detail),
        "mean_answer_completeness_pct": round(statistics.mean(r["answer_completeness_pct"] for r in detail), 2),
        "mean_evidence_hit_rate_pct": round(statistics.mean(r["evidence_hit_rate_pct"] for r in detail), 2),
        "mean_response_time_sec": round(statistics.mean(valid_latencies), 3) if valid_latencies else None,
        "median_response_time_sec": round(statistics.median(valid_latencies), 3) if valid_latencies else None,
        "total_execution_wall_time_sec": round(run.wall_time_sec, 3),
        "run_error": run.error,
    }
    return detail, summary


def difference(current: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if current is None or baseline is None:
        return None
    return round(current - baseline, 3)


def relative_change(current: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if current is None or baseline in (None, 0):
        return None
    return round((current - baseline) / baseline * 100.0, 2)


# -----------------------------------------------------------------------------
# 6. 파일 저장 및 보고서
# -----------------------------------------------------------------------------

def write_test_cases(path: Path) -> None:
    path.write_text(json.dumps(TEST_CASES, ensure_ascii=False, indent=2), encoding="utf-8")


def write_detail_csv(path: Path, details: Sequence[Dict[str, Any]]) -> None:
    fields = [
        "version", "id", "question", "answer_completeness_pct",
        "evidence_hit_rate_pct", "response_time_sec",
        "missing_answer_requirements", "missing_evidence_requirements", "answer",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in details:
            out = {k: row.get(k) for k in fields}
            out["missing_answer_requirements"] = " | ".join(row.get("missing_answer_requirements", []))
            out["missing_evidence_requirements"] = " | ".join(row.get("missing_evidence_requirements", []))
            writer.writerow(out)


def fmt(value: Optional[float], digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def arrow_for_metric(delta: Optional[float], lower_is_better: bool = False) -> str:
    if delta is None or abs(delta) < 1e-9:
        return "→"
    improved = delta < 0 if lower_is_better else delta > 0
    return "▲" if improved else "▼"


def write_report(
    path: Path,
    baseline_run: VersionRun,
    current_run: VersionRun,
    baseline_detail: Sequence[Dict[str, Any]],
    current_detail: Sequence[Dict[str, Any]],
    baseline_summary: Dict[str, Any],
    current_summary: Dict[str, Any],
) -> None:
    c_delta = difference(current_summary["mean_answer_completeness_pct"], baseline_summary["mean_answer_completeness_pct"])
    e_delta = difference(current_summary["mean_evidence_hit_rate_pct"], baseline_summary["mean_evidence_hit_rate_pct"])
    t_delta = difference(current_summary["mean_response_time_sec"], baseline_summary["mean_response_time_sec"])
    t_rel = relative_change(current_summary["mean_response_time_sec"], baseline_summary["mean_response_time_sec"])

    base_by_id = {r["id"]: r for r in baseline_detail}
    curr_by_id = {r["id"]: r for r in current_detail}

    lines = [
        "# RAG 버전 정량 비교 보고서",
        "",
        "## 1. 평가 목적",
        "",
        "동일한 PDF와 10개 테스트 질문을 사용해 이전 버전과 현재 버전의 답변 품질 및 실행 효율을 비교했습니다. 평가 지표는 답변 완전성, 근거 적중률, 평균 응답시간입니다.",
        "",
        "## 2. 평가 설정",
        "",
        f"- 테스트 문항 수: {len(TEST_CASES)}개",
        f"- 이전 버전: `{baseline_run.source_script}`",
        f"- 현재 버전: `{current_run.source_script}`",
        "- 인덱스 생성 시간과 모델 최초 로딩 시간은 질문별 응답시간에서 제외",
        "- 동일한 검색 파라미터와 context 크기를 지원되는 범위에서 적용",
        "",
        "### 지표 정의",
        "",
        "- **답변 완전성**: 질문별 필수 정보 단위 중 최종 답변에 포함된 비율",
        "- **근거 적중률**: 기대 페이지와 핵심 표현이 실제 evidence에서 함께 확인된 근거 단위의 비율",
        "- **평균 응답시간**: `answer_question()` 호출 시작부터 종료까지의 wall-clock 평균",
        "",
        "## 3. 종합 결과",
        "",
        "| 지표 | 이전 버전 | 현재 버전 | 변화 |",
        "|---|---:|---:|---:|",
        f"| 답변 완전성 | {fmt(baseline_summary['mean_answer_completeness_pct'])}% | {fmt(current_summary['mean_answer_completeness_pct'])}% | {arrow_for_metric(c_delta)} {fmt(c_delta)}%p |",
        f"| 근거 적중률 | {fmt(baseline_summary['mean_evidence_hit_rate_pct'])}% | {fmt(current_summary['mean_evidence_hit_rate_pct'])}% | {arrow_for_metric(e_delta)} {fmt(e_delta)}%p |",
        f"| 평균 응답시간 | {fmt(baseline_summary['mean_response_time_sec'], 3)}초 | {fmt(current_summary['mean_response_time_sec'], 3)}초 | {arrow_for_metric(t_delta, lower_is_better=True)} {fmt(t_delta, 3)}초 ({fmt(t_rel)}%) |",
        "",
        f"- 이전 버전 정상 답변: {baseline_summary['n_answered']}/{len(TEST_CASES)}",
        f"- 현재 버전 정상 답변: {current_summary['n_answered']}/{len(TEST_CASES)}",
        "",
        "## 4. 문항별 결과",
        "",
        "| ID | 질문 요약 | 이전 완전성 | 현재 완전성 | 이전 근거 | 현재 근거 | 이전 시간 | 현재 시간 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    for case in TEST_CASES:
        b = base_by_id.get(case["id"], {})
        c = curr_by_id.get(case["id"], {})
        short_q = case["question"]
        if len(short_q) > 38:
            short_q = short_q[:38] + "…"
        lines.append(
            f"| {case['id']} | {short_q} | "
            f"{fmt(b.get('answer_completeness_pct'))}% | {fmt(c.get('answer_completeness_pct'))}% | "
            f"{fmt(b.get('evidence_hit_rate_pct'))}% | {fmt(c.get('evidence_hit_rate_pct'))}% | "
            f"{fmt(b.get('response_time_sec'), 3)}초 | {fmt(c.get('response_time_sec'), 3)}초 |"
        )

    improved_cases = []
    regressed_cases = []
    for case in TEST_CASES:
        b = base_by_id.get(case["id"], {})
        c = curr_by_id.get(case["id"], {})
        quality_b = (b.get("answer_completeness_pct", 0) + b.get("evidence_hit_rate_pct", 0)) / 2
        quality_c = (c.get("answer_completeness_pct", 0) + c.get("evidence_hit_rate_pct", 0)) / 2
        delta = quality_c - quality_b
        if delta > 0.01:
            improved_cases.append((case["id"], delta))
        elif delta < -0.01:
            regressed_cases.append((case["id"], delta))

    lines += [
        "",
        "## 5. 해석",
        "",
    ]
    if c_delta is not None:
        if c_delta > 0:
            lines.append(f"- 현재 버전의 평균 답변 완전성은 이전 버전보다 **{c_delta:.2f}%p 향상**되었습니다.")
        elif c_delta < 0:
            lines.append(f"- 현재 버전의 평균 답변 완전성은 이전 버전보다 **{abs(c_delta):.2f}%p 하락**했습니다.")
        else:
            lines.append("- 두 버전의 평균 답변 완전성은 동일했습니다.")
    if e_delta is not None:
        if e_delta > 0:
            lines.append(f"- 현재 버전의 평균 근거 적중률은 이전 버전보다 **{e_delta:.2f}%p 향상**되었습니다.")
        elif e_delta < 0:
            lines.append(f"- 현재 버전의 평균 근거 적중률은 이전 버전보다 **{abs(e_delta):.2f}%p 하락**했습니다.")
        else:
            lines.append("- 두 버전의 평균 근거 적중률은 동일했습니다.")
    if t_rel is not None:
        if t_rel < 0:
            lines.append(f"- 평균 응답시간은 이전 버전 대비 **{abs(t_rel):.2f}% 단축**되었습니다.")
        elif t_rel > 0:
            lines.append(f"- 평균 응답시간은 이전 버전 대비 **{t_rel:.2f}% 증가**했습니다. 품질 향상과 지연시간의 trade-off를 함께 검토해야 합니다.")
        else:
            lines.append("- 두 버전의 평균 응답시간은 동일했습니다.")

    if improved_cases:
        lines.append("- 품질 평균이 향상된 문항: " + ", ".join(f"{qid}(+{delta:.1f}%p)" for qid, delta in improved_cases))
    if regressed_cases:
        lines.append("- 품질 평균이 하락한 문항: " + ", ".join(f"{qid}({delta:.1f}%p)" for qid, delta in regressed_cases))

    lines += [
        "",
        "## 6. 누락 항목 진단",
        "",
    ]
    for case in TEST_CASES:
        c = curr_by_id.get(case["id"], {})
        missing_a = c.get("missing_answer_requirements", [])
        missing_e = c.get("missing_evidence_requirements", [])
        if missing_a or missing_e:
            lines.append(f"### {case['id']} — {case['question']}")
            if missing_a:
                lines.append("- 답변 누락: " + ", ".join(missing_a))
            if missing_e:
                lines.append("- 근거 누락: " + "; ".join(missing_e))
            lines.append("")
    if not any(r.get("missing_answer_requirements") or r.get("missing_evidence_requirements") for r in current_detail):
        lines.append("현재 버전에서 정의된 필수 답변 및 근거 항목이 모두 충족되었습니다.")

    lines += [
        "",
        "## 7. 재현 파일",
        "",
        "- `test_cases.json`: 테스트 질문과 정답 기준",
        "- `metrics_by_case.csv`: 버전·문항별 세부 지표",
        "- `evaluation_summary.json`: 종합 지표와 실행 정보",
        "- `raw_baseline_results.json`: 이전 버전 원시 출력",
        "- `raw_current_results.json`: 현재 버전 원시 출력",
        "- `work/baseline/run_stdout.log`, `run_stderr.log`: 이전 버전 실행 로그",
        "- `work/current/run_stdout.log`, `run_stderr.log`: 현재 버전 실행 로그",
        "",
        "## 8. 평가 한계",
        "",
        "- 응답시간은 실행 장비, CPU/GPU 설정, 캐시 상태에 영향을 받습니다.",
        "- 더 엄밀하게 검색 정확도를 평가하기 위해선 Recall@k, MRR, nDCG와 사람 평가 기반 groundedness로써 보완해야 합니다.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------------------------------------------------------
# 7. CLI
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="이전/현재 RAG 버전 정량 비교")
    parser.add_argument("--baseline-script", type=Path, required=True, help="이전 버전 02_rag_faq.py")
    parser.add_argument("--current-script", type=Path, required=True, help="현재 버전 02_rag_faq.py")
    parser.add_argument("--pdf", type=Path, required=True, help="평가 PDF")
    parser.add_argument("--model-dir", type=Path, default=Path("./models"), help="공유 모델 디렉터리")
    parser.add_argument("--output-dir", type=Path, default=Path("./evaluation_outputs"))
    parser.add_argument("--no-ocr", action="store_true", help="OCR 인덱싱을 생략")
    parser.add_argument("--version-timeout", type=int, default=14400, help="버전당 최대 실행시간(초)")

    # 공정 비교용 파라미터
    parser.add_argument("--llm-model", default="qwen3-4b", choices=["qwen2.5-7b", "qwen3-4b"])
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--n-gpu-layers", type=int, default=0)
    parser.add_argument("--dense-k", type=int, default=60)
    parser.add_argument("--bm25-k", type=int, default=60)
    parser.add_argument("--candidate-k", type=int, default=40)
    parser.add_argument("--top-k", type=int, default=14)
    parser.add_argument("--max-context-chunks", type=int, default=24)
    parser.add_argument("--unit-cross-top-n", type=int, default=28)
    parser.add_argument("--max-answer-units", type=int, default=18)
    parser.add_argument("--num-retrieval-queries", type=int, default=3)
    parser.add_argument("--query-planner", default="heuristic", choices=["heuristic", "llm"])
    parser.add_argument("--rerank-pool-k", type=int, default=40)
    parser.add_argument("--composer-token-budget", type=int, default=2600)
    parser.add_argument("--composer-max-tokens", type=int, default=320)
    parser.add_argument("--composer-safety-margin", type=int, default=512)
    parser.add_argument("--max-composer-evidence", type=int, default=12)
    parser.add_argument("--max-composer-sections", type=int, default=3)
    parser.add_argument("--max-chars-per-composer-evidence", type=int, default=1400)
    parser.add_argument("--composer-max-attempts", type=int, default=2)
    parser.add_argument("--llm-timeout", type=int, default=600)
    parser.add_argument("--llm-n-batch", type=int, default=128)
    parser.add_argument("--llm-n-ubatch", type=int, default=128)
    return parser.parse_args()


def validate_paths(args: argparse.Namespace) -> None:
    for label, path in [
        ("baseline script", args.baseline_script),
        ("current script", args.current_script),
        ("PDF", args.pdf),
        ("model directory", args.model_dir),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"{label}을 찾을 수 없습니다: {path}")


def main() -> int:
    args = parse_args()
    validate_paths(args)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    eval_root = output_dir / "work"
    eval_root.mkdir(parents=True, exist_ok=True)

    write_test_cases(output_dir / "test_cases.json")

    print("[1/4] 이전 버전 실행")
    baseline_run = run_version(
        name="baseline",
        source_script=args.baseline_script.resolve(),
        eval_root=eval_root,
        model_dir=args.model_dir.resolve(),
        pdf_path=args.pdf.resolve(),
        args=args,
    )
    print(f"  return_code={baseline_run.return_code}, answers={len(baseline_run.results)}, error={baseline_run.error}")

    print("[2/4] 현재 버전 실행")
    current_run = run_version(
        name="current",
        source_script=args.current_script.resolve(),
        eval_root=eval_root,
        model_dir=args.model_dir.resolve(),
        pdf_path=args.pdf.resolve(),
        args=args,
    )
    print(f"  return_code={current_run.return_code}, answers={len(current_run.results)}, error={current_run.error}")

    print("[3/4] 지표 계산")
    baseline_detail, baseline_summary = evaluate_version(baseline_run)
    current_detail, current_summary = evaluate_version(current_run)
    all_detail = baseline_detail + current_detail

    (output_dir / "raw_baseline_results.json").write_text(
        json.dumps(baseline_run.results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "raw_current_results.json").write_text(
        json.dumps(current_run.results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_detail_csv(output_dir / "metrics_by_case.csv", all_detail)

    summary_payload = {
        "baseline": baseline_summary,
        "current": current_summary,
        "improvement": {
            "answer_completeness_percentage_points": difference(
                current_summary["mean_answer_completeness_pct"],
                baseline_summary["mean_answer_completeness_pct"],
            ),
            "evidence_hit_rate_percentage_points": difference(
                current_summary["mean_evidence_hit_rate_pct"],
                baseline_summary["mean_evidence_hit_rate_pct"],
            ),
            "response_time_seconds": difference(
                current_summary["mean_response_time_sec"],
                baseline_summary["mean_response_time_sec"],
            ),
            "response_time_relative_pct": relative_change(
                current_summary["mean_response_time_sec"],
                baseline_summary["mean_response_time_sec"],
            ),
        },
        "commands": {
            "baseline": baseline_run.command,
            "current": current_run.command,
        },
    }
    (output_dir / "evaluation_summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[4/4] 보고서 작성")
    report_path = output_dir / "evaluation_report.md"
    write_report(
        report_path,
        baseline_run,
        current_run,
        baseline_detail,
        current_detail,
        baseline_summary,
        current_summary,
    )

    print("\n평가 완료")
    print(f"- 보고서: {report_path}")
    print(f"- 요약 JSON: {output_dir / 'evaluation_summary.json'}")
    print(f"- 문항별 CSV: {output_dir / 'metrics_by_case.csv'}")
    print(f"- 테스트 케이스: {output_dir / 'test_cases.json'}")

    # 한 버전이라도 실행 실패하면 CI에서 감지할 수 있도록 비정상 코드 반환
    return 0 if baseline_run.return_code == 0 and current_run.return_code == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
