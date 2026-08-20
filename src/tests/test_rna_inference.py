"""Lightweight regression tests; no real RiNALMo checkpoint is loaded."""

import tempfile
import unittest
from pathlib import Path

import torch

from protein_rna.mlp_predictor import extract_sample_features
from protein_rna.rinalmo_dataset import build_dataset_features
from protein_rna.rinalmo_pipeline import RiNALMoPipeline
from protein_rna.rinalmo_processing import (
    RNAChain,
    concatenate_chain_embeddings,
    mean_pool_embedding,
    split_chain_sequences,
)


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed_chains_independently(self, sequences):
        self.calls.extend(sequences)
        values = {"AC": 1.0, "G": 3.0}
        return [torch.full((len(sequence), 1280), values[sequence]) for sequence in sequences]


class RNAInferenceTests(unittest.TestCase):
    def test_pipe_split_is_strict(self):
        self.assertEqual(split_chain_sequences("ac|GU"), ["AC", "GU"])
        with self.assertRaises(ValueError):
            split_chain_sequences("AC||GU")

    def test_mean_pool_uses_all_real_bases_and_no_separator(self):
        first = torch.ones((2, 1280))
        second = torch.full((1, 1280), 3.0)
        joined = concatenate_chain_embeddings(["AC", "G"], [first, second])
        self.assertEqual(tuple(joined.shape), (3, 1280))
        pooled = mean_pool_embedding(joined)
        self.assertTrue(torch.allclose(pooled, torch.full((1280,), 5.0 / 3.0)))

    def test_pipeline_embeds_each_chain_and_writes_full_length_mean(self):
        fake = FakeEmbedder()
        pipeline = RiNALMoPipeline(embedder=fake)
        with tempfile.TemporaryDirectory() as directory:
            result = pipeline.run(
                "sample_1",
                [RNAChain("RNA_1", "AC"), RNAChain("RNA_2", "G")],
                directory,
            )
            features = torch.load(result.combined_embedding_path, map_location="cpu")
        self.assertEqual(fake.calls, ["AC", "G"])
        self.assertTrue(
            torch.allclose(
                features["sample_1"]["mean_pooling"],
                torch.full((1280,), 5.0 / 3.0),
            )
        )

    def test_dataset_builder_raises_for_missing_chain_feature(self):
        with self.assertRaises(KeyError):
            build_dataset_features({"s1": ["AC", "G"]}, {"AC": torch.ones((2, 1280))})

    def test_mlp_feature_loading_never_zero_fills_missing_sample(self):
        with self.assertRaises(KeyError):
            extract_sample_features("missing", {}, {})


if __name__ == "__main__":
    unittest.main()
