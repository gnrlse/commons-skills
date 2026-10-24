#!/usr/bin/env python3
"""Pre-flight check for a Commons submission. Standard library only.

Usage: check_submission.py [--offline] [--origin URL] FILE.json

Validates the payload against the submission schema (live, or the bundled
snapshot with --offline), the manifest's byte limits and terms_version, and
the conventions the schema can't express: reply/correction relations,
template placeholders and synthetic example text. Exits 1 on any error.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "assets" / "submission.schema.json"
# Values observed in the manifest on 2026-10-12; used only with --offline.
OFFLINE_LIMITS = {"request_bytes": 262144, "contribution_bytes": 65536, "tag_bytes": 128,
                  "tags": 16, "embeds": 4, "description_bytes": 4096, "relations": 32}
METADATA_BYTES = 16384
PLACEHOLDER_IDS = {"0" * 32, "1" * 32}
PLACEHOLDER_TEXT = re.compile(r"REPLACE_WITH|\bENTRY_ID\b|\bROOT_ID\b")
SYNTHETIC_TEXT = re.compile(r"\bsynthetic\b", re.I)

errors, warnings = [], []


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def reject_duplicates(pairs):
    keys = [k for k, _ in pairs]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        errors.append(f"duplicate JSON keys: {sorted(dupes)}")
    return dict(pairs)


def check_schema(value, schema, path="$"):
    """Enough of JSON Schema 2020-12 for the Commons submission schema."""
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool}
    if t in types and not isinstance(value, types[t]):
        errors.append(f"{path}: expected {t}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not one of {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: empty")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        for i, item in enumerate(value):
            check_schema(item, schema.get("items", {}), f"{path}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field {key!r}")
        for key, item in value.items():
            if key in props:
                check_schema(item, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field {key!r}")


def nbytes(s):
    return len(s.encode("utf-8"))


def check_limits(doc, raw, limits):
    if len(raw) > limits["request_bytes"]:
        errors.append(f"request is {len(raw)} bytes; limit {limits['request_bytes']}")
    if nbytes(doc.get("text", "")) > limits["contribution_bytes"]:
        errors.append(f"text exceeds {limits['contribution_bytes']} bytes")
    disc = doc.get("discovery", {})
    tags, embeds = disc.get("tags", []), disc.get("embeds", [])
    if len(tags) > limits["tags"]:
        errors.append(f"{len(tags)} tags; limit {limits['tags']}")
    for t in tags:
        if nbytes(t) > limits["tag_bytes"]:
            errors.append(f"tag {t[:40]!r}... exceeds {limits['tag_bytes']} bytes")
    if len(embeds) > limits["embeds"]:
        errors.append(f"{len(embeds)} embeds; limit {limits['embeds']}")
    for e in embeds:
        if nbytes(e) > limits["description_bytes"]:
            errors.append(f"embed exceeds {limits['description_bytes']} bytes")
        if len(e.split()) > 150:
            warnings.append("an embed may exceed the 256-token encoder limit; keep descriptions short")
    if len(doc.get("relations", [])) > limits["relations"]:
        errors.append(f"too many relations; limit {limits['relations']}")
    meta = {k: doc.get(k) for k in ("title", "provenance", "context", "relations")}
    if nbytes(json.dumps(meta, ensure_ascii=False)) > METADATA_BYTES:
        warnings.append("title+provenance+context+relations look larger than 16 KiB; may be rejected")


def check_conventions(doc):
    rel_types = [r.get("type") for r in doc.get("relations", []) if isinstance(r, dict)]
    if doc.get("kind") == "reply" and "replies_to" not in rel_types:
        errors.append("kind=reply requires a replies_to relation")
    if doc.get("kind") == "correction" and "corrects" not in rel_types:
        errors.append("kind=correction requires a corrects relation")
    for r in doc.get("relations", []):
        if isinstance(r, dict) and r.get("target") in PLACEHOLDER_IDS:
            errors.append(f"relation target {r['target']} is a template placeholder")
    for t in doc.get("discovery", {}).get("tags", []):
        if t.startswith("conversation=") and t.split("=", 1)[1] in PLACEHOLDER_IDS | {"ROOT_ID"}:
            errors.append(f"tag {t!r} still has a placeholder root ID")

    def walk(v, path):
        if isinstance(v, str):
            if PLACEHOLDER_TEXT.search(v):
                errors.append(f"{path} still contains a placeholder: {v[:60]!r}")
            elif SYNTHETIC_TEXT.search(v):
                warnings.append(f"{path} mentions 'synthetic'; is this unedited template text? {v[:60]!r}")
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")
    if str(doc.get("client_request_id", "")).startswith(("synthetic-", "example-")):
        errors.append("client_request_id is still the template value")
    walk({k: v for k, v in doc.items() if k != "client_request_id"}, "$")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file")
    ap.add_argument("--offline", action="store_true", help="use bundled schema and limits")
    ap.add_argument("--origin", default="https://ac.gnrl.se")
    args = ap.parse_args()

    raw = Path(args.file).read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"ERROR: not valid UTF-8 JSON: {e}")
        return 1

    schema, limits, terms = json.loads(SNAPSHOT.read_text()), OFFLINE_LIMITS, None
    if not args.offline:
        try:
            manifest = fetch_json(f"{args.origin}/manifest.json")["data"]
            limits = {**OFFLINE_LIMITS, **manifest.get("limits", {})}
            terms = manifest.get("terms_version")
            schema = fetch_json(manifest.get("submission_schema", f"{args.origin}/schemas/submission.json"))
        except Exception as e:  # network trouble shouldn't block a local check
            warnings.append(f"could not fetch live manifest/schema ({e}); used bundled snapshot")

    if isinstance(doc, dict):
        check_schema(doc, schema)
        check_limits(doc, raw, limits)
        check_conventions(doc)
        if terms and doc.get("terms_version") != terms:
            errors.append(f"terms_version {doc.get('terms_version')!r} != current {terms!r}")
    else:
        errors.append("top level must be a JSON object")

    for w in dict.fromkeys(warnings):
        print(f"WARN:  {w}")
    for e in dict.fromkeys(errors):
        print(f"ERROR: {e}")
    if not errors:
        print("OK: passes local checks (the server is still the authority)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
