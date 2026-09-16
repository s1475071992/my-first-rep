from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


def collect_texts(data: dict) -> tuple[list[str], list[str]]:
    """Collect each review key exactly once across current and history reviews."""
    lookup: dict[str, str] = {}
    for split in ("train", "val", "test"):
        for item in data[split]:
            key = f"{item['user_id']}_{item['business_id']}"
            text = item["review_text"]
            if key in lookup and lookup[key] != text:
                raise ValueError(f"conflicting text for {key}")
            lookup[key] = text
            for hist_key, hist_text in item.get("history_reviews", []):
                if hist_key in lookup and lookup[hist_key] != hist_text:
                    raise ValueError(f"conflicting history text for {hist_key}")
                lookup[hist_key] = hist_text
    keys = list(lookup.keys())
    texts = [lookup[k] for k in keys]
    return keys, texts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="sentence-transformers/all-mpnet-base-v2")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    keys, texts = collect_texts(data)
    print(f"unique review texts: {len(keys):,}", flush=True)

    model = SentenceTransformer(args.model, device="cpu")
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = embeddings.astype(np.float16)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        keys=np.asarray(keys),
        embeddings=embeddings,
        model=np.asarray([args.model]),
    )
    print(f"saved {out} shape={embeddings.shape} dtype={embeddings.dtype}", flush=True)

    # Small manifest for validation without loading the full matrix.
    manifest = {
        "model": args.model,
        "num_embeddings": int(embeddings.shape[0]),
        "embedding_dim": int(embeddings.shape[1]),
        "dtype": str(embeddings.dtype),
        "train_rows": len(data["train"]),
        "val_rows": len(data["val"]),
        "test_rows": len(data["test"]),
    }
    with open(out.with_suffix(".manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
