# cache.py
import collections
import math

class LRUCache:
    """
    Simple set-associative LRU cache model.
    Indexing based on block address -> set index.
    """

    def __init__(self, size_kb=64, line_size=64, associativity=4):
        self.size_bytes = size_kb * 1024
        self.line_size = line_size
        self.associativity = associativity
        self.num_lines = self.size_bytes // self.line_size
        self.num_sets = max(1, self.num_lines // self.associativity)
        # Each set is an OrderedDict mapping tag -> True. Leftmost = most recent.
        self.sets = [collections.OrderedDict() for _ in range(self.num_sets)]

    def _get_index_tag(self, addr):
        # addr is block number (int)
        set_index = addr % self.num_sets
        tag = addr // self.num_sets
        return set_index, tag

    def access(self, addr):
        """
        Access block address `addr`. Return True if hit, False if miss.
        Updates LRU state.
        """
        si, tag = self._get_index_tag(addr)
        s = self.sets[si]
        if tag in s:
            # hit -> move to end (most recently used)
            s.move_to_end(tag)
            return True
        else:
            # miss -> insert, evict if needed
            if len(s) >= self.associativity:
                # evict least recently used (first key)
                s.popitem(last=False)
            s[tag] = True
            return False

    def stats(self):
        used_lines = sum(len(s) for s in self.sets)
        return {
            "cache_size_bytes": self.size_bytes,
            "line_size": self.line_size,
            "associativity": self.associativity,
            "num_sets": self.num_sets,
            "used_lines": used_lines
        }
