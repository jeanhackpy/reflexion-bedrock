# Technical Guide: Self-hosted AI Package

## Overview
This package is a comprehensive, self-hosted AI stack designed for building RAG (Retrieval-Augmented Generation) applications and AI agents locally. It leverages Docker Compose for orchestration and Caddy for secure networking.

## Service Architecture

### Logic & Automation
- **n8n:** The primary engine for AI workflows. It connects to various tools and databases to execute complex agentic logic.
- **Flowise:** Specialized in building LangChain-based agents with a drag-and-drop interface.

### Database & Storage
- **Supabase (PostgreSQL/pgvector):** Used for relational data, user authentication, and vector storage for RAG.
- **Qdrant:** A high-performance vector database, often used as an alternative or supplement to Supabase for large-scale vector search.
- **Neo4j:** A graph database for implementing GraphRAG and managing complex data relationships.

### AI Engine
- **Ollama:** Manages and serves local LLMs (e.g., Qwen, Llama) and embedding models (e.g., Nomic Embed).
- **Moltbot:** An AI gateway that provides an OpenAI-compatible API for the local Ollama models, allowing easy integration with tools that expect the OpenAI format.

### User Interface
- **Open WebUI:** A feature-rich chat interface for interacting with LLMs and n8n pipes.
- **LobeChat:** A modern AI chat UI with support for various providers and plugins.

### Networking & Search
- **Caddy:** Acts as a reverse proxy, providing automated SSL/TLS via Let's Encrypt and routing external hostnames to internal Docker services.
- **SearXNG:** A privacy-preserving metasearch engine used by AI agents to perform web searches without tracking.

### Observability
- **Langfuse:** Provides tracing and monitoring for LLM calls, helping developers debug and optimize AI workflows.

## Networking Configuration
Services are connected via a shared Docker network. Caddy handles incoming traffic on ports 80 and 443 and routes it based on the `HOSTNAME` environment variables defined in the `.env` file.

| Service | Internal Port | Default Hostname (Local) |
|---------|---------------|---------------------------|
| n8n | 5678 | :8001 |
| Open WebUI | 8080 | :8002 |
| Supabase | 8000 (Kong) | :8005 |
| Ollama | 11434 | :8004 |
| SearXNG | 8080 | :8006 |
| Moltbot | 18789 | :8009 |
| LobeChat | 3210 | :8010 |

## Resource Management
Given the high density of services (20+ containers), the package includes a `docker-compose.resource-limits.yml` file. This file enforces strict CPU and Memory caps on every service to ensure stability on smaller VPS instances (e.g., 2 vCPU, 8GB RAM).

- **Ollama:** Capped at 3GB RAM and 1.5 vCPU to allow heavy inference without crashing the host.
- **Supabase DB:** Capped at 768MB RAM.
- **Microservices:** Most support services (Auth, Rest, Kong) are capped at 128MB RAM and 0.1 vCPU.

To adjust these limits, modify `docker-compose.resource-limits.yml` before running `start_services.py`.

## Security Best Practices
1. **Automated Secret Hardening:** The `start_services.py` script automatically detects insecure default secrets (like those in `.env.example`) and replaces them with secure random values on the first run.
2. **Secret Management:** Always use unique, strong passwords. Never commit your `.env` file to version control.
3. **Access Control:** Use the `public` environment profile to expose only ports 80/443 via Caddy, keeping all other service ports internal to the Docker network.
4. **Docker Socket Security:** Some services (Moltbot, Analytics) require access to `/var/run/docker.sock`. Use this with caution and ensure these services are not exposed directly to the internet.
5. **Database Security:** Avoid using special characters like `@` in the Postgres password to prevent connection string parsing issues.
6. **Local Execution:** All AI processing happens locally by default, ensuring your data never leaves your infrastructure.

## Development & Bootstrapping
The `start_services.py` script automates the initialization of the stack:
- Merging environment variables from `.env` and `.env.example`.
- Generating required secrets (SearXNG key, Moltbot token).
- Cloning and configuring the Supabase repository.
- Orchestrating the sequential startup of database and AI services.
