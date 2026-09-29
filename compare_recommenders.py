import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_FILE = "Artifacts/main_data.csv"


def get_recommendations(data, similarity, movie_title, top_n=10):
    movie_title = movie_title.strip().casefold()

    matches = data.index[data["movie_title"] == movie_title].tolist()

    if not matches:
        return []

    movie_index = matches[0]

    scores = list(enumerate(similarity[movie_index]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    recommendations = []

    for index, score in scores:
        if index == movie_index:
            continue

        recommendations.append(
            (data.iloc[index]["movie_title"], score)
        )

        if len(recommendations) == top_n:
            break

    return recommendations


data = pd.read_csv(DATA_FILE)

data["movie_title"] = (
    data["movie_title"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

text = data["comb"].fillna("")


# -------------------------
# CountVectorizer baseline
# -------------------------
count_vectorizer = CountVectorizer()
count_matrix = count_vectorizer.fit_transform(text)
count_similarity = cosine_similarity(count_matrix)


# -------------------------
# TF-IDF candidate
# -------------------------
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(text)
tfidf_similarity = cosine_similarity(tfidf_matrix)


movies = [
    "avatar",
    "the dark knight rises",
    "spectre",
    "star wars: episode vii - the force awakens",
]


for movie in movies:
    print("\n" + "=" * 70)
    print("MOVIE:", movie)

    print("\nCOUNT VECTORIZER:")
    for title, score in get_recommendations(
        data, count_similarity, movie
    ):
        print(f"{title}  |  {score:.4f}")

    print("\nTF-IDF:")
    for title, score in get_recommendations(
        data, tfidf_similarity, movie
    ):
        print(f"{title}  |  {score:.4f}")