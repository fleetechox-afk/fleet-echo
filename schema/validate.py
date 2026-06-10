#!/usr/bin/env python3
"""
validate.py - check an event log against the core reliability schema.

Zero dependencies (Python 3 standard library only).

    python validate.py your_log.csv          # CSV
    python validate.py events.json            # JSON array OR JSON-lines
    python validate.py events.jsonl --json    # machine-readable output

Format is auto-detected from extension, then content. CSV and JSON share the
SAME validation rules (the schema says CSV/JSON field names are identical, so
the checker treats them identically too).

Core-layer rules checked:
  1. all 7 core fields present
  2. result is exactly OK or FAIL
  3. OK -> error_code == NONE; FAIL -> error_code != NONE
  4. timestamp and duration_ms are non-negative integers
  5. machine_id / firmware_version / event_type / error_code are non-empty
  6. event_type / error_code case-drift warning (same name, different casing)
  7. per-unit and per-firmware counts for a traceability eyeball

Device-specific (Layer 2) fields are allowed and ignored.
Exit code: 0 = conforms, 1 = errors found, 2 = usage / unreadable input.
"""

import csv
import json
import sys
from collections import defaultdict

CORE = ["timestamp", "machine_id", "firmware_version",
        "event_type", "duration_ms", "result", "error_code"]


def is_nonneg_int(v):
    # accept ints, or strings that are clean non-negative integers
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return v >= 0
    try:
        return int(str(v).strip()) >= 0
    except (ValueError, TypeError):
        return False


def s(v):
    """normalize a field to a stripped string for presence/enum checks"""
    if v is None:
        return ""
    return str(v).strip()


def check_record(rec, rid, state, errors, warnings):
    """Validate one event dict. Mutates state/errors/warnings. Shared by CSV+JSON."""
    missing = [c for c in CORE if c not in rec]
    if missing:
        errors.append(f"{rid}: missing core fields: {', '.join(missing)}")
        return  # can't sanely check the rest of this record

    if not is_nonneg_int(rec["timestamp"]):
        errors.append(f"{rid}: timestamp not a non-negative integer ({rec['timestamp']!r})")
    if not is_nonneg_int(rec["duration_ms"]):
        errors.append(f"{rid}: duration_ms not a non-negative integer ({rec['duration_ms']!r})")

    for col in ("machine_id", "firmware_version", "event_type", "error_code"):
        if not s(rec[col]):
            errors.append(f"{rid}: {col} is empty")

    result = s(rec["result"])
    if result not in ("OK", "FAIL"):
        errors.append(f"{rid}: result must be OK or FAIL, got {result!r}")
    else:
        ec = s(rec["error_code"])
        if result == "OK" and ec != "NONE":
            errors.append(f"{rid}: result=OK but error_code={ec!r} (should be NONE)")
        if result == "FAIL" and ec in ("NONE", ""):
            errors.append(f"{rid}: result=FAIL but error_code={ec!r} (needs a real code)")

    for field, store in (("event_type", state["events"]), ("error_code", state["errors"])):
        val = s(rec[field])
        if val:
            key = val.upper()
            if key in store and store[key] != val:
                warnings.append(f"{rid}: {field} {val!r} differs in case from {store[key]!r} — possible drift")
            else:
                store.setdefault(key, val)

    state["units"][s(rec["machine_id"])] += 1
    state["fw"][s(rec["firmware_version"])] += 1


def load_records(path):
    """Return (records, kind, id_label) or raise ValueError. Auto-detects format."""
    lower = path.lower()
    with open(path, "r", encoding="utf-8-sig") as f:
        head = f.read(2048)
        f.seek(0)
        text = f.read()

    looks_json = lower.endswith((".json", ".jsonl", ".ndjson")) or head.lstrip()[:1] in ("[", "{")

    if not looks_json:
        # CSV path
        reader = csv.DictReader(text.splitlines())
        return list(reader), "csv", "row"

    # JSON array first, else JSON-lines
    stripped = text.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, list):
            return data, "json", "item"
        if isinstance(data, dict):
            return [data], "json", "item"
        raise ValueError("top-level JSON must be an array or object of events")
    except json.JSONDecodeError:
        recs = []
        for ln, line in enumerate(stripped.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"line {ln}: not valid JSON ({e})")
        return recs, "jsonl", "line"


def main(argv):
    args = [a for a in argv if a != "--json"]
    as_json = "--json" in argv
    if len(args) != 1:
        print("usage: python validate.py <log.csv|.json|.jsonl> [--json]")
        return 2

    path = args[0]
    try:
        records, kind, label = load_records(path)
    except (OSError, ValueError) as e:
        if as_json:
            print(json.dumps({"ok": False, "error": str(e)}))
        else:
            print(f"FAIL: could not read {path}: {e}")
        return 2

    errors, warnings = [], []
    state = {"units": defaultdict(int), "fw": defaultdict(int),
             "events": {}, "errors": {}}

    start = 2 if kind == "csv" else 1  # csv row 1 is header
    for i, rec in enumerate(records, start=start):
        if not isinstance(rec, dict):
            errors.append(f"{label} {i}: not an object/record")
            continue
        check_record(rec, f"{label} {i}", state, errors, warnings)

    if as_json:
        out = {
            "ok": len(errors) == 0,
            "format": kind,
            "records": len(records),
            "units": len(state["units"]),
            "firmware_versions": len(state["fw"]),
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(out, indent=2))
        return 0 if not errors else 1

    print(f"Scanned {len(records)} {label}s ({kind}).")
    print(f"Units: {len(state['units'])}  |  Firmware versions: {len(state['fw'])}")
    if len(state["fw"]) > 1:
        print("  (multiple firmware versions present — good, you can isolate version-specific bugs)")
    for w in warnings:
        print("WARN: " + w)
    for e in errors:
        print("FAIL: " + e)
    if errors:
        print(f"\n{len(errors)} error(s). Log does NOT conform to the core schema.")
        return 1
    print("\nOK — conforms to the core schema" +
          (f" ({len(warnings)} warning(s))" if warnings else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
