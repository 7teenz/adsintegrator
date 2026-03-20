from __future__ import annotations

from abc import ABC, abstractmethod

from app.engine.types import AccountAuditSnapshot, Category, Finding, Severity

rule_registry: list[type[AuditRule]] = []


def register_rule(cls: type[AuditRule]) -> type[AuditRule]:
    rule_registry.append(cls)
    return cls


def get_all_rules() -> list["AuditRule"]:
    return [rule_class() for rule_class in rule_registry]


class AuditRule(ABC):
    rule_id: str = ""
    category: Category = Category.PERFORMANCE
    severity: Severity = Severity.MEDIUM

    @abstractmethod
    def evaluate(self, snapshot: AccountAuditSnapshot) -> list[Finding]:
        ...

    def finding(self, **kwargs) -> Finding:
        return Finding(rule_id=self.rule_id, category=self.category, severity=self.severity, **kwargs)
