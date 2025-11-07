"""Repository-related helper functions."""

from typing import Optional, Dict, Any


def _determine_backend_from_uri(uri: Optional[str]) -> Optional[str]:
    """Determine repository backend based on URI."""
    if not uri:
        return None
    normalized = uri.lower()
    if normalized.startswith(("s3://", "s3:")):
        return "s3"
    if normalized.startswith(("b2://", "b2:")):
        return "b2"
    if normalized.startswith(("azure:", "azure://")):
        return "azure"
    if normalized.startswith(("gs://", "gcs:", "gcs://")):
        return "gcs"
    return None


def _backend_display_name(backend: str) -> str:
    """Return user-facing backend name."""
    mapping = {
            "s3":    "AWS",
            "b2":    "Backblaze B2",
            "azure": "Azure",
            "gcs":   "Google Cloud Storage"
    }
    return mapping.get(backend, backend.upper())


def _repository_config_to_dict(repository_obj, name: str) -> Dict[str, Any]:
    """Convert repository configuration object or mapping to dictionary."""
    if repository_obj is None:
        return {"name": name}
    if hasattr(repository_obj, "to_dict"):
        maybe_dict = repository_obj.to_dict()
        data = dict(maybe_dict) if isinstance(maybe_dict, dict) else {"name": name}
    elif isinstance(repository_obj, dict):
        data = dict(repository_obj)
    else:
        data = {"name": name}
        for attr in ("uri", "location", "description", "tags", "password", "has_backend_credentials"):
            if hasattr(repository_obj, attr):
                value = getattr(repository_obj, attr)
                if value is not None:
                    key = "uri" if attr == "location" else attr
                    data[key] = value
    data.setdefault("name", name)
    # Normalise location/uri fields
    if "uri" not in data and "location" in data:
        data["uri"] = data.pop("location")
    return data
