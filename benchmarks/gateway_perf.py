"""
Gateway Performance Benchmark

Measures proxy routing overhead with a mock backend.
Asserts:
- p95 latency < 20ms overhead
- Throughput > 1000 req/sec

Usage:
    python benchmarks/gateway_perf.py
    pytest benchmarks/gateway_perf.py -v
"""

import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
from unittest.mock import patch

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from gateway.app import app
from gateway.auth import create_token


# --- Configuration ---

WARMUP_REQUESTS = 50
BENCHMARK_REQUESTS = 2000
CONCURRENCY_LEVELS = [1, 10, 50, 100]
P95_OVERHEAD_THRESHOLD_MS = 20.0
MIN_THROUGHPUT_RPS = 1000


# --- Mock Backend ---


class MockBackendServer:
    """Simulates a backend service with minimal latency."""

    def __init__(self, base_latency_ms: float = 0.1):
        self.base_latency_ms = base_latency_ms
        self.request_count = 0

    async def handle(self, request: httpx.Request) -> httpx.Response:
        """Handle a proxied request with minimal artificial delay."""
        self.request_count += 1
        if self.base_latency_ms > 0:
            await asyncio.sleep(self.base_latency_ms / 1000)
        return httpx.Response(
            status_code=200,
            json={
                "status": "ok",
                "request_num": self.request_count,
                "path": str(request.url.path),
            },
            headers={"content-type": "application/json"},
        )


# --- Helper Functions ---


def create_auth_client() -> TestClient:
    """Create a test client with valid authentication."""
    client = TestClient(app)
    token = create_token({"sub": "bench-user", "scopes": ["read", "write", "admin"]})
    client.headers = {"Authorization": f"Bearer {token}"}
    return client


def measure_single_request(client: TestClient, method: str, path: str, body=None) -> float:
    """Measure latency of a single request in milliseconds."""
    start = time.perf_counter()
    if method == "GET":
        client.get(path)
    elif method == "POST":
        client.post(path, json=body or {})
    end = time.perf_counter()
    return (end - start) * 1000  # Convert to ms


def calculate_percentile(latencies: List[float], percentile: float) -> float:
    """Calculate the given percentile from a list of latencies."""
    sorted_latencies = sorted(latencies)
    index = int(len(sorted_latencies) * percentile / 100)
    return sorted_latencies[min(index, len(sorted_latencies) - 1)]


def calculate_stats(latencies: List[float]) -> dict:
    """Calculate comprehensive statistics from latency measurements."""
    return {
        "count": len(latencies),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(statistics.median(latencies), 3),
        "p50_ms": round(calculate_percentile(latencies, 50), 3),
        "p90_ms": round(calculate_percentile(latencies, 90), 3),
        "p95_ms": round(calculate_percentile(latencies, 95), 3),
        "p99_ms": round(calculate_percentile(latencies, 99), 3),
        "stdev_ms": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0,
    }


# --- Benchmark Functions ---


def benchmark_sequential_latency(mock_backend: MockBackendServer) -> dict:
    """Benchmark sequential request latency to measure pure overhead."""
    client = create_auth_client()
    latencies = []

    with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
        # Warmup
        for _ in range(WARMUP_REQUESTS):
            client.post("/api/v1/scanner/scan", json={"model_id": "bench-model"})

        # Measure
        for _ in range(BENCHMARK_REQUESTS):
            latency = measure_single_request(
                client, "POST", "/api/v1/scanner/scan", {"model_id": "bench-model"}
            )
            latencies.append(latency)

    stats = calculate_stats(latencies)
    # Subtract mock backend latency to get pure gateway overhead
    stats["overhead_p95_ms"] = round(stats["p95_ms"] - mock_backend.base_latency_ms, 3)
    return stats


def benchmark_throughput(mock_backend: MockBackendServer, concurrency: int) -> dict:
    """Benchmark throughput at given concurrency level."""
    client = create_auth_client()
    request_count = BENCHMARK_REQUESTS
    completed = 0
    errors = 0

    with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for _ in range(request_count):
                futures.append(
                    executor.submit(
                        client.post,
                        "/api/v1/scanner/scan",
                        json={"model_id": "bench-model"},
                    )
                )

            for future in as_completed(futures):
                try:
                    response = future.result()
                    if response.status_code == 200:
                        completed += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        elapsed = time.perf_counter() - start_time

    rps = completed / elapsed if elapsed > 0 else 0

    return {
        "concurrency": concurrency,
        "total_requests": request_count,
        "completed": completed,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(rps, 1),
        "error_rate_percent": round((errors / request_count) * 100, 2),
    }


def benchmark_different_routes(mock_backend: MockBackendServer) -> dict:
    """Benchmark different route types to identify slow paths."""
    client = create_auth_client()
    routes = {
        "POST /scanner/scan": ("POST", "/api/v1/scanner/scan", {"model_id": "test"}),
        "GET /scanner/health": ("GET", "/api/v1/scanner/health", None),
        "POST /mcp/inspect": ("POST", "/api/v1/mcp/inspect", {"method": "tools/call", "params": {}}),
        "GET /mcp/health": ("GET", "/api/v1/mcp/health", None),
    }

    results = {}
    with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
        for route_name, (method, path, body) in routes.items():
            latencies = []
            for _ in range(500):
                latency = measure_single_request(client, method, path, body)
                latencies.append(latency)
            results[route_name] = calculate_stats(latencies)

    return results


# --- Pytest Benchmarks ---


@pytest.fixture
def mock_backend_fixture():
    """Provide mock backend for pytest tests."""
    return MockBackendServer(base_latency_ms=0.1)


class TestGatewayPerformance:
    """Performance test assertions."""

    def test_p95_latency_under_threshold(self, mock_backend_fixture):
        """Assert p95 gateway overhead is under 20ms."""
        stats = benchmark_sequential_latency(mock_backend_fixture)
        overhead_p95 = stats["overhead_p95_ms"]
        print(f"\n  p95 overhead: {overhead_p95:.3f}ms (threshold: {P95_OVERHEAD_THRESHOLD_MS}ms)")
        assert overhead_p95 < P95_OVERHEAD_THRESHOLD_MS, (
            f"p95 overhead {overhead_p95:.3f}ms exceeds threshold {P95_OVERHEAD_THRESHOLD_MS}ms"
        )

    def test_throughput_exceeds_minimum(self, mock_backend_fixture):
        """Assert throughput exceeds 1000 req/sec."""
        result = benchmark_throughput(mock_backend_fixture, concurrency=50)
        rps = result["requests_per_second"]
        print(f"\n  Throughput: {rps:.1f} req/sec (minimum: {MIN_THROUGHPUT_RPS})")
        assert rps > MIN_THROUGHPUT_RPS, (
            f"Throughput {rps:.1f} req/sec below minimum {MIN_THROUGHPUT_RPS}"
        )

    def test_no_errors_under_load(self, mock_backend_fixture):
        """Assert zero errors under normal load."""
        result = benchmark_throughput(mock_backend_fixture, concurrency=10)
        error_rate = result["error_rate_percent"]
        print(f"\n  Error rate: {error_rate:.2f}%")
        assert error_rate == 0, f"Error rate {error_rate}% is non-zero under normal load"

    def test_latency_consistency_across_routes(self, mock_backend_fixture):
        """Assert all routes have similar performance characteristics."""
        results = benchmark_different_routes(mock_backend_fixture)
        p95_values = [stats["p95_ms"] for stats in results.values()]
        max_variance = max(p95_values) - min(p95_values)
        print(f"\n  Route p95 variance: {max_variance:.3f}ms")
        # All routes should be within 10ms of each other
        assert max_variance < 10.0, (
            f"Route latency variance {max_variance:.3f}ms is too high"
        )

    def test_throughput_scales_with_concurrency(self, mock_backend_fixture):
        """Assert throughput increases with concurrency (up to a point)."""
        results = {}
        for concurrency in [1, 10, 50]:
            result = benchmark_throughput(mock_backend_fixture, concurrency=concurrency)
            results[concurrency] = result["requests_per_second"]
            print(f"\n  Concurrency {concurrency}: {results[concurrency]:.1f} req/sec")
        # Higher concurrency should yield higher throughput
        assert results[10] > results[1], "Throughput should increase from concurrency 1 to 10"

    def test_sustained_load_no_degradation(self, mock_backend_fixture):
        """Assert no performance degradation over sustained load."""
        client = create_auth_client()
        batch_size = 200
        batches = 5
        batch_latencies = []

        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend_fixture.handle):
            for batch in range(batches):
                latencies = []
                for _ in range(batch_size):
                    latency = measure_single_request(
                        client, "POST", "/api/v1/scanner/scan", {"model_id": "test"}
                    )
                    latencies.append(latency)
                batch_latencies.append(statistics.mean(latencies))
                print(f"\n  Batch {batch + 1} mean: {batch_latencies[-1]:.3f}ms")

        # Last batch shouldn't be significantly slower than first
        degradation = batch_latencies[-1] - batch_latencies[0]
        assert degradation < 5.0, (
            f"Performance degraded by {degradation:.3f}ms over sustained load"
        )


# --- CLI Runner ---


def run_full_benchmark():
    """Run full benchmark suite and print results."""
    print("=" * 70)
    print("GATEWAY PERFORMANCE BENCHMARK")
    print("=" * 70)

    mock_backend = MockBackendServer(base_latency_ms=0.1)

    # 1. Sequential latency
    print("\n[1/4] Sequential Latency (pure overhead measurement)")
    print("-" * 50)
    stats = benchmark_sequential_latency(mock_backend)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    p95_pass = stats["overhead_p95_ms"] < P95_OVERHEAD_THRESHOLD_MS
    print(f"\n  ✓ p95 overhead: {stats['overhead_p95_ms']:.3f}ms < {P95_OVERHEAD_THRESHOLD_MS}ms"
          if p95_pass else
          f"\n  ✗ p95 overhead: {stats['overhead_p95_ms']:.3f}ms >= {P95_OVERHEAD_THRESHOLD_MS}ms")

    # 2. Throughput at various concurrency levels
    print("\n[2/4] Throughput Benchmark")
    print("-" * 50)
    throughput_pass = False
    for concurrency in CONCURRENCY_LEVELS:
        result = benchmark_throughput(mock_backend, concurrency)
        rps = result["requests_per_second"]
        status = "✓" if rps > MIN_THROUGHPUT_RPS else "✗"
        print(f"  {status} Concurrency={concurrency}: {rps:.1f} req/sec "
              f"(errors: {result['errors']}, elapsed: {result['elapsed_seconds']:.2f}s)")
        if rps > MIN_THROUGHPUT_RPS:
            throughput_pass = True

    # 3. Per-route analysis
    print("\n[3/4] Per-Route Latency Analysis")
    print("-" * 50)
    route_results = benchmark_different_routes(mock_backend)
    for route, stats in route_results.items():
        print(f"  {route}:")
        print(f"    p50={stats['p50_ms']:.3f}ms  p95={stats['p95_ms']:.3f}ms  p99={stats['p99_ms']:.3f}ms")

    # 4. Summary
    print("\n[4/4] Summary")
    print("-" * 50)
    print(f"  p95 overhead < {P95_OVERHEAD_THRESHOLD_MS}ms: {'PASS' if p95_pass else 'FAIL'}")
    print(f"  Throughput > {MIN_THROUGHPUT_RPS} req/sec: {'PASS' if throughput_pass else 'FAIL'}")
    print(f"  Overall: {'PASS' if (p95_pass and throughput_pass) else 'FAIL'}")
    print("=" * 70)

    return p95_pass and throughput_pass


if __name__ == "__main__":
    success = run_full_benchmark()
    exit(0 if success else 1)
