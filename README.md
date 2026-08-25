# Kasi Pitchside

### An end-to-end data engineering platform for PSL analytics and automated sports content creation

Extracts, processes, models, and serves Premier Soccer League (PSL) data — powering automated graphics and content pipelines from raw match data to polished visual assets.

---

## Overview

The platform extracts raw match, fixture, and player logs directly from public PSL endpoints, standardizes raw payloads through a **Medallion architecture**, and loads clean data into a **PostgreSQL dimensional warehouse** built on Kimball modeling principles.

Dedicated SQL analytical views compute complex metrics — form guides, rolling goal trends, defense splits — that automatically feed Python graphics generation scripts, turning raw data into publish-ready content.

---

## Technical Stack

| Layer                   | Technology                                                      |
| ----------------------- | --------------------------------------------------------------- |
| **Language**            | Python 3.11+                                                    |
| **Database Engine**     | PostgreSQL 15+ (Production/Container) · SQLite (Local Fallback) |
| **Ingestion**           | `httpx`, `BeautifulSoup4`, `Playwright`                         |
| **Data Transformation** | `SQLAlchemy 2.0`, `Pandas`                                      |
| **Orchestration**       | Apache Airflow                                                  |
| **Infrastructure**      | Docker & Docker Compose                                         |
| **Graphic Automation**  | Python `Pillow`                                                 |

```
Ingestion → Staging (Bronze) → Warehouse (Gold) → Analytics Views → Graphics Engine
```

---

## Project Structure

```text
SA Football Data Platform/
├── ingestion/                  # Web scrapers & raw payload extractors
│   ├── historical/             # Multi-season historical data loaders
│   ├── live/                   # Weekly match & fixture polling
│   └── sources/                # Base HTTP clients & database connectors
├── transformations/            # ETL transformation scripts
│   ├── staging/                # Raw -> Cleaned Staging records
│   └── warehouse/              # Staging -> Dimensional Fact & Dimension tables
├── warehouse/                  # DDL scripts & database setup
│   ├── dimensions/             # Dimension table definitions
│   ├── facts/                  # Fact table definitions
│   └── schemas/                # System initialization DDL (init_schema.sql)
├── analytics/                  # Analytical SQL views for graphics engine
├── graphics/                   # Automated PIL image generation scripts
│   └── templates/              # Base graphic canvas layouts
├── pipelines/                  # Airflow DAGs for end-to-end scheduling
├── infrastructure/             # Containerization configs (Dockerfile, docker-compose)
├── tests/                      # Pytest unit & data validation suite
├── .gitignore                  # Git tracking rules
├── requirements.txt            # Python dependencies
└── README.md                   # Platform documentation
```

---
