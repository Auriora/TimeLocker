# 3.4.1 Performance

| ID                                    | Requirement                                                                 | Priority    | Rationale                                                                |
|---------------------------------------|-----------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------|
| <a id="nfrPerf01">**NFR‑PERF‑01**</a> | Application start‑up ≤ 2 s on reference hardware (quad‑core CPU, 8 GB RAM). | Must‑have   | Fast launch improves user experience and meets usability KPI efficiency. |
| <a id="nfrPerf02">**NFR‑PERF‑02**</a> | UI action response ≤ 200 ms.                                                | Must‑have   | Ensures perception of responsiveness.                                    |
| <a id="nfrPerf03">**NFR‑PERF‑03**</a> | Backup throughput ≥ 80 MB/s on local SSD.                                   | Should‑have | Provides efficient backup performance; hardware dependent.               |
| <a id="nfrPerf04">**NFR‑PERF‑04**</a> | CPU usage ≤ 60 % average during backup, with dynamic throttling.            | Should‑have | Prevents resource starvation on user systems.                            |
| <a id="nfrAud01">**NFR‑AUD‑01**</a>   | Each audit‑log append must complete in ≤ 1 ms on reference hardware.        | Must‑have   | Maintains low overhead for immutable logging.                            |
| <a id="nfrAud02">**NFR‑AUD‑02**</a>   | Verification of a 10 MB rotated log must finish in ≤ 2 s.                   | Must‑have   | Enables regular tamper checks without user impact.                       |