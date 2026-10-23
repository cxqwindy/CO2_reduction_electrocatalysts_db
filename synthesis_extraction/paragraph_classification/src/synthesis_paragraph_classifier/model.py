"""LDA topic model and random-forest synthesis paragraph classifier."""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import CountVectorizer

from .text import chemistry_tokenizer, sentence_split


@dataclass(frozen=True)
class ClassifierConfig:
    """Model defaults matching the cited LDA + RF method where practical."""

    n_topics: int = 200
    topic_probability_threshold: float = 0.05
    max_ngram: int = 3
    max_topics_per_sentence: int = 3
    n_estimators: int = 20
    max_depth: int = 20
    max_features: int = 8000
    min_df: int = 2
    lda_max_iter: int = 10
    max_lda_sentences: int = 50000
    random_state: int = 17


class SentenceTopicModel:
    """Sentence-level bag-of-words LDA model."""

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()
        self.vectorizer = CountVectorizer(
            tokenizer=chemistry_tokenizer,
            token_pattern=None,
            lowercase=False,
            stop_words="english",
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            max_df=0.98,
        )
        self.model = LatentDirichletAllocation(
            n_components=self.config.n_topics,
            doc_topic_prior=min(1.0, 5.0 / self.config.n_topics),
            topic_word_prior=0.01,
            learning_method="online",
            max_iter=self.config.lda_max_iter,
            random_state=self.config.random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(self, texts: Iterable[str]) -> "SentenceTopicModel":
        sentences: list[str] = []
        for text in texts:
            sentences.extend(sentence_split(text))
            if len(sentences) >= self.config.max_lda_sentences:
                sentences = sentences[: self.config.max_lda_sentences]
                break
        if len(sentences) < 2:
            raise ValueError("At least two non-empty sentences are required to train LDA")
        counts = self.vectorizer.fit_transform(sentences)
        if counts.shape[1] < 2:
            raise ValueError("LDA corpus produced fewer than two vocabulary terms")
        self.model.fit(counts)
        self.is_fitted = True
        return self

    def transform(self, sentences: Sequence[str]) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("SentenceTopicModel must be fitted before transform")
        if not sentences:
            return np.empty((0, self.config.n_topics), dtype=float)
        counts = self.vectorizer.transform(sentences)
        return self.model.transform(counts)

    def top_words(self, topic: int, n: int = 20) -> list[tuple[str, float]]:
        """Return highest-weight words for one topic."""
        if not self.is_fitted:
            raise RuntimeError("SentenceTopicModel must be fitted before inspection")
        if topic < 0 or topic >= self.config.n_topics:
            raise IndexError(f"Topic must be in [0, {self.config.n_topics})")
        names = self.vectorizer.get_feature_names_out()
        weights = self.model.components_[topic]
        indices = weights.argsort()[::-1][:n]
        total = float(weights.sum()) or 1.0
        return [(str(names[index]), float(weights[index] / total)) for index in indices]


class SynthesisParagraphClassifier:
    """Binary synthesis classifier based on topic sequences in adjacent sentences."""

    label_names = {0: "not_synthesis", 1: "synthesis"}

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()
        self.sentence_model = SentenceTopicModel(self.config)
        self.feature_vectorizer = DictVectorizer(sparse=True)
        self.classifier = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            class_weight="balanced_subsample",
            random_state=self.config.random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def _active_topics(self, distributions: np.ndarray) -> list[list[tuple[int, float]]]:
        active: list[list[tuple[int, float]]] = []
        for row in distributions:
            indices = np.flatnonzero(row >= self.config.topic_probability_threshold)
            if not len(indices):
                indices = np.asarray([int(row.argmax())])
            ranked = sorted(
                ((int(index), float(row[index])) for index in indices),
                key=lambda item: item[1],
                reverse=True,
            )[: self.config.max_topics_per_sentence]
            active.append(ranked)
        return active

    def _feature_dict(self, paragraph: str) -> dict[str, float]:
        sentences = sentence_split(paragraph)
        if not sentences:
            return {"empty_paragraph": 1.0}
        distributions = self.sentence_model.transform(sentences)
        active = self._active_topics(distributions)
        features: dict[str, float] = {}
        for sentence_topics in active:
            for topic, probability in sentence_topics:
                name = f"topic_{topic}"
                features[name] = max(features.get(name, 0.0), probability)
        for ngram_size in range(2, self.config.max_ngram + 1):
            for start in range(0, len(active) - ngram_size + 1):
                window = active[start : start + ngram_size]
                for combination in itertools.product(*window):
                    topics = "_".join(str(topic) for topic, _ in combination)
                    features[f"topic_ngram_{ngram_size}_{topics}"] = 1.0
        features["sentence_count"] = min(len(sentences), 50) / 50.0
        return features

    def fit(
        self,
        paragraphs: Sequence[str],
        labels: Sequence[int],
        *,
        lda_corpus: Iterable[str] | None = None,
    ) -> "SynthesisParagraphClassifier":
        if len(paragraphs) != len(labels):
            raise ValueError("paragraphs and labels must have equal lengths")
        if set(int(label) for label in labels) != {0, 1}:
            raise ValueError("labels must contain both 0 and 1")
        self.sentence_model.fit(lda_corpus if lda_corpus is not None else paragraphs)
        dictionaries = [self._feature_dict(paragraph) for paragraph in paragraphs]
        features = self.feature_vectorizer.fit_transform(dictionaries)
        self.classifier.fit(features, np.asarray(labels, dtype=int))
        self.is_fitted = True
        return self

    @property
    def feature_names(self) -> list[str]:
        if not self.is_fitted:
            return []
        return [str(value) for value in self.feature_vectorizer.get_feature_names_out()]

    def featurize_paragraph(self, paragraph: str):
        if not self.is_fitted:
            raise RuntimeError("Classifier must be fitted before inference")
        return self.feature_vectorizer.transform([self._feature_dict(paragraph)])

    def predict(self, paragraphs: str | Sequence[str]) -> np.ndarray:
        values = [paragraphs] if isinstance(paragraphs, str) else list(paragraphs)
        features = self.feature_vectorizer.transform([self._feature_dict(value) for value in values])
        return self.classifier.predict(features)

    def predict_proba(self, paragraphs: str | Sequence[str]) -> np.ndarray:
        values = [paragraphs] if isinstance(paragraphs, str) else list(paragraphs)
        features = self.feature_vectorizer.transform([self._feature_dict(value) for value in values])
        return self.classifier.predict_proba(features)

    def classify_paragraph(self, paragraph: str) -> tuple[str, float, dict[str, Any]]:
        """Classify one paragraph using an interface similar to the cited package."""
        probabilities = self.predict_proba([paragraph])[0]
        by_class = {int(label): float(value) for label, value in zip(self.classifier.classes_, probabilities)}
        prediction = max(by_class, key=by_class.get)
        details = {
            "predictions": {self.label_names[label]: probability for label, probability in by_class.items()},
            "sentence_topics": self.paragraph_topics(paragraph),
        }
        return self.label_names[prediction], by_class[prediction], details

    def paragraph_topics(self, paragraph: str) -> list[dict[str, Any]]:
        sentences = sentence_split(paragraph)
        distributions = self.sentence_model.transform(sentences)
        active = self._active_topics(distributions)
        return [
            {
                "sentence": sentence,
                "topics": {str(topic): probability for topic, probability in topics},
            }
            for sentence, topics in zip(sentences, active)
        ]

    def save(self, model_dir: str | Path) -> None:
        """Save separate trained LDA and complete paragraph classifier artifacts."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted classifier")
        output = Path(model_dir)
        output.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.sentence_model, output / "lda_model.joblib", compress=3)
        joblib.dump(self, output / "paragraph_classifier.joblib", compress=3)
        metadata = {
            "config": asdict(self.config),
            "labels": self.label_names,
            "vocabulary_size": len(self.sentence_model.vectorizer.vocabulary_),
            "feature_count": len(self.feature_names),
            "artifact_files": ["lda_model.joblib", "paragraph_classifier.joblib"],
        }
        (output / "model_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, model_path: str | Path) -> "SynthesisParagraphClassifier":
        path = Path(model_path)
        if path.is_dir():
            path = path / "paragraph_classifier.joblib"
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError(f"Artifact at {path} is not a {cls.__name__}")
        return model


def get_default_model(model_path: str | Path | None = None) -> SynthesisParagraphClassifier:
    """Load the bundled/default trained classifier."""
    if model_path is None:
        project_default = Path(__file__).resolve().parents[2] / "models" / "paragraph_classifier.joblib"
        package_default = Path(__file__).resolve().parent / "models" / "paragraph_classifier.joblib"
        model_path = project_default if project_default.exists() else package_default
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Trained classifier not found: {path}. Run the train command first.")
    return SynthesisParagraphClassifier.load(path)
