# 4.4 GDPR Impact Mapping

| GDPR Principle / Article | Practical Impact on the App | Requirement IDs |
| --- | --- | --- |
| Lawful basis & transparency (Arts. 5–6, 13) | No silent telemetry; onboarding notice lists stored data. | [FR‑SEC‑007](3-1-3-Security.md#frSec007) |
| Data minimisation (Art. 5‑1c) | Exclude temp dirs by default; minimal metadata retained. | [FR‑BK‑002](3-1-2-Backup-Operations.md#frBk002), [FR‑PM‑003](3-1-5-Policy-Management.md#frPm003) |
| Storage limitation & right‑to‑erasure (Arts. 5‑1e, 17) | Retention pruning and "Forget file" workflow. | [FR‑PM‑001](3-1-5-Policy-Management.md#frPm001), [FR‑SEC‑006](3-1-3-Security.md#frSec006) |
| Integrity & confidentiality (Art. 32) | AES‑256 encryption, TLS 1.3, vault locking, RBAC. | [FR‑SEC‑001](3-1-3-Security.md#frSec001), [FR‑SEC‑003](3-1-3-Security.md#frSec003) |
| Accountability & audit trail (Arts. 5‑2, 30) | Immutable hash‑chained audit log, exportable records. | [FR‑MON‑003](3-1-6-Monitoring-Reporting.md#frMon003), [FR‑MON‑006](3-1-6-Monitoring-Reporting.md#frMon006) |
| Data‑subject rights (Arts. 15–22) | Export/erase personal metadata via UI/CLI. | [FR‑SEC‑005](3-1-3-Security.md#frSec005), [FR‑SEC‑006](3-1-3-Security.md#frSec006) |
| Breach notification (Art. 33) | Automatic detection & configurable alerts. | [FR‑MON‑005](3-1-6-Monitoring-Reporting.md#frMon005) |
| International transfers (Ch. V) | Region picker with EEA/UK enforcement option. | [FR‑RM‑004](3-1-1-Repository-Management.md#frRm004) |
| Data‑protection by design (Art. 25) | Secure defaults, opt‑in telemetry, DPIA docs. | [FR‑SEC‑007](3-1-3-Security.md#frSec007), [FR‑SEC‑008](3-1-3-Security.md#frSec008) |

*Source: GDPR Compliance Impact Analysis (April 2025).*