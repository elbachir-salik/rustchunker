"""Massive-scale real-corpus benchmark: how each chunking library behaves
as the number of real documents grows to 10^4 and 10^5.

Uses the unique real-document corpus built by fetch_massive_corpus.py.
Runs every library at every size (this is slow -- the sequential
pure-Python libraries can take tens of minutes at 10^5 -- so run it in the
background). Results are printed incrementally and dumped to JSON as they
complete, so a partial run still yields usable data.
"""
import argparse
import glob
import json
import os
import sys
import traceback

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import LIBRARIES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "massive_data"))
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "bench_massive_scaling.png"))
    parser.add_argument("--results", default=os.path.join(os.path.dirname(__file__), "bench_massive_scaling.json"))
    args = parser.parse_args()

    all_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))
    if not all_paths:
        raise SystemExit(
            f"No files in {args.data_dir}. Run `python benchmarks/fetch_massive_corpus.py` first."
        )

    sizes = [s for s in sorted(args.sizes) if s <= len(all_paths)]
    if max(args.sizes) > len(all_paths):
        print(f"NOTE: only {len(all_paths):,} files available; capping sizes to {sizes}.")

    results = []  # {library, size, seconds, chunks, docs_per_sec}

    # size-outer so the cheap sizes complete (and are saved) before the
    # expensive 10^5 runs that dominate wall-clock.
    for size in sizes:
        paths = all_paths[:size]
        print(f"\n===== {size:,} documents =====", flush=True)
        for name, _, bench_fn in LIBRARIES:
            try:
                elapsed, chunks = bench_fn(paths)
            except ImportError as e:
                print(f"  {name}: skipped (not installed: {e})", flush=True)
                continue
            except Exception:
                print(f"  {name}: ERROR\n{traceback.format_exc()}", flush=True)
                continue
            dps = size / elapsed if elapsed > 0 else float("inf")
            print(f"  {name:24} {elapsed:9.2f}s  ({chunks:,} chunks, {dps:,.0f} docs/s)", flush=True)
            results.append(
                {"library": name, "size": size, "seconds": elapsed, "chunks": chunks, "docs_per_sec": dps}
            )
            with open(args.results, "w") as f:
                json.dump(results, f, indent=2)

    # ---- chart: time vs document count, log-log, one line per library ----
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, color, _ in LIBRARIES:
        pts = [(r["size"], r["seconds"]) for r in results if r["library"] == name]
        if len(pts) >= 1:
            xs, ys = zip(*sorted(pts))
            ax.plot(xs, ys, marker="o", label=name, color=color)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of real documents")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Chunking-library scaling on a massive real corpus")
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}\nResults saved to {args.results}")


if __name__ == "__main__":
    main()
