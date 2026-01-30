# Architecture Audit Report: Self-hosted AI Package

## 1. Executive Summary
This report provides a comprehensive audit of the Self-hosted AI Package prototype. While the system successfully orchestrates a complex stack of 20+ services (Supabase + AI tools), it currently suffers from critical stability issues due to resource over-subscription and security risks from default configuration patterns.

## 2. Architecture Audit

### 2.1 Service Density vs. Hardware Constraints
The system is currently deployed on a VPS with **2 vCPUs** and **8GB RAM**.
- **Issue:** Running 20+ containers without strict resource limits on a 2-core system leads to CPU load averages exceeding 9.0 (as observed in VPS logs).
- **Impact:** System instability, slow response times, and potential OOM (Out of Memory) kills.

### 2.2 Security & Secret Management
- **Insecure Defaults:** The `start_services.py` script relies on `supabase/docker/.env.example` which contains static, public secrets. If users don't manually override every secret, the system remains vulnerable.
- **Docker Socket Exposure:** `moltbot` and `supabase-analytics` mount `/var/run/docker.sock`. This provides root-level access to the host if these containers are compromised.
- **Plain-text Credentials:** Many services store credentials in plain-text environment variables within the Docker Compose files.

### 2.3 Reliability & Bootstrapping
- **Runtime Dependencies:** Cloning the Supabase repository during initialization (`start_services.py`) introduces a dependency on external network conditions and GitHub availability.
- **Brittle Orchestration:** Sequential startup logic in Python is a good start but lacks robust error recovery and state management.

## 3. Technical Debt Identification
- **Resource Limits:** Total lack of CPU and memory limits for the majority of the Supabase stack.
- **Type Safety:** Minimal use of static typing in Python scripts, making them harder to maintain as they grow.
- **Duplication:** Configuration logic is fragmented across multiple override files, making it difficult to trace the final state.
- **Testing:** Zero automated tests for the bootstrapping and configuration logic.

## 4. Refactoring Plan (Modern Standards)

### Phase 1: Stability & Security (Immediate)
1.  **Strict Resource Governance:** Implement a universal `docker-compose.resource-limits.yml` to cap every service's CPU and Memory usage.
2.  **Automated Secret Hardening:** Enhance `start_services.py` to detect and replace insecure default secrets with cryptographically secure random values during the first run.
3.  **Health-Driven Orchestration:** Add robust health checks to all core services (Postgres, Kong, n8n, Ollama) and use `depends_on: { condition: service_healthy }` more effectively.

### Phase 2: Modernization (Short-term)
1.  **TypeScript Migration:** Port `start_services.py` and `n8n_pipe.py` to TypeScript. Use `oclif` for the CLI and `Zod` for strict configuration validation.
2.  **Next.js Management Dashboard:** Develop a lightweight web UI to replace the CLI, allowing users to monitor service health, view logs, and manage secrets.
3.  **Secret Store Integration:** Move away from `.env` files towards a local secret store (e.g., Infisical or encrypted Vault).

### Phase 3: Scaling & Enterprise Readiness (Long-term)
1.  **Infrastructure as Code (IaC):** Provide Terraform/Pulumi templates for one-click deployment to major cloud providers.
2.  **Kubernetes Support:** Develop Helm charts for users needing high availability and horizontal scaling.
3.  **CI/CD Pipelines:** Implement automated testing for the entire stack's initialization and basic functionality.

## 5. Priority File Changes
- `start_services.py`: Security hardening and resource limit support.
- `docker-compose.resource-limits.yml`: (New) Centralized resource control.
- `docker-compose.yml`: Health check implementation and deduplication.
- `TECHNICAL_GUIDE.md`: Comprehensive documentation update.
