# HECE/src/hece/discover.py
"""Command line entry point for inventor mode:  python -m hece.discover "your goal" --iterations 12"""
import argparse

from dotenv import load_dotenv

from hece.explorer import DiscoveryConfig
from hece.pipeline import run_discovery


def main(argv=None) -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="HECE inventor mode: explore many mechanisms for a goal.")
    parser.add_argument("goal", help="the problem to solve, e.g. 'reduce the energy consumption of seawater desalination'")
    parser.add_argument("--name", default="Discovery", help="project name (used in the report file name)")
    parser.add_argument("--iterations", type=int, default=12, help="maximum number of attempts")
    parser.add_argument("--target", type=int, default=2, help="stop after this many ACTIVE candidates")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducible recombination")
    parser.add_argument("--no-new-physics", action="store_true", help="forbid postulating new quantities or laws")
    parser.add_argument("--no-rag", action="store_true", help="do not search arXiv; use only the model's own knowledge")
    parser.add_argument("--requirement", action="append", default=None,
                        help="a physical requirement you define (repeat the option for several); skips the model-derived ones")
    parser.add_argument("--minutes", type=float, default=None, help="optional time limit in minutes")
    args = parser.parse_args(argv)

    config = DiscoveryConfig(max_iterations=args.iterations, target_count=args.target, seed=args.seed,
                             allow_new_physics=not args.no_new_physics, max_minutes=args.minutes)
    run = run_discovery(args.name, args.goal, config, use_rag=not args.no_rag, on_event=print,
                        requirements=args.requirement)

    print("\n" + run.conclusion)
    print(f"\n[+] Exploration log: {run.json_path}")
    if run.pdf_path:
        print(f"[+] Report: {run.pdf_path}")


if __name__ == "__main__":
    main()
