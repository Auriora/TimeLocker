---
title: Testing documentation
doc_type: reference
id: "RM-006"
type: [ readme ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-19
tags: [ readme, testing ]
links:
    tooling: [ ]
---

# Testing Documentation

This area contains current test commands, dependency profiles, and quality-gate
guidance. Point-in-time results belong in CI artifacts, commits, issues, or an
active specification package.

## Test Profiles

### Normal correctness and coverage

```bash
python -m pytest -m "not performance and not stress and not minio"
```

This is the default CI profile. It owns the configured 50 percent coverage
gate, includes mocked S3/MinIO contract tests, and does not contact a live
MinIO service.

### Live MinIO integration

```bash
python -m pytest -m minio --no-cov
```

The `minio` marker identifies only tests that contact a live MinIO service.
Before running this profile, provide these non-production inputs:

- `MINIO_ENDPOINT_URL`, such as `http://127.0.0.1:9000`;
- `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`;
- `MINIO_BUCKET` and `MINIO_REGION`;
- `MINIO_VERIFY_SSL`, set to `false` only for a trusted local HTTP service.

The GitHub Actions MinIO job starts a pinned ephemeral container, waits up to
30 seconds for `/minio/health/live`, creates the test bucket, runs the profile,
and removes the container. Missing configuration or an unavailable service is
a dependency failure; it is never treated as a skip. Coverage is disabled for
this four-test profile because the normal profile owns the repository gate.

### Performance and stress

```bash
python -m pytest -m "performance or stress" --no-cov
```

This opt-in profile is intended for representative performance environments;
it does not own the correctness coverage gate. Run it without coverage because
instrumentation changes timing enough to invalidate performance comparisons.

Selection stress testing separates two signals:

- deterministic repeated-operation correctness runs in the normal profile;
- sustained timing runs in the opt-in profile against a 1.0-second-per-operation
  representative baseline and a 2.0x regression tolerance.

The timing test warms the selection caches, measures 12 fixed operations with a
monotonic clock, and gates on the median. This avoids the previous contract,
which required an absolute iteration count inside a fixed one-minute window and
therefore changed outcome with host load. The baseline represents the slower
supported development observations captured in issue 68; the tolerance absorbs
normal shared-runner variance while still failing a material sustained slowdown.
The observed median, baseline, and tolerance are emitted as test properties.

To reproduce only this contract, run:

```bash
python -m pytest \
  tests/TimeLocker/integration/test_stress_testing.py::TestStressTesting::test_sustained_selection_performance \
  --no-cov -q -s
```

Repeat the command at least three times on a representative host when changing
selection traversal, size estimation, pattern handling, or the threshold. Record
the environment and results in the owning issue rather than this durable guide.

## Local MinIO

Use a disposable MinIO instance or an explicitly approved shared test service.
Never use production credentials or a production bucket. The detailed
[MinIO testing guide](./guide-minio-testing.md) describes environment-based
configuration and manual troubleshooting.

## Other Testing Documents

- [Testing quick start](./quickstart-testing.md)
- [MinIO testing checklist](./checklist-minio-testing.md)
- [MinIO setup summary](./summary-minio-setup.md)
- [Test-plan template](../templates/test-plan.md)
