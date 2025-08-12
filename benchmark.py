# benchmark.py
import os
import json
import time
import threading
import numpy as np
from cache import LRUCache

class MemoryModel:
    def __init__(self, dram_ns=100, sram_ns=10, flash_ns=500, cache: LRUCache = None):
        self.dram_ns = dram_ns
        self.sram_ns = sram_ns
        self.flash_ns = flash_ns
        self.cache = cache

    def access(self, block_addr):
        """
        Simulate an access to block_addr (integer).
        If cache enabled and hit -> sram latency, else DRAM (or flash based on addr heuristic).
        Return latency in microseconds for convenience.
        """
        # Simple heuristic: blocks < 0.8*working_set -> DRAM hot, else flash cold
        # But for this benchmark we will not encode working set here; caller determines.
        if self.cache:
            hit = self.cache.access(block_addr)
            if hit:
                return self.sram_ns / 1000.0  # us
            else:
                # miss -> DRAM latency
                return self.dram_ns / 1000.0
        else:
            return self.dram_ns / 1000.0

class BenchmarkRunner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg["benchmark"].get("random_seed", None))
        cache_cfg = cfg["cache"]
        self.cache = None
        if cache_cfg.get("enabled", True):
            self.cache = LRUCache(
                size_kb=cache_cfg.get("size_kb", 64),
                line_size=cache_cfg.get("line_size_bytes", 64),
                associativity=cache_cfg.get("associativity", 4),
            )
        mem_cfg = cfg["memory"]
        self.mem = MemoryModel(
            dram_ns=mem_cfg.get("dram_latency_ns", 100),
            sram_ns=mem_cfg.get("sram_latency_ns", 10),
            flash_ns=mem_cfg.get("flash_latency_ns", 500),
            cache=self.cache
        )
        self.working_set_kb = cfg["benchmark"].get("working_set_kb", 1024)
        # create block space (block per cache line)
        self.line_size = cfg["cache"].get("line_size_bytes", 64)
        self.num_blocks = max(1, (self.working_set_kb * 1024) // self.line_size)
        self.num_requests = cfg["benchmark"].get("num_requests", 10000)
        self.num_threads = cfg["benchmark"].get("num_threads", 4)
        self.read_ratio = cfg["benchmark"].get("read_ratio", 0.8)
        self.access_pattern = cfg["benchmark"].get("access_pattern", "mixed")
        self.results_lock = threading.Lock()
        self.latencies = []
        self.hits = 0
        self.misses = 0

    def _generate_address(self):
        if self.access_pattern == "sequential":
            # simple sequential pointer with wrap
            addr = getattr(self, "_seq_ptr", 0)
            self._seq_ptr = (addr + 1) % self.num_blocks
            return addr
        elif self.access_pattern == "random":
            return int(self.rng.integers(0, self.num_blocks))
        else:  # mixed: mostly sequential with some random
            if self.rng.random() < 0.8:
                return self._generate_mostly_sequential()
            else:
                return int(self.rng.integers(0, self.num_blocks))

    def _generate_mostly_sequential(self):
        # small stride across working set
        addr = getattr(self, "_seq_ptr", 0)
        stride = 1
        self._seq_ptr = (addr + stride) % self.num_blocks
        return addr

    def _worker(self, requests_per_thread):
        local_latencies = []
        local_hits = 0
        local_misses = 0
        for _ in range(requests_per_thread):
            addr = self._generate_address()
            latency_us = self.mem.access(addr)
            local_latencies.append(latency_us)
            # Note: LRUCache.access updates state and returns hit bool
            if self.cache:
                # determine hit or miss by attempting to access but we already did in mem.access
                # We'll cheat slightly: call cache.access once more would mutate; instead track by testing presence
                # But LRUCache doesn't expose presence; so replicate logic: call access and treat result as ground-truth
                # To avoid double mutation, we can instrument LRUCache.access return; since mem.access called it already,
                # we'll approximate hit/miss by comparing latency value (sram_ns -> hit)
                if latency_us * 1000.0 == self.mem.sram_ns:
                    local_hits += 1
                else:
                    local_misses += 1
            else:
                local_misses += 1

        with self.results_lock:
            self.latencies.extend(local_latencies)
            self.hits += local_hits
            self.misses += local_misses

    def run(self):
        threads = []
        per_thread = self.num_requests // self.num_threads
        start = time.time()
        for _ in range(self.num_threads):
            t = threading.Thread(target=self._worker, args=(per_thread,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        end = time.time()

        total = len(self.latencies)
        avg_latency = sum(self.latencies) / total if total else 0
        throughput = total / (end - start) if (end - start) > 0 else 0
        hit_rate = (self.hits / (self.hits + self.misses)) if (self.hits + self.misses) else 0

        summary = {
            "total_requests": total,
            "avg_latency_us": avg_latency,
            "throughput_ops_per_sec": throughput,
            "hit_rate": hit_rate,
            "duration_s": end - start
        }
        return summary, self.latencies

    def save_results(self, summary, out_cfg):
        os.makedirs(out_cfg.get("results_dir", "results"), exist_ok=True)
        path = os.path.join(out_cfg.get("results_dir", "results.json"))
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        return path
