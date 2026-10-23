from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from synthesis_paragraph_classifier.data import build_training_dataset, load_jsonl
from synthesis_paragraph_classifier.model import ClassifierConfig, SynthesisParagraphClassifier
from synthesis_paragraph_classifier.text import chemistry_tokenizer, sentence_split


class TextTests(unittest.TestCase):
    def test_scientific_tokenization_and_sentences(self):
        text = "Cu(NO3)2 was dissolved in 20 mL water. The product was heated at 80 °C for 2 h."
        self.assertEqual(len(sentence_split(text)), 2)
        tokens = chemistry_tokenizer(text)
        self.assertIn("20", tokens)
        self.assertIn("ml", tokens)


class DataTests(unittest.TestCase):
    def test_exact_requested_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "gold"
            root.mkdir()
            sections = []
            for index in range(80):
                sections.append(
                    {
                        "heading": f"Synthesis of catalyst {index}",
                        "text": (
                            f"In a typical synthesis, sample {index} was dissolved in 20 mL water. "
                            "The solution was stirred, heated at 80 °C for 2 h, washed, and dried overnight."
                        ),
                    }
                )
                sections.append(
                    {
                        "heading": f"Results and discussion {index}",
                        "text": (
                            f"Catalytic performance result {index} demonstrates stable current density and selective conversion. "
                            "Spectroscopic characterization confirms the observed surface state without giving a preparation recipe."
                        ),
                    }
                )
            for article in range(8):
                (root / f"article-{article}.json").write_text(
                    json.dumps({"sections": sections}), encoding="utf-8"
                )
            out = Path(directory) / "data"
            positives, negatives = build_training_dataset(
                root, out, positive_count=20, negative_count=30
            )
            self.assertEqual((len(positives), len(negatives)), (20, 30))
            self.assertEqual(len(load_jsonl(out / "paragraph_classification_training_data.jsonl")), 50)


class ModelTests(unittest.TestCase):
    def test_train_save_load_predict(self):
        positives = [
            "Cu nitrate was dissolved in water. The solution was stirred and heated at 80 °C. The solid was washed and dried.",
            "The precursor was mixed with ethanol. It was calcined at 500 °C for 2 h and then cooled.",
            "Nickel foam was immersed in solution. The electrode was deposited, rinsed, and dried overnight.",
            "Powders were ground and pressed into pellets. The pellets were sintered at 900 °C.",
        ]
        negatives = [
            "The catalyst shows high selectivity. Current density remains stable during testing.",
            "XRD patterns confirm a crystalline phase. Raman spectra reveal structural defects.",
            "Carbon dioxide emissions cause climate change. Efficient conversion is therefore important.",
            "The measured Faradaic efficiency reaches fifty percent. The result agrees with prior reports.",
        ]
        config = ClassifierConfig(n_topics=4, min_df=1, lda_max_iter=2, max_features=200)
        model = SynthesisParagraphClassifier(config).fit(positives + negatives, [1] * 4 + [0] * 4)
        label, confidence, details = model.classify_paragraph(positives[0])
        self.assertIn(label, {"synthesis", "not_synthesis"})
        self.assertGreaterEqual(confidence, 0.5)
        self.assertIn("sentence_topics", details)
        with tempfile.TemporaryDirectory() as directory:
            model.save(directory)
            restored = SynthesisParagraphClassifier.load(directory)
            self.assertEqual(restored.predict(positives[0]).shape, (1,))
            self.assertTrue((Path(directory) / "lda_model.joblib").exists())


if __name__ == "__main__":
    unittest.main()
