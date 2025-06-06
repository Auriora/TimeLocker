# 6.5 Repository Configuration Schema (Region-Aware excerpt)

```yaml
# Example repository config snippet after region-awareness update
repo:
  id: 123e4567-e89b-12d3-a456-426614174000
  type: s3
  endpoint: https://s3.eu-central-1.amazonaws.com
  region_code: EU      # ISO-3166-1 alpha-2 or custom "EU/UK/US" enum
  enforce_region: true # true = block backups outside declared region
```

This schema addition underpins **[FR-RM-004](3-1-1-Repository-Management.md#frRm004)/[005](3-1-1-Repository-Management.md#frRm005)** and *
*[NFR-SEC-12](3-4-6-Security-Compliance.md#nfrSec12)**, enabling GDPR-compliant control over data-transfer regions.