# Dataset notice

`laptops.csv` currently contains the same **synthetic, development-only** rows
as `sample_laptops_development.csv`, to make the local dashboard and model
workflow runnable. These rows were not scraped from Amazon and must not be
reported as real collected data. Running the scraper replaces `laptops.csv`
with its real, collected output.

Version 1 reads `product_url` values from this same CSV as its stored URL
source. They are intentionally blank in the development sample: no Amazon
URLs were supplied with this project, and the application does not invent any.
