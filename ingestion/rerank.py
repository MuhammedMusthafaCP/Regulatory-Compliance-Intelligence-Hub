"""Cross-encoder rerankers (free Hugging Face models, pinned to exact revisions)."""

# key -> (repo id, revision). All have permissive licences, safetensors weights and no custom code.
RERANKERS = {
    "bge-base": ("BAAI/bge-reranker-base", "2cfc18c9415c912f9d8155881c133215df768a70"),           # MIT, 278M
    "bge-m3": ("BAAI/bge-reranker-v2-m3", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"),           # Apache-2.0, 568M
    "mxbai-base": ("mixedbread-ai/mxbai-rerank-base-v1", "800f24c113213a187e65bde9db00c15a2bb12738"),  # Apache-2.0, 184M
}


PIPELINE_RERANKER = "mxbai-base"   # the reranker the chosen pipeline uses (ADR 0002)


def device():
    """Apple GPU (MPS) when available: ~10x faster than CPU here with the same scores (max diff 5e-4).
    Override with RERANK_DEVICE=cpu. Embeddings stay on CPU so they match the stored vectors exactly."""
    import os
    import torch
    return os.environ.get("RERANK_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")


def load_reranker(key):
    from sentence_transformers import CrossEncoder
    repo, rev = RERANKERS[key]
    return CrossEncoder(repo, revision=rev, device=device(), max_length=512)
