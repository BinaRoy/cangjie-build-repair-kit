from __future__ import annotations

from abc import ABC, abstractmethod

from driver.contracts import ProjectConfig, VerifyResult


class BuildAdapter(ABC):
    @abstractmethod
    def verify(self, project: ProjectConfig) -> VerifyResult:
        raise NotImplementedError
