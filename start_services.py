#!/usr/bin/env python3
"""
start_services.py

Bootstraps and starts the Self-hosted AI Package services.
Refactored for robustness, cross-platform compatibility, and clean code.
"""

import os
import subprocess
import shutil
import time
import argparse
import sys
import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    load_dotenv = None
    set_key = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(cmd: List[str], cwd: Optional[str] = None):
    """Run a shell command and log it."""
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
        raise

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    supabase_dir = Path("supabase")
    if not supabase_dir.exists():
        logger.info("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        run_command(["git", "-C", "supabase", "sparse-checkout", "init", "--cone"])
        run_command(["git", "-C", "supabase", "sparse-checkout", "set", "docker"])
        run_command(["git", "-C", "supabase", "checkout", "master"])
    else:
        if (supabase_dir / ".git").exists():
            logger.info("Supabase repository already exists, updating...")
            run_command(["git", "-C", "supabase", "pull"])
        else:
            logger.info("Supabase directory exists and is fully integrated (no .git folder). Skipping update.")

def generate_supabase_keys() -> Dict[str, str]:
    """Generate secure keys for Supabase similar to their generate-keys.sh script."""
    import base64
    import json
    import hashlib
    import hmac

    def base64_url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

    def gen_token(payload: dict, secret: str) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64_url_encode(json.dumps(header, separators=(',', ':')).encode())
        payload_b64 = base64_url_encode(json.dumps(payload, separators=(',', ':')).encode())

        signed_content = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            secret.encode(),
            signed_content.encode(),
            hashlib.sha256
        ).digest()
        return f"{signed_content}.{base64_url_encode(signature)}"

    jwt_secret = secrets.token_urlsafe(32)
    iat = int(time.time())
    exp = iat + (5 * 365 * 24 * 3600)  # 5 years

    anon_payload = {"role": "anon", "iss": "supabase", "iat": iat, "exp": exp}
    service_payload = {"role": "service_role", "iss": "supabase", "iat": iat, "exp": exp}

    return {
        "JWT_SECRET": jwt_secret,
        "ANON_KEY": gen_token(anon_payload, jwt_secret),
        "SERVICE_ROLE_KEY": gen_token(service_payload, jwt_secret),
        "POSTGRES_PASSWORD": secrets.token_hex(16),
        "DASHBOARD_PASSWORD": secrets.token_hex(16),
        "SECRET_KEY_BASE": secrets.token_urlsafe(48),
        "VAULT_ENC_KEY": secrets.token_hex(16),
        "PG_META_CRYPTO_KEY": secrets.token_urlsafe(24),
        "LOGFLARE_PUBLIC_ACCESS_TOKEN": secrets.token_urlsafe(24),
        "LOGFLARE_PRIVATE_ACCESS_TOKEN": secrets.token_urlsafe(24),
    }

def prepare_supabase_env():
    """Merge root .env with supabase/docker/.env.example and harden defaults."""
    root_env_path = Path(".env")
    example_env = Path("supabase/docker/.env.example")
    target_env = Path("supabase/docker/.env")

    if not example_env.exists():
        logger.warning(f"Supabase example env not found at {example_env}")
        return

    logger.info(f"Preparing Supabase environment at {target_env}")
    
    env_vars: Dict[str, str] = {}

    # 1. Load defaults from .env.example
    with open(example_env, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

    # 2. Check root .env for existing overrides
    root_overrides: Dict[str, str] = {}
    if root_env_path.exists():
        with open(root_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    root_overrides[key] = value

    # 3. Harden secrets if they are missing or still set to insecure defaults in root .env
    insecure_defaults = [
        "your-super-secret-and-long-postgres-password",
        "your-super-secret-jwt-token-with-at-least-32-characters-long",
        "this_password_is_insecure_and_should_be_updated",
        "your-32-character-encryption-key",
        "your-encryption-key-32-chars-min",
        "your-super-secret-and-long-logflare-key-public",
        "your-super-secret-and-long-logflare-key-private"
    ]

    # We only auto-generate if the user hasn't provided a CUSTOM secure alternative in .env
    needs_hardening = False
    for key in ["POSTGRES_PASSWORD", "JWT_SECRET", "DASHBOARD_PASSWORD"]:
        val = root_overrides.get(key)
        if not val or val in insecure_defaults:
            needs_hardening = True
            break

    if needs_hardening:
        logger.info("Insecure or missing Supabase secrets detected. Generating secure replacements...")
        new_keys = generate_supabase_keys()
        for key, val in new_keys.items():
            current_val = root_overrides.get(key)
            if not current_val or current_val in insecure_defaults or key not in root_overrides:
                root_overrides[key] = val
                # Persist to root .env so it's consistent across runs
                if set_key:
                    set_key(str(root_env_path), key, val)
                else:
                    with open(root_env_path, 'a') as f:
                        f.write(f"{key}={val}\n")

    # 4. Merge hardened root overrides into target env
    env_vars.update(root_overrides)

    # 5. Write merged variables to supabase/docker/.env
    target_env.parent.mkdir(parents=True, exist_ok=True)
    with open(target_env, 'w') as f:
        f.write("# Generated by start_services.py - Merged & Hardened configuration\n")
        f.write("# Defaults from supabase/docker/.env.example, overrides from root .env\n\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info(f"Successfully created {target_env}")

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG using Python (cross-platform)."""
    settings_path = Path("searxng/settings.yml")
    settings_base_path = Path("searxng/settings-base.yml")

    if not settings_base_path.exists():
        logger.warning(f"SearXNG base settings not found at {settings_base_path}")
        return

    if not settings_path.exists():
        logger.info(f"Creating {settings_path} from {settings_base_path}")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(settings_base_path, settings_path)

    with open(settings_path, 'r') as f:
        content = f.read()

    if 'ultrasecretkey' in content:
        logger.info("Generating secure SearXNG secret key...")
        new_key = secrets.token_hex(32)
        content = content.replace('ultrasecretkey', new_key)
        with open(settings_path, 'w') as f:
            f.write(content)
        logger.info("SearXNG secret key generated.")

def prepare_moltbot_env():
    """Ensure OPENCLAW_GATEWAY_TOKEN is set in the root .env."""
    root_env_path = Path(".env")
    token_key = "OPENCLAW_GATEWAY_TOKEN"

    if not root_env_path.exists():
        logger.info(f"Creating {root_env_path}...")
        root_env_path.touch()

    token_exists = False
    with open(root_env_path, 'r') as f:
        if f"{token_key}=" in f.read():
            token_exists = True

    if not token_exists:
        logger.info(f"Generating secure {token_key}...")
        new_token = secrets.token_hex(32)
        if set_key:
            set_key(str(root_env_path), token_key, new_token)
        else:
            with open(root_env_path, 'a') as f:
                f.write(f"\n{token_key}={new_token}\n")
        logger.info(f"Persisted {token_key} to {root_env_path}")

def check_searxng_permissions():
    """Check and modify docker-compose.yml for SearXNG first run permissions."""
    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        return

    # Check for initialization file
    uwsgi_config = Path("searxng/uwsgi.ini")
    is_first_run = not uwsgi_config.exists()

    with open(compose_path, 'r') as f:
        content = f.read()

    # Make target more specific to SearXNG service
    target = "searxng:\n    container_name: searxng\n    image: docker.io/searxng/searxng:latest\n    restart: unless-stopped\n    expose:\n      - 8080/tcp\n    volumes:\n      - ./searxng:/etc/searxng:rw\n    environment:\n      - SEARXNG_BASE_URL=https://${SEARXNG_HOSTNAME:-localhost}/\n      - UWSGI_WORKERS=${SEARXNG_UWSGI_WORKERS:-4}\n      - UWSGI_THREADS=${SEARXNG_UWSGI_THREADS:-4}\n    cap_drop:\n      - ALL"
    replacement = "searxng:\n    container_name: searxng\n    image: docker.io/searxng/searxng:latest\n    restart: unless-stopped\n    expose:\n      - 8080/tcp\n    volumes:\n      - ./searxng:/etc/searxng:rw\n    environment:\n      - SEARXNG_BASE_URL=https://${SEARXNG_HOSTNAME:-localhost}/\n      - UWSGI_WORKERS=${SEARXNG_UWSGI_WORKERS:-4}\n      - UWSGI_THREADS=${SEARXNG_UWSGI_THREADS:-4}\n    # cap_drop:  # Temporarily disabled for first run\n      # - ALL"

    if is_first_run and target in content:
        logger.info("First run detected for SearXNG. Temporarily disabling cap_drop...")
        content = content.replace(target, replacement)
        with open(compose_path, 'w') as f:
            f.write(content)
    elif not is_first_run and replacement in content:
        logger.info("SearXNG initialized. Re-enabling cap_drop...")
        content = content.replace(replacement, target)
        with open(compose_path, 'w') as f:
            f.write(content)

def start_services(profile: str, environment: str):
    # Base command for both stacks
    supabase_compose = Path("supabase/docker/docker-compose.yml")
    ai_compose = Path("docker-compose.yml")
    supabase_limits = Path("docker-compose.supabase-limits.yml")
    ai_limits = Path("docker-compose.ai-limits.yml")

    # 1. Start Supabase
    logger.info("Starting Supabase services...")
    supabase_cmd = ["docker", "compose", "-p", "localai", "-f", str(supabase_compose)]

    if supabase_limits.exists():
        logger.info(f"Applying resource limits from {supabase_limits}")
        supabase_cmd.extend(["-f", str(supabase_limits)])

    if environment == "public":
        supabase_cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])

    supabase_cmd.extend(["up", "-d"])
    run_command(supabase_cmd)

    logger.info("Waiting for Supabase to initialize (10s)...")
    time.sleep(10)

    # 2. Start AI Services
    logger.info("Starting Local AI services...")
    ai_cmd = ["docker", "compose", "-p", "localai", "-f", str(ai_compose)]

    if profile and profile != "none":
        ai_cmd.extend(["--profile", profile])

    if ai_limits.exists():
        logger.info(f"Applying resource limits from {ai_limits}")
        ai_cmd.extend(["-f", str(ai_limits)])

    if environment == "private":
        ai_cmd.extend(["-f", "docker-compose.override.private.yml"])
    elif environment == "public":
        ai_cmd.extend(["-f", "docker-compose.override.public.yml"])

    ai_cmd.extend(["up", "-d"])
    run_command(ai_cmd)

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Docker profile (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment type (default: private)')
    args = parser.parse_args()

    try:
        clone_supabase_repo()
        prepare_moltbot_env()
        generate_searxng_secret_key()
        prepare_supabase_env()
        check_searxng_permissions()

        logger.info("Stopping existing project containers...")
        down_cmd = ["docker", "compose", "-p", "localai", "-f", "docker-compose.yml"]
        if args.profile and args.profile != "none":
            down_cmd.extend(["--profile", args.profile])
        down_cmd.extend(["down"])
        run_command(down_cmd)

        start_services(args.profile, args.environment)

        logger.info("All services started successfully!")
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
