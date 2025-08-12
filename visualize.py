# visualize.py
import os
import matplotlib.pyplot as plt

def plot_latency_vs_throughput(latencies, throughput, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    # For a simple plot we visualize latency distribution and annotate throughput
    plt.figure(figsize=(8,4))
    plt.plot(sorted(latencies), marker='.', linewidth=0.5)
    plt.title(f"Latency Distribution (Throughput: {throughput:.1f} ops/s)")
    plt.xlabel("Sorted Request Index")
    plt.ylabel("Latency (us)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()

def plot_hit_miss_rate(hit_rate, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    plt.figure(figsize=(4,4))
    labels = ['Hit', 'Miss']
    sizes = [hit_rate, 1.0 - hit_rate]
    plt.pie(sizes, labels=labels, autopct='%1.1f%%')
    plt.title("Cache Hit/Miss Rate")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()
