# MovieMatch — Content-Based Movie Recommender

MovieMatch is a deployed Flask web application that suggests movies similar to a title the visitor enjoys. It combines a local content-based recommendation model with optional TMDB metadata enrichment for posters, ratings, and release dates.

> **Live demo:** Add your deployed URL here before sharing the project on your resume.

## What it does

- Returns the top 10 similar movies from a local catalogue.
- Uses cosine similarity over a combined representation of genres, cast, director, and plot-related metadata.
- Shows recommendation reasons, including shared genres, cast members, and directors.
- Uses TMDB server-side for optional artwork and details; the API key is never sent to the browser.
- Handles unavailable third-party data gracefully while local recommendations remain available.

This is a **content-based** recommender, not a personalized or collaborative-filtering system: it does not store user accounts, ratings, or viewing history.

## Architecture

```text
Browser → Flask API → Local movie metadata + cosine-similarity model
                         └─ optional server-side TMDB enrichment
```

The local model is loaded once per application process and caches data in memory. Public search routes have an in-memory per-IP rate limit. For a multi-instance production deployment, use a shared rate-limit store such as Redis.

## Tech stack

Python · Flask · pandas · scikit-learn · NumPy · Docker · Gunicorn · TMDB API

## Run locally

Prerequisites: Python 3.12 and a TMDB API key if you want external-title lookup and metadata enrichment.

```bash
git clone https://github.com/KalyanMurapaka45/End-to-End-Movie-Recommendation-System.git
cd End-to-End-Movie-Recommendation-System
python -m venv .venv
```

Activate `.venv` (`.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux), then install dependencies:

```bash
pip install -r requirements.txt
copy .env.example .env  # Windows; use cp on macOS/Linux
python app.py
```

Set `TMDB_API_KEY` in `.env`. Never commit this file. The local catalogue recommendations work without a TMDB key; TMDB-powered enrichment and unknown-title lookup do not.

Visit `http://127.0.0.1:5000` and check `http://127.0.0.1:5000/health` for deployment readiness.

## Run with Docker

```bash
docker build -t moviematch .
docker run --rm -p 5000:5000 --env-file .env moviematch
```

The image uses Gunicorn, runs as a non-root user, excludes local secrets and notebooks from its build context, and exposes port `5000`. Configure your hosting provider with the `TMDB_API_KEY` environment variable rather than uploading `.env`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Deployment checklist

- Rotate any TMDB key that was previously committed or exposed in a browser bundle.
- Set `TMDB_API_KEY` as a host-managed environment variable.
- Confirm `/health` returns `200` after deployment.
- Test a known local title, an unknown title, and behavior with TMDB unavailable.
- Add the production URL, a screenshot/GIF, and data-source attribution before publishing.

## Data and attribution

Movie metadata is stored in the `Artifacts/` directory. TMDB data and images are provided by [The Movie Database (TMDB)](https://www.themoviedb.org/) and are subject to TMDB’s terms of use. This product uses the TMDB API but is not endorsed or certified by TMDB.

## Resume-ready description

> Built and deployed a Flask-based content recommendation system that generates top-10 movie suggestions using cosine similarity over genre, cast, director, and plot metadata; integrated server-side TMDB enrichment for movie artwork and details.

## License

Distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
