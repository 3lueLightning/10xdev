"""Deliberately inefficient workload for exercising the profiler fixture.

Lives under scripts/ (the relaxed sandbox) on purpose -- this is a throwaway
perf-repro script, not shipping code, so the gate's naming/size/typing checks
correctly leave it alone. `fib` is the CPU hotspot (naive recursion, no
memoization); `build_big_list` is the memory hog.
"""

from __future__ import annotations


def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def build_big_list(size: int) -> list[int]:
    values: list[int] = []
    for i in range(size):
        values.append(i * i)
    return values


def main() -> None:
    print(fib(35))
    values = build_big_list(15_000_000)
    print(len(values))


if __name__ == "__main__":
    main()
