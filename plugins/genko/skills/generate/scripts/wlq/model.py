# ported from: internal/infrastructure/quality/checker.go:214-234,
#              internal/infrastructure/temporal/activity/check_quality.go:21-29
#              @ autopostd 20c740b
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    name: str
    passed: bool
    severity: str  # "error" | "warning"
    detail: str
    category: str = ""
    location: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        d = {"name": self.name, "passed": self.passed,
             "severity": self.severity, "detail": self.detail}
        if self.category:
            d["category"] = self.category
        if self.location:
            d["location"] = self.location
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


def check_pass(name: str, detail: str, severity: str) -> Finding:
    return Finding(name=name, passed=True, severity=severity, detail=detail)


def check_fail(name: str, detail: str, suggestion: str, severity: str) -> Finding:
    return Finding(name=name, passed=False, severity=severity,
                   detail=detail, suggestion=suggestion)
