"""Orquestra duas execuções de containers (Cenário A, depois Cenário B) sobre os mesmos dados, 
depois lê os dois relatórios que o container ``sus-database`` salvou.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from src.metrics import ComparisonReport, write_comparison

REPORTS_DIR = "reports"
REPORT_A = os.path.join(REPORTS_DIR, "report-scenario-a.json")
REPORT_B = os.path.join(REPORTS_DIR, "report-scenario-b.json")


def _load_dotenv(path: str = ".env") -> None:
    """Le as variaveis do .env"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.split("#", 1)[0].strip() 
            if key and key not in os.environ:
                os.environ[key] = value


def _compose(args: list[str], env: dict, profile: str | None = None) -> None:
    """Executa um comando ``docker compose``, levantando exceção se falhar."""
    cmd = ["docker", "compose"]
    if profile:
        cmd += ["--profile", profile]
    cmd += args
    subprocess.run(cmd, check=True, env={**os.environ, **env})

def _container_id(env: dict, profile: str | None, service: str) -> str:
    cmd = ["docker", "compose"]
    if profile:
        cmd += ["--profile", profile]
    cmd += ["ps", "-q", service]
    out = subprocess.run(
        cmd, check=True, env={**os.environ, **env}, capture_output=True, text=True
    )
    return out.stdout.strip()


def _run_scenario(label: str, env: dict, profile: str | None) -> None:
    """Sobe um cenário, aguarda o banco de dados finalizar, depois derruba."""
    print(f"\n=== Running {label} (containers) ===", flush=True)
    _compose(["up", "-d", "--build"], env, profile)
    try:
        cid = _container_id(env, profile, "sus-database")
        subprocess.run(["docker", "wait", cid], check=True)
        subprocess.run(["docker", "logs", cid], check=False)
    finally:
        _compose(["down", "-v"], env, profile)


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    _load_dotenv()   # faz o .env valer também para o main.py, não só para o compose

    posts = int(os.environ.get("POSTS", "5"))
    consultations = int(os.environ.get("CONSULTATIONS", "200"))
    base_seed = int(os.environ.get("BASE_SEED", "42"))
    coverage = float(os.environ.get("COVERAGE", "0.9"))
    idle_timeout = os.environ.get("IDLE_TIMEOUT", "5")

    shared = {
        "POSTS": str(posts),
        "CONSULTATIONS": str(consultations),
        "BASE_SEED": str(base_seed),
        "IDLE_TIMEOUT": str(idle_timeout),
    }

    if os.environ.get("RUN_SCENARIOS", "1") != "0":
        _run_scenario("Scenario A", {**shared, "SCENARIO": "A"}, profile=None)
        _run_scenario(
            "Scenario B",
            {**shared, "SCENARIO": "B", "COVERAGE": str(coverage)},
            profile="scenario-b",
        )

    if not (os.path.exists(REPORT_A) and os.path.exists(REPORT_B)):
        sys.exit(
            f"Missing reports. Expected {REPORT_A} and {REPORT_B}.\n"
            "Run the scenarios first (or unset RUN_SCENARIOS=0)."
        )

    comparison = ComparisonReport(
        report_a=_load(REPORT_A),
        report_b=_load(REPORT_B),
        posts=posts,
        consultations_per_post=consultations,
        base_seed=base_seed,
        coverage=coverage,
    )

    print("\n" + comparison.render() + "\n", flush=True)

    try:
        paths = write_comparison(comparison, REPORTS_DIR, "report-comparison")
        print(f"[compare] comparison written to: {', '.join(paths)}", flush=True)
    except OSError as exc:
        print(f"[compare] could not write comparison files: {exc}", flush=True)


if __name__ == "__main__":
    main()
