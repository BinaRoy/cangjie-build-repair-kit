from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from driver.contracts import ErrorSchema, PatchPlan


class RepairStrategy(ABC):
    @abstractmethod
    def propose(self, error: ErrorSchema, context: Any) -> PatchPlan:
        raise NotImplementedError
