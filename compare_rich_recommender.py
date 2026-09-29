import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MAIN_FILE = "Artifacts/main_data.csv"
RAW_FILE = "Artifacts/movies.csv"


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


# ---------------------------------------------------------
# Load datasets
# ---------------------------------------------------------
main = pd.read_csv(MAIN_FILE)
raw = pd.read_csv(RAW_FILE, low_memory=False)

main["movie_title_clean"] = (
    main["movie_title"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

raw["title_clean"] = (
    raw["title"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

# Keep one raw record per normalized title
raw_lookup = raw.drop_duplicates("title_clean").set_index("title_clean")


# ---------------------------------------------------------
# Build richer dataset only for matched movies
# ---------------------------------------------------------
rows = []

for _, movie in main.iterrows():
    title_key = movie["movie_title_clean"]

    if title_key not in raw_lookup.index:
        continue

    rich = raw_lookup.loc[title_key]

    text = " ".join(
        [
            clean_text(rich.get("overview")),
            clean_text(rich.get("keywords")),
            clean_text(rich.get("genres")),
            clean_text(rich.get("cast")),
            clean_text(rich.get("director")),
        ]
    )

    rows.append(
        {
            "title": movie["movie_title"],
            "text": text,
        }
    )

rich_data = pd.DataFrame(rows)

print("Main dataset movies:", len(main))
print("Matched rich movies:", len(rich_data))
print(
    "Coverage:",
    round(100 * len(rich_data) / len(main), 2),
    "%"
)


# ---------------------------------------------------------
# Current recommender: CountVectorizer
# ---------------------------------------------------------
main_text = main["comb"].fillna("").astype(str)

count_vectorizer = CountVectorizer()
count_matrix = count_vectorizer.fit_transform(main_text)

count_similarity = cosine_similarity(count_matrix)


# ---------------------------------------------------------
# Rich recommender: TF-IDF
# ---------------------------------------------------------
tfidf_vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    min_df=2,
)

tfidf_matrix = tfidf_vectorizer.fit_transform(rich_data["text"])

tfidf_similarity = cosine_similarity(tfidf_matrix)


# ---------------------------------------------------------
# Recommendation functions
# ---------------------------------------------------------
def current_recommendations(title, n=10):
    title = title.strip().casefold()

    matches = main.index[
        main["movie_title_clean"] == title
    ]

    if len(matches) == 0:
        return []

    index = matches[0]

    scores = list(enumerate(count_similarity[index]))
    scores = sorted(
        scores,
        key=lambda x: x[1],
        reverse=True
    )

    results = []

    for movie_index, score in scores[1:n + 1]:
        results.append(
            (
                main.iloc[movie_index]["movie_title"],
                round(float(score), 4),
            )
        )

    return results


def rich_recommendations(title, n=10):
    title = title.strip().casefold()

    matches = rich_data.index[
        rich_data["title"].astype(str).str.strip().str.casefold()
        == title
    ]

    if len(matches) == 0:
        return []

    index = matches[0]

    scores = list(enumerate(tfidf_similarity[index]))
    scores = sorted(
        scores,
        key=lambda x: x[1],
        reverse=True
    )

    results = []

    for movie_index, score in scores[1:n + 1]:
        results.append(
            (
                rich_data.iloc[movie_index]["title"],
                round(float(score), 4),
            )
        )

    return results


# ---------------------------------------------------------
# Compare examples
# ---------------------------------------------------------
test_movies = [
    "Avatar",
    "The Dark Knight Rises",
    "Spectre",
]


for movie in test_movies:
    print("\n" + "=" * 70)
    print(movie)
    print("=" * 70)

    print("\nCURRENT RECOMMENDER:")
    for title, score in current_recommendations(movie):
        print(f"{title} ({score})")

    print("\nRICH TF-IDF RECOMMENDER:")
    for title, score in rich_recommendations(movie):
        print(f"{title} ({score})")