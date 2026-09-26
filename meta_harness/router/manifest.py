from __future__ import annotations

import json
import dataclasses
from typing import List, Literal, Optional, Any

try:
    from pydantic import BaseModel, Field
    try:
        from pydantic import ConfigDict
        HAS_CONFIG_DICT = True
    except ImportError:
        HAS_CONFIG_DICT = False

    class RoutingManifest(BaseModel):
        """Pydantic Schema describing a Repomap routing request."""

        intent: Literal[
            "repomap_summary",
            "symbol_trace",
            "schema_registry",
            "refactor_code",
            "dependency_check",
        ] = Field(..., description="The high-level operation to execute.")

        primary_target_symbols: List[str] = Field(
            default_factory=list,
            description="List of fully qualified symbol names that are the primary focus of the request.",
        )

        focus_files: List[str] = Field(
            default_factory=list,
            description="Optional list of file paths that should be prioritized during processing.",
        )

        repomap_token_budget: int = Field(
            default=2048,
            ge=512,
            le=8192,
            description="Maximum token budget for the Repomap summary operation.",
        )

        require_blast_radius: bool = Field(
            default=False,
            description="If True, perform a blast-radius trace around the primary symbols.",
        )

        execution_engine: Literal["antigravity_cli", "repomap_only"] = Field(
            default="repomap_only",
            description="Select which execution backend to use.",
        )

        task_instructions: str = Field(
            default="",
            description="Free-form instructions for the orchestrator or tooling.",
        )

        if HAS_CONFIG_DICT:
            model_config = ConfigDict(
                populate_by_name=True,
                use_enum_values=True,
                str_strip_whitespace=True,
            )
        else:
            class Config:
                validate_by_name = True
                use_enum_values = True
                str_strip_whitespace = True

        def json(self) -> str:
            return self.model_dump_json(indent=2) if hasattr(self, "model_dump_json") else super().json(indent=2)

        def dict(self) -> dict:
            return self.model_dump() if hasattr(self, "model_dump") else super().dict()

except ImportError:

    class ValidationError(ValueError):
        """Fallback validation error when Pydantic is not installed."""
        pass

    @dataclasses.dataclass
    class RoutingManifest:
        """Dataclass fallback schema describing a Repomap routing request."""

        intent: str
        primary_target_symbols: List[str] = dataclasses.field(default_factory=list)
        focus_files: List[str] = dataclasses.field(default_factory=list)
        repomap_token_budget: int = 2048
        require_blast_radius: bool = False
        execution_engine: str = "repomap_only"
        task_instructions: str = ""

        def __post_init__(self):
            valid_intents = {
                "repomap_summary",
                "symbol_trace",
                "schema_registry",
                "refactor_code",
                "dependency_check",
            }
            if self.intent not in valid_intents:
                raise ValueError(f"Invalid intent '{self.intent}'. Must be one of {valid_intents}")

            if not (512 <= self.repomap_token_budget <= 8192):
                raise ValueError(f"repomap_token_budget {self.repomap_token_budget} out of bounds [512, 8192]")

        def json(self) -> str:
            return json.dumps(dataclasses.asdict(self), indent=2)

        def dict(self) -> dict:
            return dataclasses.asdict(self)
