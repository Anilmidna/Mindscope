# MindScope — AI Psychometric Assessment Platform

An AI-powered psychometric assessment platform combining scientifically validated scoring (RIASEC + Big Five + Aptitude) with LLM-generated personalized reports.

## Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (Amazon RDS)
- **AI:** Claude Sonnet via Amazon Bedrock
- **PDF:** WeasyPrint + Jinja2
- **Storage:** Amazon S3
- **Email:** Amazon SES
- **Auth:** Google OAuth 2.0 + JWT
- **Hosting:** AWS App Runner
- **Frontend:** React / HTML + Tailwind

## Project Structure

```
mindscope/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── routers/             # API route handlers
│   ├── models/              # SQLAlchemy DB models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic (scoring, PDF, LLM)
│   ├── db/                  # DB session, migrations config
│   └── core/                # Config, security, dependencies
├── scoring/                 # Psychometric scoring engines
│   ├── riasec.py
│   ├── bigfive.py
│   └── aptitude.py
├── templates/               # Jinja2 HTML report templates
│   └── report_default.html
├── static/                  # CSS + assets
│   └── report.css
├── tests/                   # pytest test suite
├── alembic/                 # DB migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Branch Strategy

- `main` — production-ready code only; protected branch
- `dev` — integration branch; all features merged here first
- `feature/<name>` — individual feature branches off `dev`
- `hotfix/<name>` — urgent fixes branched off `main`

## Getting Started

```bash
# 1. Clone and set up environment
git clone https://github.com/Anilmidna/Mindscope.git
cd Mindscope
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Copy env file and fill in values
cp .env.example .env

# 3. Run locally
uvicorn app.main:app --reload
```

## Environment Variables

See `.env.example` for all required variables.
