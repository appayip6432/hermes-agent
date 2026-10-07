"""Content-addressed alignment snapshots and explicit review receipts.

Hashes detect corruption, not malicious writes by the local account. No pointer
is advanced automatically: configuration selects an exact approved version.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from agent.alignment_synthesis import MAX_INPUT_BYTES, synthesize


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Invalid alignment version")
    return value


def read_json(path, *, limit=MAX_INPUT_BYTES):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Alignment file exceeds budget")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_keys)
    except (RecursionError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid alignment JSON encoding or nesting") from exc
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 12:
            raise ValueError("Invalid alignment JSON nesting")
        children = item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return value


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate alignment JSON key")
        result[key] = value
    return result


def _publish(path, value):
    """Publish a complete file exclusively; never expose a partially written version."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".alignment-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            if read_json(path, limit=MAX_INPUT_BYTES + 8000) != value:
                raise ValueError("Existing alignment artifact differs") from None
    finally:
        Path(name).unlink()


def _extend(previous, delta):
    synthesize(delta)
    result = {"schema": 1}
    for key, identity in (("sources", "ref"), ("reflections", "id")):
        rows = {row[identity]: row for row in previous[key]}
        for row in delta[key]:
            old = rows.get(row[identity])
            if old is not None and old != row:
                raise ValueError("Original evidence and reflection ids are immutable; append a correction")
            rows[row[identity]] = row
        result[key] = list(rows.values())
    return result


def save_snapshot(store, bundle, *, parent=None):
    """Generate a shadow snapshot; a parent preserves all earlier evidence and corrections."""
    if parent is not None:
        previous = load_snapshot(store, parent)
        bundle = _extend(previous["evidence"], bundle)
    result = dict(synthesize(bundle), parent=parent)
    result["version"] = hashlib.sha256(_canonical(result)).hexdigest()
    _publish(Path(store) / "versions" / f"{result['version']}.json", result)
    return result


def load_snapshot(store, version):
    version = _version(version)
    result = read_json(Path(store) / "versions" / f"{version}.json", limit=MAX_INPUT_BYTES + 8000)
    if not isinstance(result, dict) or result.get("version") != version:
        raise ValueError("Alignment version mismatch")
    payload = {key: value for key, value in result.items() if key != "version"}
    if hashlib.sha256(_canonical(payload)).hexdigest() != version:
        raise ValueError("Alignment digest mismatch")
    if result.get("parent") is not None:
        _version(result["parent"])
    expected = dict(synthesize(result.get("evidence")), parent=result.get("parent"), version=version)
    if result != expected:
        raise ValueError("Alignment snapshot does not match validated evidence")
    return result


def approve(store, version):
    """Record review of this exact candidate, without modifying config or any prompt."""
    load_snapshot(store, version)
    _publish(Path(store) / "approved" / f"{version}.json", {"schema": 1, "version": version})


def is_approved(store, version):
    version = _version(version)
    try:
        receipt = read_json(Path(store) / "approved" / f"{version}.json", limit=256)
    except FileNotFoundError:
        return False
    return receipt == {"schema": 1, "version": version}


def diff_versions(store, old, new):
    """Include evidence and reflection changes, even when the compact prompt is unchanged."""
    before, after = (load_snapshot(store, version) for version in (old, new))
    return "\n".join(difflib.unified_diff(
        json.dumps(before, indent=2, sort_keys=True).splitlines(),
        json.dumps(after, indent=2, sort_keys=True).splitlines(),
        fromfile=old, tofile=new, lineterm="",
    ))
