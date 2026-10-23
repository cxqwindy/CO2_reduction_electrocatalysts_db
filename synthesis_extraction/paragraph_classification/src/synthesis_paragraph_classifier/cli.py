"""Command-line interface for data generation, training, and inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data import build_training_dataset, iter_gold_paragraphs, load_jsonl
from .model import ClassifierConfig, SynthesisParagraphClassifier


def _generate_data(args: argparse.Namespace) -> int:
    positives, negatives = build_training_dataset(
        args.gold_data,
        args.output_dir,
        positive_count=args.positive_count,
        negative_count=args.negative_count,
        seed=args.seed,
    )
    print(json.dumps({"positive": len(positives), "negative": len(negatives), "total": len(positives) + len(negatives)}))
    return 0


def _train(args: argparse.Namespace) -> int:
    records = load_jsonl(args.training_data)
    paragraphs = [record.text for record in records]
    labels = [int(record.label) for record in records if record.label is not None]
    if len(labels) != len(records):
        raise ValueError("Every training record must have a label")
    lda_corpus = (record.text for record in iter_gold_paragraphs(args.gold_data))
    config = ClassifierConfig(
        n_topics=args.n_topics,
        lda_max_iter=args.lda_iterations,
        max_lda_sentences=args.max_lda_sentences,
        random_state=args.seed,
    )
    model = SynthesisParagraphClassifier(config)
    model.fit(paragraphs, labels, lda_corpus=lda_corpus)
    model.save(args.model_dir)
    print(
        json.dumps(
            {
                "training_examples": len(records),
                "topics": config.n_topics,
                "features": len(model.feature_names),
                "model_dir": str(args.model_dir),
            }
        )
    )
    return 0


def _predict(args: argparse.Namespace) -> int:
    model = SynthesisParagraphClassifier.load(args.model)
    label, confidence, details = model.classify_paragraph(args.text)
    print(json.dumps({"label": label, "confidence": confidence, "details": details}, ensure_ascii=False, indent=2))
    return 0


def _topics(args: argparse.Namespace) -> int:
    model = SynthesisParagraphClassifier.load(args.model)
    values = model.sentence_model.top_words(args.topic, args.words)
    print(json.dumps({"topic": args.topic, "words": values}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synthesis-paragraph-classifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    data_parser = subparsers.add_parser("generate-data", help="build 228 positive and 532 negative examples")
    data_parser.add_argument("--gold-data", type=Path, default=Path("gold_data"))
    data_parser.add_argument("--output-dir", type=Path, default=Path("data"))
    data_parser.add_argument("--positive-count", type=int, default=228)
    data_parser.add_argument("--negative-count", type=int, default=532)
    data_parser.add_argument("--seed", type=int, default=17)
    data_parser.set_defaults(func=_generate_data)

    train_parser = subparsers.add_parser("train", help="train LDA and paragraph classifier")
    train_parser.add_argument("--training-data", type=Path, default=Path("data/paragraph_classification_training_data.jsonl"))
    train_parser.add_argument("--gold-data", type=Path, default=Path("gold_data"))
    train_parser.add_argument("--model-dir", type=Path, default=Path("models"))
    train_parser.add_argument("--n-topics", type=int, default=200)
    train_parser.add_argument("--lda-iterations", type=int, default=10)
    train_parser.add_argument("--max-lda-sentences", type=int, default=50000)
    train_parser.add_argument("--seed", type=int, default=17)
    train_parser.set_defaults(func=_train)

    predict_parser = subparsers.add_parser("predict", help="classify one paragraph")
    predict_parser.add_argument("text")
    predict_parser.add_argument("--model", type=Path, default=Path("models/paragraph_classifier.joblib"))
    predict_parser.set_defaults(func=_predict)

    topic_parser = subparsers.add_parser("topics", help="show high-probability words for one topic")
    topic_parser.add_argument("topic", type=int)
    topic_parser.add_argument("--words", type=int, default=20)
    topic_parser.add_argument("--model", type=Path, default=Path("models/paragraph_classifier.joblib"))
    topic_parser.set_defaults(func=_topics)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
