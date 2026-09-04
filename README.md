# Laptop Intelligence — Web Scraping & Machine Learning Platform

End-to-end application for analyzing the Kaggle laptop dataset, scraping supported retail sites, and running source-specific ML for price prediction, classification, recommendation, and model comparison.

## Architecture

```
Home → Dataset Analysis (Kaggle) ─┐
                                 ├→ Catalog → Prediction → Classification → Recommendation → ML Analysis
Home → Web Scraping (Amazon/…) ──┘
```

Kaggle and scraped sources are stored separately and never overwrite each other:

```
backend/data/kaggle/laptops.csv
backend/data/scraped/amazon/laptops.csv
backend/data/scraped/flipkart/laptops.csv
backend/data/scraped/oneplus/laptops.csv
backend/data/scraped/custom/laptops.csv
```

Models are trained and saved per source under `backend/ml/saved_models/<source>/`.

## Setup

### Backend

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Set-Location backend
python scripts\import_kaggle.py
python ml\train.py
python app.py
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Optional: set `VITE_API_URL` (default `http://127.0.0.1:5000/api`).

## Kaggle dataset

Source: [Laptop Price Prediction](https://www.kaggle.com/datasets/eslamelsolya/laptop-price-prediction)

Place the raw CSV as `backend/data/_kaggle_raw.csv` (already imported in this repo) and run `python scripts/import_kaggle.py` to refresh the normalized file.

## Scraping

Enter an Amazon company name or URL on **Web Scraping**, e.g. `Amazon laptops` or `https://www.amazon.in/`.

- Currently supported live scraping: **Amazon**
- Flipkart / OnePlus: **Coming Soon** (shown in the UI; not selectable as empty sources)
- Unsupported sites return a clear error — no fake products.
- Sites that block automation return a blocked-access message.

## ML algorithms

| Algorithm | Purpose |
|-----------|---------|
| Linear Regression | Price prediction |
| Random Forest Regressor | Price prediction |
| Random Forest Classifier | Budget / Mid Range / Premium |
| KNN | Similar laptop recommendation |

## API (selected)

- `GET /api/datasets/kaggle`
- `GET /api/catalog?source=kaggle`
- `GET /api/stats?source=amazon`
- `POST /api/scrape` `{ "query": "Amazon laptops" }`
- `POST /api/predict-price` `{ "source": "kaggle", ...specs }`
- `POST /api/classify`
- `POST /api/recommend`
- `GET /api/ml-analysis?source=kaggle`

## Tests & build

```powershell
Set-Location backend
python -m pytest tests -q

Set-Location ..\frontend
npm run build
```

## Notes

- Active source is persisted in the frontend (`localStorage`) and sent with API calls.
- Kaggle and scraped CSVs are stored separately; scraping never overwrites the Kaggle dataset.
- Real-world scrapers may be blocked by CAPTCHA / bot protection (Flipkart often returns HTTP 403); the app reports that honestly and never invents products.
- Amazon search phrases like `Amazon laptops` are resolved to a clean `laptops` query on amazon.in.
