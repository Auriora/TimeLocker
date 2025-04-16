# 3.4.1 Performance

| ID              | Requirement                                                                 | Priority    | Rationale                                                                |
| --------------- | --------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------ |
| **NFR‑PERF‑01** | Application start‑up ≤ 2 s on reference hardware (quad‑core CPU, 8 GB RAM). | Must‑have   | Fast launch improves user experience and meets usability KPI efficiency. |
| **NFR‑PERF‑02** | UI action response ≤ 200 ms.                                                | Must‑have   | Ensures perception of responsiveness.                                    |
| **NFR‑PERF‑03** | Backup throughput ≥ 80 MB/s on local SSD.                                   | Should‑have | Provides efficient backup performance; hardware dependent.               |
| **NFR‑PERF‑04** | CPU usage ≤ 60 % average during backup, with dynamic throttling.            | Should‑have | Prevents resource starvation on user systems.                            |
| **NFR‑AUD‑01**  | Each audit‑log append must complete in ≤ 1 ms on reference hardware.        | Must‑have   | Maintains low overhead for immutable logging.                            |
| **NFR‑AUD‑02**  | Verification of a 10 MB rotated log must finish in ≤ 2 s.                   | Must‑have   | Enables regular tamper checks without user impact.                       |