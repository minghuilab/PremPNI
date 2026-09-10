"""Dependency-free input and export contract matching the PremPNI website."""
import csv
import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

AA = "ACDEFGHIKLMNPQRSTVWY"
MUTATION = re.compile(r"^([" + AA + r"])(\d+)([" + AA + r"])$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
TSV_HEADER = ["sample_id", "complex_type", "protein_sequence", "nucleic_acid_sequences", "mutations"]
CSV_HEADER = ["job_id", "interaction_type", "protein_sequence", "nucleic_acid_sequences", "mutation", "predictor", "prediction_kcal_per_mol", "predicted_effect", "submitted_at_utc_plus_8", "processing_time_seconds", "computed"]
COLLECTION_HEADER = ["sample_id", "complex_type", "protein_sequence", "nucleic_acid_sequences", "mutation", "status", "ddg_kcal_mol", "predicted_effect", "error"]


def normalize(value):
    if not isinstance(value, str):
        raise ValueError("Expected a sequence or mutation string")
    return re.sub(r"\s+", "", value).upper()


def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100 or not IDENTIFIER.fullmatch(value.strip()):
        raise ValueError("Identifiers must be 1–100 letters, digits, dots, underscores or hyphens, starting with a letter or digit")
    return value.strip()


def validate_request(raw):
    if not isinstance(raw, dict):
        raise ValueError("Each input must be a JSON object")
    sample = identifier(raw.get("sample_id"))
    kind = str(raw.get("complex_type", "")).lower()
    if kind not in ("dna", "rna"):
        raise ValueError("complex_type must be dna or rna")
    protein = normalize(raw.get("protein_sequence"))
    if not protein or len(protein) > 5000 or not set(protein) <= set(AA):
        raise ValueError("Protein must contain 1–5000 standard amino acids")
    chains = raw.get("chains")
    if not isinstance(chains, list) or not 1 <= len(chains) <= 32:
        raise ValueError("Provide 1–32 nucleic-acid chains")
    normalized, ids = [], set()
    for chain in chains:
        if not isinstance(chain, dict):
            raise ValueError("Each chain must have chain_id and sequence")
        cid, sequence = identifier(chain.get("chain_id")), normalize(chain.get("sequence"))
        if cid in ids:
            raise ValueError("Duplicate chain_id: " + cid)
        if not sequence or not set(sequence) <= set("ACGT" if kind == "dna" else "ACGU"):
            raise ValueError("Invalid " + kind.upper() + " chain: " + cid)
        ids.add(cid)
        normalized.append({"chain_id": cid, "sequence": sequence})
    if sum(len(c["sequence"]) for c in normalized) > 10000:
        raise ValueError("Total nucleic-acid length must not exceed 10000")
    mode = raw.get("submission_mode", "single")
    if mode == "single":
        if raw.get("mutations"):
            raise ValueError("Use mutation_list for multiple mutations")
        mutations = [raw.get("mutation")]
    elif mode == "mutation_list":
        mutations = raw.get("mutations")
        if raw.get("mutation") or not isinstance(mutations, list) or not mutations:
            raise ValueError("mutation_list requires a nonempty mutations array and no mutation field")
    elif mode == "alanine_scan":
        if raw.get("mutation") or raw.get("mutations"):
            raise ValueError("alanine_scan generates its own mutations")
        mutations = [f"{residue}{i}A" for i, residue in enumerate(protein, 1)]
    else:
        raise ValueError("Unsupported submission_mode")
    checked = []
    for value in mutations:
        match = MUTATION.fullmatch(normalize(value))
        if not match:
            raise ValueError("Mutation must use one-based notation such as A39T")
        wt, position, mut = match.groups()
        position = int(position)
        if not 1 <= position <= len(protein) or protein[position - 1] != wt:
            raise ValueError("Mutation position or wild-type residue does not match protein_sequence")
        if wt == mut and wt != "A":
            raise ValueError("Only Ala-to-Ala is allowed as a no-change output row")
        label = f"{wt}{position}{mut}"
        if label in checked:
            raise ValueError("Duplicate mutation: " + label)
        checked.append(label)
    return {"sample_id": sample, "complex_type": kind, "protein_sequence": protein, "chains": normalized,
            "submission_mode": mode, "mutations": checked}


def read_collection(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        if next(reader, None) != TSV_HEADER:
            raise ValueError("Use the exact five-column website TSV header")
        requests = []
        for line, cells in enumerate(reader, 2):
            if not cells or not any(c.strip() for c in cells):
                continue
            if len(cells) != 5:
                raise ValueError(f"Line {line}: expected five tab-separated columns")
            sample, kind, protein, chains, mutations = [c.strip() for c in cells]
            labels = mutations.split("|")
            raw = {"sample_id": sample, "complex_type": kind, "protein_sequence": protein,
                   "chains": [{"chain_id": f"{kind.upper()}_{i}", "sequence": seq} for i, seq in enumerate(chains.split("|"), 1)],
                   "submission_mode": "mutation_list", "mutations": labels}
            request = validate_request(raw)
            if len(labels) == 1:
                request["submission_mode"] = "single"
            requests.append(request)
    return unique_requests(requests)


def unique_requests(requests):
    if not requests:
        raise ValueError("At least one complex is required")
    ids = [r["sample_id"] for r in requests]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate sample_id in collection")
    return requests


def read_mutations(path):
    """Website TXT/CSV/TSV mutation-list forms, preserving order."""
    values = []
    for line, raw in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        cells = [c.strip("\"'") for c in re.split(r"[\s,;]+", raw.upper()) if c]
        complete = [c for c in cells if MUTATION.fullmatch(c)]
        if complete:
            values.extend(complete)
            continue
        for i in range(len(cells) - 2):
            if cells[i] in AA and len(cells[i]) == 1 and cells[i+1].isdigit() and len(cells[i+2]) == 1 and cells[i+2] in AA:
                values.append("".join(cells[i:i+3]))
                break
        else:
            for i in range(len(cells) - 1):
                if re.fullmatch(r"[" + AA + r"]\d+", cells[i]) and len(cells[i+1]) == 1 and cells[i+1] in AA:
                    values.append(cells[i] + cells[i+1])
                    break
            else:
                if any(c in ("MUTATION", "PROTEIN_MUTATION", "RESIDUE", "MUTANT", "MUTANT_RESIDUE") for c in cells):
                    continue
                raise ValueError(f"Invalid mutation file line {line}")
    return values


def effect(value):
    if value is None:
        return ""
    if not math.isfinite(value):
        raise ValueError("Prediction must be finite")
    return "Stabilizing" if value < 0 else "Destabilizing"


def display(value):
    # JS Number.toFixed rounds exact halfway cases away from zero; Python
    # format() uses ties-to-even. Preserve JS negative-zero display semantics.
    if value is None:
        return ""
    rounded = Decimal.from_float(abs(float(value))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return ("-" if value < 0 else "") + format(rounded, ".3f")


def write_csv(path, payload, collection=False):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(COLLECTION_HEADER if collection else CSV_HEADER)
        for item in payload["results"]:
            request = item["input"]
            for row in item["predictions"]:
                ddg = row.get("mean_ddg")
                if collection:
                    writer.writerow([request["sample_id"], request["complex_type"], request["protein_sequence"],
                                     "|".join(c["sequence"] for c in request["chains"]), row["mutation"], row["status"], display(ddg), effect(ddg), row.get("error", "")])
                else:
                    submitted = datetime.fromisoformat(payload["submitted_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([payload["job_id"], "Protein-" + request["complex_type"].upper(), request["protein_sequence"],
                                     ";".join(c["chain_id"] + ":" + c["sequence"] for c in request["chains"]), row["mutation"], item["predictor"], display(ddg), effect(ddg), submitted,
                                     display(item["timing_seconds"]["total"]), str(row["computed"]).lower()])
