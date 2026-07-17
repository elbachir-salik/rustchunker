"""Fairness decomposition for the massive-corpus benchmark.

The headline massive-scale result compares rustchunker's parallel
`chunk_files` against the other libraries run in a sequential Python loop.
That conflates two things: (a) rustchunker's per-core algorithm speed, and
(b) the fact that it uses all cores while the others don't. This script
separates them into a 2x2 -- {rustchunker, competitors} x {1 core, all
cores} -- so the win can be attributed honestly.

- rustchunker @1 core / @all cores: same `chunk_files`, run in a subprocess
  with RAYON_NUM_THREADS pinned to 1 or to the CPU count.
- competitors @1 core: the normal sequential loop (their real default).
- competitors @all cores: the same per-document splitting spread across a
  multiprocessing.Pool -- i.e. what a practitioner would actually do to
  parallelize a pure-Python, GIL-bound splitter. Pool startup (process
  spawn + per-worker import) is included in the timing, as it would be in
  practice.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool, cpu_count

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import LIBRARIES

# Rebuilt in every spawned worker on import, so workers can look a bench
# function up by name (functions themselves aren't passed across processes).
_BENCH = {name: fn for name, _, fn in LIBRARIES}
_COMPETITORS = [name for name, _, _ in LIBRARIES if name != "rustchunker"]
RUNNER = os.path.join(os.path.dirname(__file__), "_rustchunker_runner.py")


def _competitor_worker(task):
    lib_name, paths = task
    return _BENCH[lib_name](paths)[1]  # chunk count only (keep IPC tiny)


def _batches(paths, n):
    k, r = divmod(len(paths), n)
    out, i = [], 0
    for w in range(n):
        size = k + (1 if w < r else 0)
        out.append(paths[i : i + size])
        i += size
    return [b for b in out if b]


def time_competitor_sequential(lib_name, paths):
    return _BENCH[lib_name](paths)  # (seconds, chunks)


def time_competitor_parallel(lib_name, paths, n_workers):
    tasks = [(lib_name, b) for b in _batches(paths, n_workers)]
    start = time.perf_counter()
    with Pool(n_workers) as pool:
        counts = pool.map(_competitor_worker, tasks)
    return time.perf_counter() - start, sum(counts)


def run_rustchunker(data_dir, size, threads):
    env = {**os.environ, "RAYON_NUM_THREADS": str(threads)}
    proc = subprocess.run(
        [sys.executable, RUNNER, "--data-dir", data_dir, "--size", str(size)],
        env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"rustchunker runner failed:\n{proc.stderr}")
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    return data["seconds"], data["chunks"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "massive_data"))
    parser.add_argument("--size", type=int, default=30000)
    parser.add_argument("--workers", type=int, default=cpu_count())
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "bench_massive_parallelism.png"))
    args = parser.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    all_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))
    size = min(args.size, len(all_paths))
    if not all_paths:
        raise SystemExit("No corpus -- run fetch_massive_corpus.py first.")
    paths = all_paths[:size]
    print(f"Decomposition on {size:,} documents, {args.workers} workers.\n", flush=True)

    rows = {}  # library -> (one_core_s, all_core_s)

    r1_s, r1_c = run_rustchunker(args.data_dir, size, threads=1)
    rN_s, rN_c = run_rustchunker(args.data_dir, size, threads=args.workers)
    rows["rustchunker"] = (r1_s, rN_s)
    print(f"rustchunker    1 core={r1_s:8.2f}s   {args.workers} cores={rN_s:8.2f}s   "
          f"self-speedup={r1_s / rN_s:4.1f}x   ({r1_c:,} chunks)", flush=True)

    for name in _COMPETITORS:
        try:
            seq_s, seq_c = time_competitor_sequential(name, paths)
            par_s, par_c = time_competitor_parallel(name, paths, args.workers)
        except ImportError as e:
            print(f"{name}: skipped ({e})", flush=True)
            continue
        rows[name] = (seq_s, par_s)
        print(f"{name:14} 1 core={seq_s:8.2f}s   {args.workers} cores={par_s:8.2f}s   "
              f"self-speedup={seq_s / par_s:4.1f}x   ({seq_c:,} chunks)", flush=True)

    # Derived: rustchunker's advantage at equal core budgets.
    print("\nrustchunker advantage at EQUAL core budget:", flush=True)
    for name in _COMPETITORS:
        if name in rows:
            oc = rows[name][0] / rows["rustchunker"][0]
            ac = rows[name][1] / rows["rustchunker"][1]
            print(f"  vs {name:14} 1-core={oc:4.1f}x   all-core={ac:4.1f}x", flush=True)

    # ---- grouped bar chart: 1-core vs all-core, per library ----
    libs = list(rows)
    x = range(len(libs))
    width = 0.4
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - width / 2 for i in x], [rows[l][0] for l in libs], width, label="1 core", color="#c94c4c")
    ax.bar([i + width / 2 for i in x], [rows[l][1] for l in libs], width, label=f"{args.workers} cores", color="#2b7a78")
    ax.set_xticks(list(x))
    ax.set_xticklabels(libs, rotation=20, ha="right")
    ax.set_ylabel("Time (seconds)")
    ax.set_title(f"1 core vs {args.workers} cores, {size:,} documents")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}", flush=True)


if __name__ == "__main__":
    main()
