import csv
import json
import tempfile
import unittest
from pathlib import Path

from run_prempni import load_requests, parse_args, run
from web_contract import CSV_HEADER, COLLECTION_HEADER, display, effect, read_collection, read_mutations, validate_request


def request(**changes):
    data = dict(sample_id="example", complex_type="dna", protein_sequence="MAK", chains=[dict(chain_id="DNA_1", sequence="ACGT")], mutation="M1V")
    data.update(changes)
    return data


class WebContractTests(unittest.TestCase):
    def test_rounding_matches_js_halfway_and_sign(self):
        self.assertEqual(display(0.0625), "0.063")
        self.assertEqual(display(-0.0625), "-0.063")
        self.assertEqual(display(-0.00001), "-0.000")
        self.assertEqual(display(-0.0), "0.000")
        self.assertEqual(effect(-0.00001), "Stabilizing")
        self.assertEqual(effect(0.0), "Destabilizing")
        self.assertEqual(effect(None), "")

    def test_invalid_requests(self):
        for changes in [dict(mutation="K1A"), dict(mutation="M0V"), dict(mutation="M4V"), dict(mutation="M1M"),
                        dict(protein_sequence="MXK"), dict(chains=[dict(chain_id="DNA_1", sequence="ACGU")]),
                        dict(chains=[dict(chain_id="DNA_1", sequence="")]), dict(sample_id="../escape"),
                        dict(mutation=None, submission_mode="mutation_list", mutations=["M1V", "M01V"])]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_request(request(**changes))

    def test_normalization_and_all_alanine(self):
        result = validate_request(request(protein_sequence=" a a\n", mutation=None, submission_mode="alanine_scan"))
        self.assertEqual(result["mutations"], ["A1A", "A2A"])
        result = validate_request(request(protein_sequence=" m a k ", mutation=" m01v "))
        self.assertEqual(result["mutations"], ["M1V"])

    def test_real_website_examples(self):
        # Tests run from repository root or /opt/prempni in the image.
        directory = Path("examples")
        result = read_collection(directory / "PremPNI_complexes_example.tsv")
        self.assertEqual([r["sample_id"] for r in result], ["2KO0", "1AUD"])
        for kind in ("dna", "rna"):
            args = parse_args(["--input-json", str(directory / f"prempni_{kind}_example.json")])
            requests, collection = load_requests(args)
            self.assertFalse(collection)
            self.assertEqual(len(requests), 1)
            self.assertEqual(args.protein_device, "cpu")

    def test_mutation_file_and_bad_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "input.txt"
            p.write_text("# comment\nMutation\nM\t1\tV\nK3 A\nA2A\n", encoding="utf-8")
            self.assertEqual(read_mutations(p), ["M1V", "K3A", "A2A"])
            p.write_text("nonsense", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_mutations(p)
            p.write_text("sample_id\tcomplex_type\tprotein_sequence\tnucleic_acid_sequences\tmutations\nx\tdna\tMA\tACGT\tM1V|\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_collection(p)

    def test_scan_order_zero_rows_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            args = parse_args(["--output-root", directory])
            calls = []
            def infer(req, mutation, args, scratch):
                calls.append(mutation)
                return {"mean_ddg": -0.00001, "timing_seconds": {"protein_embedding": 1}}
            req = validate_request(request(mutation=None, submission_mode="alanine_scan"))
            self.assertEqual(run(args, [req], False, infer), 0)
            self.assertEqual(calls, ["M1A", "K3A"])
            root = Path(directory) / "protein_dna/example/prediction"
            payload = json.loads((root / "prempni_prediction.json").read_text())
            self.assertEqual([r["mutation"] for r in payload["predictions"]], ["M1A", "A2A", "K3A"])
            self.assertFalse(payload["predictions"][1]["computed"])
            self.assertEqual(payload["predictions"][1]["mean_ddg"], 0)
            with (root / "prempni_prediction.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], CSV_HEADER)
            self.assertEqual(rows[1][5:8], ["PremPDI2", "-0.000", "Stabilizing"])
            self.assertEqual(rows[2][6:8], ["0.000", "Destabilizing"])
            with self.assertRaises(FileExistsError):
                run(args, [req], False, infer)

    def test_collection_failure_preserves_rows_without_classification(self):
        with tempfile.TemporaryDirectory() as directory:
            args = parse_args(["--output-root", directory])
            reqs = [validate_request(request()), validate_request(request(sample_id="rna", complex_type="rna", chains=[dict(chain_id="RNA_1", sequence="ACGU")], mutation="A2A"))]
            def fail(*unused):
                raise RuntimeError("test inference failure")
            self.assertEqual(run(args, reqs, True, fail), 1)
            path = next(Path(directory).glob("collections/*/prempni_prediction.csv"))
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], COLLECTION_HEADER)
            self.assertEqual(rows[1][5:8], ["failed", "", ""])
            self.assertEqual(rows[2][5:8], ["completed", "0.000", "Destabilizing"])


if __name__ == "__main__":
    unittest.main()
