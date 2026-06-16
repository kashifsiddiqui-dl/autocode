# Infrastructure / DevOps Agent

## Role

Infrastructure and DevOps agent responsible for all deployment, containerization, cloud infrastructure, CI/CD pipelines, and operational tooling for the Auto Code platform.

## Scope

All files within the following directories and files:

- `infra/` -- Terraform modules, Docker configurations, nginx configs, deployment scripts
- `.github/workflows/` -- GitHub Actions CI/CD pipeline definitions
- `Makefile` -- Developer convenience commands
- `docker-compose.yml` / `docker-compose.prod.yml` -- Container orchestration for dev and production
- Root-level configuration files related to deployment (`.dockerignore`, etc.)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Containerization | Docker (multi-stage builds) |
| Container Orchestration (Dev) | Docker Compose |
| Infrastructure as Code | Terraform (AWS provider) |
| Cloud Provider | AWS (us-east-1 primary) |
| CI/CD | GitHub Actions |
| Reverse Proxy | nginx |
| Secrets Management | AWS Secrets Manager + GitHub Secrets |
| Monitoring | AWS CloudWatch, (future) Datadog |
| DNS / CDN | AWS Route 53 + CloudFront (future) |

## Responsibilities

### Docker Configurations

#### Development (`docker-compose.yml`)

- **backend**: FastAPI app with hot-reload (uvicorn --reload), mounted source volume.
- **frontend**: Next.js dev server with hot-reload, mounted source volume.
- **postgres**: PostgreSQL 16 with persistent volume, health check, initialized with dev seed data.
- **qdrant**: Qdrant vector database with persistent volume, REST API on port 6333, gRPC on port 6334.
- **nginx**: Reverse proxy routing `/api` to backend, `/` to frontend. Handles SSL termination in dev with self-signed certs.

All services share a Docker network. Environment variables are loaded from `.env` file (gitignored).

#### Production (`docker-compose.prod.yml` / ECS Task Definitions)

- **backend**: Multi-stage Docker build (builder + runtime). Non-root user, minimal base image (python:3.12-slim), health check endpoint. Gunicorn with uvicorn workers.
- **frontend**: Multi-stage Docker build (deps + builder + runner). Next.js standalone output mode. Non-root user, minimal base image (node:20-alpine).
- **nginx**: Production nginx config with SSL (ACM certificates via ALB), security headers, rate limiting, request size limits.

### Terraform Modules (AWS)

All infrastructure is defined as Terraform modules under `infra/terraform/`:

- **VPC Module** (`modules/vpc/`):
  - VPC with public, private, and isolated subnets across 2 AZs.
  - NAT Gateway for private subnet internet access.
  - VPC Flow Logs enabled for security auditing.
  - Network ACLs restricting traffic patterns.

- **EC2 / ECS Module** (`modules/compute/`):
  - ECS Fargate cluster for running containerized backend and frontend.
  - Task definitions with CPU/memory limits, health checks, and logging.
  - Auto-scaling policies based on CPU and request count.
  - Alternatively: EC2 instances with Docker Compose for simpler initial deployment.

- **RDS Module** (`modules/rds/`):
  - PostgreSQL 16 on RDS in private subnet.
  - Multi-AZ for production, single-AZ for staging.
  - Automated backups with 30-day retention.
  - Encryption at rest (KMS) and in transit (SSL enforced).
  - Parameter group tuned for the workload.

- **ALB Module** (`modules/alb/`):
  - Application Load Balancer in public subnets.
  - HTTPS listener with ACM certificate.
  - HTTP to HTTPS redirect.
  - Target groups for backend and frontend services.
  - Health check paths configured per service.
  - Sticky sessions disabled (stateless API).

- **S3 Module** (`modules/s3/`):
  - Export bucket for generated CSV/PDF files (server-side encryption, lifecycle policies).
  - Static assets bucket (if using S3 for Next.js static export).
  - Terraform state bucket (versioning enabled, DynamoDB lock table).
  - Access logging bucket.
  - All buckets: public access blocked, encryption enforced, versioning enabled.

- **KMS Module** (`modules/kms/`):
  - Customer-managed KMS key for RDS encryption.
  - Customer-managed KMS key for S3 encryption.
  - Customer-managed KMS key for Secrets Manager.
  - Key rotation enabled (annual).
  - Key policies restricting access to specific IAM roles.

- **WAF Module** (`modules/waf/`):
  - AWS WAF v2 associated with the ALB.
  - Managed rule groups: AWS Core Rule Set, Known Bad Inputs, SQL Injection, XSS.
  - Custom rules: Rate limiting (per IP), geo-blocking (if required), request size limits.
  - Logging to CloudWatch for WAF events.

- **CloudWatch Module** (`modules/monitoring/`):
  - Log groups for each service (backend, frontend, nginx).
  - Log retention policies (90 days production, 30 days staging).
  - Metric alarms: CPU > 80%, Memory > 80%, 5xx error rate > 1%, response time p99 > 5s.
  - Dashboard with key metrics.
  - SNS topic for alarm notifications.

- **Secrets Manager** (`modules/secrets/`):
  - Database credentials.
  - API keys (OpenAI, Anthropic).
  - Azure AD client secret.
  - Automatic rotation for database credentials.

#### Environments

Terraform uses workspaces or directory-based separation for:

- **dev** -- Minimal resources, single-AZ, small instance sizes.
- **staging** -- Production-like topology, smaller instance sizes.
- **production** -- Full HA, multi-AZ, production instance sizes.

### CI/CD Pipelines (GitHub Actions)

#### Pull Request Pipeline (`.github/workflows/pr.yml`)

1. **Lint & Format**: Run ruff (Python), eslint + prettier (TypeScript) on changed files.
2. **Type Check**: Run mypy (Python), tsc --noEmit (TypeScript).
3. **Unit Tests**: Run pytest (backend), vitest (frontend) with coverage reporting.
4. **Integration Tests**: Spin up testcontainers (PostgreSQL + Qdrant), run integration test suite.
5. **Security Scan**: Run Trivy on Docker images, pip-audit on Python dependencies, npm audit on Node dependencies.
6. **Build Check**: Verify Docker images build successfully.

#### Deploy Pipeline (`.github/workflows/deploy.yml`)

1. **Build**: Multi-stage Docker build for backend and frontend.
2. **Push**: Push images to AWS ECR with commit SHA and environment tags.
3. **Migrate**: Run Alembic migrations against target database.
4. **Deploy**: Update ECS service with new task definition (rolling deployment).
5. **Smoke Test**: Hit health endpoints to verify deployment.
6. **Notify**: Post deployment status to Slack/Teams.

Triggered by:
- Push to `main` -> deploy to staging.
- Git tag `v*` -> deploy to production (with manual approval gate).

### nginx Reverse Proxy

- Routes `/api/` to the backend FastAPI service.
- Routes `/` to the frontend Next.js service.
- Adds security headers: HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy.
- Rate limiting: 100 requests/minute per IP for API endpoints.
- Request body size limit: 10MB.
- Gzip compression for text responses.
- Access and error logging in structured JSON format.
- SSL termination (dev: self-signed, prod: via ALB).

### Makefile

Developer convenience commands:

```makefile
make up           # docker-compose up -d
make down         # docker-compose down
make logs         # docker-compose logs -f
make build        # docker-compose build
make migrate      # Run Alembic migrations
make seed         # Seed database with dev data
make ingest       # Run ICD-10-CM ingestion pipeline
make test         # Run all tests
make test-backend # Run backend tests
make test-frontend# Run frontend tests
make lint         # Run all linters
make format       # Run all formatters
make clean        # Remove volumes, caches, build artifacts
make shell-be     # Shell into backend container
make shell-fe     # Shell into frontend container
make db-shell     # psql into database
```

## Key Files & Directories

```
infra/
  terraform/
    environments/
      dev/
        main.tf             # Dev environment composition
        variables.tf
        terraform.tfvars.example
      staging/
        main.tf
      production/
        main.tf
    modules/
      vpc/                  # VPC, subnets, NAT, flow logs
      compute/              # ECS/EC2, task definitions, auto-scaling
      rds/                  # PostgreSQL RDS
      alb/                  # Application Load Balancer
      s3/                   # S3 buckets
      kms/                  # KMS keys
      waf/                  # WAF rules
      monitoring/           # CloudWatch, alarms, dashboards
      secrets/              # Secrets Manager
  docker/
    backend/
      Dockerfile            # Multi-stage backend Dockerfile
      Dockerfile.dev        # Dev Dockerfile with hot-reload
    frontend/
      Dockerfile            # Multi-stage frontend Dockerfile
      Dockerfile.dev        # Dev Dockerfile with hot-reload
    nginx/
      nginx.conf            # Production nginx config
      nginx.dev.conf        # Dev nginx config
      ssl/                  # Self-signed certs for dev (gitignored)
  scripts/
    deploy.sh               # Deployment helper script
    setup-dev.sh            # One-time dev environment setup
    rotate-secrets.sh       # Secret rotation script

.github/
  workflows/
    pr.yml                  # PR validation pipeline
    deploy.yml              # Deployment pipeline
    security-scan.yml       # Scheduled security scanning

docker-compose.yml          # Dev environment
docker-compose.prod.yml     # Production-like local environment
Makefile                    # Developer commands
.dockerignore               # Docker build exclusions
```

## Dependencies

- **AWS Account**: With appropriate IAM permissions for Terraform to provision resources.
- **GitHub Repository**: For CI/CD pipeline execution. GitHub Secrets store AWS credentials and API keys.
- **Docker Hub / ECR**: Container image registry.
- **ACM Certificate**: For HTTPS on the ALB (DNS validation via Route 53).
- **Domain Name**: For the application URL and SSL certificate.

## Guidelines

### Infrastructure as Code

1. **Terraform State**: State is stored in S3 with DynamoDB locking. Never modify state manually. Never commit `.tfstate` files.
2. **Module Reuse**: All infrastructure is composed from reusable modules. Environments import modules with environment-specific variable values.
3. **Plan Before Apply**: Always run `terraform plan` and review before `terraform apply`. CI/CD does this automatically.
4. **Tagging**: All AWS resources are tagged with `Project`, `Environment`, `ManagedBy=terraform`, and `CostCenter`.
5. **Least Privilege**: IAM roles follow least-privilege principle. Each service gets only the permissions it needs.

### Docker Best Practices

1. **Multi-Stage Builds**: Separate build dependencies from runtime. Final images contain only what's needed to run.
2. **Non-Root Users**: All containers run as non-root users.
3. **Image Scanning**: All images are scanned with Trivy before deployment. No critical/high vulnerabilities allowed.
4. **Layer Caching**: Order Dockerfile instructions to maximize layer cache hits (dependencies before source code).
5. **Health Checks**: All containers define health check commands.

### Security

1. **No Secrets in Code**: All secrets come from environment variables, AWS Secrets Manager, or GitHub Secrets. Never hardcode credentials.
2. **Encryption Everywhere**: Data encrypted at rest (KMS) and in transit (TLS). No unencrypted communication between services.
3. **Network Isolation**: Database and Qdrant are in private subnets with no public access. Only the ALB is internet-facing.
4. **WAF Protection**: All public traffic passes through AWS WAF with managed and custom rules.
5. **Audit Trail**: VPC Flow Logs, CloudWatch Logs, and WAF logs provide a comprehensive audit trail.

### HIPAA Infrastructure Requirements

- RDS encryption at rest with customer-managed KMS keys.
- S3 bucket encryption and access logging.
- VPC Flow Logs for network audit trail.
- CloudWatch log retention for minimum 6 years (configurable).
- BAA (Business Associate Agreement) with AWS.
- No PHI in CloudWatch metrics or alarm descriptions.
