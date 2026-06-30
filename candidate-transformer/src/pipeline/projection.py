"""Runtime configurable JSON projection layer."""

import re
from typing import Any

from src.interfaces.projector import BaseProjector


class ConfigurableJSONProjector(BaseProjector):
    """Projects data into a runtime-configured JSON schema."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with an optional projection configuration."""
        self.config = config

    def project(self, data: Any) -> dict[str, Any]:
        """Project data into an output representation.

        Args:
            data: A CanonicalCandidate or equivalent Pydantic model.

        Returns:
            Projected output dictionary.
        """
        # Default behavior: dump complete canonical candidate
        from typing import cast
        base_dict = cast(dict[str, Any], data.model_dump(mode="json"))

        if not self.config or "fields" not in self.config:
            return base_dict

        result: dict[str, Any] = {}
        for field_def in self.config["fields"]:
            path = field_def.get("path")
            if not path:
                continue

            source_expr = field_def.get("from", path)
            value = self._evaluate_expr(base_dict, source_expr)

            if value is not None and field_def.get("normalize") == "E164":
                value = self._normalize_e164(value)

            result[path] = value

        if self.config.get("include_confidence", False):
            result["overall_confidence"] = base_dict.get("overall_confidence")

        if self.config.get("include_provenance", False):
            result["provenance"] = base_dict.get("provenance")

        return result

    def _evaluate_expr(self, data: Any, expr: str) -> Any:
        """Evaluate simple extraction expressions against a dictionary.
        
        Supports:
        - Direct keys: 'full_name'
        - Nested keys: 'identity.full_name'
        - Array index: 'phones[0]'
        - Array projection: 'skills[].name'
        """
        parts = expr.split(".")
        current = data
        for i, part in enumerate(parts):
            if current is None:
                return None

            # Array projection: e.g. skills[]
            if part.endswith("[]"):
                key = part[:-2]
                if isinstance(current, dict) and key in current:
                    arr = current[key]
                    if not isinstance(arr, list):
                        return None
                    remaining_expr = ".".join(parts[i + 1 :])
                    if not remaining_expr:
                        return arr
                    return [
                        self._evaluate_expr(item, remaining_expr)
                        for item in arr
                    ]
                return None

            # Array indexing: e.g. phones[0]
            match = re.match(r"^(.+)\[(\d+)\]$", part)
            if match:
                key, idx_str = match.groups()
                idx = int(idx_str)
                if isinstance(current, dict) and key in current:
                    arr = current[key]
                    if isinstance(arr, list) and len(arr) > idx:
                        current = arr[idx]
                    else:
                        return None
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
        return current

    def _normalize_e164(self, val: Any) -> str:
        """Naive E164 normalizer."""
        digits = re.sub(r"\D", "", str(val))
        return f"+{digits}" if digits else ""
