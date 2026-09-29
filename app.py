import json
import os
from dotenv import load_dotenv
import time
import pandas as pd
import urllib.request
import urllib.parse
import urllib.error
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from flask import Flask, jsonify, render_template, request
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

# loading the dataset and the trained model
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "Artifacts"

DATA_FILE = ARTIFACTS_DIR / "main_data.csv"
MOVIES_FILE = ARTIFACTS_DIR / "movies.csv"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w342"

app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024,
    JSON_SORT_KEYS=False,
)


@app.after_request
def add_security_headers(response):
    """Apply safe browser defaults without constraining required CDN assets."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

# A small in-memory guard for this public demo. For multiple application
# instances, replace this with a shared limiter such as Redis/Flask-Limiter.
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 45
_rate_limit_buckets = {}
_rate_limit_lock = threading.Lock()


def rate_limit(view):
    """Limit public API requests per client IP without adding infrastructure."""
    def wrapped(*args, **kwargs):
        if app.config.get("TESTING"):
            return view(*args, **kwargs)
        now = time.monotonic()
        client = request.remote_addr or "unknown"
        with _rate_limit_lock:
            timestamps = _rate_limit_buckets.setdefault(client, [])
            timestamps[:] = [stamp for stamp in timestamps if now - stamp < RATE_LIMIT_WINDOW_SECONDS]
            if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
                return jsonify(error="Too many requests. Please wait a minute and try again."), 429
            timestamps.append(now)
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped

# creating a similarity matrix using count vectorizer and cosine similarity
@lru_cache(maxsize=1)
def create_similarity():
    """Load the local recommendation model once, rather than on every search."""
    data = pd.read_csv(DATA_FILE)
    data['movie_title'] = data['movie_title'].fillna('').astype(str).str.strip().str.casefold()
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(data['comb'].fillna(''))
    return data, cosine_similarity(count_matrix)

def rcmd(m):
    m = str(m or '').strip().casefold()

    if not m:
        return 'Please enter a movie title.'

    data, similarity = create_similarity()

    if m not in set(data['movie_title']):
        return 'Sorry! The movie you requested is not in our database. Please check the spelling or try with some other movies'

    i = data.loc[data['movie_title'] == m].index[0]

    lst = list(enumerate(similarity[i]))
    lst = sorted(lst, key=lambda x: x[1], reverse=True)

    lst = lst[1:11]

    recommendations = []

    for item in lst:
        movie_index = item[0]
        recommendations.append(data['movie_title'][movie_index])

    return recommendations


@lru_cache(maxsize=512)
def tmdb_get(path, **params):
    """Call TMDB over verified HTTPS and cache successful GET responses."""
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB is not configured. Set the TMDB_API_KEY environment variable.")
    query = urllib.parse.urlencode({"api_key": TMDB_API_KEY, **params})
    tmdb_request = urllib.request.Request(
        f"{TMDB_API_URL}{path}?{query}",
        headers={"User-Agent": "Movie-Recommendation-System/1.0"},
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(tmdb_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.25 * (attempt + 1))
    raise last_error


def tmdb_movie_card(movie):
    poster_path = movie.get("poster_path")
    return {
        "id": movie.get("id"),
        "title": movie.get("title") or movie.get("original_title") or "Untitled",
        "overview": movie.get("overview") or "No overview is available.",
        "release_date": movie.get("release_date") or "",
        "rating": movie.get("vote_average"),
        "poster": f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else None,
        "genre_ids": movie.get("genre_ids", []),
        "genres": [genre.get("name") for genre in movie.get("genres", []) if genre.get("name")],
    }


@lru_cache(maxsize=1)
def local_title_to_tmdb_id():
    """Build a title-to-TMDB-ID lookup from the local movie metadata."""
    movies = pd.read_csv(MOVIES_FILE, usecols=["id", "title"])
    movies = movies.dropna(subset=["id", "title"])
    return {
        str(title).strip().casefold(): int(movie_id)
        for movie_id, title in zip(movies["id"], movies["title"])
        if str(title).strip()
    }


@lru_cache(maxsize=1)
def local_movie_overviews():
    """Load local plot summaries keyed by the same normalized movie title."""
    movies = pd.read_csv(MOVIES_FILE, usecols=["title", "overview"])
    movies = movies.dropna(subset=["title"])
    return {
        str(title).strip().casefold(): str(overview).strip()
        for title, overview in zip(movies["title"], movies["overview"].fillna(""))
        if str(title).strip()
    }


@lru_cache(maxsize=4096)
def tmdb_details_for_title(title):
    """Return TMDB card details for a local title, or an empty mapping on failure."""
    if not TMDB_API_KEY:
        return {}

    normalized_title = str(title or "").strip().casefold()
    if not normalized_title:
        return {}

    try:
        movie_id = local_title_to_tmdb_id().get(normalized_title)
        if movie_id:
            movie = tmdb_get(f"/movie/{movie_id}")
        else:
            matches = tmdb_get("/search/movie", query=title, include_adult="false").get("results", [])
            movie = next(
                (
                    match for match in matches
                    if str(match.get("title") or match.get("original_title") or "").strip().casefold() == normalized_title
                ),
                matches[0] if matches else None,
            )

        poster_path = movie.get("poster_path") if movie else None
        if not movie:
            return {}
        return {
            "poster": f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else None,
            "rating": movie.get("vote_average"),
            "release_date": movie.get("release_date") or "",
        }
    except Exception as error:
        app.logger.info("Poster lookup failed for %r: %s", title, error)
        return {}


@lru_cache(maxsize=1)
def local_movie_metadata():
    """Get display metadata that is already present in the recommendation dataset."""
    data, _ = create_similarity()
    overviews = local_movie_overviews()
    metadata = {}
    for _, row in data.iterrows():
        title = row["movie_title"]
        if title and title not in metadata:
            genre = str(row.get("genres", "") or "").strip()
            cast = []
            for column in ("actor_1_name", "actor_2_name", "actor_3_name"):
                actor = row.get(column, "")
                if pd.notna(actor) and str(actor).strip():
                    cast.append(str(actor).strip())
            director = row.get("director_name", "")
            metadata[title] = {
                "genre": genre,
                "overview": overviews.get(title, ""),
                "director": str(director).strip() if pd.notna(director) else "",
                "cast": cast,
            }
    return metadata


def local_matching_features(source_title, candidate_title):
    """Expose only genuine overlaps from the fields used by the local model."""
    metadata = local_movie_metadata()
    source = metadata.get(str(source_title).strip().casefold(), {})
    candidate = metadata.get(str(candidate_title).strip().casefold(), {})
    if not source or not candidate:
        return {}

    source_genres = set(str(source.get("genre", "")).casefold().split())
    candidate_genres = set(str(candidate.get("genre", "")).casefold().split())
    shared_genres = sorted(source_genres & candidate_genres)
    source_cast = {name.casefold(): name for name in source.get("cast", [])}
    candidate_cast = {name.casefold(): name for name in candidate.get("cast", [])}
    shared_cast = [
        name for name in source.get("cast", [])
        if name.casefold() in candidate_cast
    ]
    matching = {}

    if shared_genres:
        matching["genres"] = [genre.title() for genre in shared_genres]
    if shared_cast:
        matching["cast"] = shared_cast
    if source.get("director") and source.get("director").casefold() == candidate.get("director", "").casefold():
        matching["director"] = source["director"]

    return matching


def local_recommendation_cards(source_title, titles):
    """Keep local ranking, then enrich its cards with TMDB artwork in parallel."""
    titles = list(titles)
    metadata = local_movie_metadata()
    if not TMDB_API_KEY:
        return [
            {
                "title": title.title(),
                "genre": metadata.get(title, {}).get("genre", ""),
                "overview": metadata.get(title, {}).get("overview", ""),
                "matching_features": local_matching_features(source_title, title),
            }
            for title in titles
        ]

    with ThreadPoolExecutor(max_workers=5) as executor:
        details = list(executor.map(tmdb_details_for_title, titles))

    return [
        {
            "title": title.title(),
            "genre": metadata.get(title, {}).get("genre", ""),
            "overview": metadata.get(title, {}).get("overview", ""),
            "matching_features": local_matching_features(source_title, title),
            **movie_details,
        }
        for title, movie_details in zip(titles, details)
    ]


def tmdb_recommendations(title):
    """Find a TMDB movie, then get its recommendations (or similar movies)."""
    matches = tmdb_get("/search/movie", query=title, include_adult="false").get("results", [])
    if not matches:
        return None, []
    selected = matches[0]
    selected_details = tmdb_get(f"/movie/{selected['id']}")
    recommendations = tmdb_get(f"/movie/{selected['id']}/recommendations").get("results", [])
    if not recommendations:
        recommendations = tmdb_get(f"/movie/{selected['id']}/similar").get("results", [])
    try:
        genre_map = {
            genre["id"]: genre["name"]
            for genre in tmdb_get("/genre/movie/list", language="en-US").get("genres", [])
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, RuntimeError):
        genre_map = {}
    selected_card = tmdb_movie_card(selected_details)
    selected_genres = set(selected_card["genres"])
    recommendation_cards = []

    for movie in recommendations[:10]:
        card = tmdb_movie_card(movie)
        card_genres = [genre_map[genre_id] for genre_id in card["genre_ids"] if genre_id in genre_map]
        card["genres"] = card_genres
        shared_genres = [genre for genre in card_genres if genre in selected_genres]
        card["matching_features"] = {"shared_genres": shared_genres}
        recommendation_cards.append(card)

    return selected_card, recommendation_cards
    
def get_suggestions():
    data, _ = create_similarity()
    return list(data['movie_title'].str.title())

@app.route("/")
@app.route("/home")
def home():
    suggestions = get_suggestions()
    return render_template('home.html',suggestions=suggestions)

@app.route("/movie-search", methods=["GET"])
@rate_limit
def movie_search():
    query = request.args.get("query", "").strip()[:200]

    if not query:
        return jsonify(results=[])

    try:
        data = tmdb_get(
            "/search/movie",
            query=query,
            include_adult="false"
        )

        results = []

        for movie in data.get("results", [])[:8]:
            results.append({
                "id": movie.get("id"),
                "title": movie.get("title") or movie.get("original_title"),
                "release_date": movie.get("release_date") or "",
                "poster": (
                    f"{TMDB_IMAGE_URL}{movie['poster_path']}"
                    if movie.get("poster_path")
                    else None
                )
            })

        return jsonify(results=results)

    except Exception:
        app.logger.exception("TMDB movie search failed")
        return jsonify(results=[], error="Movie search is temporarily unavailable. Please try again shortly."), 503


@app.route("/health", methods=["GET"])
def health():
    """Deployment health check that never reveals secrets or internal paths."""
    required_artifacts = (DATA_FILE, MOVIES_FILE)
    artifacts_ready = all(path.is_file() for path in required_artifacts)
    status = "ok" if artifacts_ready else "degraded"
    return jsonify(
        status=status,
        artifacts_ready=artifacts_ready,
        tmdb_configured=bool(TMDB_API_KEY),
    ), 200 if artifacts_ready else 503


@app.route("/similarity",methods=["POST"])
@rate_limit
def similarity():
    movie = request.form.get('name', '').strip()[:200]
    if not movie:
        return jsonify(error="Please enter a movie title."), 400
    rc = rcmd(movie)
    if not isinstance(rc, str):
        return jsonify(
            source="local-ml",
            title=movie,
            selected={"title": movie},
            recommendations=local_recommendation_cards(movie, rc),
        )

    try:
        selected, recommendations = tmdb_recommendations(movie)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, RuntimeError):
        app.logger.exception("TMDB recommendation lookup failed")
        return jsonify(error="Movie search is temporarily unavailable. Please try again shortly."), 503
    if not selected:
        return jsonify(error="No movie was found with that title."), 404
    if not recommendations:
        return jsonify(error=f"TMDB found {selected['title']}, but has no recommendations yet."), 404
    return jsonify(source="tmdb", title=selected["title"], selected=selected, recommendations=recommendations)

if __name__ == '__main__':
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
