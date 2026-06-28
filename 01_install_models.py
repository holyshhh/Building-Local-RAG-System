from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download

BASE = Path(__file__).resolve().parent
MODELS = BASE / "models"

EMBED_REPO = "intfloat/multilingual-e5-small"
RERANKER_REPO = "BAAI/bge-reranker-v2-m3"


LLM_REPO = "Qwen/Qwen3-4B-GGUF"
LLM_DIR_NAME = "qwen3-4b-gguf"
LLM_FILES = [
    "Qwen3-4B-Q4_K_M.gguf",
]


def main():
    MODELS.mkdir(exist_ok=True, parents=True)

    print("[1/3] Download embedding model")
    snapshot_download(
        repo_id=EMBED_REPO,
        local_dir=MODELS / "multilingual-e5-small",
        local_dir_use_symlinks=False,
    )

    print("[2/3] Download reranker model")
    snapshot_download(
        repo_id=RERANKER_REPO,
        local_dir=MODELS / "bge-reranker-v2-m3",
        local_dir_use_symlinks=False,
    )

    print("[3/3] Download LLM GGUF")
    llm_dir = MODELS / LLM_DIR_NAME
    llm_dir.mkdir(exist_ok=True, parents=True)

    for filename in LLM_FILES:
        hf_hub_download(
            repo_id=LLM_REPO,
            filename=filename,
            local_dir=llm_dir,
            local_dir_use_symlinks=False,
        )

    print("모델 설치 완료")
    print(f"LLM repo: {LLM_REPO}")
    print(f"LLM dir: {llm_dir}")
    for filename in LLM_FILES:
        print(f"- {llm_dir / filename}")


if __name__ == "__main__":
    main()