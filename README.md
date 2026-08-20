# Laptop Price Analysis and ML Project

An end-to-end student project that collects laptop listings from Amazon India, extracts structured features, trains scikit-learn models, and serves them through a Flask + React dashboard.

## Current repository status

The original repository had a working Selenium/BeautifulSoup scraper draft and a feature helper, but the Flask app, ML code, data, tests, React files, and documentation were empty. The scraper's import was broken (`feature_extractor` vs `feature_extraction`), its RAM/storage extraction confused generic GB values, and it included an automation-masking browser option. These are corrected. No live Amazon scrape was run during development.

`backend/data/sample_laptops_development.csv` is a **clearly labelled synthetic development/testing sample**, not scraped Amazon data. Do not present it as scraped data. To run the dashboard before obtaining real data, copy it to `laptops.csv`; replace it with real scraper output for any analysis you present.

## Architecture

`Stored Amazon India product URLs in CSV → Selenium → Amazon product page → BeautifulSoup/JSON-LD → CSV upsert → ML → Flask API → React dashboard`

- Version 1 reads only `product_url` values already stored in `backend/data/laptops.csv`. It accepts Amazon India product URLs only; it never accepts user-entered or arbitrary URLs. If no stored URLs exist, it returns a clean no-URLs summary.
- Selenium uses an isolated temporary profile per stored URL, explicit page waits, Selenium Manager's compatible driver, and always quits Chrome in `finally`.
- Feature extraction derives brand, RAM, storage, display size, and documented CPU/GPU **tiers**. The tier values are not benchmarks.
- The preprocessing pipeline imputes missing values, scales numeric variables, and one-hot encodes brands inside the train-fitted pipeline to prevent leakage.
- Linear Regression predicts price. Random Forest is saved only as an evaluation comparison—not claimed to be best.
- Logistic Regression predicts project-defined `Budget (<₹50k)`, `Mid-range (<₹90k)`, or `Premium` categories.
- Content recommendations score the requested specification against candidate laptops using cosine similarity over scaled features.

## Install and run

Use two terminals from the project root on Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\data\sample_laptops_development.csv backend\data\laptops.csv
Set-Location backend
python ml\train.py
python app.py
```

In the second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the Vite URL printed by the second command. The backend is `http://localhost:5000`.

The frontend reads `VITE_API_URL` when it is supplied; copy
`frontend/.env.example` to `frontend/.env` only if the backend runs at a
different address. The dashboard's **Start scraping** button calls the
controlled `POST /api/scrape` route, displays a loading state, and refreshes
the catalog only after a successful response.

To scrape stored URLs (sparingly and only where Amazon's terms permit it), first ensure existing catalog rows contain `product_url` values for Amazon India product pages, then run `python scraper\scraper.py` from `backend` or use **Start scraping**. The scraper never invents URLs or accepts user-entered URLs. Existing ASIN/product-URL records are updated; new ones are inserted. Train again if real records change the dataset.

## API

- `GET /api/laptops` — dataset rows
- `GET /api/laptops/<id>` — one row
- `GET /api/stats` — summary values and brands
- `POST /api/predict-price` — six numeric feature fields plus optional `brand`
- `POST /api/classify` — same feature schema; returns category and probability
- `POST /api/recommend` — `ram_gb`, `storage_gb`, `budget`, optional `min_rating`, `brand`
- `POST /api/scrape` — scrape only already-stored Amazon India product URLs; returns total, succeeded, failed, inserted, and updated counts

Example prediction body:

```json
{"ram_gb":16,"storage_gb":512,"processor_score":7,"gpu_score":7,"screen_size":15.6,"rating":4.3,"brand":"ASUS"}
```

## Testing

From `backend` after installing requirements:

```powershell
python -m pytest tests
```

## Limitations

Amazon selectors and access controls can change; this project does not bypass them. Real model quality depends on enough varied, legitimately collected rows; the supplied sample is only for development. Engineered CPU/GPU tiers are simplified, and price bands are project-defined, not industry standards.

## Interview explanation

“I used Selenium only to render search pages and BeautifulSoup to parse listing fields. I transformed raw title text into safe structured features, saved the dataset to CSV, and trained reusable pipelines so preprocessing is fit only on training data. Linear Regression produces a numeric price, Logistic Regression classifies explicitly defined price bands, and cosine similarity ranks laptops closest to a user's requested specification. Flask exposes each capability as an API, while React calls those APIs rather than calculating predictions in the browser.”
