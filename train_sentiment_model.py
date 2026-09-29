"""Train the review-sentiment artifacts used by the Flask application.

Run this after changing the scikit-learn version:
    python train_sentiment_model.py
"""

import json
import pickle
from pathlib import Path

import pandas as pd
import sklearn
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB


BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "Artifacts"
REVIEWS_FILE = ARTIFACTS_DIR / "reviews.txt"
MODEL_FILE = ARTIFACTS_DIR / "nlp_model.pkl"
VECTORIZER_FILE = ARTIFACTS_DIR / "tranform.pkl"
METADATA_FILE = ARTIFACTS_DIR / "sentiment_model_metadata.json"


def main():
    reviews = pd.read_csv(
        REVIEWS_FILE,
        sep="\t",
        header=None,
        names=["label", "review"],
        dtype={"label": int, "review": str},
        keep_default_na=False,
    )
    if reviews.empty or reviews["label"].nunique() < 2:
        raise ValueError("reviews.txt must contain labelled positive and negative reviews.")

    vectorizer = TfidfVectorizer(
        use_idf=True,
        lowercase=True,
        strip_accents="ascii",
        stop_words=list(ENGLISH_STOP_WORDS),
    )
    features = vectorizer.fit_transform(reviews["review"])
    classifier = MultinomialNB().fit(features, reviews["label"])

    with MODEL_FILE.open("wb") as model_file:
        pickle.dump(classifier, model_file, protocol=pickle.HIGHEST_PROTOCOL)
    with VECTORIZER_FILE.open("wb") as vectorizer_file:
        pickle.dump(vectorizer, vectorizer_file, protocol=pickle.HIGHEST_PROTOCOL)

    METADATA_FILE.write_text(
        json.dumps(
            {
                "artifact_format": 1,
                "model": "MultinomialNB",
                "vectorizer": "TfidfVectorizer",
                "scikit_learn_version": sklearn.__version__,
                "training_rows": int(len(reviews)),
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Trained {len(reviews)} reviews with scikit-learn {sklearn.__version__}.")


if __name__ == "__main__":
    main()
