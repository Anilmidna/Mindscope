# MindScope — AI Psychometric Assessment Platform

An AI-powered psychometric assessment platform combining scientifically validated scoring (RIASEC + Big Five + Aptitude) with LLM-generated personalized reports.

## Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (Amazon RDS)
- **AI:** Claude Opus (reports) + Sonnet (corrections) via Amazon Bedrock
- **PDF:** Playwright on AWS Lambda + Jinja2 (WeasyPrint fallback for local dev)
- **Storage:** Amazon S3
- **Email:** Amazon SES
- **Auth:** Google OAuth 2.0 + JWT
- **Backend hosting:** AWS ECS Express Mode + ECR
- **Frontend hosting:** S3 + CloudFront (static SPA — `npm run build` → `dist/` → S3 bucket `mindscope-frontend`)

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

## Deployment

### Backend — AWS ECS (Fargate)

CI/CD is fully automated via GitHub Actions (`.github/workflows/deploy.yml`).

**One-time AWS setup (do once before first deploy):**

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name mindscope-api --region us-east-1

# 2. Create ECS cluster
aws ecs create-cluster --cluster-name mindscope --region us-east-1

# 3. Create CloudWatch log groups
aws logs create-log-group --log-group-name /mindscope/api --region us-east-1
aws logs create-log-group --log-group-name /mindscope/bedrock --region us-east-1

# 4. Store secrets in Secrets Manager
aws secretsmanager create-secret --name mindscope/database-url \
  --secret-string "postgresql://user:pass@<rds-endpoint>:5432/mindscope"
aws secretsmanager create-secret --name mindscope/jwt-secret \
  --secret-string "$(openssl rand -base64 48)"
aws secretsmanager create-secret --name mindscope/google-oauth \
  --secret-string '{"client_id":"...","client_secret":"...","redirect_uri":"https://<your-domain>/auth/google/callback"}'
aws secretsmanager create-secret --name mindscope/admin-api-key \
  --secret-string "$(python -c 'import secrets; print(secrets.token_hex(32))')"
# ADMIN_API_KEY gates /admin/* (runtime model switching) and /b2b/* (org/invite creation).
# The app fails closed with 403 if this is unset — but that will silently break those
# endpoints in production, so it must be set before first deploy.

# 5. Register task definition
aws ecs register-task-definition --cli-input-json file://infra/ecs-task-definition.json

# 6. Create ECS service (ALB wiring done separately in console or via CDK)
aws ecs create-service \
  --cluster mindscope \
  --service-name mindscope-api \
  --task-definition mindscope-api \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet-id>],securityGroups=[<sg-id>],assignPublicIp=ENABLED}"
```

**GitHub Actions deploy (automatic on push to `main`):**
- Runs tests → builds Docker image → pushes to ECR → updates ECS service
- Requires GitHub secret `AWS_ROLE_ARN` = `arn:aws:iam::868859238853:role/mindscope-github-actions`

**Run migrations manually (first time or after schema changes):**
```bash
# Exec into a running container, or run a one-off ECS task
alembic upgrade head
```

### Frontend — S3 + CloudFront

The React/Vite SPA is hosted as a static bundle on S3 + CloudFront. No server runtime is needed at request time.

```bash
cd frontend

# 1. Build the production bundle
npm run build   # outputs to frontend/dist/

# 2. Upload to S3 (mindscope-frontend bucket — separate from mindscope-reports)
aws s3 sync dist/ s3://mindscope-frontend --delete

# 3. Invalidate CloudFront cache after every deploy
aws cloudfront create-invalidation --distribution-id <DISTRIBUTION_ID> --paths "/*"
```

**One-time CloudFront setup (do once):**
- Create S3 bucket `mindscope-frontend` (static website hosting or OAC — do NOT share with `mindscope-reports`)
- Create a CloudFront distribution pointing at the bucket
- **SPA routing fix (required):** add a custom error response — HTTP 403/404 → `/index.html`, response code 200. Without this, any hard refresh on a non-root route (e.g. `/dashboard`) will 404.
- **ACM certificate must be in `us-east-1`** regardless of which region the rest of the stack runs in — CloudFront hard requirement.
- Add the CloudFront domain (and custom domain once attached) to the backend's `CORS_ORIGINS` env var.

**Environment variable for the frontend build:**
```
VITE_API_URL=https://<your-ecs-alb-or-domain>
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>
```

### IAM Roles Required

| Role | Purpose |
|---|---|
| `ecsTaskExecutionRole` | Pull ECR images, read Secrets Manager, write CloudWatch logs |
| `mindscope-task-role` | Call Bedrock, read/write S3, send SES email |
| `mindscope-github-actions` | GitHub OIDC role — push ECR, register task definition, update ECS service |

## API Reference

Run `python scripts/export_openapi.py` to regenerate `openapi.json`. The live interactive docs are at `<api-url>/docs` (Swagger UI) and `<api-url>/redoc`.
