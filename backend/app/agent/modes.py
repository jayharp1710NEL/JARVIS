"""Mode configurations — flags that drive the orchestrator pipeline."""
from __future__ import annotations

from dataclasses import dataclass

from .schemas import Mode


@dataclass(frozen=True)
class ModeConfig:
    mode: Mode
    web_default: bool          # default web usage when router is unsure
    do_plan: bool
    do_verify: bool
    do_critique: bool
    num_queries: int
    read_top_n: int            # number of pages to read in research
    require_citations: bool
    force_local: bool = False
    structured: str | None = None  # "truth" / "debate" hints handled in prompt


_CONFIGS: dict[Mode, ModeConfig] = {
    Mode.fast: ModeConfig(Mode.fast, False, False, False, False, 1, 0, False),
    Mode.research: ModeConfig(Mode.research, True, False, True, True, 4, 3, True),
    Mode.deep: ModeConfig(Mode.deep, False, True, True, True, 3, 2, True),
    Mode.builder: ModeConfig(Mode.builder, False, True, False, True, 2, 1, False),
    Mode.truth: ModeConfig(Mode.truth, False, True, True, False, 2, 2, True, structured="truth"),
    Mode.debate: ModeConfig(Mode.debate, True, True, True, True, 3, 2, True, structured="debate"),
    Mode.privacy: ModeConfig(Mode.privacy, False, False, False, False, 0, 0, False, force_local=True),
    Mode.autopilot: ModeConfig(Mode.autopilot, False, True, True, False, 2, 1, False),
}


def get_mode_config(mode: Mode) -> ModeConfig:
    return _CONFIGS.get(mode, _CONFIGS[Mode.fast])
