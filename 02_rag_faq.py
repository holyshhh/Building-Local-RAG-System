import argparse
import gc
import time
import json
import os
import re
import shutil
import select
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import fitz
import numpy as np
import pdfplumber
from PIL import Image
from rank_bm25 import BM25Okapi
from rich.console import Console
from sentence_transformers import CrossEncoder, SentenceTransformer
from tqdm import tqdm


console = Console()

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache"
OUTPUT_DIR = BASE / "outputs"
MODEL_DIR = BASE / "models"

EMBED_MODEL_PATH = MODEL_DIR / "multilingual-e5-small"
RERANKER_MODEL_PATH = MODEL_DIR / "bge-reranker-v2-m3"
LLM_PROFILES = {
    "qwen2.5-7b": {
        "label": "Qwen2.5-7B-Instruct-GGUF Q4_K_M",
        "path": MODEL_DIR
        / "qwen2.5-7b-instruct-gguf"
        / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
    },
    "qwen3-4b": {
        "label": "Qwen3-4B-GGUF Q4_K_M",
        "path": MODEL_DIR
        / "qwen3-4b-gguf"
        / "Qwen3-4B-Q4_K_M.gguf",
    },
}
DEFAULT_LLM_MODEL = "qwen3-4b"
LLM_MODEL_PATH = LLM_PROFILES[DEFAULT_LLM_MODEL]["path"]

DEFAULT_PDF_CANDIDATES = [
    Path("/home/project/data/개인통관고유부호 발급 시스템이용 FAQ.pdf"),
]

PROBLEM_SET = [
    {
        "id": "q1",
        "question": "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
    },
    {
        "id": "q2",
        "question": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
    },
]

@dataclass
class Chunk:
    chunk_id: str
    source_title: str
    page: int
    kind: str
    locator: str
    text: str
    bbox: Optional[List[float]] = None
    page_end: Optional[int] = None
    parent_id: Optional[str] = None

    role: Optional[str] = None
    anchor_text: Optional[str] = None
    answer_text: Optional[str] = None



def resolve_pdf_path(user_path: Optional[str]) -> Path:
    candidates: List[Path] = []

    if user_path:
        candidates.append(Path(user_path))

    candidates.extend([Path(p) for p in DEFAULT_PDF_CANDIDATES])

    for p in candidates:
        if p.exists():
            return p

    msg = "PDF 파일을 찾지 못했습니다. 확인한 경로:\n" + "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(msg)


def clean_text(text: Any) -> str:
    text = str(text).replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_space(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def split_long_text(text: str, max_chars: int = 900, overlap: int = 120) -> List[str]:
    text = clean_text(text)

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    pieces = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        piece = text[start:end]

        if end < len(text):
            cut = max(
                piece.rfind("\n"),
                piece.rfind(". "),
                piece.rfind("? "),
                piece.rfind("다."),
            )
            if cut > max_chars * 0.55:
                piece = piece[: cut + 1]
                end = start + cut + 1

        piece = clean_text(piece)
        if piece:
            pieces.append(piece)

        if end >= len(text):
            break

        start = max(0, end - overlap)

    return pieces


def table_to_markdown(table: List[List[Any]]) -> str:
    rows = []

    for row in table:
        if row is None:
            continue

        cleaned = [clean_text(cell) if cell is not None else "" for cell in row]
        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        return ""

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]

    header = rows[0]
    body = rows[1:]

    md = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]

    for row in body:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)


def block_number_from_chunk_id(chunk_id: str) -> Optional[int]:
    m = re.search(r"_text_b(\d+)_", chunk_id)
    if not m:
        return None
    return int(m.group(1))


def extract_text_chunks(pdf_path: Path, source_title: str) -> List[Chunk]:
    chunks: List[Chunk] = []
    doc = fitz.open(pdf_path)

    for page_idx, page in enumerate(tqdm(doc, desc="PyMuPDF text blocks")):
        page_no = page_idx + 1
        blocks = page.get_text("blocks")
        blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))

        for block_idx, block in enumerate(blocks):
            if len(block) < 5:
                continue

            x0, y0, x1, y1, text = block[:5]
            text = clean_text(text)

            if len(text) < 10:
                continue

            for sub_idx, piece in enumerate(split_long_text(text)):
                chunks.append(
                    Chunk(
                        chunk_id=f"p{page_no}_text_b{block_idx}_{sub_idx}",
                        source_title=source_title,
                        page=page_no,
                        page_end=page_no,
                        kind="text",
                        locator=f"텍스트블록 {block_idx}, 분할 {sub_idx}",
                        text=piece,
                        bbox=[float(x0), float(y0), float(x1), float(y1)],
                    )
                )

    doc.close()
    return chunks


SECTION_HEADING_RE = re.compile(r"^\s*(\d{1,2})\.\s+(.+?)\s*$")
TOC_HEADING_RE = re.compile(r"^\s*Q\s*(\d{1,2})\.\s*(.+?)\s*(?:[·.․…]+\s*)?(\d{1,2})\s*$", re.IGNORECASE)


def normalize_heading_title(text: str) -> str:
    text = normalize_space(text)
    text = re.sub(r"^Q?\s*\d{1,2}\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[·.․…]+\s*\d{1,2}\s*$", "", text)
    text = re.sub(r"\s+\d{1,2}\s*$", "", text)
    text = re.sub(r"[^가-힣a-zA-Z0-9]+", "", text).lower()
    return text


def extract_toc_heading_map(block_chunks: List[Chunk]) -> Dict[str, str]:
    """목차에서 FAQ 번호와 제목을 추출"""
    toc_map: Dict[str, str] = {}
    lines: List[str] = []
    for c in block_chunks:
        if c.page > 2:
            continue
        for line in str(c.text).splitlines():
            t = normalize_space(line)
            if t:
                lines.append(t)

    pending: Optional[str] = None
    for t in lines:
        if re.match(r"^Q\s*\d{1,2}\.", t, flags=re.IGNORECASE):
            if pending:
                m0 = re.match(r"^Q\s*(\d{1,2})\.\s*(.+)$", pending, flags=re.IGNORECASE)
                if m0:
                    title0 = normalize_heading_title(m0.group(2))
                    if len(title0) >= 4:
                        toc_map[m0.group(1)] = title0
            pending = t
        elif pending:
            pending = normalize_space(pending + " " + t)

        if pending:
            m = TOC_HEADING_RE.match(pending)
            if m:
                title = normalize_heading_title(m.group(2))
                if len(title) >= 4:
                    toc_map[m.group(1)] = title
                pending = None

    if pending:
        m = re.match(r"^Q\s*(\d{1,2})\.\s*(.+)$", pending, flags=re.IGNORECASE)
        if m:
            title = normalize_heading_title(m.group(2))
            if len(title) >= 4:
                toc_map[m.group(1)] = title
    return toc_map


def is_section_heading_text(text: str, toc_heading_map: Optional[Dict[str, str]] = None) -> bool:
    """텍스트 블록이 FAQ 섹션 제목인지 판단"""
    t = normalize_space(text)
    m = SECTION_HEADING_RE.match(t)
    if not m:
        return False
    if "··" in t or "…" in t:
        return False
    if len(t) > 140:
        return False

    section_no = m.group(1)
    title_norm = normalize_heading_title(m.group(2))

    if toc_heading_map:
        toc_title = toc_heading_map.get(section_no)
        if toc_title:
            if title_norm == toc_title:
                return True
            if title_norm and (title_norm in toc_title or toc_title in title_norm):
                return True
            common = set(title_norm) & set(toc_title)
            denom = max(len(set(title_norm) | set(toc_title)), 1)
            return len(common) / denom >= 0.72

        # 목차 파싱 실패가 section 경계 전체를 무너뜨리지 않도록 독립적인 질문형 제목도 허용
        # 번호, 짧은 제목, 질문형 어미를 모두 포함해 본문의 번호 목록을 제목으로 오인하는 위험 축소
        if len(title_norm) >= 6 and re.search(r"(나요|까요|어요|아요|싶어요|해주세요|알려주세요|안돼요)$", t):
            return True
        return False


    if "다음과같습니다" in normalize_heading_title(t):
        return False
    return True


def build_section_chunks_from_blocks(
    block_chunks: List[Chunk],
    source_title: str,
    max_chars: int = 4500,
    overlap: int = 250,
) -> Tuple[List[Chunk], Dict[str, str]]:
    """텍스트 블록을 FAQ 섹션 단위의 parent chunk로 묶기"""
    def block_sort_key(c: Chunk) -> Tuple[int, int]:
        block_no = block_number_from_chunk_id(c.chunk_id)
        return (c.page, block_no if block_no is not None else 10_000)

    ordered = sorted(
        [c for c in block_chunks if c.kind == "text"],
        key=block_sort_key,
    )

    toc_heading_map = extract_toc_heading_map(ordered)

    heading_positions = []
    for i, c in enumerate(ordered):
        if is_section_heading_text(c.text, toc_heading_map=toc_heading_map):
            m = SECTION_HEADING_RE.match(normalize_space(c.text))
            section_no = m.group(1) if m else str(len(heading_positions) + 1)
            heading_positions.append((i, section_no, c.text))

    if not heading_positions:
        return [], {}

    section_chunks: List[Chunk] = []
    parent_map: Dict[str, str] = {}

    for pos_idx, (start_i, section_no, heading_text) in enumerate(heading_positions):
        end_i = heading_positions[pos_idx + 1][0] if pos_idx + 1 < len(heading_positions) else len(ordered)
        section_blocks = ordered[start_i:end_i]

        if len(section_blocks) < 2:
            continue

        heading_chunk = section_blocks[0]
        body_blocks = section_blocks[1:]

        start_page = section_blocks[0].page
        end_page = section_blocks[-1].page
        anchor_text = clean_text(heading_text)
        retrieval_text = clean_text("\n".join(clean_text(c.text) for c in section_blocks if clean_text(c.text)))
        answer_view_text = clean_text("\n".join(clean_text(c.text) for c in body_blocks if clean_text(c.text)))

        if len(retrieval_text) < 30 or len(answer_view_text) < 10:
            continue


        heading_chunk.role = "anchor_question"
        heading_chunk.anchor_text = anchor_text
        heading_chunk.answer_text = None
        for body in body_blocks:
            if body.role is None:
                body.role = "body"
            body.anchor_text = anchor_text

        pieces = split_long_text(retrieval_text, max_chars=max_chars, overlap=overlap)
        answer_pieces = split_long_text(answer_view_text, max_chars=max_chars, overlap=overlap)

        for sub_idx, piece in enumerate(pieces):
            section_id = f"section_{section_no}_{sub_idx}"
            locator = f"섹션 {section_no}, p.{start_page}" if start_page == end_page else f"섹션 {section_no}, p.{start_page}-{end_page}"
            answer_text_piece = answer_pieces[min(sub_idx, len(answer_pieces) - 1)] if answer_pieces else answer_view_text
            section_chunks.append(
                Chunk(
                    chunk_id=section_id,
                    source_title=source_title,
                    page=start_page,
                    page_end=end_page,
                    kind="section",
                    locator=f"{locator}, 분할 {sub_idx}",
                    text=piece,
                    bbox=None,
                    parent_id=None,
                    role="section",
                    anchor_text=anchor_text,
                    answer_text=answer_text_piece,
                )
            )

        primary_parent_id = f"section_{section_no}_0"
        for c in section_blocks:
            parent_map[c.chunk_id] = primary_parent_id
            c.parent_id = primary_parent_id


    for c in ordered:
        if c.role is None:
            if TOC_HEADING_RE.match(normalize_space(c.text)):
                c.role = "toc"
            else:
                c.role = "body"

    return section_chunks, parent_map

def extract_table_chunks(pdf_path: Path, source_title: str) -> List[Chunk]:
    chunks: List[Chunk] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(tqdm(pdf.pages, desc="pdfplumber tables")):
            page_no = page_idx + 1

            try:
                tables = page.extract_tables()
            except Exception as e:
                console.print(f"[yellow]표 추출 실패 p.{page_no}: {e}[/yellow]")
                continue

            for table_idx, table in enumerate(tables or []):
                md = table_to_markdown(table)

                if len(md) < 20:
                    continue

                for sub_idx, piece in enumerate(split_long_text(md, max_chars=1200, overlap=100)):
                    chunks.append(
                        Chunk(
                            chunk_id=f"p{page_no}_table_t{table_idx}_{sub_idx}",
                            source_title=source_title,
                            page=page_no,
                            page_end=page_no,
                            kind="table",
                            locator=f"표 {table_idx}, 분할 {sub_idx}",
                            text="[표 추출]\n" + piece,
                            bbox=None,
                            parent_id=None,
                        )
                    )

    return chunks


def can_use_tesseract() -> bool:
    return shutil.which("tesseract") is not None


def extract_ocr_chunks(pdf_path: Path, source_title: str, dpi_scale: float = 2.0) -> List[Chunk]:
    chunks: List[Chunk] = []

    if not can_use_tesseract():
        console.print("[yellow]tesseract executable이 없어 OCR을 건너뜁니다.[/yellow]")
        return chunks

    try:
        import pytesseract
    except Exception as e:
        console.print(f"[yellow]pytesseract import 실패로 OCR을 건너뜁니다: {e}[/yellow]")
        return chunks

    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(dpi_scale, dpi_scale)

    for page_idx, page in enumerate(tqdm(doc, desc="OCR page images")):
        page_no = page_idx + 1

        try:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.open(BytesIO(pix.tobytes("png")))

            try:
                text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 6")
            except Exception:
                text = pytesseract.image_to_string(img, config="--psm 6")

            text = clean_text(text)
        except Exception as e:
            console.print(f"[yellow]OCR 실패 p.{page_no}: {e}[/yellow]")
            continue

        if len(text) < 30:
            continue

        for sub_idx, piece in enumerate(split_long_text(text, max_chars=1000, overlap=120)):
            chunks.append(
                Chunk(
                    chunk_id=f"p{page_no}_ocr_{sub_idx}",
                    source_title=source_title,
                    page=page_no,
                    page_end=page_no,
                    kind="ocr",
                    locator=f"페이지 이미지 OCR {sub_idx}",
                    text="[이미지/OCR 추출]\n" + piece,
                    bbox=None,
                    parent_id=None,
                )
            )

    doc.close()
    return chunks


def page_text_lengths(chunks: List[Chunk]) -> Dict[int, int]:
    lengths: Dict[int, int] = {}
    for c in chunks:
        if c.kind in {"text", "section"}:
            lengths[c.page] = lengths.get(c.page, 0) + len(c.text)
    return lengths


def filter_ocr_chunks_for_index(
    ocr_chunks: List[Chunk],
    clean_text_chunks: List[Chunk],
    min_clean_chars_per_page: int = 80,
) -> List[Chunk]:
    """텍스트 레이어가 부족한 페이지만 OCR chunk로 남김"""
    lengths = page_text_lengths(clean_text_chunks)
    filtered = []
    for c in ocr_chunks:
        if lengths.get(c.page, 0) < min_clean_chars_per_page:
            filtered.append(c)
    return filtered


def extract_all_chunks(pdf_path: Path, use_ocr: bool, include_noisy_ocr: bool = False) -> List[Chunk]:
    """PDF에서 텍스트, 섹션, 표, OCR chunk를 모두 추출"""
    source_title = pdf_path.name

    text_chunks = extract_text_chunks(pdf_path, source_title)
    section_chunks, parent_map = build_section_chunks_from_blocks(text_chunks, source_title)

    for c in text_chunks:
        if c.chunk_id in parent_map:
            c.parent_id = parent_map[c.chunk_id]

    table_chunks = extract_table_chunks(pdf_path, source_title)

    ocr_chunks: List[Chunk] = []
    if use_ocr:


        ocr_chunks = extract_ocr_chunks(pdf_path, source_title)

    chunks = []
    chunks.extend(section_chunks)
    chunks.extend(text_chunks)
    chunks.extend(table_chunks)
    chunks.extend(ocr_chunks)

    seen = set()
    unique = []

    for c in chunks:

        key = (c.kind, re.sub(r"\s+", " ", c.text)[:900])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


def save_chunks(chunks: List[Chunk]) -> None:
    CACHE_DIR.mkdir(exist_ok=True, parents=True)

    with open(CACHE_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def load_chunks() -> List[Chunk]:
    path = CACHE_DIR / "chunks.jsonl"

    if not path.exists():
        raise FileNotFoundError("cache/chunks.jsonl이 없습니다. 먼저 --rebuild를 실행하세요.")

    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)

            for key in ["bbox", "page_end", "parent_id", "role", "anchor_text", "answer_text"]:
                data.setdefault(key, None)
            chunks.append(Chunk(**data))

    return chunks


def e5_passage(text: str) -> str:
    return "passage: " + text


def e5_query(text: str) -> str:
    return "query: " + text


@lru_cache(maxsize=1)
def get_embedder():
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer(str(EMBED_MODEL_PATH), device=device)


@lru_cache(maxsize=1)
def get_reranker():
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if RERANKER_MODEL_PATH.exists():
        return CrossEncoder(str(RERANKER_MODEL_PATH), device=device)

    console.print("[yellow]로컬 reranker가 없어 Hugging Face id로 로드합니다. 사전 설치를 권장합니다.[/yellow]")
    return CrossEncoder("BAAI/bge-reranker-v2-m3", device=device)


def build_index(chunks: List[Chunk]) -> None:
    if not EMBED_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"임베딩 모델이 없습니다: {EMBED_MODEL_PATH}. install_models.py에서 먼저 다운로드하세요."
        )

    embedder = get_embedder()
    texts = [e5_passage(c.text) for c in chunks]

    embeddings = embedder.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    faiss.write_index(index, str(CACHE_DIR / "faiss.index"))
    np.save(CACHE_DIR / "embeddings.npy", embeddings)


def load_index():
    index_path = CACHE_DIR / "faiss.index"

    if not index_path.exists():
        raise FileNotFoundError("cache/faiss.index가 없습니다. 먼저 --rebuild를 실행하세요.")

    return faiss.read_index(str(index_path))


STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "에", "에서", "으로", "로",
    "와", "과", "도", "만", "및", "또는", "그리고", "하라", "하세요",
    "답하세요", "알려주세요", "나열하세요", "이상", "중", "시", "때",
    "경우", "대한", "대해", "함께",
}


def normalize_for_tokenize(text: str) -> str:
    text = str(text).lower()
    text = text.replace("·", " ")
    text = text.replace("ㆍ", " ")
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = re.sub(r"[^가-힣a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str, min_len: int = 1) -> List[str]:
    norm = normalize_for_tokenize(text)
    terms = re.findall(r"[가-힣a-z0-9]+", norm)

    cleaned = []
    for term in terms:
        if len(term) < min_len:
            continue
        if term in STOPWORDS:
            continue
        cleaned.append(term)

    return cleaned


def reciprocal_rank_fusion(ranked_lists: List[List[int]], k: int = 60) -> Dict[int, float]:
    scores: Dict[int, float] = {}

    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    return scores


_BM25_CACHE_KEY = None
_BM25_CACHE = None

def get_bm25_index(chunks: List[Chunk]):
    """같은 chunk 집합에 대해 BM25 corpus를 한 번만 구성"""
    global _BM25_CACHE_KEY, _BM25_CACHE
    key = (len(chunks), chunks[0].chunk_id if chunks else None, chunks[-1].chunk_id if chunks else None)
    if _BM25_CACHE is None or _BM25_CACHE_KEY != key:
        tokenized_corpus = [tokenize(c.text) for c in chunks]
        _BM25_CACHE = BM25Okapi(tokenized_corpus)
        _BM25_CACHE_KEY = key
    return _BM25_CACHE

def first_stage_retrieve(
    question: str,
    chunks: List[Chunk],
    index,
    dense_k: int = 80,
    bm25_k: int = 80,
    rrf_k: int = 60,
    candidate_k: int = 50,
) -> List[Dict[str, Any]]:
    embedder = get_embedder()

    q_emb = embedder.encode(
        [e5_query(question)],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    dense_k = min(dense_k, len(chunks))
    dense_scores, dense_ids = index.search(q_emb, dense_k)

    dense_ranked = [int(i) for i in dense_ids[0] if int(i) >= 0]
    dense_score_map = {
        int(idx): float(score)
        for idx, score in zip(dense_ids[0], dense_scores[0])
        if int(idx) >= 0
    }

    bm25 = get_bm25_index(chunks)
    bm25_scores = bm25.get_scores(tokenize(question))

    bm25_ranked = np.argsort(-bm25_scores)[: min(bm25_k, len(chunks))].tolist()
    bm25_score_map = {int(i): float(bm25_scores[i]) for i in bm25_ranked}

    rrf_scores = reciprocal_rank_fusion([dense_ranked, bm25_ranked], k=rrf_k)
    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:candidate_k]

    results = []
    for rank, (idx, rrf_score) in enumerate(fused, start=1):
        results.append(
            {
                "rank": rank,
                "chunk_index": idx,
                "rrf_score": float(rrf_score),
                "dense_score": float(dense_score_map.get(idx, 0.0)),
                "bm25_score": float(bm25_score_map.get(idx, 0.0)),
                "rerank_score": None,
                "chunk": chunks[idx],
                "source": "hybrid_rrf",
            }
        )

    return results


def rerank(
    question: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 16,
    enabled: bool = True,
) -> List[Dict[str, Any]]:
    if not enabled or not candidates:
        return candidates[:top_k]

    reranker = get_reranker()
    pairs = [(question, c["chunk"].text) for c in candidates]
    scores = reranker.predict(pairs, batch_size=32, show_progress_bar=False)

    rescored = []
    for item, score in zip(candidates, scores):
        copied = dict(item)
        copied["rerank_score"] = float(score)
        rescored.append(copied)

    rescored.sort(key=lambda x: x["rerank_score"], reverse=True)

    for rank, item in enumerate(rescored[:top_k], start=1):
        item["rank"] = rank

    return rescored[:top_k]


def parse_text_block_number(locator: str) -> Optional[int]:
    m = re.search(r"텍스트블록\s+(\d+)", locator)
    if not m:
        return None
    return int(m.group(1))


def add_parent_sections(
    hits: List[Dict[str, Any]],
    chunks: List[Chunk],
) -> List[Dict[str, Any]]:
    """검색된 하위 블록에 연결된 FAQ parent section을 함께 추가"""
    chunk_by_id = {c.chunk_id: (idx, c) for idx, c in enumerate(chunks)}
    selected = {h["chunk"].chunk_id: h for h in hits}
    output = list(hits)

    for h in hits:
        c = h["chunk"]
        if not c.parent_id:
            continue

        parent_pair = chunk_by_id.get(c.parent_id)
        if parent_pair is None:
            continue

        parent_idx, parent = parent_pair
        if parent.chunk_id in selected:
            continue

        parent_item = {
            "rank": h["rank"],
            "chunk_index": parent_idx,
            "rrf_score": h.get("rrf_score", 0.0),
            "dense_score": h.get("dense_score", 0.0),
            "bm25_score": h.get("bm25_score", 0.0),
            "rerank_score": h.get("rerank_score", None),
            "chunk": parent,
            "source": "parent_section_expansion",
            "context_type": "parent_section",
            "expanded_from": c.chunk_id,
        }
        output.append(parent_item)
        selected[parent.chunk_id] = parent_item

    return output


def expand_neighbors(
    hits: List[Dict[str, Any]],
    chunks: List[Chunk],
    window: int = 2,
    max_context_chunks: int = 28,
) -> List[Dict[str, Any]]:
    hits = add_parent_sections(hits, chunks)

    page_block_index: Dict[Tuple[int, int], Tuple[int, Chunk]] = {}

    for idx, c in enumerate(chunks):
        if c.kind != "text":
            continue
        block_no = parse_text_block_number(c.locator)
        if block_no is not None:
            page_block_index[(c.page, block_no)] = (idx, c)

    selected: Dict[str, Dict[str, Any]] = {}

    for h in hits:
        c = h["chunk"]
        selected[c.chunk_id] = {
            **h,
            "context_type": h.get("context_type", "retrieved"),
            "expanded_from": h.get("expanded_from", c.chunk_id),
        }

        if c.kind != "text":
            continue

        block_no = parse_text_block_number(c.locator)
        if block_no is None:
            continue

        for nb in range(block_no - window, block_no + window + 1):
            pair = page_block_index.get((c.page, nb))
            if pair is None:
                continue

            idx, neighbor = pair
            if neighbor.chunk_id in selected:
                continue

            selected[neighbor.chunk_id] = {
                "rank": h["rank"],
                "chunk_index": idx,
                "rrf_score": h.get("rrf_score", 0.0),
                "dense_score": h.get("dense_score", 0.0),
                "bm25_score": h.get("bm25_score", 0.0),
                "rerank_score": h.get("rerank_score", None),
                "chunk": neighbor,
                "source": "neighbor_expansion",
                "context_type": "neighbor",
                "expanded_from": c.chunk_id,
            }

    expanded = list(selected.values())

    def sort_key(item):
        c = item["chunk"]
        rank = int(item.get("rank", 9999))

        kind_order = {"section": 0, "text": 1, "table": 2, "ocr": 3}.get(c.kind, 9)
        block_no = parse_text_block_number(c.locator)
        block_no = 100000 if block_no is None else block_no
        return (rank, kind_order, c.page, block_no)

    expanded.sort(key=sort_key)
    return expanded[:max_context_chunks]



@dataclass
class AnswerUnit:
    unit_id: str
    text: str
    title: str
    page: str
    locator: str
    source_chunk_id: str
    source_kind: str
    source_role: Optional[str]
    context_rank: int
    context_type: str
    score: float = 0.0
    cross_score: Optional[float] = None


def answer_view_for_chunk(chunk: Chunk) -> str:
    """chunk 종류에 맞춰 답변 후보로 사용할 본문을 반환"""
    if chunk.answer_text:
        return clean_text(chunk.answer_text)
    if chunk.role in {"anchor_question", "toc"}:
        return ""
    return clean_text(chunk.text)


def strip_anchor_lines(text: str) -> str:
    """FAQ 제목이나 목차 줄을 제외하고 본문만 남김"""
    lines = [clean_text(x) for x in str(text).splitlines() if clean_text(x)]
    kept = []
    for i, line in enumerate(lines):
        if i == 0 and (TOC_HEADING_RE.match(line) or is_section_heading_text(line)):
            continue
        kept.append(line)
    return clean_text("\n".join(kept))


def get_llm_model_path(model_key: str) -> Path:
    if model_key not in LLM_PROFILES:
        valid = ", ".join(LLM_PROFILES.keys())
        raise ValueError(f"지원하지 않는 LLM 모델입니다: {model_key}. 사용 가능: {valid}")
    return Path(LLM_PROFILES[model_key]["path"])


def get_llm_model_label(model_key: str) -> str:
    if model_key not in LLM_PROFILES:
        return model_key
    return str(LLM_PROFILES[model_key].get("label", model_key))



class SubprocessLlamaClient:
    """LLM을 별도 장기 실행 프로세스에서 호출해 메인 RAG 프로세스를 보호"""

    def __init__(
        self,
        model_key: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        n_batch: int = 128,
        n_ubatch: int = 128,
        timeout: int = 240,
        force_cpu: bool = True,
        max_restarts: int = 1,
    ):
        self.model_key = model_key
        self.model_path = get_llm_model_path(model_key)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"LLM GGUF가 없습니다: {self.model_path}. 01_install_models.py에서 먼저 다운로드하세요."
            )
        self.n_ctx = int(n_ctx)
        self.n_gpu_layers = 0 if force_cpu else int(n_gpu_layers)
        self.n_batch = int(n_batch)
        self.n_ubatch = int(n_ubatch)
        self.timeout = int(timeout)
        self.force_cpu = bool(force_cpu)
        self.max_restarts = int(max_restarts)
        self.proc: Optional[subprocess.Popen] = None
        self.stderr_file = None
        self.stderr_path: Optional[Path] = None
        self._request_id = 0
        self._start_worker()

    def _worker_code(self) -> str:
        return r'''
import json
import os
import sys
import traceback

cfg = json.loads(sys.argv[1])

if cfg.get("force_cpu", True):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["LLAMA_ARG_DEVICE"] = "none"
    os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

from llama_cpp import Llama

base_kwargs = {
    "model_path": cfg["model_path"],
    "n_ctx": int(cfg.get("n_ctx", 4096)),
    "n_gpu_layers": 0 if cfg.get("force_cpu", True) else int(cfg.get("n_gpu_layers", 0)),
    "n_batch": int(cfg.get("n_batch", 128)),
    "n_threads": max(2, os.cpu_count() or 4),
    "verbose": False,
}
optional_kwargs = {
    "n_ubatch": int(cfg.get("n_ubatch", 128)),
    "offload_kqv": False if cfg.get("force_cpu", True) else True,
    "flash_attn": False,
    "op_offload": False,
}

kwargs = dict(base_kwargs)
kwargs.update(optional_kwargs)
try:
    llm = Llama(**kwargs)
except TypeError:
    kwargs = dict(base_kwargs)
    for k in ["offload_kqv", "flash_attn"]:
        kwargs[k] = optional_kwargs[k]
    try:
        llm = Llama(**kwargs)
    except TypeError:
        llm = Llama(**base_kwargs)

for line in sys.stdin:
    try:
        req = json.loads(line)
        req_id = req.get("request_id")
        op = req.get("op", "chat")
        if op == "count_chat_tokens":
            messages = req["messages"]
            # llama.cpp가 실제 completion에 적용하는 chat template까지 포함해 계산한다.
            try:
                rendered = llm.apply_chat_template(messages, add_generation_prompt=True)
                if isinstance(rendered, str):
                    token_count = len(llm.tokenize(rendered.encode("utf-8"), add_bos=False, special=True))
                else:
                    token_count = len(rendered)
            except Exception:
                # 구버전 llama-cpp-python 호환 경로
                joined = "\n".join(str(m.get("role", "")) + ": " + str(m.get("content", "")) for m in messages)
                token_count = len(llm.tokenize(joined.encode("utf-8"), add_bos=True, special=True)) + 16
            print(json.dumps({"ok": True, "request_id": req_id, "response": {"token_count": token_count}}, ensure_ascii=False), flush=True)
            continue

        call_kwargs = {
            "messages": req["messages"],
            "temperature": float(req.get("temperature", 0.0)),
            "top_p": float(req.get("top_p", 0.9)),
            "max_tokens": int(req.get("max_tokens", 512)),
        }
        if req.get("response_format") is not None:
            call_kwargs["response_format"] = req.get("response_format")
        resp = llm.create_chat_completion(**call_kwargs)
        print(json.dumps({"ok": True, "request_id": req_id, "response": resp}, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "request_id": req.get("request_id") if isinstance(req, dict) else None,
            "error": str(e),
            "traceback": traceback.format_exc()[-4000:],
        }, ensure_ascii=False), flush=True)
'''

    def _start_worker(self) -> None:
        self.close()
        cfg = {
            "model_path": str(self.model_path),
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": self.n_batch,
            "n_ubatch": self.n_ubatch,
            "force_cpu": self.force_cpu,
        }
        env = os.environ.copy()
        env.setdefault("TOKENIZERS_PARALLELISM", "false")
        if self.force_cpu:
            env["CUDA_VISIBLE_DEVICES"] = ""
            env["LLAMA_ARG_DEVICE"] = "none"
            env["LLAMA_CPP_LOG_LEVEL"] = "ERROR"
        stderr_dir = CACHE_DIR / "llm_worker_logs"
        stderr_dir.mkdir(exist_ok=True, parents=True)
        self.stderr_path = stderr_dir / f"{self.model_key.replace('.', '_')}_worker_stderr.log"
        self.stderr_file = open(self.stderr_path, "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-c", self._worker_code(), json.dumps(cfg, ensure_ascii=False)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr_file,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            bufsize=1,
        )

    def _stderr_tail(self, n: int = 4000) -> str:
        if not self.stderr_path or not self.stderr_path.exists():
            return ""
        try:
            return self.stderr_path.read_text(encoding="utf-8", errors="replace")[-n:]
        except Exception:
            return ""

    def _send_once(self, req: Dict[str, Any]) -> Dict[str, Any]:
        if self.proc is None or self.proc.poll() is not None:
            raise RuntimeError(f"LLM worker is not running. stderr_tail={self._stderr_tail()}")
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        fd = self.proc.stdout.fileno()
        ready, _, _ = select.select([fd], [], [], self.timeout)
        if not ready:
            self.kill()
            raise TimeoutError(f"LLM worker timeout after {self.timeout}s. stderr_tail={self._stderr_tail()}")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"LLM worker ended without response. returncode={self.proc.poll()} stderr_tail={self._stderr_tail()}")
        obj = json.loads(line)
        if not obj.get("ok"):
            raise RuntimeError(f"LLM worker returned error: {obj.get('error')}\n{obj.get('traceback', '')}")
        return obj["response"]

    def tokenize(self, data: bytes) -> List[int]:
        text = data.decode("utf-8", errors="ignore") if isinstance(data, (bytes, bytearray)) else str(data)
        return [0] * estimate_token_count(text)

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        top_p: float = 0.9,
        max_tokens: int = 512,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        self._request_id += 1
        req = {
            "request_id": self._request_id,
            "op": "chat",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "response_format": response_format,
        }
        last_error = None
        for attempt in range(self.max_restarts + 1):
            try:
                return self._send_once(req)
            except Exception as e:
                last_error = e
                if attempt >= self.max_restarts:
                    break
                self._start_worker()
        raise RuntimeError(f"LLM worker failed after restart attempts: {last_error}")

    def count_chat_tokens(self, messages: List[Dict[str, str]]) -> int:
        """worker 내부의 실제 GGUF tokenizer와 chat template으로 prompt token 수를 계산한다."""
        self._request_id += 1
        req = {
            "request_id": self._request_id,
            "op": "count_chat_tokens",
            "messages": messages,
        }
        last_error = None
        for attempt in range(self.max_restarts + 1):
            try:
                resp = self._send_once(req)
                return int(resp["token_count"])
            except Exception as e:
                last_error = e
                if attempt >= self.max_restarts:
                    break
                self._start_worker()
        raise RuntimeError(f"LLM token counting failed after restart attempts: {last_error}")

    def kill(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except Exception:
                pass
        self.proc = None

    def close(self) -> None:
        if getattr(self, "proc", None) is not None:
            try:
                if self.proc.poll() is None:
                    if self.proc.stdin:
                        self.proc.stdin.close()
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=5)
                    except Exception:
                        self.proc.kill()
            except Exception:
                pass
            self.proc = None
        if getattr(self, "stderr_file", None) is not None:
            try:
                self.stderr_file.close()
            except Exception:
                pass
            self.stderr_file = None

    def __del__(self):
        self.close()

def estimate_token_count(text: str) -> int:
    """GGUF tokenizer를 매번 띄우지 않기 위한 보수적 토큰 수 추정"""
    text = str(text)
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    non_ascii_chars = len(text) - ascii_chars
    return max(1, int(ascii_chars / 4) + int(non_ascii_chars / 1.7) + 32)


def load_llm(
    n_ctx: int = 8192,
    n_gpu_layers: int = 0,
    model_key: str = DEFAULT_LLM_MODEL,
    llm_backend: str = "subprocess",
    llm_force_cpu: bool = True,
    n_batch: int = 128,
    n_ubatch: int = 128,
    llm_timeout: int = 240,
):
    model_path = get_llm_model_path(model_key)
    if not model_path.exists():
        raise FileNotFoundError(
            f"LLM GGUF가 없습니다: {model_path}. 01_install_models.py에서 먼저 다운로드하세요."
        )

    if llm_backend == "subprocess":
        return SubprocessLlamaClient(
            model_key=model_key,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_batch=n_batch,
            n_ubatch=n_ubatch,
            timeout=llm_timeout,
            force_cpu=llm_force_cpu,
        )

    from llama_cpp import Llama

    try:
        return Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_batch=n_batch,
            n_ubatch=n_ubatch,
            n_threads=max(2, os.cpu_count() or 4),
            offload_kqv=not llm_force_cpu,
            op_offload=False if llm_force_cpu else None,
            flash_attn=False,
            verbose=False,
        )
    except Exception as e:
        console.print(f"[yellow]{model_key} 직접 로딩 실패. CPU 설정으로 재시도합니다: {e}[/yellow]")
        return Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=0,
            n_batch=n_batch,
            n_ubatch=n_ubatch,
            n_threads=max(2, os.cpu_count() or 4),
            offload_kqv=False,
            op_offload=False,
            flash_attn=False,
            verbose=False,
        )

def safe_json_loads(text: str) -> Dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"JSON 객체를 찾지 못했습니다:\n{text}")

    return json.loads(m.group(0))


def count_llama_tokens(llm, text: str) -> int:
    if hasattr(llm, "tokenize"):
        try:
            return len(llm.tokenize(str(text).encode("utf-8")))
        except Exception:
            pass
    return estimate_token_count(text)


UNIT_START_RE = re.compile(r"^\s*(?:[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\d+[\.)]|[‣∎•○●※*\-])\s*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[다요]\.)\s+|(?<=니다\.)\s+|(?<=습니다\.)\s+|(?<=합니다\.)\s+")


def split_answer_units_from_text(text: str, max_unit_chars: int = 1500) -> List[str]:
    """본문 텍스트를 답변 후보 unit으로 나눔"""
    body = strip_anchor_lines(text)
    raw_lines = [clean_text(x) for x in str(body).splitlines() if clean_text(x)]
    if not raw_lines:
        return []

    units: List[str] = []
    current: List[str] = []

    for line in raw_lines:
        starts_new = bool(UNIT_START_RE.match(line))


        if not starts_new and re.match(r"^\s*[A-Z]?[\[\(]?.{0,12}[:：]", line) and len(line) < 600:
            starts_new = bool(current) and (line.count(":") + line.count("：") > 0)

        if starts_new and current:
            units.append(normalize_space(" ".join(current)))
            current = [line]
        else:
            current.append(line)

    if current:
        units.append(normalize_space(" ".join(current)))

    refined: List[str] = []
    for unit in units:
        unit = normalize_space(unit)
        if not unit:
            continue


        list_like = list_signal_score(unit) >= 1.2 or "," in unit or "，" in unit or "http" in unit
        if len(unit) > max_unit_chars and not list_like:
            parts = [normalize_space(x) for x in SENTENCE_SPLIT_RE.split(unit) if normalize_space(x)]
            buf = ""
            for part in parts:
                if not buf:
                    buf = part
                elif len(buf) + len(part) + 1 <= max_unit_chars:
                    buf += " " + part
                else:
                    refined.append(buf)
                    buf = part
            if buf:
                refined.append(buf)
        else:
            refined.append(unit[:max_unit_chars].rstrip())


    seen = set()
    out = []
    for unit in refined:
        key = normalize_space(unit)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def infer_question_intent(question: str) -> str:
    """질문의 답변 형태를 고르기 위한 간단한 의도 분류 수행"""
    q = normalize_space(question)
    if re.search(r"나열|열거|종류|목록|항목|예시|\d+\s*가지|두\s*가지|세\s*가지|이상", q):
        return "list"
    if re.search(r"24\s*시간|가능|되나요|됩니까|즉시|제한|필요|해야|바로|언제", q):
        return "availability"
    if re.search(r"어떻게|방법|절차|신청하고 싶|조회하고 싶|변경|수정|재발급|확인|알고 싶|하고 싶", q):
        return "procedure"
    if re.search(r"무엇인가요|무엇입니까|무슨|의미|개념|제도|용도", q):
        return "definition"
    return "general"


def is_list_style_question(question: str) -> bool:
    return infer_question_intent(question) == "list"


def list_signal_score(text: str) -> float:
    t = normalize_space(text)
    comma_count = t.count(",") + t.count("，")
    bullet_count = len(re.findall(r"[‣∎•○●-]\s*[^\n]+", text))
    colon_count = t.count(":") + t.count("：")
    paren_count = min(t.count("(") + t.count(")"), 8)
    marker_count = len(re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩]", t))
    return (
        min(comma_count, 12) * 0.35
        + min(bullet_count, 8) * 0.25
        + min(colon_count, 4) * 0.4
        + paren_count * 0.05
        + min(marker_count, 8) * 0.2
    )


def query_overlap_score(question: str, text: str) -> float:
    q_terms = set(tokenize(question, min_len=2))
    if not q_terms:
        return 0.0
    t_norm = normalize_for_tokenize(text)
    matched = sum(1 for term in q_terms if term in t_norm)
    return matched / max(len(q_terms), 1)


def unit_base_score(question: str, unit_text: str, context_item: Dict[str, Any], unit_pos: int) -> float:
    intent = infer_question_intent(question)
    score = 0.0
    score += 4.0 * query_overlap_score(question, unit_text)
    score += 0.20 * float(context_item.get("rerank_score") or 0.0)
    score += 1.50 * float(context_item.get("rrf_score") or 0.0)


    if context_item.get("chunk") is not None and getattr(context_item.get("chunk"), "kind", None) == "ocr":

        score -= 2.2
        if len(unit_text) > 300:
            score -= 1.5
        if len(unit_text) > 800:
            score -= 2.0
        score -= 2.0 * ocr_noise_ratio(unit_text)
        if is_noisy_ocr_unit(unit_text):
            score -= 2.0

    if intent == "list":
        score += list_signal_score(unit_text)

        if re.search(r"https?://", unit_text):
            score -= 0.7
        if re.search(r"[①②③④⑤⑥⑦⑧⑨⑩]", unit_text) and list_signal_score(unit_text) < 1.5:
            score -= 0.5
    elif intent == "procedure":
        if re.search(r"[①②③④⑤⑥⑦⑧⑨⑩]|클릭|입력|선택|접속|기재|인증|등록|조회|확인", unit_text):
            score += 1.1
    elif intent == "definition":
        if re.search(r"입니다|있습니다|운영|제도|고유번호|의미|위하여", unit_text):
            score += 0.8
        if re.search(r"[①②③④⑤⑥⑦⑧⑨⑩]|클릭|입력|선택|접속", unit_text):
            score -= 0.4
    elif intent == "availability":
        if re.search(r"가능|불가|됩니다|있습니다|없습니다|제한|해야|즉시", unit_text):
            score += 0.9

    if len(unit_text) >= 25:
        score += 0.15
    if len(unit_text) > 1200:
        score -= 0.4
    score -= unit_pos * 0.015
    return score


def page_string_for_chunk(chunk: Chunk) -> str:
    return f"p.{chunk.page}" if not chunk.page_end or chunk.page_end == chunk.page else f"p.{chunk.page}-{chunk.page_end}"


def split_ocr_units_for_question(text: str, question: str, max_unit_chars: int = 700) -> List[str]:
    """OCR 텍스트에서 질문과 관련된 짧은 답변 후보만 추림"""
    body = clean_text(str(text).replace("[이미지/OCR 추출]", ""))
    if not body:
        return []

    q_terms = set(tokenize(question, min_len=2))
    critical_terms = set(critical_question_terms(question))
    wanted = {normalize_for_tokenize(t) for t in (q_terms | critical_terms) if normalize_for_tokenize(t)}


    rough_parts: List[str] = []
    for line in body.splitlines():
        line = clean_text(line)
        if not line:
            continue
        sub_parts = re.split(r"(?<=[다요]\.)\s+|(?<=\))\s+|(?=Q\s*\d+\.)|(?=A\s+)", line)
        for part in sub_parts:
            part = clean_unit_for_final(part)
            if 5 <= len(part) <= max_unit_chars:
                rough_parts.append(part)

    focused: List[str] = []
    for part in rough_parts:
        norm = normalize_for_tokenize(part)
        if wanted and any(w and w in norm for w in wanted):
            focused.append(part)

    if not focused:
        focused = [u for u in split_answer_units_from_text(body, max_unit_chars=max_unit_chars) if len(u) <= max_unit_chars]


    out: List[str] = []
    seen = set()
    for u in focused:
        u = clean_unit_for_final(u)
        if not (5 <= len(u) <= max_unit_chars):
            continue


        if is_noisy_ocr_unit(u):
            continue
        key = canonical_unit_text(u)
        if key and key not in seen:
            seen.add(key)
            out.append(u)
    return out


def build_candidate_units(
    question: str,
    context_items: List[Dict[str, Any]],
    max_units_per_chunk: int = 16,
    max_unit_chars: int = 1500,
) -> List[AnswerUnit]:
    """검색 context를 답변 선택에 사용할 unit 후보로 변환"""
    units: List[AnswerUnit] = []
    seen_texts = set()
    uid = 1

    for ctx_pos, item in enumerate(context_items):
        c = item["chunk"]

        text = answer_view_for_chunk(c)
        if not normalize_space(text):
            continue

        if c.kind == "ocr":
            raw_units = split_ocr_units_for_question(text, question, max_unit_chars=min(max_unit_chars, 700))


            local_max_units = min(max_units_per_chunk, 10)
        else:
            raw_units = split_answer_units_from_text(text, max_unit_chars=max_unit_chars)
            local_max_units = max_units_per_chunk
        for unit_pos, unit_text in enumerate(raw_units[:local_max_units]):
            unit_text = normalize_space(unit_text)
            if not unit_text:
                continue
            key = re.sub(r"\s+", " ", unit_text)
            if key in seen_texts:
                continue
            seen_texts.add(key)

            base_score = unit_base_score(question, unit_text, item, unit_pos)
            units.append(
                AnswerUnit(
                    unit_id=f"U{uid}",
                    text=unit_text,
                    title=c.source_title,
                    page=page_string_for_chunk(c),
                    locator=c.locator,
                    source_chunk_id=c.chunk_id,
                    source_kind=c.kind,
                    source_role=c.role,
                    context_rank=int(item.get("rank", 9999)),
                    context_type=str(item.get("context_type", "retrieved")),
                    score=float(base_score),
                )
            )
            uid += 1

    units.sort(key=lambda u: u.score, reverse=True)
    return units


def rerank_answer_units(
    question: str,
    units: List[AnswerUnit],
    top_n_for_cross: int = 60,
    final_top_n: int = 24,
    enabled: bool = True,
) -> List[AnswerUnit]:
    if not units:
        return []

    prelim = sorted(units, key=lambda u: u.score, reverse=True)[:top_n_for_cross]
    if enabled:
        try:
            reranker = get_reranker()
            pairs = [(question, u.text) for u in prelim]
            scores = reranker.predict(pairs, batch_size=32, show_progress_bar=False)
            for u, s in zip(prelim, scores):
                u.cross_score = float(s)

                u.score = float(s) + 0.15 * u.score
        except Exception as e:
            console.print(f"[yellow]unit rerank 실패, base score로 진행합니다: {e}[/yellow]")

    prelim.sort(key=lambda u: u.score, reverse=True)

    selected = prelim[:final_top_n]
    for i, u in enumerate(selected, start=1):
        u.unit_id = f"U{i}"
    return selected


def format_units(units: List[AnswerUnit]) -> str:
    parts = []
    for u in units:
        parts.append(
            textwrap.dedent(
                f"""
                [{u.unit_id}]
                title: {u.title}
                page: {u.page}
                locator: {u.locator}
                source_kind: {u.source_kind}
                context_type: {u.context_type}
                text:
                {u.text}
                """
            ).strip()
        )
    return "\n\n".join(parts)


def build_unit_selection_prompt(question: str, units: List[AnswerUnit]) -> Tuple[str, str]:
    system_prompt = """
You are a unit selector for a PDF-only RAG system.

Rules:
- Do NOT write a new answer.
- Select only the minimal unit_id(s) that directly answer the question.
- Unit IDs must come from the provided Candidate Answer Units.
- If the question asks for examples, items, names, services, types, or multiple things, select the unit that lists those items.
- If the question asks for a procedure, select only the necessary step unit(s).
- If the question asks for a definition, select only the definition/explanation unit(s).
- Do not select surrounding procedure steps unless they are necessary to answer the exact question.
- Return only JSON.
""".strip()

    user_prompt = f"""
[Question]
{question}

[Candidate Answer Units]
{format_units(units)}

[Output JSON schema]
{{
  "selected_unit_ids": ["U<number>"],
  "additional_explanation": "없음"
}}
""".strip()
    return system_prompt, user_prompt


def fit_units_to_llm_budget(
    llm,
    question: str,
    units: List[AnswerUnit],
    token_budget: int = 6200,
    min_units: int = 4,
) -> List[AnswerUnit]:
    if not units:
        return []

    current = list(units)
    while len(current) >= min_units:
        system_prompt, user_prompt = build_unit_selection_prompt(question, current)
        n_tokens = count_llama_tokens(llm, system_prompt + "\n\n" + user_prompt)
        if n_tokens <= token_budget:
            return current
        current = current[:-1]

    return current if current else units[:1]


def select_answer_units_with_llm(
    llm,
    question: str,
    units: List[AnswerUnit],
) -> Dict[str, Any]:
    if not units:
        return {"selected_unit_ids": [], "additional_explanation": "없음"}

    system_prompt, user_prompt = build_unit_selection_prompt(question, units)
    try:
        resp = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            top_p=0.9,
            max_tokens=250,
            response_format={"type": "json_object"},
        )
        return safe_json_loads(resp["choices"][0]["message"]["content"])
    except Exception as e:
        console.print(f"[yellow]LLM unit selection 실패. rerank 상위 unit으로 fallback합니다: {e}[/yellow]")
        return {"selected_unit_ids": [u.unit_id for u in units[: min(3, len(units))]], "additional_explanation": "LLM 선택 실패로 상위 근거를 사용했습니다."}


def validate_selected_units(selection_obj: Dict[str, Any], units: List[AnswerUnit]) -> Dict[str, Any]:
    unit_map = {u.unit_id: u for u in units}
    selected = []
    for raw_id in selection_obj.get("selected_unit_ids", []):
        uid = str(raw_id).strip()
        if uid in unit_map and uid not in {u.unit_id for u in selected}:
            selected.append(unit_map[uid])

    return {
        "selected_units": selected,
        "additional_explanation": selection_obj.get("additional_explanation", "없음"),
    }


def fallback_unit_answer(question: str, units: List[AnswerUnit]) -> Dict[str, Any]:
    if not units:
        return {
            "final_answer": "문서에서 확인되지 않음",
            "evidence": [],
            "additional_explanation": "검색된 근거가 없습니다.",
            "render_diagnostics": {
                "render_mode": "no_evidence",
                "raw_selected_units": [],
                "deduped_units": [],
                "answer_units": [],
            },
        }

    top = sorted(units, key=lambda u: u.score, reverse=True)[0]
    return build_answer_from_units(
        {"selected_units": [top], "additional_explanation": "없음"},
        question=question,
    )


def clean_unit_for_final(text: str) -> str:
    """최종답 표시 전에 bullet, 공백, 쉼표 등 추출 노이즈만 정리"""
    t = normalize_space(text)
    t = re.sub(r"^[‣∎•○●\-*\s]+", "", t).strip()
    t = re.sub(r"\s*,\s*,\s*", ", ", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s+", ", ", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,")


def canonical_unit_text(text: str) -> str:
    t = clean_unit_for_final(text)
    t = re.sub(r"[^가-힣a-zA-Z0-9]+", "", t).lower()
    return t


def ocr_noise_ratio(text: str) -> float:
    """OCR 텍스트의 깨짐 정도를 비율로 계산"""
    t = normalize_space(text)
    chars = [ch for ch in t if not ch.isspace()]
    if not chars:
        return 1.0
    ok = 0
    for ch in chars:
        if re.match(r"[가-힣a-zA-Z0-9]", ch):
            ok += 1
        elif ch in "().,:%/+-[]{}<>·ㆍ'\"!?？:;=~_#&*@₩☎ ":
            ok += 1
    return max(0.0, 1.0 - ok / max(1, len(chars)))


def ocr_text_quality_score(text: str) -> float:
    """OCR unit이 최종답 후보로 쓸 만큼 깨끗한지 점수화"""
    t = normalize_space(text)
    if not t:
        return 0.0
    noise = ocr_noise_ratio(t)
    meaningful = len(re.findall(r"[가-힣a-zA-Z0-9]", t)) / max(1, len(re.sub(r"\s+", "", t)))
    length_penalty = 0.0
    if len(t) > 300:
        length_penalty += 0.15
    if len(t) > 700:
        length_penalty += 0.25
    return max(0.0, meaningful - noise - length_penalty)


def is_noisy_ocr_unit(text: str, threshold: float = 0.28) -> bool:
    """최종답에 그대로 쓰기 어려운 OCR unit인지 판단"""
    t = normalize_space(text)
    if not t:
        return True
    if len(t) > 600 and ocr_noise_ratio(t) > 0.16:
        return True
    if ocr_noise_ratio(t) >= threshold:
        return True

    symbolish = len(re.findall(r"[<>{}\[\]=_/\\|]", t)) / max(1, len(t))
    if len(t) > 250 and symbolish > 0.035:
        return True
    return False


def fuzzy_unit_similarity(a: str, b: str) -> float:
    """OCR 오탈자를 고려해 두 unit의 중복 가능성을 계산"""
    ak = canonical_unit_text(a)
    bk = canonical_unit_text(b)
    if not ak or not bk:
        return 0.0
    if ak in bk or bk in ak:
        return 1.0

    def grams(x: str):
        return {x[i:i+2] for i in range(max(0, len(x)-1))} or {x}
    ga, gb = grams(ak), grams(bk)
    jacc = len(ga & gb) / max(1, len(ga | gb))
    seq = SequenceMatcher(None, ak, bk).ratio()
    return max(jacc, seq)


def unit_priority_for_answer(question: str, u: AnswerUnit) -> Tuple[int, int, int, float]:
    """중복 후보 중 최종답에 남길 unit의 우선순위를 정함"""


    kind_priority = {"text": 0, "table": 1, "section": 2, "ocr": 8}.get(u.source_kind, 9)
    role_priority = {"body": 0, "table": 1, "section": 2, None: 3, "anchor_question": 9, "toc": 9}.get(u.source_role, 4)
    return (kind_priority, role_priority, len(clean_unit_for_final(u.text)), -float(u.score))


def dedupe_selected_units(question: str, selected_units: List[AnswerUnit]) -> List[AnswerUnit]:
    """선택된 답변 unit 중 의미가 겹치는 항목을 정리"""
    if not selected_units:
        return []

    ordered = sorted(selected_units, key=lambda u: unit_priority_for_answer(question, u))
    accepted: List[AnswerUnit] = []
    accepted_keys: List[str] = []

    for u in ordered:
        key = canonical_unit_text(u.text)
        if not key:
            continue

        duplicate = False
        remove_indices: List[int] = []
        for i, ak in enumerate(list(accepted_keys)):
            old_u = accepted[i]
            sim = fuzzy_unit_similarity(u.text, old_u.text)
            if key == ak or sim >= 0.88:

                cur_pri = unit_priority_for_answer(question, u)
                old_pri = unit_priority_for_answer(question, old_u)
                if cur_pri < old_pri:
                    remove_indices.append(i)
                    break
                duplicate = True
                break


            if len(key) > len(ak) and ak in key and len(ak) >= 12:
                cur_pri = unit_priority_for_answer(question, u)
                old_pri = unit_priority_for_answer(question, old_u)
                if cur_pri < old_pri:
                    remove_indices.append(i)
                    break
                duplicate = True
                break

            if len(ak) > len(key) and key in ak and len(key) >= 12:
                cur_pri = unit_priority_for_answer(question, u)
                old_pri = unit_priority_for_answer(question, old_u)
                if cur_pri < old_pri:
                    remove_indices.append(i)
                    break
                duplicate = True
                break

        for i in sorted(remove_indices, reverse=True):
            accepted.pop(i)
            accepted_keys.pop(i)

        if duplicate:
            continue

        accepted.append(u)
        accepted_keys.append(key)


    def out_order(u: AnswerUnit) -> Tuple[int, str, int]:
        return (int(u.context_rank), u.locator, len(clean_unit_for_final(u.text)))

    return sorted(accepted, key=out_order)


KOREAN_NUMBERS = {
    "한": 1,
    "하나": 1,
    "두": 2,
    "둘": 2,
    "세": 3,
    "셋": 3,
    "네": 4,
    "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}


def parse_requested_item_count(question: str) -> Optional[int]:
    """질문에서 요청한 최소 나열 개수를 추출"""
    q = normalize_space(question)

    m = re.search(r"(\d+)\s*(?:가지|개|종|명|항목)\s*이상", q)
    if m:
        return int(m.group(1))

    m = re.search(r"(한|하나|두|둘|세|셋|네|넷|다섯|여섯|일곱|여덟|아홉|열)\s*(?:가지|개|종|명|항목)\s*이상", q)
    if m:
        return KOREAN_NUMBERS.get(m.group(1))

    return None


def split_list_payload(text: str) -> Tuple[str, List[str]]:
    """목록형 unit에서 표시용 항목들을 분리"""
    t = clean_unit_for_final(text)

    if ":" in t or "：" in t:
        parts = re.split(r"[:：]", t, maxsplit=1)
        if len(parts) == 2 and len(parts[1].strip()) >= 2:
            t = parts[1].strip()

    t = re.sub(r"\s*,\s*,\s*", ", ", t)
    t = re.sub(r"^[,，\s]+|[,，\s]+$", "", t)
    t = normalize_space(t)

    raw_items = re.split(r"\s*,\s*|，|、", t)
    items = []
    for item in raw_items:
        item = clean_unit_for_final(item)
        if not item:
            continue

        if item in {",", "，", "ㆍ", "·"}:
            continue
        items.append(item)

    deduped = []
    seen = set()
    for item in items:
        key = canonical_unit_text(item)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return t, deduped


def render_label_value_list_answer(question: str, unit_text: str) -> Tuple[str, str]:
    """목록형 답변을 항목 중심으로 짧게 만듦"""
    payload, items = split_list_payload(unit_text)
    min_count = parse_requested_item_count(question)
    default_max = 6

    if items and len(items) >= 2:
        max_items = max(default_max, min_count or 0)
        shown = items[:max_items]
        suffix = " 등" if len(items) > len(shown) else ""
        return ", ".join(shown) + suffix, "label_value_list"

    return payload, "label_value_payload"


def source_is_clean(u: AnswerUnit) -> bool:
    return u.source_kind in {"text", "section", "table"}


def unit_contains_all_terms(u: AnswerUnit, terms: List[str]) -> bool:
    if not terms:
        return False
    norm = normalize_for_tokenize(u.text)
    return all(normalize_for_tokenize(t) in norm for t in terms if normalize_for_tokenize(t))


def prefer_clean_units_for_final(question: str, units: List[AnswerUnit]) -> Tuple[List[AnswerUnit], Dict[str, Any]]:
    """같은 내용을 담은 clean evidence가 있으면 OCR을 최종답에서 제외"""
    if not units:
        return units, {"applied": False, "reason": "empty"}

    clean_units = [u for u in units if source_is_clean(u)]
    ocr_units = [u for u in units if u.source_kind == "ocr"]
    noisy_ocr_units = [u for u in ocr_units if is_noisy_ocr_unit(u.text)]
    if noisy_ocr_units and clean_units:
        units = [u for u in units if not (u.source_kind == "ocr" and is_noisy_ocr_unit(u.text))]
        ocr_units = [u for u in units if u.source_kind == "ocr"]
        if not ocr_units:
            return units, {"applied": True, "reason": "dropped_noisy_ocr_units", "dropped_ocr": len(noisy_ocr_units)}
    if not ocr_units:
        return units, {"applied": False, "reason": "no_ocr_selected"}
    if not clean_units:
        return units, {"applied": False, "reason": "ocr_only"}

    intent = infer_question_intent(question)
    if intent == "list":
        min_items = parse_requested_item_count(question) or 2
        clean_viable = [u for u in clean_units if len(split_list_payload(u.text)[1]) >= min_items]
        if clean_viable:
            return clean_viable, {"applied": True, "reason": "clean_list_unit_available", "dropped_ocr": len(ocr_units)}
        return units, {"applied": False, "reason": "no_clean_list_unit"}

    terms = critical_question_terms(question)
    clean_cover = [u for u in clean_units if unit_contains_all_terms(u, terms)] if terms else []
    if clean_cover:
        return clean_cover, {"applied": True, "reason": "clean_unit_covers_critical_terms", "dropped_ocr": len(ocr_units)}



    clean_overlap = [u for u in clean_units if query_overlap_score(question, u.text) > 0]
    if clean_overlap:
        return clean_overlap, {"applied": True, "reason": "clean_unit_has_query_overlap", "dropped_ocr": len(ocr_units)}

    return units, {"applied": False, "reason": "no_clean_replacement"}


def collect_ocr_supporting_evidence(question: str, units: List[AnswerUnit], limit: int = 3) -> List[Dict[str, Any]]:
    ocr_units = [u for u in units if u.source_kind == "ocr"]
    if not ocr_units:
        return []
    ranked = sorted(
        ocr_units,
        key=lambda u: (query_overlap_score(question, u.text), -len(clean_unit_for_final(u.text))),
        reverse=True,
    )[:limit]
    return [
        {
            "title": u.title,
            "page": u.page,
            "locator": u.locator,
            "quote_preview": clean_unit_for_final(u.text)[:500],
            "source_chunk_id": u.source_chunk_id,
            "ocr_noise_ratio": ocr_noise_ratio(u.text),
            "ocr_quality_score": ocr_text_quality_score(u.text),
        }
        for u in ranked
    ]


def has_many_garbled_tokens(text: str) -> bool:
    """OCR 텍스트에 깨진 토큰이 과도한지 확인"""
    t = normalize_space(text)
    if not t:
        return True
    compact = re.sub(r"\s+", "", t)
    if not compact:
        return True

    symbol_count = len(re.findall(r"[<>{}\[\]=_/\\|~`^]", compact))
    long_digit_runs = len(re.findall(r"\d{5,}", compact))
    broken_urlish = len(re.findall(r"(?:https?|www|[0-9]{2}//|\.do|\.go|\.kr)", t, flags=re.I))
    rare = len(re.findall(r"[^가-힣a-zA-Z0-9\s().,:%/+-\[\]{}<>·ㆍ'\"!?？:;=~_#&*@₩☎]", t))
    ratio = (symbol_count + rare + 3 * long_digit_runs + 2 * broken_urlish) / max(1, len(compact))
    return ratio >= 0.055 or (len(t) > 250 and (long_digit_runs >= 2 or broken_urlish >= 2))


def is_unacceptable_final_ocr(unit: AnswerUnit) -> bool:
    """최종답 본문에 쓰면 안 되는 OCR unit인지 판정"""
    if getattr(unit, "source_kind", None) != "ocr":
        return False
    t = normalize_space(unit.text)
    if len(t) > 300:
        return True
    if is_noisy_ocr_unit(t):
        return True
    if has_many_garbled_tokens(t):
        return True
    return False


def extract_minimal_ocr_window(question: str, text: str, max_chars: int = 260) -> str:
    """OCR-only 상황에서 질문과 가까운 짧은 구간만 잘라냄"""
    t = clean_unit_for_final(text)
    if not t:
        return ""
    terms = [normalize_for_tokenize(x) for x in critical_question_terms(question)]
    q_tokens = set(tokenize(question, min_len=2))
    lines = [normalize_space(x) for x in re.split(r"[\n\r]+|(?<=[다요]\.)\s+", t) if normalize_space(x)]
    scored = []
    for i, line in enumerate(lines):
        ln = normalize_for_tokenize(line)
        token_overlap = len(set(tokenize(line, min_len=2)) & q_tokens)
        term_hits = sum(1 for term in terms if term and term in ln)
        score = 2 * term_hits + token_overlap - 0.002 * len(line)
        if score > 0:
            window = " ".join(lines[max(0, i-1): min(len(lines), i+2)])
            scored.append((score, window))
    if scored:
        scored.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
        out = scored[0][1]
    else:
        out = t
    out = normalize_space(out)
    if len(out) > max_chars:

        norm = normalize_for_tokenize(out)
        cut_at = 0
        for term in terms:
            if term:
                idx = norm.find(term)
                if idx >= 0:
                    cut_at = max(0, idx - 60)
                    break
        out = out[cut_at:cut_at + max_chars].strip()
    return out


def final_ocr_unit_safety_gate(
    question: str,
    answer_units: List[AnswerUnit],
    candidate_units: List[AnswerUnit],
) -> Tuple[List[AnswerUnit], Dict[str, Any]]:
    """최종 렌더링 직전 OCR 후보 재점검"""
    if not answer_units:
        return answer_units, {"applied": False, "reason": "empty"}
    ocr_units = [u for u in answer_units if u.source_kind == "ocr"]
    if not ocr_units:
        return answer_units, {"applied": False, "reason": "no_ocr_in_final_units"}

    unacceptable = [u for u in ocr_units if is_unacceptable_final_ocr(u)]
    if not unacceptable:
        return answer_units, {"applied": False, "reason": "ocr_units_pass_quality_gate", "ocr_final_count": len(ocr_units)}

    intent = infer_question_intent(question)
    clean_candidates = [u for u in candidate_units if source_is_clean(u)]
    replacement: List[AnswerUnit] = []

    if intent == "list":
        min_items = parse_requested_item_count(question) or 2
        viable = [u for u in clean_candidates if len(split_list_payload(u.text)[1]) >= min_items]
        viable.sort(
            key=lambda u: (
                list_signal_score(u.text),
                len(split_list_payload(u.text)[1]),
                query_overlap_score(question, u.text),
                -len(clean_unit_for_final(u.text)),
            ),
            reverse=True,
        )
        if viable:
            replacement = [viable[0]]
    else:
        terms = critical_question_terms(question)
        viable = [u for u in clean_candidates if (unit_contains_all_terms(u, terms) if terms else query_overlap_score(question, u.text) > 0)]
        viable.sort(
            key=lambda u: (
                unit_contains_all_terms(u, terms),
                query_overlap_score(question, u.text),
                -len(clean_unit_for_final(u.text)),
            ),
            reverse=True,
        )
        if viable:
            replacement = [viable[0]]

    if replacement:
        return replacement, {
            "applied": True,
            "reason": "replaced_unacceptable_ocr_with_clean_candidate",
            "dropped_ocr_count": len(unacceptable),
            "replacement_unit_ids": [u.unit_id for u in replacement],
        }


    safe_ocr_units: List[AnswerUnit] = []
    rejected = 0
    for u in answer_units:
        if u.source_kind != "ocr":
            safe_ocr_units.append(u)
            continue
        window = extract_minimal_ocr_window(question, u.text)
        pseudo = AnswerUnit(
            unit_id=u.unit_id,
            text=window,
            title=u.title,
            page=u.page,
            locator=f"{u.locator} / OCR minimal window",
            source_chunk_id=u.source_chunk_id,
            source_kind=u.source_kind,
            source_role=u.source_role,
            context_rank=u.context_rank,
            context_type=u.context_type,
            score=u.score,
            cross_score=u.cross_score,
        )
        if window and len(window) <= 300 and not is_noisy_ocr_unit(window) and not has_many_garbled_tokens(window):
            safe_ocr_units.append(pseudo)
        else:
            rejected += 1

    if safe_ocr_units and len(safe_ocr_units) < len(answer_units):
        return safe_ocr_units, {
            "applied": True,
            "reason": "replaced_full_ocr_with_minimal_window_and_dropped_rejected_ocr",
            "dropped_ocr_count": rejected,
        }
    if safe_ocr_units:
        return safe_ocr_units, {
            "applied": True,
            "reason": "replaced_full_ocr_with_minimal_window",
            "dropped_ocr_count": rejected,
        }

    return [], {
        "applied": True,
        "reason": "dropped_unacceptable_ocr_no_clean_or_safe_window",
        "dropped_ocr_count": len(unacceptable),
    }

def choose_units_for_render(question: str, units: List[AnswerUnit]) -> Tuple[List[AnswerUnit], str]:
    """질문 의도에 맞게 최종답에 사용할 unit 수와 종류를 고름"""
    intent = infer_question_intent(question)
    choose_units_for_render.last_clean_preference_diagnostics = {"applied": False, "reason": "not_run"}
    choose_units_for_render.last_final_ocr_gate_diagnostics = {"applied": False, "reason": "not_run"}
    if not units:
        return [], intent

    units, clean_pref_diag = prefer_clean_units_for_final(question, units)
    choose_units_for_render.last_clean_preference_diagnostics = clean_pref_diag

    if intent == "list":

        answer_units = [sorted(
            units,
            key=lambda u: (
                0 if source_is_clean(u) else -1,
                list_signal_score(u.text),
                query_overlap_score(question, u.text),
                -len(clean_unit_for_final(u.text)),
            ),
            reverse=True,
        )[0]]
    elif intent == "availability":

        answer_units = [sorted(
            units,
            key=lambda u: (
                0 if source_is_clean(u) else 1,
                is_unacceptable_final_ocr(u) if u.source_kind == "ocr" else False,
                -query_overlap_score(question, u.text),
                len(clean_unit_for_final(u.text)),
                unit_priority_for_answer(question, u),
            ),
        )[0]]
    elif intent == "definition":
        answer_units = units[:2]
    elif intent == "procedure":
        answer_units = units[:6]
    else:
        answer_units = units[:2]


    choose_units_for_render.last_final_ocr_gate_diagnostics = {
        "applied": False,
        "reason": "deferred_to_repair_answer_if_needed_with_full_ranked_units",
    }
    return answer_units, intent

def render_answer_from_units(question: str, selected_units: List[AnswerUnit]) -> Dict[str, Any]:
    """선택된 unit과 근거를 사용자 출력 형식으로 변환"""
    raw_selected_units = list(selected_units)
    deduped_units = dedupe_selected_units(question, raw_selected_units)

    answer_units, intent = choose_units_for_render(question, deduped_units)
    clean_preference_diagnostics = getattr(choose_units_for_render, "last_clean_preference_diagnostics", {"applied": False, "reason": "not_recorded"})
    final_ocr_gate_diagnostics = getattr(choose_units_for_render, "last_final_ocr_gate_diagnostics", {"applied": False, "reason": "not_recorded"})
    ocr_supporting_evidence = collect_ocr_supporting_evidence(question, raw_selected_units)

    if not answer_units:
        return {
            "final_answer": "문서에서 확인되지 않음",
            "evidence": [],
            "render_diagnostics": {
                "render_mode": "empty",
                "question_intent": intent,
                "raw_selected_units": [asdict(u) for u in raw_selected_units],
                "deduped_units": [asdict(u) for u in deduped_units],
                "clean_preference_diagnostics": clean_preference_diagnostics,
                "final_ocr_gate_diagnostics": final_ocr_gate_diagnostics,
                "answer_units": [],
            },
            "ocr_supporting_evidence": ocr_supporting_evidence,
        }

    render_mode = "unit_extract"
    if intent == "list":
        final_answer, render_mode = render_label_value_list_answer(question, answer_units[0].text)
    else:
        final_answer = normalize_space(" ".join(clean_unit_for_final(u.text) for u in answer_units))

    evidence = [
        {
            "title": u.title,
            "page": u.page,
            "locator": u.locator,
            "quote": u.text,
            "source_kind": u.source_kind,
            "source_role": u.source_role,
            "source_chunk_id": u.source_chunk_id,
            "context_type": u.context_type,
        }
        for u in answer_units
    ]

    return {
        "final_answer": final_answer,
        "evidence": evidence,
        "ocr_supporting_evidence": ocr_supporting_evidence,
        "render_diagnostics": {
            "render_mode": render_mode,
            "question_intent": intent,
            "raw_selected_units": [asdict(u) for u in raw_selected_units],
            "deduped_units": [asdict(u) for u in deduped_units],
            "clean_preference_diagnostics": clean_preference_diagnostics,
            "final_ocr_gate_diagnostics": final_ocr_gate_diagnostics,
            "answer_units": [asdict(u) for u in answer_units],
            "ocr_supporting_evidence": ocr_supporting_evidence,
            "rendered_answer": final_answer,
        },
    }


def build_answer_from_units(validated_obj: Dict[str, Any], question: str) -> Dict[str, Any]:
    selected_units: List[AnswerUnit] = validated_obj.get("selected_units", [])
    if not selected_units:
        return fallback_unit_answer(question, [])

    rendered = render_answer_from_units(question, selected_units)
    rendered["additional_explanation"] = validated_obj.get("additional_explanation", "없음")
    return rendered


def critical_question_terms(question: str) -> List[str]:
    """coverage 확인에 사용할 질문 내 핵심 표현을 추출"""
    q = normalize_for_tokenize(question)
    terms = []
    for t in tokenize(question, min_len=2):
        if re.search(r"\d", t):
            terms.append(t)
    for literal in ["즉시", "가능", "불가", "정지", "재발급", "조회", "변경", "수정"]:
        if literal in question:
            terms.append(literal)
    return list(dict.fromkeys(terms))


def count_rendered_list_items(answer_text: str) -> int:
    _, items = split_list_payload(answer_text)
    if items:
        return len(items)

    pieces = [normalize_space(x) for x in re.split(r"[,，、]", answer_text) if normalize_space(x)]
    pieces = [p for p in pieces if p not in {"등", "없음"}]
    return len(pieces)


def evaluate_answer_coverage(question: str, answer_obj: Dict[str, Any]) -> Dict[str, Any]:
    final_answer = normalize_space(answer_obj.get("final_answer", ""))
    intent = infer_question_intent(question)
    report: Dict[str, Any] = {
        "ok": True,
        "intent": intent,
        "missing_critical_terms": [],
        "required_min_items": parse_requested_item_count(question) or 0,
        "rendered_item_count": 0,
        "repaired": False,
        "reason": "ok",
    }

    missing = []
    ans_norm = normalize_for_tokenize(final_answer)
    for term in critical_question_terms(question):

        if normalize_for_tokenize(term) not in ans_norm:
            missing.append(term)

    if missing:
        report["ok"] = False
        report["missing_critical_terms"] = missing
        report["reason"] = "missing_critical_terms"

    if intent == "list":
        min_items = parse_requested_item_count(question) or 2
        item_count = count_rendered_list_items(final_answer)
        report["required_min_items"] = min_items
        report["rendered_item_count"] = item_count
        if item_count < min_items:
            report["ok"] = False
            report["reason"] = "not_enough_list_items"

    return report


def repair_answer_if_needed(question: str, answer_obj: Dict[str, Any], ranked_units: List[AnswerUnit]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """선택 답변이 조건을 덜 채우면 검색 후보 안에서 보완"""
    before = evaluate_answer_coverage(question, answer_obj)
    intent = infer_question_intent(question)

    def apply_final_gate(obj: Dict[str, Any], before_report: Dict[str, Any], after_report: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """복구 단계에서 OCR final gate를 적용"""
        evidence = obj.get("evidence", []) or []
        current_units: List[AnswerUnit] = []
        for i, ev in enumerate(evidence, start=1):
            current_units.append(
                AnswerUnit(
                    unit_id=f"FINAL_E{i}",
                    text=str(ev.get("quote", "")),
                    title=str(ev.get("title", "")),
                    page=str(ev.get("page", "")),
                    locator=str(ev.get("locator", "")),
                    source_chunk_id=str(ev.get("source_chunk_id", "")),
                    source_kind=str(ev.get("source_kind", "")),
                    source_role=ev.get("source_role"),
                    context_rank=9999,
                    context_type=str(ev.get("context_type", "final_evidence")),
                    score=0.0,
                    cross_score=None,
                )
            )
        if not current_units:
            return obj, {"before": before_report, "after": after_report, "final_ocr_safety_gate": {"applied": False, "reason": "no_evidence"}}

        gated_units, gate_report = final_ocr_unit_safety_gate(question, current_units, ranked_units)
        if not gate_report.get("applied"):

            obj.setdefault("render_diagnostics", {})["final_ocr_safety_gate_after_repair"] = gate_report
            return obj, {"before": before_report, "after": after_report, "final_ocr_safety_gate": gate_report}

        if gated_units:
            gated_obj = render_answer_from_units(question, gated_units)
            gated_obj["additional_explanation"] = obj.get("additional_explanation", "없음")

            merged_support = list(obj.get("ocr_supporting_evidence", []) or []) + list(gated_obj.get("ocr_supporting_evidence", []) or [])
            if merged_support:
                seen = set()
                uniq = []
                for item in merged_support:
                    key = (item.get("source_chunk_id"), item.get("quote_preview"))
                    if key not in seen:
                        seen.add(key)
                        uniq.append(item)
                gated_obj["ocr_supporting_evidence"] = uniq
            after_gate = evaluate_answer_coverage(question, gated_obj)
            after_gate["repaired"] = True
            after_gate["reason"] = "final_ocr_safety_gate_applied"
            return gated_obj, {"before": before_report, "after": after_gate, "final_ocr_safety_gate": gate_report}


        blocked = dict(obj)
        blocked["final_answer"] = "문서에서 명확한 답변 문장을 확인하지 못함"
        blocked["evidence"] = []
        blocked.setdefault("render_diagnostics", {})["final_ocr_safety_gate_after_repair"] = gate_report
        after_block = evaluate_answer_coverage(question, blocked)
        after_block["repaired"] = True
        after_block["reason"] = "blocked_unacceptable_ocr_final_answer"
        return blocked, {"before": before_report, "after": after_block, "final_ocr_safety_gate": gate_report}


    has_ocr_evidence = any(ev.get("source_kind") == "ocr" or "OCR" in str(ev.get("locator", "")) for ev in answer_obj.get("evidence", []))
    if has_ocr_evidence:
        min_items = parse_requested_item_count(question) or 2
        clean_viable: List[AnswerUnit] = []
        if intent == "list":
            clean_viable = [u for u in ranked_units if source_is_clean(u) and len(split_list_payload(u.text)[1]) >= min_items]
            clean_viable.sort(
                key=lambda u: (
                    len(split_list_payload(u.text)[1]),
                    list_signal_score(u.text),
                    query_overlap_score(question, u.text),
                    -len(clean_unit_for_final(u.text)),
                ),
                reverse=True,
            )
        else:
            terms = critical_question_terms(question)
            clean_viable = [u for u in ranked_units if source_is_clean(u) and (unit_contains_all_terms(u, terms) if terms else query_overlap_score(question, u.text) > 0)]
            clean_viable.sort(
                key=lambda u: (
                    unit_contains_all_terms(u, terms),
                    query_overlap_score(question, u.text),
                    -len(clean_unit_for_final(u.text)),
                ),
                reverse=True,
            )
        if clean_viable:
            repaired_clean = render_answer_from_units(question, [clean_viable[0]])
            repaired_clean["additional_explanation"] = answer_obj.get("additional_explanation", "없음")
            after_clean = evaluate_answer_coverage(question, repaired_clean)
            after_clean["repaired"] = True
            after_clean["reason"] = "replaced_noisy_ocr_with_clean_evidence"
            if after_clean.get("ok"):
                return apply_final_gate(repaired_clean, before, after_clean)

    if before.get("ok"):
        return apply_final_gate(answer_obj, before, before)

    repaired = None

    if intent == "list":
        min_items = parse_requested_item_count(question) or 2
        viable = []
        for u in ranked_units:
            _, items = split_list_payload(u.text)
            if len(items) >= min_items:
                viable.append(u)
        if viable:

            viable.sort(
                key=lambda u: (
                    1 if source_is_clean(u) else 0,
                    list_signal_score(u.text),
                    len(split_list_payload(u.text)[1]),
                    query_overlap_score(question, u.text),
                    -len(clean_unit_for_final(u.text)),
                ),
                reverse=True,
            )
            repaired = render_answer_from_units(question, [viable[0]])
            repaired["additional_explanation"] = answer_obj.get("additional_explanation", "없음")

    else:
        missing_terms = before.get("missing_critical_terms", [])
        if missing_terms:
            viable = []
            for u in ranked_units:
                u_norm = normalize_for_tokenize(u.text)
                if all(normalize_for_tokenize(t) in u_norm for t in missing_terms):
                    viable.append(u)
            if viable:
                viable.sort(
                    key=lambda u: (
                        1 if source_is_clean(u) else 0,
                        query_overlap_score(question, u.text),
                        -len(clean_unit_for_final(u.text)),
                    ),
                    reverse=True,
                )
                repaired = render_answer_from_units(question, [viable[0]])
                repaired["additional_explanation"] = answer_obj.get("additional_explanation", "없음")

    if repaired is None:
        after = dict(before)
        after["repaired"] = False
        return apply_final_gate(answer_obj, before, after)

    after = evaluate_answer_coverage(question, repaired)
    after["repaired"] = True
    if not after.get("ok"):

        return apply_final_gate(answer_obj, before, after)

    return apply_final_gate(repaired, before, after)


def safe_list_of_strings(value: Any, max_items: int = 5) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        s = normalize_space(item)
        if s and s not in out:
            out.append(s)
        if len(out) >= max_items:
            break
    return out


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return default


def normalize_requirement_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        text = normalize_space(item.get("requirement") or item.get("need") or item.get("text") or item.get("description") or "")
        rid = normalize_space(item.get("id") or "")
        rtype = normalize_space(item.get("type") or "")
        return {"id": rid, "requirement": text, "type": rtype}
    text = normalize_space(item)
    return {"id": "", "requirement": text, "type": ""}


def normalize_question_plan(raw: Dict[str, Any], question: str, max_queries: int) -> Dict[str, Any]:
    requirements_raw = raw.get("requirements", []) if isinstance(raw, dict) else []
    requirements = []
    if isinstance(requirements_raw, list):
        for item in requirements_raw:
            req = normalize_requirement_item(item)
            if req.get("requirement"):
                if not req.get("id"):
                    req["id"] = f"R{len(requirements) + 1}"
                requirements.append(req)

    queries = safe_list_of_strings(raw.get("retrieval_queries", []), max_items=max_queries) if isinstance(raw, dict) else []
    if question not in queries:
        queries = [question] + [q for q in queries if q != question]
    queries = queries[:max_queries] or [question]

    answer_style = normalize_space(raw.get("answer_style", "")) if isinstance(raw, dict) else ""
    requires_comprehensive = safe_bool(raw.get("requires_comprehensive_coverage"), default=len(requirements) > 1) if isinstance(raw, dict) else len(requirements) > 1

    return {
        "enabled": True,
        "question": question,
        "answer_style": answer_style or infer_question_intent(question),
        "requires_comprehensive_coverage": requires_comprehensive,
        "requirements": requirements,
        "retrieval_queries": queries,
        "raw": raw,
    }


def plan_question_heuristically(question: str, max_queries: int = 3, max_requirements: int = 6) -> Dict[str, Any]:
    """
    LLM 호출 없이 복합 질문의 요구사항과 검색 질의를 구성
    원 질문을 항상 유지하고 연결어, 구두점 기준으로 분리한 절을 focused query로 사용
    """
    q = normalize_space(question)
    stripped = re.sub(r"(?:알려\s*주세요|답(?:하|해)세요|나열(?:하|해)세요|설명(?:하|해)세요)[?.!]*$", "", q).strip()
    parts = re.split(r"\s*(?:그리고|또한|및|와|과|,|;|/|\?|\.)\s*", stripped)
    parts = [normalize_space(p) for p in parts if len(normalize_space(p)) >= 4]

    requirements = []
    seen = set()
    for p in parts:
        key = normalize_for_tokenize(p)
        if not key or key in seen:
            continue
        seen.add(key)
        requirements.append({"id": f"R{len(requirements)+1}", "requirement": p, "type": infer_question_intent(p)})
        if len(requirements) >= max_requirements:
            break

    queries = [q]
    for req in requirements:
        rq = req["requirement"]
        if normalize_for_tokenize(rq) != normalize_for_tokenize(q) and rq not in queries:
            queries.append(rq)
        if len(queries) >= max_queries:
            break

    intent = infer_question_intent(q)
    comprehensive = bool(re.search(r"모두|전부|각각|나열|전체|가능한|방법들|경로들", q)) or len(requirements) > 1
    return {
        "enabled": True,
        "planner": "heuristic",
        "question": q,
        "answer_style": intent,
        "requires_comprehensive_coverage": comprehensive,
        "requirements": requirements,
        "retrieval_queries": queries[:max_queries],
        "raw": {"source": "heuristic"},
    }

def plan_question_with_llm(llm, question: str, max_queries: int = 3, max_requirements: int = 6) -> Dict[str, Any]:
    question = normalize_space(question)
    if max_queries <= 1:
        return normalize_question_plan({"requirements": [], "retrieval_queries": [question]}, question, 1)

    system_prompt = """
You are a query planner for a local PDF-only RAG system.
Analyze the user's question, but do not answer it.
Return a compact plan that helps retrieve and compose evidence from the PDF.
Do not use external knowledge.
Return only JSON.
""".strip()
    user_prompt = f"""
[User question]
{question}

Create a plan with:
1. requirements: the separate information needs that must be covered in the final answer.
2. retrieval_queries: up to {max_queries} compact Korean retrieval queries likely to find the evidence in the PDF.
3. answer_style: one of fact, list, procedure, comparison, summary, other.
4. requires_comprehensive_coverage: true if the question asks for all paths/methods/cases/items or has multiple requirements.

Rules:
- Include the original question as the first retrieval query.
- Split multi-part questions into focused retrieval queries.
- Use document-like terms rather than assumptions.
- Do not invent expected answers.

[Output JSON schema]
{{
  "answer_style": "list",
  "requires_comprehensive_coverage": true,
  "requirements": [
    {{"id": "R1", "requirement": "first required information", "type": "fact"}}
  ],
  "retrieval_queries": ["query 1", "query 2"]
}}
""".strip()
    try:
        resp = llm.create_chat_completion(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            top_p=0.9,
            max_tokens=450,
            response_format={"type": "json_object"},
        )
        raw = safe_json_loads(resp["choices"][0]["message"]["content"])
        plan = normalize_question_plan(raw, question, max_queries=max_queries)
    except Exception as e:
        plan = normalize_question_plan({"requirements": [], "retrieval_queries": [question], "error": str(e)}, question, max_queries=max_queries)
        plan["planner_error"] = str(e)
    return plan


def plan_requirement_terms(question_plan: Optional[Dict[str, Any]]) -> List[str]:
    if not question_plan:
        return []
    terms: List[str] = []
    for req in question_plan.get("requirements", []) or []:
        if isinstance(req, dict):
            text = normalize_space(req.get("requirement", ""))
        else:
            text = normalize_space(req)
        if text:
            terms.append(text)
    return terms


def is_comprehensive_plan(question_plan: Optional[Dict[str, Any]]) -> bool:
    if not question_plan:
        return False
    return bool(question_plan.get("requires_comprehensive_coverage")) or len(question_plan.get("requirements", []) or []) > 1


def structural_line_score(line: str) -> float:
    line = normalize_space(line)
    if not line:
        return 0.0
    score = 0.0
    if UNIT_START_RE.match(line):
        score += 1.0
    if re.search(r"[\[\(].{1,40}[\]\)]", line):
        score += 0.5
    if re.search(r"[:：]\s*$", line):
        score += 0.3
    if re.search(r"\b[A-Z][A-Z0-9/]{1,8}\b", line):
        score += 0.2
    if len(line) <= 80 and re.search(r"방법|절차|경로|항목|종류|목록|이용\s*시|경우|단계|선택|조회|신청|발급", line):
        score += 0.7
    return score


def extract_query_focused_text_for_composer(
    question: str,
    text: str,
    question_plan: Optional[Dict[str, Any]] = None,
    max_chars: int = 1800,
) -> str:
    """
    composer에 넘길 evidence를 질문 중심으로 압축
    단일 top span만 남기지 않고, 복수 조건/나열형 질문에서는 같은 section 내부 구조적 하위 항목과 인접 줄을 함께 보존
    """
    text = clean_text(text)
    if not text:
        return ""

    comprehensive = is_comprehensive_plan(question_plan)
    effective_max_chars = int(max_chars)
    if comprehensive:
        effective_max_chars = min(max(len(text), max_chars), max(2600, int(max_chars * 1.8)))

    if len(text) <= effective_max_chars:
        return text

    q_tokens = set(tokenize(question, min_len=2))
    req_tokens = set()
    for req_text in plan_requirement_terms(question_plan):
        req_tokens.update(tokenize(req_text, min_len=2))
    all_tokens = q_tokens | req_tokens

    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    if not lines:
        return text[:effective_max_chars].rstrip()

    selected_idx = set()
    scored: List[Tuple[float, int]] = []

    for i, line in enumerate(lines):
        line_tokens = set(tokenize(line, min_len=2))
        overlap = len(line_tokens & all_tokens)
        structural = structural_line_score(line)
        score = 1.4 * overlap + structural
        if comprehensive and structural > 0:
            score += 1.0
        if score > 0:
            scored.append((score, i))

    if comprehensive:
        # 복수 조건/전체 나열 질문은 한 줄짜리 span만 남기면 누락이 생기므로
        # 관련 줄 주변과 구조적 bullet/heading을 원래 순서대로 함께 보존
        for score, idx in scored:
            if score <= 0:
                continue
            for j in range(max(0, idx - 1), min(len(lines), idx + 4)):
                selected_idx.add(j)

        for i, line in enumerate(lines):
            if structural_line_score(line) >= 0.8:
                selected_idx.add(i)
                if i + 1 < len(lines):
                    selected_idx.add(i + 1)
                if i + 2 < len(lines) and len(lines[i + 1]) < 160:
                    selected_idx.add(i + 2)

        if scored:
            scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
            anchor_positions = sorted({idx for _, idx in scored[:6]})
            if anchor_positions:
                start_idx = max(0, anchor_positions[0] - 1)
                end_idx = min(len(lines), anchor_positions[-1] + 8)
                # 동일 section의 하위 항목을 많이 보존하되, 새 FAQ 제목으로 넘어가면 멈춤
                for j in range(start_idx, end_idx):
                    if j > start_idx and is_section_heading_text(lines[j]):
                        break
                    selected_idx.add(j)
    else:
        scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        for _, idx in scored[: max(8, min(40, len(scored)) )]:
            selected_idx.add(idx)
            if idx + 1 < len(lines):
                selected_idx.add(idx + 1)
            if idx > 0 and structural_line_score(lines[idx]) < 0.5:
                selected_idx.add(idx - 1)

    if not selected_idx:
        return text[:effective_max_chars].rstrip()

    out_lines: List[str] = []
    seen = set()
    total = 0
    for i in sorted(selected_idx):
        line = lines[i]
        key = canonical_unit_text(line)
        if not key or key in seen:
            continue
        if total + len(line) + 1 > effective_max_chars:
            # 구조적 라인은 최대한 살리고, 일반 긴 문장은 건너뜀
            if comprehensive and structural_line_score(line) >= 0.8 and len(line) < 220:
                pass
            else:
                continue
        seen.add(key)
        out_lines.append(line)
        total += len(line) + 1

    out = clean_text("\n".join(out_lines))
    return out or text[:effective_max_chars].rstrip()


def generate_retrieval_queries_with_llm(llm, question: str, max_queries: int = 3) -> Tuple[List[str], Dict[str, Any]]:
    question = normalize_space(question)
    if max_queries <= 1:
        return [question], {"enabled": False, "reason": "max_queries<=1", "queries": [question]}

    system_prompt = """
You create retrieval queries for a local PDF-only RAG system.
Return compact Korean queries that help find evidence in the document.
Do not answer the question.
Do not use external knowledge.
Return only JSON.
""".strip()
    user_prompt = f"""
[User question]
{question}

Create up to {max_queries} retrieval queries.
Rules:
- Include the original question as the first query.
- If the question has multiple requirements, split them into focused retrieval queries.
- Use terms likely to appear in the PDF.

[Output JSON schema]
{{
  "queries": ["query 1", "query 2"]
}}
""".strip()
    try:
        resp = llm.create_chat_completion(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            top_p=0.9,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        obj = safe_json_loads(resp["choices"][0]["message"]["content"])
        queries = safe_list_of_strings(obj.get("queries"), max_items=max_queries)
    except Exception as e:
        obj = {"error": str(e)}
        queries = []

    if question not in queries:
        queries = [question] + [q for q in queries if q != question]
    queries = queries[:max_queries] or [question]
    return queries, {"enabled": True, "raw": obj, "queries": queries}



NEGATION_PATTERNS = (
    r"없(?:는|을|어|습니다|나요|다면)?", r"아니", r"안\s*되", r"못\s*하", r"불가", r"제한"
)
POSITIVE_ONLY_PATTERNS = (
    r"있는\s*경우", r"가능합니다", r"가능하며", r"할\s*수\s*있"
)


def contains_negation(text: str) -> bool:
    t = normalize_space(text)
    return any(re.search(p, t) for p in NEGATION_PATTERNS)


def anchor_relevance_score(question: str, chunk: Chunk) -> float:
    """
    FAQ 제목/anchor와 사용자 질문의 일치도를 별도로 계산
    본문이 길수록 공통 단어가 많은 다른 FAQ가 Cross-Encoder 상위로 올라올 수 있으므로,
    질문형 문서에서는 제목 일치도를 rerank pool 보존과 최종 정렬에 사용
    """
    anchor = normalize_space(chunk.anchor_text or "")
    if not anchor and chunk.role == "anchor_question":
        anchor = normalize_space(chunk.text)
    if not anchor and chunk.kind == "section":
        anchor = normalize_space(str(chunk.text).splitlines()[0] if chunk.text else "")
    if not anchor:
        return 0.0
    lexical = query_overlap_score(question, anchor)
    qn = set(tokenize(question, min_len=2))
    an = set(tokenize(anchor, min_len=2))
    jaccard = len(qn & an) / max(len(qn | an), 1)
    return 0.55 * lexical + 0.45 * jaccard


def polarity_adjustment(question: str, text: str) -> float:
    """부정 조건 질문에 정반대의 긍정 조건 문장이 선택되는 것을 완화"""
    q_neg = contains_negation(question)
    t_neg = contains_negation(text)
    if q_neg and not t_neg and any(re.search(p, text) for p in POSITIVE_ONLY_PATTERNS):
        return -0.35
    if q_neg and t_neg:
        return 0.12
    return 0.0


def build_rerank_pool(question: str, merged_candidates: List[Dict[str, Any]], pool_k: int) -> List[Dict[str, Any]]:
    """RRF 상위 후보와 FAQ anchor 일치 후보를 함께 보존"""
    if not merged_candidates:
        return []
    pool_k = max(1, int(pool_k))
    regular_k = max(1, pool_k - min(8, max(2, pool_k // 5)))
    chosen = list(merged_candidates[:regular_k])
    seen = {x["chunk"].chunk_id for x in chosen}
    anchor_ranked = sorted(
        merged_candidates,
        key=lambda x: (
            anchor_relevance_score(question, x["chunk"]),
            float(x.get("merge_score") or 0.0),
        ),
        reverse=True,
    )
    for item in anchor_ranked:
        if len(chosen) >= pool_k:
            break
        cid = item["chunk"].chunk_id
        if cid in seen:
            continue
        if anchor_relevance_score(question, item["chunk"]) <= 0:
            continue
        chosen.append(item)
        seen.add(cid)
    if len(chosen) < pool_k:
        for item in merged_candidates:
            if len(chosen) >= pool_k:
                break
            if item["chunk"].chunk_id not in seen:
                chosen.append(item)
                seen.add(item["chunk"].chunk_id)
    return chosen


def rerank_with_structure(question: str, candidates: List[Dict[str, Any]], top_k: int, enabled: bool) -> List[Dict[str, Any]]:
    hits = rerank(question=question, candidates=candidates, top_k=len(candidates), enabled=enabled)
    rescored = []
    for item in hits:
        copied = dict(item)
        base = float(copied.get("rerank_score") or 0.0) if enabled else float(copied.get("merge_score") or copied.get("rrf_score") or 0.0)
        anchor = anchor_relevance_score(question, copied["chunk"])
        polarity = polarity_adjustment(question, clean_text(copied["chunk"].answer_text or copied["chunk"].text))
        copied["anchor_relevance_score"] = anchor
        copied["polarity_adjustment"] = polarity
        copied["structured_rerank_score"] = base + 0.55 * anchor + polarity
        rescored.append(copied)
    rescored.sort(key=lambda x: x["structured_rerank_score"], reverse=True)
    for rank, item in enumerate(rescored[:top_k], start=1):
        item["rank"] = rank
    return rescored[:top_k]

def retrieve_context_items_for_queries(question: str, retrieval_queries: List[str], chunks: List[Chunk], index, args) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    다중 질의의 1차 검색 결과를 먼저 합친 뒤 Cross-Encoder를 한 번만 실행
    각 질의의 Dense/BM25/RRF coverage를 보존하면서 후보를 통합하고, 원 질문 기준으로 한 번만 재랭킹
    """
    merged: Dict[str, Dict[str, Any]] = {}
    per_query: List[Dict[str, Any]] = []

    for q_idx, retrieval_query in enumerate(retrieval_queries, start=1):
        candidates = first_stage_retrieve(
            question=retrieval_query, chunks=chunks, index=index,
            dense_k=args.dense_k, bm25_k=args.bm25_k, rrf_k=args.rrf_k,
            candidate_k=args.candidate_k,
        )
        per_query.append({"query_index": q_idx, "query": retrieval_query, "candidate_count": len(candidates)})
        for item in candidates:
            c = item["chunk"]
            key = c.chunk_id
            if key not in merged:
                copied = dict(item)
                copied["retrieval_queries"] = [retrieval_query]
                copied["query_support_count"] = 1
                copied["aggregate_rrf_score"] = float(item.get("rrf_score") or 0.0)
                merged[key] = copied
            else:
                cur = merged[key]
                if retrieval_query not in cur["retrieval_queries"]:
                    cur["retrieval_queries"].append(retrieval_query)
                    cur["query_support_count"] += 1
                cur["aggregate_rrf_score"] += float(item.get("rrf_score") or 0.0)
                cur["dense_score"] = max(float(cur.get("dense_score") or 0.0), float(item.get("dense_score") or 0.0))
                cur["bm25_score"] = max(float(cur.get("bm25_score") or 0.0), float(item.get("bm25_score") or 0.0))

    merged_candidates = list(merged.values())
    for item in merged_candidates:
        item["rrf_score"] = float(item.get("aggregate_rrf_score") or 0.0)
        item["retrieval_query"] = " | ".join(item.get("retrieval_queries", []))
        item["merge_score"] = item["rrf_score"] + 0.01 * int(item.get("query_support_count", 1))
    merged_candidates.sort(key=lambda x: x.get("merge_score", 0.0), reverse=True)

    rerank_pool_k = int(getattr(args, "rerank_pool_k", max(args.candidate_k, args.top_k * 2)))
    rerank_pool = build_rerank_pool(question, merged_candidates, rerank_pool_k)
    hits = rerank_with_structure(
        question=question, candidates=rerank_pool, top_k=args.top_k, enabled=not args.no_reranker
    )
    expanded = expand_neighbors(hits=hits, chunks=chunks, window=args.expand_window, max_context_chunks=args.max_context_chunks)

    diagnostics = {
        "queries": retrieval_queries,
        "per_query": per_query,
        "unique_candidate_count": len(merged_candidates),
        "rerank_pool_count": len(rerank_pool),
        "reranker_calls": 1 if (not args.no_reranker and rerank_pool) else 0,
        "final_context_count": len(expanded),
    }
    return expanded, diagnostics

def composer_item_from_unit(unit: AnswerUnit, source: str) -> Dict[str, Any]:
    """AnswerUnit을 grounded composer가 사용하는 공통 evidence 형식으로 변환"""
    return {
        "source": source,
        "text": clean_unit_for_final(unit.text),
        "title": unit.title,
        "page": unit.page,
        "locator": unit.locator,
        "source_kind": unit.source_kind,
        "source_role": unit.source_role,
        "source_chunk_id": unit.source_chunk_id,
        "context_type": unit.context_type,
        "unit_score": float(getattr(unit, "score", 0.0) or 0.0),
        "cross_score": float(getattr(unit, "cross_score", 0.0) or 0.0),
    }


def composer_item_from_context(item: Dict[str, Any], source: str) -> Dict[str, Any]:
    """검색 context item을 grounded composer가 사용하는 공통 evidence 형식으로 변환"""
    c = item["chunk"]
    return {
        "source": source,
        "text": clean_text(c.answer_text if c.answer_text else c.text),
        "title": c.source_title,
        "page": page_string_for_chunk(c),
        "locator": c.locator,
        "source_kind": c.kind,
        "source_role": c.role,
        "source_chunk_id": c.chunk_id,
        "context_type": str(item.get("context_type", "retrieved")),
        "rerank_score": float(item.get("rerank_score") or 0.0),
        "anchor_relevance_score": float(item.get("anchor_relevance_score") or anchor_relevance_score("", c)),
        "anchor_text": str(c.anchor_text or ""),
    }


def build_composer_evidence(
    question: str,
    answer_obj: Dict[str, Any],
    ranked_units: List[AnswerUnit],
    context_items: List[Dict[str, Any]],
    max_items: int = 24,
    max_sections: int = 5,
    max_chars_per_item: int = 1800,
    question_plan: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen = set()
    comprehensive = is_comprehensive_plan(question_plan)

    def add(item: Dict[str, Any], source_priority: int = 5) -> None:
        if not item.get("text"):
            return
        key = (item.get("source_chunk_id"), canonical_unit_text(item.get("text", ""))[:160])
        if key in seen:
            return
        seen.add(key)
        item = dict(item)
        item["text"] = extract_query_focused_text_for_composer(
            question=question,
            text=item["text"],
            question_plan=question_plan,
            max_chars=max_chars_per_item,
        )
        item["source_priority"] = source_priority
        item["evidence_id"] = f"G{len(items) + 1}"
        items.append(item)

    def context_relevance(item: Dict[str, Any]) -> float:
        c = item["chunk"]
        text = clean_text(c.answer_text if c.answer_text else c.text)
        score = query_overlap_score(question, text)
        for req in plan_requirement_terms(question_plan):
            score += 0.7 * query_overlap_score(req, text)
        score += 0.05 * float(item.get("rerank_score") or 0.0)
        score += 0.3 * float(item.get("rrf_score") or 0.0)
        return score

    section_items = [item for item in context_items if item["chunk"].kind == "section"]
    section_items.sort(key=context_relevance, reverse=True)

    if comprehensive:
        # 포괄 질문이라고 관련 section을 여러 개 무조건 넣으면 다른 FAQ가 composer를 오염시킴
        # 질문과 FAQ anchor가 가장 가까운 section을 우선하고, 최고점과 충분히 가까운 section만 제한적으로 보존
        section_count = 0
        top_anchor = max((anchor_relevance_score(question, x["chunk"]) for x in section_items), default=0.0)
        for item in section_items:
            if len(items) >= max_items or section_count >= min(max_sections, 2):
                break
            a_score = anchor_relevance_score(question, item["chunk"])
            if section_count > 0 and top_anchor > 0 and a_score < top_anchor * 0.72:
                continue
            ev = composer_item_from_context(item, "coverage_parent_section_context")
            ev["anchor_relevance_score"] = a_score
            add(ev, source_priority=0)
            section_count += 1

    for ev in answer_obj.get("evidence", []) or []:
        add({
            "source": "extractive_answer_evidence",
            "text": str(ev.get("quote", "")),
            "title": str(ev.get("title", "")),
            "page": str(ev.get("page", "")),
            "locator": str(ev.get("locator", "")),
            "source_kind": str(ev.get("source_kind", "")),
            "source_role": ev.get("source_role"),
            "source_chunk_id": str(ev.get("source_chunk_id", "")),
            "context_type": str(ev.get("context_type", "final_evidence")),
        }, source_priority=1)

    for unit in ranked_units:
        if len(items) >= max_items:
            break
        add(composer_item_from_unit(unit, "ranked_answer_unit"), source_priority=2)

    if not comprehensive:
        section_count = 0
        for item in section_items:
            if len(items) >= max_items or section_count >= max_sections:
                break
            add(composer_item_from_context(item, "parent_section_context"), source_priority=3)
            section_count += 1

    if comprehensive:
        for item in sorted(context_items, key=context_relevance, reverse=True):
            if len(items) >= max_items:
                break
            c = item["chunk"]
            if c.kind == "section":
                continue
            add(composer_item_from_context(item, "supporting_context"), source_priority=4)

    items.sort(key=lambda ev: (int(ev.get("source_priority", 5)), int(str(ev.get("evidence_id", "G999")).replace("G", "") or 999)))
    for i, item in enumerate(items, start=1):
        item["evidence_id"] = f"G{i}"
    return items[:max_items]



def build_requirement_evidence_map(
    question: str,
    question_plan: Optional[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
    top_per_requirement: int = 3,
    max_total: int = 10,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """
    각 질문 요구사항에 직접 대응하는 evidence를 우선 선택
    요구사항별 점수로 대표 근거를 뽑아 coverage를 확보하고, 같은 section의 중복 chunk 발생을 제한
    """
    if not evidence_items:
        return [], {}
    reqs = []
    for idx, req in enumerate((question_plan or {}).get("requirements", []) or [], start=1):
        if isinstance(req, dict):
            rid = str(req.get("id") or f"R{idx}")
            text = normalize_space(req.get("requirement", ""))
        else:
            rid, text = f"R{idx}", normalize_space(req)
        if text:
            reqs.append((rid, text))
    if not reqs:
        reqs = [("R1", normalize_space(question))]

    selected_ids = set()
    mapping: Dict[str, List[str]] = {}
    per_section_count: Dict[str, int] = {}

    def score(req_text: str, ev: Dict[str, Any]) -> float:
        text = normalize_space(ev.get("text", ""))
        anchor = normalize_space(ev.get("anchor_text", ""))
        val = 1.15 * query_overlap_score(req_text, text)
        val += 0.45 * query_overlap_score(question, text)
        if anchor:
            val += 0.9 * query_overlap_score(req_text, anchor)
            val += 0.35 * query_overlap_score(question, anchor)
        val += 0.18 * float(ev.get("cross_score") or ev.get("rerank_score") or 0.0)
        val += 0.08 * float(ev.get("unit_score") or 0.0)
        val -= 0.06 * int(ev.get("source_priority", 5))
        val += polarity_adjustment(question, text)
        if ev.get("source_kind") == "ocr":
            val -= 0.25
        return val

    for rid, req_text in reqs:
        ranked = sorted(evidence_items, key=lambda ev: score(req_text, ev), reverse=True)
        picked = []
        for ev in ranked:
            eid = ev.get("evidence_id")
            if not eid:
                continue
            section_key = str(ev.get("source_chunk_id") or "")
            # 동일 parent/section의 거의 같은 근거가 한 requirement를 독점하지 않게 제한
            if section_key and per_section_count.get(section_key, 0) >= 2 and eid not in selected_ids:
                continue
            picked.append(eid)
            selected_ids.add(eid)
            if section_key:
                per_section_count[section_key] = per_section_count.get(section_key, 0) + 1
            if len(picked) >= top_per_requirement:
                break
        mapping[rid] = picked

    # 질문 anchor와 가장 가까운 parent section은 포괄 질문에서
    # 전체 대안/경로를 담고 있을 가능성이 높으므로 반드시 보존
    if is_comprehensive_plan(question_plan):
        sections = [ev for ev in evidence_items if ev.get("source_kind") == "section"]
        if sections:
            best = max(
                sections,
                key=lambda ev: query_overlap_score(question, ev.get("anchor_text", ""))
                + 0.5 * query_overlap_score(question, ev.get("text", "")),
            )
            selected_ids.add(best["evidence_id"])
            mapping.setdefault("R1", [])
            if best["evidence_id"] not in mapping["R1"]:
                mapping["R1"].insert(0, best["evidence_id"])

    selected = []
    for ev in evidence_items:
        if ev.get("evidence_id") not in selected_ids:
            continue
        ev2 = dict(ev)
        ev2["supports_requirements"] = [rid for rid, ids in mapping.items() if ev2["evidence_id"] in ids]
        selected.append(ev2)
    selected.sort(key=lambda ev: (
        min([int(r[1:]) for r in ev.get("supports_requirements", []) if r[1:].isdigit()] or [999]),
        int(ev.get("source_priority", 5)),
        -float(ev.get("anchor_relevance_score") or 0.0),
    ))
    selected = selected[:max_total]
    selected_set = {ev["evidence_id"] for ev in selected}
    mapping = {rid: [eid for eid in ids if eid in selected_set] for rid, ids in mapping.items()}
    return selected, mapping


def format_composer_evidence(evidence_items: List[Dict[str, Any]]) -> str:
    blocks = []
    for ev in evidence_items:
        blocks.append(textwrap.dedent(f"""
        [{ev['evidence_id']}]
        title: {ev.get('title', '')}
        page: {ev.get('page', '')}
        locator: {ev.get('locator', '')}
        source_kind: {ev.get('source_kind', '')}
        supports_requirements: {', '.join(ev.get('supports_requirements', [])) or 'general'}
        text:
        {ev.get('text', '')}
        """).strip())
    return "\n\n".join(blocks)


def format_question_plan_for_prompt(question_plan: Optional[Dict[str, Any]]) -> str:
    if not question_plan:
        return "없음"
    compact = {
        "answer_style": question_plan.get("answer_style", ""),
        "requires_comprehensive_coverage": question_plan.get("requires_comprehensive_coverage", False),
        "requirements": question_plan.get("requirements", []),
    }
    return json.dumps(compact, ensure_ascii=False, indent=2)




def generated_answer_is_too_extractive(
    final_answer: str,
    extractive_answer: str,
    evidence_items: List[Dict[str, Any]],
    question_plan: Optional[Dict[str, Any]] = None,
) -> bool:
    """생성 답변이 단일 근거 원문 복사에 가까운지 확인"""
    fa = normalize_space(final_answer)
    if not fa:
        return True
    ex = normalize_space(extractive_answer)
    if ex and (fa == ex or SequenceMatcher(None, canonical_unit_text(fa), canonical_unit_text(ex)).ratio() >= 0.96):
        return True
    comprehensive = is_comprehensive_plan(question_plan)
    if comprehensive:
        used_like = 0
        for ev in evidence_items:
            ev_text = normalize_space(ev.get("text", ""))
            if not ev_text:
                continue
            sim = SequenceMatcher(None, canonical_unit_text(fa), canonical_unit_text(ev_text)).ratio()
            if sim >= 0.94 or canonical_unit_text(fa) in canonical_unit_text(ev_text):
                used_like += 1
        if used_like >= 1 and len(evidence_items) >= 3:
            return True
    return False


def call_grounded_composer(
    llm,
    question: str,
    evidence_items: List[Dict[str, Any]],
    question_plan: Optional[Dict[str, Any]],
    max_tokens: int,
    strict_synthesis: bool = False,
) -> Dict[str, Any]:
    """JSON 우선, 실패 시 plain-text 형식으로 한 번 더 생성"""
    system_prompt, user_prompt = build_grounded_answer_prompt(
        question,
        evidence_items,
        question_plan=question_plan,
        strict_synthesis=strict_synthesis,
    )
    try:
        resp = llm.create_chat_completion(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            top_p=0.9,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return safe_json_loads(resp["choices"][0]["message"]["content"])
    except Exception as json_error:
        error_text = str(json_error)
        if "exceed context window" in error_text.lower() or "requested tokens" in error_text.lower():
            raise
        plain_system = system_prompt + "\nJSON 생성에 실패했습니다. 아래 지정 형식만 출력하십시오."
        plain_user = f"""
[Question]
{question}

[Question plan]
{format_question_plan_for_prompt(question_plan)}

[Evidence]
{format_composer_evidence(evidence_items)}

Write the answer in this exact format:
FINAL_ANSWER: <natural Korean answer grounded only in the evidence>
USED_EVIDENCE_IDS: <comma-separated evidence ids>
ADDITIONAL_EXPLANATION: 없음
""".strip()
        resp = llm.create_chat_completion(
            messages=[{"role": "system", "content": plain_system}, {"role": "user", "content": plain_user}],
            temperature=0.0,
            top_p=0.9,
            max_tokens=max_tokens,
        )
        content = resp["choices"][0]["message"]["content"]
        final = ""
        used_ids: List[str] = []
        add = "없음"
        m = re.search(r"FINAL_ANSWER\s*:\s*(.+?)(?:\nUSED_EVIDENCE_IDS\s*:|\Z)", content, flags=re.S | re.I)
        if m:
            final = normalize_space(m.group(1))
        else:
            final = normalize_space(content)
        m = re.search(r"USED_EVIDENCE_IDS\s*:\s*(.+?)(?:\nADDITIONAL_EXPLANATION\s*:|\Z)", content, flags=re.S | re.I)
        if m:
            used_ids = re.findall(r"G\d+", m.group(1))
        m = re.search(r"ADDITIONAL_EXPLANATION\s*:\s*(.+)$", content, flags=re.S | re.I)
        if m:
            add = normalize_space(m.group(1)) or "없음"
        return {
            "final_answer": final,
            "used_evidence_ids": used_ids,
            "covered_requirements": {},
            "missing_requirements": [],
            "additional_explanation": add,
            "plain_fallback_used": True,
            "json_error": str(json_error),
        }


def build_seed_answer_for_grounded_generation(
    question: str,
    ranked_units: List[AnswerUnit],
    max_seed_units: int = 6,
) -> Dict[str, Any]:
    """grounded composer에 넘길 초기 근거 객체를 만듦"""
    if not ranked_units:
        return {
            "final_answer": "문서에서 확인되지 않음",
            "evidence": [],
            "additional_explanation": "검색된 근거가 없습니다.",
            "render_diagnostics": {"render_mode": "grounded_seed_empty"},
            "ocr_supporting_evidence": [],
        }
    seed_units = dedupe_selected_units(question, ranked_units[:max_seed_units])
    if not seed_units:
        seed_units = ranked_units[:1]
    evidence = []
    for u in seed_units:
        evidence.append({
            "title": u.title,
            "page": u.page,
            "locator": u.locator,
            "quote": clean_unit_for_final(u.text),
            "source_kind": u.source_kind,
            "source_role": u.source_role,
            "source_chunk_id": u.source_chunk_id,
            "context_type": u.context_type,
        })
    return {
        "final_answer": normalize_space(" ".join(ev["quote"] for ev in evidence[:2])),
        "evidence": evidence,
        "additional_explanation": "없음",
        "render_diagnostics": {
            "render_mode": "grounded_seed",
            "seed_unit_ids": [u.unit_id for u in seed_units],
        },
        "ocr_supporting_evidence": collect_ocr_supporting_evidence(question, ranked_units),
    }
def build_grounded_answer_prompt(
    question: str,
    evidence_items: List[Dict[str, Any]],
    question_plan: Optional[Dict[str, Any]] = None,
    strict_synthesis: bool = False,
) -> Tuple[str, str]:
    system_prompt = """
당신은 PDF 근거 기반 질의응답 시스템의 최종 답변 작성자입니다.
제공된 근거만 사용해 질문에 직접 답하십시오.

작성 규칙:
1. 근거 문장을 그대로 이어 붙이지 말고, 질문의 문법에 맞는 자연스러운 한국어 문장으로 재구성합니다.
2. 절차형 원문이 '설치된 앱 실행 후 메뉴 선택'이라고 되어 있더라도, 질문이 설치할 앱을 묻는다면 'OO 앱을 설치한 뒤, 앱에서 XX 메뉴를 선택합니다'처럼 답합니다.
3. 질문이 요구하는 정보만 답하고, 같은 단어가 등장하더라도 다른 업무·절차·조회 목적의 근거는 제외합니다.
4. supports_requirements가 지정된 근거를 우선 사용하고, R1·R2 등 모든 요구사항을 각각 답변에 반영합니다.
5. '모두', '전부', '가능한 대안', '경로'를 묻는 질문은 선택된 근거 안에 명시된 서로 다른 대안·경로·제한을 빠짐없이 나열합니다.
6. 질문과 다른 FAQ 제목·다른 업무 목적의 내용은 절대 답변에 포함하지 않습니다. 예를 들어 부호 조회 질문에 통관이력 조회, 정보 변경, 재발급 절차를 섞지 않습니다.
7. used_evidence_ids에는 최종 답변의 모든 핵심 문장을 직접 뒷받침하는 근거 ID를 모두 기록합니다. 근거 하나가 답변 전체를 뒷받침하지 않으면 필요한 ID를 추가합니다.
8. 답변은 간결하되 완전해야 하며, 출처 문구·번호·화살표를 그대로 복사한 발췌문 형태로 작성하지 않습니다.
9. 근거에 없는 사실은 추론하거나 추가하지 않습니다.
10. 반드시 JSON 객체 하나만 반환합니다.
""".strip()
    user_prompt = f"""
[질문]
{question}

[질문 요구사항]
{format_question_plan_for_prompt(question_plan)}

[근거]
{format_composer_evidence(evidence_items)}

[출력 JSON]
{{
  "final_answer": "질문에 직접 답하는 자연스러운 한국어 문장",
  "used_evidence_ids": ["G1"],
  "covered_requirements": {{"R1": true}},
  "missing_requirements": [],
  "additional_explanation": "없음"
}}
""".strip()
    return system_prompt, user_prompt


def fit_composer_evidence_to_budget(
    llm,
    question: str,
    evidence_items: List[Dict[str, Any]],
    n_ctx: int,
    max_tokens: int,
    safety_margin: int = 384,
    min_items: int = 2,
    question_plan: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """실제 chat template token 수를 기준으로 context에 들어갈 evidence를 선택한다."""
    current = list(evidence_items)
    prompt_limit = max(512, int(n_ctx) - int(max_tokens) - int(safety_margin))
    history = []

    def prompt_tokens(items: List[Dict[str, Any]]) -> int:
        system_prompt, user_prompt = build_grounded_answer_prompt(
            question, items, question_plan=question_plan, strict_synthesis=True
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if hasattr(llm, "count_chat_tokens"):
            return int(llm.count_chat_tokens(messages))
        return count_llama_tokens(llm, system_prompt + "\n\n" + user_prompt) + 32

    while current:
        count = prompt_tokens(current)
        history.append({"evidence_count": len(current), "prompt_tokens": count})
        if count <= prompt_limit:
            return current, {
                "reason": "fit_ok",
                "prompt_tokens": count,
                "prompt_limit": prompt_limit,
                "history": history,
            }

        if len(current) > min_items:
            current = current[:-1]
            continue

        # 최소 evidence 수도 너무 길면 각 evidence를 균등하게 압축
        overflow_ratio = max(0.25, min(0.85, prompt_limit / max(count, 1) * 0.88))
        changed = False
        shortened = []
        for ev in current:
            ev2 = dict(ev)
            text = str(ev2.get("text", ""))
            target_chars = max(240, int(len(text) * overflow_ratio))
            if len(text) > target_chars:
                ev2["text"] = text[:target_chars].rstrip() + "…"
                changed = True
            shortened.append(ev2)
        if not changed:
            break
        current = shortened

    return current[:1], {
        "reason": "fit_minimal",
        "prompt_limit": prompt_limit,
        "history": history,
    }


def compose_grounded_answer_with_llm(
    llm,
    question: str,
    answer_obj: Dict[str, Any],
    ranked_units: List[AnswerUnit],
    context_items: List[Dict[str, Any]],
    args,
    question_plan: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if getattr(args, "answer_mode", "grounded") != "grounded":
        return answer_obj, {"enabled": False, "reason": "answer_mode_not_grounded"}

    evidence_items = build_composer_evidence(
        question=question,
        answer_obj=answer_obj,
        ranked_units=ranked_units,
        context_items=context_items,
        max_items=getattr(args, "max_composer_evidence", 24),
        max_sections=getattr(args, "max_composer_sections", 5),
        max_chars_per_item=getattr(args, "max_chars_per_composer_evidence", 1800),
        question_plan=question_plan,
    )
    if not evidence_items:
        answer_obj = dict(answer_obj)
        answer_obj["additional_explanation"] = "근거 생성용 evidence가 없어 추출형 답변을 사용했습니다."
        return answer_obj, {"enabled": True, "reason": "no_evidence_items"}

    evidence_items, requirement_evidence_map = build_requirement_evidence_map(
        question=question,
        question_plan=question_plan,
        evidence_items=evidence_items,
        top_per_requirement=3,
        max_total=min(int(getattr(args, "max_composer_evidence", 12)), 10),
    )
    if not evidence_items:
        answer_obj = dict(answer_obj)
        answer_obj["additional_explanation"] = "요구사항에 대응하는 근거를 선택하지 못해 추출형 답변을 사용했습니다."
        return answer_obj, {"enabled": True, "reason": "no_requirement_evidence"}

    requested_budget = getattr(args, "composer_token_budget", getattr(args, "context_token_budget", 6200))
    n_ctx = int(getattr(args, "n_ctx", 8192))
    max_tokens = int(getattr(args, "composer_max_tokens", 320))
    safety_margin = int(getattr(args, "composer_safety_margin", 384))

    fitted, fitting_diagnostics = fit_composer_evidence_to_budget(
        llm=llm,
        question=question,
        evidence_items=evidence_items,
        n_ctx=n_ctx,
        max_tokens=max_tokens,
        safety_margin=safety_margin,
        question_plan=question_plan,
    )
    if not fitted:
        fitted = evidence_items[: min(4, len(evidence_items))]

    attempts: List[Dict[str, Any]] = []
    last_error = None
    obj: Optional[Dict[str, Any]] = None
    used_evidence_items = fitted

    # 기본 경로는 strict synthesis 1회 호출하나,
    # 빈 결과나 실행 오류일 때만 더 작은 evidence로 한 번 재시도
    max_attempts = max(1, int(getattr(args, "composer_max_attempts", 2)))
    candidate_sets = [fitted]
    if max_attempts > 1 and len(fitted) > 4:
        candidate_sets.append(fitted[: max(4, len(fitted) // 2)])

    for pass_idx, candidate_evidence in enumerate(candidate_sets[:max_attempts], start=1):
        try:
            obj = call_grounded_composer(
                llm=llm, question=question, evidence_items=candidate_evidence,
                question_plan=question_plan, max_tokens=max_tokens, strict_synthesis=True,
            )
            final = normalize_space(obj.get("final_answer", ""))
            attempts.append({
                "pass": pass_idx, "strict_synthesis": True,
                "evidence_count": len(candidate_evidence), "ok": bool(final),
                "plain_fallback_used": bool(obj.get("plain_fallback_used")),
            })
            if final:
                used_evidence_items = candidate_evidence
                break
            obj = None
        except Exception as e:
            last_error = e
            obj = None
            attempts.append({
                "pass": pass_idx, "strict_synthesis": True,
                "evidence_count": len(candidate_evidence), "ok": False,
                "error": str(e)[:500],
            })

    if obj is None or not normalize_space(obj.get("final_answer", "")):
        fallback = dict(answer_obj)
        fallback["additional_explanation"] = (
            "LLM 기반 최종 답변 생성에 실패하여 추출형 답변을 사용했습니다. "
            f"원인: {str(last_error)[:300] if last_error else 'empty generation'}"
        )
        fallback.setdefault("render_diagnostics", {})["grounded_generation"] = {
            "enabled": True,
            "reason": "generation_failed_all_attempts",
            "attempts": attempts,
        }
        return fallback, fallback["render_diagnostics"]["grounded_generation"]

    final_answer = normalize_space(obj.get("final_answer", ""))
    evidence_map = {ev["evidence_id"]: ev for ev in used_evidence_items}
    used_ids = [str(x).strip() for x in obj.get("used_evidence_ids", []) if str(x).strip() in evidence_map]
    if not used_ids:
        used_ids = [ev["evidence_id"] for ev in used_evidence_items[: min(5, len(used_evidence_items))]]

    new_evidence = []
    for eid in used_ids:
        ev = evidence_map[eid]
        new_evidence.append({
            "title": ev.get("title", ""),
            "page": ev.get("page", ""),
            "locator": ev.get("locator", ""),
            "quote": ev.get("text", ""),
            "source_kind": ev.get("source_kind", ""),
            "source_role": ev.get("source_role"),
            "source_chunk_id": ev.get("source_chunk_id", ""),
            "context_type": ev.get("context_type", ""),
        })

    generated = dict(answer_obj)
    generated.setdefault("render_diagnostics", {})["extractive_answer_before_generation"] = answer_obj.get("final_answer", "")
    generated["final_answer"] = final_answer
    generated["evidence"] = new_evidence or answer_obj.get("evidence", [])
    generated["additional_explanation"] = normalize_space(obj.get("additional_explanation", "없음")) or "없음"
    generated.setdefault("render_diagnostics", {})["grounded_generation"] = {
        "enabled": True,
        "reason": "ok",
        "used_evidence_ids": used_ids,
        "evidence_count": len(used_evidence_items),
        "total_evidence_candidates": len(evidence_items),
        "safe_token_budget": fitting_diagnostics.get("prompt_limit"),
        "fitting_diagnostics": fitting_diagnostics,
        "attempts": attempts,
        "question_plan": question_plan,
        "requirement_evidence_map": requirement_evidence_map,
        "raw": obj,
    }
    return generated, generated["render_diagnostics"]["grounded_generation"]

def answer_question(
    llm,
    question: str,
    chunks: List[Chunk],
    index,
    args,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    stage_t0 = time.perf_counter()
    planner_mode = getattr(args, "query_planner", "heuristic")
    if planner_mode == "llm":
        question_plan = plan_question_with_llm(
            llm=llm, question=question,
            max_queries=getattr(args, "num_retrieval_queries", 1),
            max_requirements=getattr(args, "max_question_requirements", 6),
        )
    else:
        question_plan = plan_question_heuristically(
            question=question,
            max_queries=getattr(args, "num_retrieval_queries", 1),
            max_requirements=getattr(args, "max_question_requirements", 6),
        )
    planner_sec = time.perf_counter() - stage_t0
    retrieval_queries = question_plan.get("retrieval_queries", [question]) or [question]
    stage_t0 = time.perf_counter()
    context_items, retrieval_diagnostics = retrieve_context_items_for_queries(
        question=question,
        retrieval_queries=retrieval_queries,
        chunks=chunks,
        index=index,
        args=args,
    )
    retrieval_sec = time.perf_counter() - stage_t0
    raw_context_count = len(context_items)
    stage_t0 = time.perf_counter()
    candidate_units = build_candidate_units(question, context_items, args.max_units_per_chunk, args.max_chars_per_answer_unit)
    ranked_units = rerank_answer_units(question, candidate_units, args.unit_cross_top_n, args.max_answer_units, enabled=not args.no_reranker)
    unit_rerank_sec = time.perf_counter() - stage_t0
    generation_t0 = time.perf_counter()

    if getattr(args, "answer_mode", "grounded") == "grounded":
        selection_obj = {
            "selected_unit_ids": [],
            "additional_explanation": "grounded 모드에서는 최종 composer가 답변을 생성하므로 selector는 생략했습니다.",
            "selector_skipped": True,
        }
        llm_units = ranked_units[: min(len(ranked_units), args.max_answer_units)]
        validated_obj = {"selected_units": [], "additional_explanation": selection_obj["additional_explanation"]}
        answer_obj = build_seed_answer_for_grounded_generation(question, ranked_units)
        coverage_diagnostics = {"before": {}, "after": {}, "reason": "deferred_to_grounded_composer"}
        extractive_answer_obj = dict(answer_obj)
        answer_obj, generation_diagnostics = compose_grounded_answer_with_llm(
            llm, question, answer_obj, ranked_units, context_items, args, question_plan=question_plan
        )
    else:
        llm_units = fit_units_to_llm_budget(llm, question, ranked_units, token_budget=args.context_token_budget)
        selection_obj = select_answer_units_with_llm(llm, question, llm_units)
        validated_obj = validate_selected_units(selection_obj, llm_units)
        if not validated_obj.get("selected_units"):
            answer_obj = fallback_unit_answer(question, llm_units or ranked_units)
        else:
            answer_obj = build_answer_from_units(validated_obj, question=question)
        extractive_answer_obj = dict(answer_obj)
        answer_obj, coverage_diagnostics = repair_answer_if_needed(question, answer_obj, ranked_units)
        generation_diagnostics = {"enabled": False, "reason": "extractive_mode"}
    generation_sec = time.perf_counter() - generation_t0
    generated_coverage = evaluate_answer_coverage(question, answer_obj)
    diagnostics = {
        "question_plan": question_plan,
        "query_plan": {"enabled": True, "queries": retrieval_queries, "source": "question_planner"},
        "retrieval_diagnostics": retrieval_diagnostics,
        "unit_selection_raw": selection_obj,
        "raw_selected_units": [asdict(u) for u in validated_obj.get("selected_units", [])],
        "extractive_answer_before_generation": extractive_answer_obj.get("final_answer", ""),
        "render_diagnostics": answer_obj.get("render_diagnostics", {}),
        "coverage_diagnostics": coverage_diagnostics,
        "generated_coverage_diagnostics": generated_coverage,
        "generation_diagnostics": generation_diagnostics,
        "top_candidate_units": [asdict(u) for u in ranked_units[: min(len(ranked_units), 20)]],
        "raw_context_count": raw_context_count,
        "candidate_unit_count": len(candidate_units),
        "llm_unit_count": len(llm_units),
        "question_intent": infer_question_intent(question),
        "stage_timing_sec": {
            "query_planning": round(planner_sec, 4),
            "retrieval_and_chunk_rerank": round(retrieval_sec, 4),
            "answer_unit_rerank": round(unit_rerank_sec, 4),
            "answer_generation": round(generation_sec, 4),
            "total": round(planner_sec + retrieval_sec + unit_rerank_sec + generation_sec, 4),
        },
    }
    return answer_obj, context_items, diagnostics

def make_debug_block(
    question_id: str,
    question: str,
    context_items: List[Dict[str, Any]],
    diagnostics: Optional[Dict[str, Any]] = None,
) -> str:
    lines = []
    lines.append(f"## {question_id} 검색 디버그")
    lines.append("")
    lines.append(f"질문: {question}")
    lines.append("")

    if diagnostics:
        lines.append("### LLM unit selection")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(diagnostics, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    for i, item in enumerate(context_items, start=1):
        c = item["chunk"]
        preview = re.sub(r"\s+", " ", c.text)[:700]
        rerank_score = item.get("rerank_score", None)
        page = f"p.{c.page}" if not c.page_end or c.page_end == c.page else f"p.{c.page}-{c.page_end}"

        lines.append(
            f"- E{i} | rank={item.get('rank')} "
            f"source={item.get('source')} "
            f"context_type={item.get('context_type')} "
            f"rrf={float(item.get('rrf_score', 0.0)):.4f} "
            f"dense={float(item.get('dense_score', 0.0)):.4f} "
            f"bm25={float(item.get('bm25_score', 0.0)):.4f} "
            f"rerank={rerank_score if rerank_score is not None else 'None'} | "
            f"{page} / {c.kind} / {c.locator} / {c.chunk_id}\n"
            f"  - {preview}"
        )

    lines.append("")
    return "\n".join(lines)


def safe_model_filename(model_key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", model_key).strip("_")


def selected_llm_model_keys(args) -> List[str]:
    requested = getattr(args, "llm_model", DEFAULT_LLM_MODEL)
    if requested == "all":
        return list(LLM_PROFILES.keys())
    if requested not in LLM_PROFILES:
        valid = ", ".join(list(LLM_PROFILES.keys()) + ["all"])
        raise ValueError(f"지원하지 않는 --llm_model 값입니다: {requested}. 사용 가능: {valid}")
    return [requested]



def selected_reranker_modes(args) -> List[bool]:
    requested = getattr(args, "reranker_mode", "on")
    if getattr(args, "no_reranker", False):
        requested = "off"
    if requested == "all":
        return [True, False]
    if requested == "on":
        return [True]
    if requested == "off":
        return [False]
    raise ValueError(f"지원하지 않는 --reranker_mode 값입니다: {requested}. 사용 가능: on, off, all")


def reranker_suffix(reranker_enabled: bool) -> str:
    return "reranker_on" if reranker_enabled else "reranker_off"


def output_path_for_config(base_name: str, model_key: str, reranker_enabled: bool, multi_config: bool) -> Path:
    if not multi_config:
        return OUTPUT_DIR / base_name
    stem, suffix = os.path.splitext(base_name)
    return OUTPUT_DIR / f"{stem}_{safe_model_filename(model_key)}_{reranker_suffix(reranker_enabled)}{suffix}"


def run_problem_set_for_config(args, model_key: str, reranker_enabled: bool, multi_config: bool) -> List[Dict[str, Any]]:
    chunks = load_chunks()
    index = load_index()
    run_args = argparse.Namespace(**vars(args))
    run_args.no_reranker = not reranker_enabled

    llm = load_llm(n_ctx=run_args.n_ctx, n_gpu_layers=run_args.n_gpu_layers, model_key=model_key, llm_backend=run_args.llm_backend, llm_force_cpu=run_args.llm_force_cpu, n_batch=run_args.llm_n_batch, n_ubatch=run_args.llm_n_ubatch, llm_timeout=run_args.llm_timeout)
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    all_results = []

    reranker_label = "reranker on" if reranker_enabled else "reranker off"
    title = f"{get_llm_model_label(model_key)} / {reranker_label}"
    md_lines = [f"# B형 RAG 문제세트 답변 결과 - {title}", ""]
    debug_lines = [f"# Retrieval Debug Log - {title}", ""]

    for item in PROBLEM_SET:
        qid = item["id"]
        question = item["question"]
        console.print(f"\n[bold cyan]{qid}[/bold cyan] {question} [dim]({model_key}, {reranker_label})[/dim]")
        answer_obj, context_items, diagnostics = answer_question(llm=llm, question=question, chunks=chunks, index=index, args=run_args)
        gen_diag = diagnostics.get("generation_diagnostics", {}) if isinstance(diagnostics, dict) else {}
        gen_note = ""
        if gen_diag and gen_diag.get("enabled") and gen_diag.get("reason") != "ok":
            gen_note = f" / 생성상태: {gen_diag.get('reason')}"
        md_lines += [f"## {qid}", "", f"**질문**: {question}", "", f"**최종답**: {answer_obj.get('final_answer', '')}", "", "**근거**"]
        for ev in answer_obj.get("evidence", []):
            md_lines.append(f"- 제목: {ev.get('title', '')} / 페이지: {ev.get('page', '')} / 위치: {ev.get('locator', '')} / 근거 발췌: {ev.get('quote', '')}")
        md_lines += ["", f"**추가설명**: {answer_obj.get('additional_explanation', '없음')}{gen_note}", ""]
        debug_lines.append(make_debug_block(qid, question, context_items, diagnostics))
        all_results.append({
            "model_key": model_key,
            "model_label": get_llm_model_label(model_key),
            "reranker_enabled": reranker_enabled,
            "reranker_label": reranker_label,
            "id": qid,
            "question": question,
            "answer": answer_obj.get("final_answer", ""),
            "evidence": answer_obj.get("evidence", []),
            "ocr_supporting_evidence": answer_obj.get("ocr_supporting_evidence", []),
            "additional_explanation": answer_obj.get("additional_explanation", "없음"),
            "diagnostics": diagnostics,
            "context": [{
                "evidence_id": f"E{i}",
                "rank": item_ctx.get("rank"),
                "source": item_ctx.get("source"),
                "context_type": item_ctx.get("context_type"),
                "retrieval_query": item_ctx.get("retrieval_query"),
                "rrf_score": item_ctx.get("rrf_score"),
                "dense_score": item_ctx.get("dense_score"),
                "bm25_score": item_ctx.get("bm25_score"),
                "rerank_score": item_ctx.get("rerank_score"),
                "chunk": asdict(item_ctx["chunk"]),
            } for i, item_ctx in enumerate(context_items, start=1)],
        })

    answers_md = output_path_for_config("answers.md", model_key, reranker_enabled, multi_config)
    answers_json = output_path_for_config("answers.json", model_key, reranker_enabled, multi_config)
    debug_md = output_path_for_config("retrieval_debug.md", model_key, reranker_enabled, multi_config)

    answers_md.write_text("\n".join(md_lines), encoding="utf-8")
    with open(answers_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    debug_md.write_text("\n".join(debug_lines), encoding="utf-8")
    write_ocr_debug(chunks)

    console.print(f"\n[green]완료[/green] {model_key} / {reranker_label}")
    console.print(f"- {answers_md}")
    console.print(f"- {answers_json}")
    console.print(f"- {debug_md}")

    del llm
    gc.collect()
    return all_results


def write_compare_outputs(all_config_results: Dict[str, List[Dict[str, Any]]]) -> None:
    if len(all_config_results) <= 1:
        return
    lines = ["# LLM / Reranker 비교 결과", ""]
    combined = []
    by_qid: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for config_key, results in all_config_results.items():
        for row in results:
            combined.append(row)
            by_qid.setdefault(row["id"], {})[config_key] = row
    for qid, config_rows in by_qid.items():
        question = next(iter(config_rows.values())).get("question", "")
        lines += [f"## {qid}", "", f"**질문**: {question}", ""]
        for config_key, row in config_rows.items():
            label = f"{row.get('model_label', row.get('model_key'))} / {row.get('reranker_label')}"
            lines += [f"### {label}", "", row.get("answer", ""), ""]
    (OUTPUT_DIR / "answers_compare.md").write_text("\n".join(lines), encoding="utf-8")
    with open(OUTPUT_DIR / "answers_compare.json", "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)


def run_problem_set(args) -> None:
    model_keys = selected_llm_model_keys(args)
    reranker_modes = selected_reranker_modes(args)
    multi_config = len(model_keys) * len(reranker_modes) > 1
    all_config_results: Dict[str, List[Dict[str, Any]]] = {}

    for model_key in model_keys:
        for reranker_enabled in reranker_modes:
            config_key = f"{model_key}_{reranker_suffix(reranker_enabled)}"
            all_config_results[config_key] = run_problem_set_for_config(args, model_key, reranker_enabled, multi_config)

    write_compare_outputs(all_config_results)

def chunk_kind_counts(chunks: List[Chunk]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in chunks:
        counts[c.kind] = counts.get(c.kind, 0) + 1
    return counts


def write_ocr_debug(chunks: List[Chunk]) -> None:
    """OCR chunk가 인덱스에 포함됐는지 확인할 수 있는 로그를 씀"""
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    ocr_chunks = [c for c in chunks if c.kind == "ocr"]
    pages = sorted({c.page for c in ocr_chunks})
    lines = [
        "# OCR / Image Indexing Debug",
        "",
        f"- OCR chunks indexed: {len(ocr_chunks)}",
        f"- OCR pages indexed: {pages}",
        "",
    ]
    for c in ocr_chunks[:50]:
        preview = re.sub(r"\s+", " ", c.text)[:500]
        lines.append(f"## {c.chunk_id} / p.{c.page} / {c.locator}")
        lines.append(preview)
        lines.append("")
    (OUTPUT_DIR / "ocr_debug.md").write_text("\n".join(lines), encoding="utf-8")


def rebuild(args) -> None:
    pdf_path = resolve_pdf_path(args.pdf)
    console.print(f"[bold]PDF 사용:[/bold] {pdf_path}")

    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    chunks = extract_all_chunks(
        pdf_path,
        use_ocr=args.ocr,
        include_noisy_ocr=args.include_noisy_ocr,
    )

    if not chunks:
        raise RuntimeError("추출된 chunk가 없습니다. PDF 경로 또는 OCR 환경을 확인하세요.")

    save_chunks(chunks)
    write_ocr_debug(chunks)
    build_index(chunks)

    kind_counts = chunk_kind_counts(chunks)

    console.print(f"[green]인덱스 구축 완료[/green] chunks={len(chunks)} kinds={kind_counts}")
    if args.ocr and kind_counts.get("ocr", 0) == 0:
        console.print("[red]경고: --ocr가 지정되었지만 인덱스에 포함된 OCR chunk가 0개입니다. tesseract/언어팩/OCR 추출 로그를 확인하세요.[/red]")



def ask_one(args) -> None:
    chunks = load_chunks()
    index = load_index()
    results = {}
    model_keys = selected_llm_model_keys(args)
    reranker_modes = selected_reranker_modes(args)

    for model_key in model_keys:
        for reranker_enabled in reranker_modes:
            run_args = argparse.Namespace(**vars(args))
            run_args.no_reranker = not reranker_enabled
            reranker_label = "reranker on" if reranker_enabled else "reranker off"
            config_key = f"{model_key}_{reranker_suffix(reranker_enabled)}"

            llm = load_llm(n_ctx=run_args.n_ctx, n_gpu_layers=run_args.n_gpu_layers, model_key=model_key, llm_backend=run_args.llm_backend, llm_force_cpu=run_args.llm_force_cpu, n_batch=run_args.llm_n_batch, n_ubatch=run_args.llm_n_ubatch, llm_timeout=run_args.llm_timeout)
            answer_obj, context_items, diagnostics = answer_question(
                llm=llm,
                question=run_args.ask,
                chunks=chunks,
                index=index,
                args=run_args,
            )
            results[config_key] = {
                "model_key": model_key,
                "model_label": get_llm_model_label(model_key),
                "reranker_enabled": reranker_enabled,
                "reranker_label": reranker_label,
                "answer": answer_obj,
                "diagnostics": diagnostics,
            }
            print(f"\n===== {get_llm_model_label(model_key)} / {reranker_label} =====")
            print(json.dumps(answer_obj, ensure_ascii=False, indent=2))
            print("\n\n--- 검색 디버그 ---")
            print(make_debug_block("사용자질문", run_args.ask, context_items, diagnostics))

            del llm
            gc.collect()

    if len(results) > 1:
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        with open(OUTPUT_DIR / "ask_compare.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--pdf", type=str, default=None)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--include_noisy_ocr", action="store_true")
    parser.add_argument("--run_problem_set", action="store_true")
    parser.add_argument("--ask", type=str, default=None)
    parser.add_argument("--llm_model", type=str, default=DEFAULT_LLM_MODEL, choices=list(LLM_PROFILES.keys()) + ["all"])
    parser.add_argument("--answer_mode", type=str, default="grounded", choices=["extractive", "grounded"])

    parser.add_argument("--dense_k", type=int, default=60)
    parser.add_argument("--bm25_k", type=int, default=60)
    parser.add_argument("--rrf_k", type=int, default=60)
    parser.add_argument("--candidate_k", type=int, default=40)
    parser.add_argument("--top_k", type=int, default=14)
    parser.add_argument("--expand_window", type=int, default=2)
    parser.add_argument("--max_context_chunks", type=int, default=24)
    parser.add_argument("--context_token_budget", type=int, default=6200)
    parser.add_argument("--max_llm_context_items", type=int, default=14)
    parser.add_argument("--max_chars_per_context_item", type=int, default=1200)
    parser.add_argument("--max_units_per_chunk", type=int, default=16)
    parser.add_argument("--max_chars_per_answer_unit", type=int, default=1500)
    parser.add_argument("--unit_cross_top_n", type=int, default=28)
    parser.add_argument("--max_answer_units", type=int, default=18)
    parser.add_argument("--num_retrieval_queries", type=int, default=3)
    parser.add_argument("--max_question_requirements", type=int, default=6)
    parser.add_argument("--query_planner", type=str, default="heuristic", choices=["heuristic", "llm"])
    parser.add_argument("--rerank_pool_k", type=int, default=40)
    parser.add_argument("--composer_token_budget", type=int, default=2600)
    parser.add_argument("--composer_max_tokens", type=int, default=320)
    parser.add_argument("--max_composer_evidence", type=int, default=12)
    parser.add_argument("--max_composer_sections", type=int, default=3)
    parser.add_argument("--max_chars_per_composer_evidence", type=int, default=1400)
    parser.add_argument("--composer_max_attempts", type=int, default=2)
    parser.add_argument("--composer_safety_margin", type=int, default=384)

    parser.add_argument("--reranker_mode", type=str, default="on", choices=["on", "off", "all"])
    parser.add_argument("--no_reranker", action="store_true")
    parser.add_argument("--llm_backend", type=str, default="subprocess", choices=["subprocess", "python"])
    parser.add_argument("--llm_force_cpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--llm_timeout", type=int, default=240)
    parser.add_argument("--llm_n_batch", type=int, default=128)
    parser.add_argument("--llm_n_ubatch", type=int, default=128)
    parser.add_argument("--n_ctx", type=int, default=8192)
    parser.add_argument("--n_gpu_layers", type=int, default=0)

    args = parser.parse_args()

    if args.rebuild:
        rebuild(args)

    if args.run_problem_set:
        run_problem_set(args)

    if args.ask:
        ask_one(args)

    if not args.rebuild and not args.run_problem_set and not args.ask:
        parser.print_help()


if __name__ == "__main__":
    main()
