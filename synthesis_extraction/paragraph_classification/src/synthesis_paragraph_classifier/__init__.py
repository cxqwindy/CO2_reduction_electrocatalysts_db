"""Synthesis paragraph classification using sentence topics and a random forest."""

from .data import (
    ParagraphRecord,
    build_training_dataset,
    generate_negative_examples,
    generate_positive_examples,
    load_jsonl,
)
from .model import (
    ClassifierConfig,
    SentenceTopicModel,
    SynthesisParagraphClassifier,
    get_default_model,
)

__all__ = [
    "ClassifierConfig",
    "ParagraphRecord",
    "SentenceTopicModel",
    "SynthesisParagraphClassifier",
    "build_training_dataset",
    "generate_negative_examples",
    "generate_positive_examples",
    "get_default_model",
    "load_jsonl",
]

__version__ = "1.0.0"
