# 3.1.7 Error Handling &amp; Resource Management

| ID             | Requirement                                                       | Priority    | Rationale              |
|----------------|-------------------------------------------------------------------|-------------|------------------------|
| <a id="frErr001">**FR‑ERR‑001**</a> | Implement retry with exponential back‑off for transient failures. | Must‑have   | Resilience.            |
| <a id="frErr002">**FR‑ERR‑002**</a> | Maintain backup consistency in case of interruptions.             | Must‑have   | Data integrity.        |
| <a id="frRes001">**FR‑RES‑001**</a> | Support bandwidth throttling and backup windows.                  | Should‑have | Resource optimisation. |
| <a id="frRes002">**FR‑RES‑002**</a> | Automate pruning and cleanup of outdated backups.                 | Must‑have   | Storage control.       |