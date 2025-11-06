# ⚽ Premier League Data Engineering Pipeline (Azure + Python)

This project extracts Premier League data from BBC and WorldFootball, transforms it with Python, and loads it to Azure Blob Storage and PostgreSQL for analysis in Power BI.

## 🧱 Architecture
BeautifulSoup → Pandas → Azure Blob Storage → Azure PostgreSQL → Power BI  
Automated via GitHub Actions

## 🚀 Tools
- Python (pandas, BeautifulSoup, SQLAlchemy, pyarrow)
- Azure Blob Storage
- Azure PostgreSQL Database
- GitHub Actions

## 📊 Results
- 5 Parquet datasets uploaded to Azure Blob
- 5 Postgres tables for analytical queries
