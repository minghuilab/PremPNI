#!/usr/bin/env python3
"""CPU-first standalone PremPNI with the website input and reporting contract."""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from web_contract import display, effect, read_collection, read_mutations, unique_requests, validate_request, write_csv

VERSION = "0.2.1"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="PremPNI " + VERSION)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input-json", type=Path, help="Website single request, JSON array, or {samples: [...]} collection")
    source.add_argument("--input-tsv", type=Path, help="Website five-column multi-complex TSV")
    parser.add_argument("--complex-type", choices=("dna", "rna"))
    parser.add_argument("--sample-id")
    parser.add_argument("--protein-sequence")
    parser.add_argument("--chain", action="append", help="Repeat CHAIN_ID=SEQUENCE, each chain 5-prime to 3-prime")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--mutation", help="One substitution, e.g. A39T")
    modes.add_argument("--mutations", help="Independent substitutions separated by |, e.g. A39T|A39V")
    modes.add_argument("--mutation-file", type=Path, help="Website mutation list TXT/CSV/TSV")
    modes.add_argument("--alanine-scan", action="store_true", help="One XnA output row per protein position")
    parser.add_argument("--output-root", type=Path, default=Path(os.environ.get("PREMPNI_OUTPUT_ROOT", "/output")))
    parser.add_argument("--overwrite", action="store_true")
    for name in ("protein", "na", "mlp"):
        parser.add_argument("--" + name + "-device", default=os.environ.get("PREMPNI_" + name.upper() + "_DEVICE", "cpu"))
    parser.add_argument("--timeout", type=int, default=14400, help="Maximum seconds per computed mutation")
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    if args.input_json or args.input_tsv:
        if any([args.complex_type, args.sample_id, args.protein_sequence, args.chain, args.mutation, args.mutations, args.mutation_file, args.alanine_scan]):
            parser.error("File input cannot be mixed with individual input fields")
    return args


def load_requests(args):
    if args.input_tsv:
        return read_collection(args.input_tsv), True
    if args.input_json:
        data = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
        collection = isinstance(data, list) or isinstance(data, dict) and "samples" in data
        entries = data if isinstance(data, list) else data.get("samples", []) if collection else [data]
        if not isinstance(entries, list):
            raise ValueError("samples must be an array")
        return unique_requests([validate_request(item) for item in entries]), collection
    raw = {"sample_id": args.sample_id, "complex_type": args.complex_type, "protein_sequence": args.protein_sequence, "chains": []}
    for chain in args.chain or []:
        if "=" not in chain:
            raise ValueError("Use --chain CHAIN_ID=SEQUENCE")
        cid, sequence = chain.split("=", 1)
        raw["chains"].append({"chain_id": cid, "sequence": sequence})
    if args.alanine_scan:
        raw["submission_mode"] = "alanine_scan"
    elif args.mutations is not None or args.mutation_file:
        raw.update(submission_mode="mutation_list", mutations=read_mutations(args.mutation_file) if args.mutation_file else args.mutations.split("|"))
    else:
        raw["mutation"] = args.mutation
    return [validate_request(raw)], False


def atomic_json(path, value):
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def compute(request, mutation, args, scratch):
    """Isolate large model lifetimes; never reuse features from another input."""
    with tempfile.TemporaryDirectory(prefix="mutation-", dir=scratch) as directory:
        command = [sys.executable, str(Path(__file__).with_name("run_prempni_single.py")),
                   "--complex-type", request["complex_type"], "--sample-id", request["sample_id"],
                   "--protein-sequence", request["protein_sequence"], "--mutation", mutation, "--output-root", directory]
        for chain in request["chains"]:
            command.extend(["--chain", chain["chain_id"] + "=" + chain["sequence"]])
        for stage in ("protein", "na", "mlp"):
            command.extend(["--" + stage + "-device", getattr(args, stage + "_device")])
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=args.timeout)
        if process.returncode:
            raise RuntimeError(process.stdout[-4000:] or f"Inference exited {process.returncode}")
        path = Path(directory) / request["sample_id"] / "prediction/prempni_prediction.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        if not math.isfinite(result["mean_ddg"]):
            raise ValueError("Inference returned a nonfinite prediction")
        return result


def run(args, requests, collection, infer=compute):
    submitted = datetime.now(timezone.utc)
    job_id = "PNI-" + submitted.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:16]
    target = args.output_root / ("collections/" + job_id if collection else "protein_" + requests[0]["complex_type"] + "/" + requests[0]["sample_id"] + "/prediction")
    target.mkdir(parents=True, exist_ok=True)
    result_path = target / "prempni_prediction.json"
    status_path = target / "job.json"
    if not args.overwrite and any((target / name).exists() for name in ("job.json", "prempni_prediction.json", "prempni_prediction.csv")):
        raise FileExistsError("Result already exists; use a new sample ID or --overwrite")
    # Exclusive lock prevents concurrent writes, including with --overwrite.
    lock = target / ".running"
    with lock.open("x"):
        pass
    payload = {"version": VERSION, "job_id": job_id, "status": "running", "submitted_at": submitted.isoformat(), "started_at": datetime.now(timezone.utc).isoformat(),
               "classification_rule": "mean_ddg < 0: Stabilizing; mean_ddg >= 0: Destabilizing (before rounding)", "results": []}
    start = time.perf_counter()
    try:
        atomic_json(status_path, payload)
        with tempfile.TemporaryDirectory(prefix=".work-", dir=target) as scratch:
            for request in requests:
                item = {"sample_id": request["sample_id"], "complex_type": request["complex_type"],
                        "predictor": "PremPDI2" if request["complex_type"] == "dna" else "PremPRI2", "input": request,
                        "predictions": [], "timing_seconds": {"protein_embedding": 0.0, "nucleic_acid_embedding": 0.0, "mlp_prediction": 0.0, "total": 0.0}}
                item["input_lengths"] = {"protein_length": len(request["protein_sequence"]), "nucleic_acid_type": request["complex_type"].upper(),
                                         "nucleic_acid_chain_count": len(request["chains"]), "nucleic_acid_chain_lengths": {c["chain_id"]: len(c["sequence"]) for c in request["chains"]},
                                         "nucleic_acid_total_length": sum(len(c["sequence"]) for c in request["chains"])}
                payload["results"].append(item)
                item_start = time.perf_counter()
                for mutation in request["mutations"]:
                    noop = mutation[0] == mutation[-1] == "A"
                    row = {"mutation": mutation, "computed": False, "status": "completed"}
                    try:
                        result = {"mean_ddg": 0.0} if noop else infer(request, mutation, args, scratch)
                        value = result["mean_ddg"]
                        row.update(mean_ddg=value, prediction_display=display(value), classification=effect(value), predicted_effect=effect(value), computed=not noop)
                        for key in ("protein_embedding", "nucleic_acid_embedding", "mlp_prediction"):
                            item["timing_seconds"][key] += result.get("timing_seconds", {}).get(key, 0.0)
                    except (RuntimeError, ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
                        row.update(status="failed", mean_ddg=None, classification="", predicted_effect="", prediction_display="", error=str(error))
                    item["predictions"].append(row)
                    item["timing_seconds"]["total"] = time.perf_counter() - item_start
                    atomic_json(status_path, payload)
                    print(f"{request['sample_id']} {mutation} {item['predictor']}: {row['prediction_display']} {row['classification']} [{row['status']}]", flush=True)
                item["status"] = "failed" if any(r["status"] == "failed" for r in item["predictions"]) else "completed"
                item["mutation_count"] = len(item["predictions"])
                item["computed_mutation_count"] = sum(r["computed"] for r in item["predictions"])
        failed = any(item["status"] == "failed" for item in payload["results"])
        payload.update(status="failed" if failed else "completed", completed_at=datetime.now(timezone.utc).isoformat(), processing_time_seconds=time.perf_counter() - start)
        if not collection:
            item = payload["results"][0]
            payload.update({key: item[key] for key in ("sample_id", "complex_type", "predictor", "predictions", "timing_seconds", "input_lengths", "mutation_count", "computed_mutation_count")})
            payload["submission_mode"] = item["input"]["submission_mode"]
            if len(item["predictions"]) == 1:
                payload.update({key: item["predictions"][0][key] for key in ("mean_ddg", "classification", "predicted_effect", "prediction_display", "computed")})
        atomic_json(result_path, payload)
        write_csv(target / "prempni_prediction.csv", payload, collection)
        atomic_json(status_path, payload)
        print("JSON: " + str(result_path), flush=True)
        return 1 if failed else 0
    except BaseException as error:
        payload.update(status="failed", error=str(error), completed_at=datetime.now(timezone.utc).isoformat())
        atomic_json(status_path, payload)
        raise
    finally:
        lock.unlink()


def main():
    try:
        args = parse_args()
        requests, collection = load_requests(args)
        return run(args, requests, collection)
    except (ValueError, OSError, TypeError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
