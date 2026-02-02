#!/usr/bin/env python3
"""
Try to connect to the Postgres database using backend/.env settings.
Reports whether you're connected to Docker Postgres or host Postgres.
Run from project root: python check_postgres.py
"""
from pathlib import Path

# Load backend/.env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / "backend" / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # use existing env

import os
import re
import subprocess
import sys

def _pid_listening_on(host: str, port: int) -> int | None:
    """Return PID of process listening on host:port, or None."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        return None
    try:
        # ss -ltnp or lsof -i :port
        out = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return None
        # LINE: LISTEN 0 128 127.0.0.1:5432 0.0.0.0:* users:(("postgres",pid=123,fd=6))
        pattern = rf":{port}\s+.*pid=(\d+)"
        for line in out.stdout.splitlines():
            m = re.search(pattern, line)
            if m:
                return int(m.group(1))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None

def _is_pid_in_docker(pid: int) -> bool:
    """Return True if PID is inside a Docker/containerd cgroup."""
    cgroup_path = Path(f"/proc/{pid}/cgroup")
    if not cgroup_path.exists():
        return False
    try:
        text = cgroup_path.read_text()
        return "docker" in text or "containerd" in text
    except OSError:
        return False

def _infer_from_data_dir(data_dir: str) -> str:
    """Infer Docker vs host from PostgreSQL data_directory."""
    if not data_dir:
        return "unknown"
    # Official Postgres Docker image: /var/lib/postgresql/data
    if data_dir.rstrip("/") == "/var/lib/postgresql/data":
        return "Docker (official image)"
    # Debian/Ubuntu host: /var/lib/postgresql/16/main etc.
    if "/var/lib/postgresql/" in data_dir and "/main" in data_dir:
        return "Host (Debian/Ubuntu style)"
    return "unknown"

def main():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    dbname = os.environ.get("POSTGRES_DB", "real_estate_agent")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")

    print(f"Connecting to Postgres: host={host} port={port} db={dbname} user={user}")
    if not password:
        print("Warning: POSTGRES_PASSWORD is empty (set in backend/.env)")

    try:
        import psycopg
    except ImportError:
        print("Error: psycopg not installed. Run: pip install 'psycopg[binary]'")
        print("  Or from project root: pip install -r backend/requirements.txt")
        sys.exit(1)

    try:
        with psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password or None,
            connect_timeout=5,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                cur.execute("SHOW data_directory;")
                data_dir_row = cur.fetchone()
                data_dir = data_dir_row[0] if data_dir_row else ""
            print("OK: Connected.")
            print(f"    {row[0]}")
            print()
            # 1) Infer from data_directory (reliable for Docker official image vs Debian host)
            inference = _infer_from_data_dir(data_dir)
            print(f"    data_directory: {data_dir}")
            print(f"    => {inference}")
            # 2) If localhost, try to confirm via process cgroup (needs ss -ltnp showing PID)
            pid = _pid_listening_on(host, port)
            if pid is not None:
                in_docker = _is_pid_in_docker(pid)
                print(f"    Process on port {port}: pid={pid}, in Docker cgroup: {in_docker}")
                if in_docker:
                    print("    => You are connected to Postgres running inside Docker.")
                else:
                    print("    => You are connected to Postgres running on the host (not Docker).")
            else:
                if "Docker" in inference:
                    print("    => You are connected to Postgres running inside Docker.")
                elif "Host" in inference:
                    print("    => You are connected to Postgres running on the host (not Docker).")
                else:
                    print("    (Process on port not visible; run with sudo to confirm via cgroup.)")
    except psycopg.OperationalError as e:
        print(f"Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
