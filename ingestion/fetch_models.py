"""Download the pinned models into the Hugging Face cache.

Used by the backend Docker build (so the container runs offline) and for fresh-machine setup:

    python -m ingestion.fetch_models          # embedding model + the reranker the pipeline uses
    python -m ingestion.fetch_models --all    # also the other rerankers tried in the experiments

Only safetensors weights and tokenizer/config files are fetched (no pickle .bin, ONNX or other duplicates).
"""
import argparse

from huggingface_hub import snapshot_download

from .embedding import MODEL, REVISION
from .rerank import PIPELINE_RERANKER, RERANKERS

SKIP = ["*.bin", "*.onnx", "onnx/*", "openvino/*", "*.h5", "*.msgpack", "*.ot"]


def models(include_all=False):
    keys = list(RERANKERS) if include_all else [PIPELINE_RERANKER]
    return [(MODEL, REVISION)] + [RERANKERS[k] for k in keys]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also fetch the experiment rerankers")
    args = ap.parse_args(argv)
    for repo, revision in models(args.all):
        path = snapshot_download(repo_id=repo, revision=revision, ignore_patterns=SKIP)
        print(f"{repo}@{revision[:8]} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
