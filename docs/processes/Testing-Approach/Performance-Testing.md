# Performance Testing

Performance testing verifies that software meets requirements for responsiveness, stability, and resource usage. For solo developers, a basic approach can
identify issues before they impact users.

## Why It Matters

For solo developers, performance testing:

- Prevents user frustration from slow responses
- Identifies bottlenecks before they become major problems
- Validates that your design can handle expected load
- Helps avoid unexpected issues in production
- Improves overall user experience

## What to Test

Focus your performance testing on:

1. **Critical operations**:
    - Database queries
    - High-traffic API endpoints
    - Computationally intensive operations
    - User-facing transactions

2. **Key metrics to measure**:
    - Response time (average and 95th percentile)
    - Throughput (requests per second)
    - Resource usage (CPU, memory, network)
    - Error rates under load

## Quick Start Guide

1. **Establish baselines**:
    - Measure current performance
    - Set realistic performance targets
    - Create benchmarks for comparison

2. **Use simple tools first**:
    - Browser developer tools for frontend
    - Built-in language profilers (like cProfile for Python)
    - Command-line tools (ab, wrk, siege)

3. **Create realistic scenarios**:
    - Test with production-like data volumes
    - Simulate typical user behavior
    - Start with single user, then increase load

## Example: Basic Load Test

```javascript
// Using k6 for API load testing
import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 10,         // 10 virtual users
  duration: '30s', // for 30 seconds
};

export default function() {
  http.get('https://api.example.com/products');
  sleep(1);  // Wait between requests
}
```

## Example: Query Performance Test

```python
import time

def test_query_performance():
    times = []

    # Run query multiple times
    for _ in range(10):
        start = time.time()
        result = db.execute("SELECT * FROM products WHERE category = 'electronics'")
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    print(f"Average query time: {avg_time:.4f}s")

    # Verify performance meets requirements
    assert avg_time < 0.1, "Query too slow"
```

## Common Performance Issues

- **N+1 query problem**: Making multiple database queries when one would suffice
- **Missing indexes**: Database queries without proper indexing
- **Inefficient algorithms**: Using O(n²) when O(n) would work
- **Memory leaks**: Not releasing resources properly
- **Blocking operations**: Synchronous I/O on main thread

## Recommended Tools

- **k6/Locust**: Modern load testing tools
- **Lighthouse**: Web performance testing
- **Chrome DevTools**: Frontend profiling
- **Language profilers**: cProfile (Python), dotTrace (.NET)
- **Prometheus/Grafana**: Metrics collection and visualization

## Practical Tips

- Start with simple performance tests of critical paths
- Test performance after significant changes
- Use realistic data volumes and scenarios
- Document performance benchmarks over time
- Focus on user-perceived performance first
