from __future__ import annotations

import math
from typing import Literal


def to_million_yen(value: float, mode: Literal["round", "floor"] = "round") -> int:
    million = value / 1_000_000
    if mode == "floor":
        return math.floor(million)
    return math.floor(million + 0.5) if million >= 0 else math.ceil(million - 0.5)

