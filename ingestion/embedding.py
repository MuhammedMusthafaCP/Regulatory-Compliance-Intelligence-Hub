"""Shared embedding settings and helpers (model pinned to an exact revision)."""
import hashlib

MODEL = "BAAI/bge-small-en-v1.5"          # MIT licence, 384-dim, 512-token input
REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"  # Hugging Face commit; weights can't change under us
DIM = 384
VARIANT_A = "A"                            # embedded string == chunk text, nothing added


def _variant_t(c):
    """T: article title in front of the text (recitals unchanged)."""
    return f"{c['article_title']}\n{c['text']}" if c["type"] == "article" else c["text"]


def _variant_h(c):
    """H: chapter | article title | citation header, then the text."""
    if c["type"] != "article":
        return f"{c['citation']}\n{c['text']}"
    return f"{c['chapter_title']} | {c['article_title']} | {c['citation']}\n{c['text']}"


# What string is embedded for each variant. Display text and citations are never changed.
VARIANTS = {"A": lambda c: c["text"], "T": _variant_t, "H": _variant_h}
# bge-v1.5 recommends this prefix on *queries* (not on passages) for short-question -> passage search
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def load_model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, revision=REVISION, device="cpu")
    dim = getattr(model, "get_embedding_dimension", model.get_sentence_embedding_dimension)()
    assert dim == DIM, "unexpected embedding dimension"
    return model


def embed(model, texts, batch_size=32, progress=False):
    """L2-normalised float32 vectors, so cosine similarity == dot product."""
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        show_progress_bar=progress, convert_to_numpy=True)


def truncated(model, texts):
    """Indexes of texts longer than the model's input limit (they would be silently cut)."""
    limit = model.max_seq_length
    lens = [len(ids) for ids in model.tokenizer(texts, add_special_tokens=True)["input_ids"]]
    return [(i, n) for i, n in enumerate(lens) if n > limit], limit, max(lens)


def text_sha256(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
