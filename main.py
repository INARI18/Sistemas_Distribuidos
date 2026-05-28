"""Entry point for the SUS data integration simulation.

Usage:
    python main.py
    python main.py --posts 8 --consultations 500 --seed 7

Acts as the composition root: it builds the configuration, runs Scenario A
and prints the resulting metrics report.
"""

from __future__ import annotations

import argparse

from src.config import SimulationConfig
from src.simulation import ScenarioA


def parse_args() -> SimulationConfig:
    parser = argparse.ArgumentParser(description="SUS Scenario A simulation")
    parser.add_argument("--posts", type=int, default=5, help="number of health posts")
    parser.add_argument("--consultations", type=int, default=200,
                        help="consultations generated per post")
    parser.add_argument("--seed", type=int, default=42, help="base random seed")
    args = parser.parse_args()
    return SimulationConfig(
        post_count=args.posts,
        consultations_per_post=args.consultations,
        base_seed=args.seed,
    )


def main() -> None:
    config = parse_args()
    report = ScenarioA(config).run()
    print(report.render())


if __name__ == "__main__":
    main()
