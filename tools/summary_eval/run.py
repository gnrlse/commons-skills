#!/usr/bin/env python3
"""Measure how well task summaries from different agents match under Commons' encoder.

Commons scores semantic search with all-MiniLM-L6-v2 (mean pooling, L2 norm,
no truncation, threshold 0.45). Local scores matched live ones to 6 decimal
places on 2026-10-24. Data in data/ came from Haiku, Sonnet and Opus
summarizing the requests in data/tasks.md, with and without the SKILL.md
style guide.

Setup (outside the repo):
    python3 -m venv VENV && VENV/bin/pip install onnxruntime tokenizers numpy huggingface_hub
Run:
    VENV/bin/python tools/summary_eval/run.py [--cache DIR]

Reports two things for each recipe:
  same-request  three models summarize the same request: do they match each other?
  cross-project a differently worded request of the same task type: does it retrieve them?
"""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

DATA = Path(__file__).resolve().parent / "data"
MODELS = ("haiku", "sonnet", "opus")
NEAR = {(1, 2), (3, 4), (5, 6)}
TH = 0.45


class Encoder:
    def __init__(self, cache):
        repo = "sentence-transformers/all-MiniLM-L6-v2"
        self.tok = Tokenizer.from_file(hf_hub_download(repo, "tokenizer.json", cache_dir=cache))
        self.tok.no_truncation()
        self.sess = ort.InferenceSession(hf_hub_download(repo, "onnx/model.onnx", cache_dir=cache))

    def __call__(self, text):
        e = self.tok.encode(text)
        ids, mask = np.array([e.ids]), np.array([e.attention_mask])
        out = self.sess.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)})[0]
        v = ((out * mask[..., None]).sum(1) / mask.sum())[0]
        return v / np.linalg.norm(v)


def load(name, enc):
    return {int(k[1:]): enc(v) for k, v in json.loads((DATA / f"{name}.json").read_text()).items()}


def same_request(recipe, enc):
    vec = {m: load(f"{recipe}-{m}", enc) for m in MODELS}
    same, near, other, top1 = [], [], [], 0
    for a, b in itertools.permutations(MODELS, 2):
        for i in range(1, 11):
            sims = {j: float(vec[a][i] @ vec[b][j]) for j in range(1, 11)}
            same.append(sims[i])
            top1 += max(sims, key=sims.get) == i
            for j in sims:
                if j != i:
                    (near if tuple(sorted((i, j))) in NEAR else other).append(sims[j])
    same, near, other = map(np.array, (same, near, other))
    print(f"same-request  {recipe:6}  same-task mean {same.mean():.3f} min {same.min():.3f}  top1 {top1 / len(same):.0%}"
          f"  near-miss>=TH {np.mean(near >= TH):.0%}  other>=TH {np.mean(other >= TH):.0%}")


def cross_project(query, corpus, enc):
    q = load(f"variant-{query}-sonnet", enc)
    docs = [(j, v) for m in MODELS for j, v in load(f"{corpus}-{m}", enc).items()]
    best, top1, wrong = [], 0, []
    for i, qv in q.items():
        scored = sorted(((float(qv @ v), j) for j, v in docs), reverse=True)
        best.append(max(s for s, j in scored if j == i))
        top1 += scored[0][1] == i
        wrong += [s for s, j in scored if j != i]
    print(f"cross-project {query:6} vs {corpus:6}  best same-task mean {np.mean(best):.3f} min {min(best):.3f}"
          f"  top1 {top1}/10  max wrong-task {max(wrong):.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", help="Hugging Face cache directory")
    enc = Encoder(ap.parse_args().cache)
    for recipe in ("free", "recipe"):
        same_request(recipe, enc)
    for query, corpus in itertools.product(("free", "recipe"), repeat=2):
        cross_project(query, corpus, enc)


if __name__ == "__main__":
    main()
