# main.py
import json
import os
from benchmark import BenchmarkRunner
from visualize import plot_latency_vs_throughput, plot_hit_miss_rate

def load_config(path="config.json"):
    with open(path, "r") as f:
        return json.load(f)

def main():
    cfg = load_config("config.json")
    runner = BenchmarkRunner(cfg)
    print("Starting benchmark with config:", cfg["benchmark"])
    summary, latencies = runner.run()
    results_path = runner.save_results(summary, cfg["output"])
    print("Benchmark Summary:", summary)
    print("Results saved to:", results_path)

    # Plots
    plot_latency_vs_throughput(latencies, summary["throughput_ops_per_sec"], cfg["output"].get("latency_plot", "results/latency_vs_throughput.png"))
    plot_hit_miss_rate(summary["hit_rate"], cfg["output"].get("hitmiss_plot", "results/hit_miss_rate.png"))
    print("Plots saved in results/")

if __name__ == "__main__":
    main()
