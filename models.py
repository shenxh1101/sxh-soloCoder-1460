from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple


PHASE_NAMES = ["设计", "采购", "机加", "装配", "调试"]


@dataclass
class PhaseBudget:
    purchased_parts: float = 0.0
    standard_parts: float = 0.0
    machining_fee: float = 0.0
    labor_cost: float = 0.0

    @property
    def total(self) -> float:
        return self.purchased_parts + self.standard_parts + self.machining_fee + self.labor_cost

    def to_dict(self) -> dict:
        return {
            "purchased_parts": self.purchased_parts,
            "standard_parts": self.standard_parts,
            "machining_fee": self.machining_fee,
            "labor_cost": self.labor_cost,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PhaseBudget":
        return cls(
            purchased_parts=d.get("purchased_parts", 0.0),
            standard_parts=d.get("standard_parts", 0.0),
            machining_fee=d.get("machining_fee", 0.0),
            labor_cost=d.get("labor_cost", 0.0),
        )


@dataclass
class PhaseCost:
    purchased_parts: float = 0.0
    standard_parts: float = 0.0
    machining_fee: float = 0.0
    labor_hours: float = 0.0
    labor_hour_rate: float = 0.0

    @property
    def labor_cost(self) -> float:
        return self.labor_hours * self.labor_hour_rate

    @property
    def total(self) -> float:
        return self.purchased_parts + self.standard_parts + self.machining_fee + self.labor_cost

    def to_dict(self) -> dict:
        return {
            "purchased_parts": self.purchased_parts,
            "standard_parts": self.standard_parts,
            "machining_fee": self.machining_fee,
            "labor_hours": self.labor_hours,
            "labor_hour_rate": self.labor_hour_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PhaseCost":
        return cls(
            purchased_parts=d.get("purchased_parts", 0.0),
            standard_parts=d.get("standard_parts", 0.0),
            machining_fee=d.get("machining_fee", 0.0),
            labor_hours=d.get("labor_hours", 0.0),
            labor_hour_rate=d.get("labor_hour_rate", 0.0),
        )


@dataclass
class Phase:
    name: str
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    owner: str = ""
    completion_percent: float = 0.0
    cost: PhaseCost = field(default_factory=PhaseCost)
    budget: PhaseBudget = field(default_factory=PhaseBudget)

    def is_delayed(self) -> bool:
        if self.actual_end and self.planned_end:
            return self.actual_end > self.planned_end
        if not self.actual_end and self.planned_end:
            today = date.today()
            return today > self.planned_end and self.completion_percent < 100
        return False

    def delay_days(self) -> int:
        if self.actual_end and self.planned_end:
            delta = self.actual_end - self.planned_end
            return max(0, delta.days)
        if not self.actual_end and self.planned_end:
            today = date.today()
            delta = today - self.planned_end
            return max(0, delta.days)
        return 0

    def is_over_budget(self) -> bool:
        if self.budget.total == 0:
            return False
        return self.cost.total > self.budget.total

    def budget_variance(self) -> float:
        return self.cost.total - self.budget.total

    def budget_variance_percent(self) -> float:
        if self.budget.total == 0:
            return 0.0
        return (self.budget_variance() / self.budget.total) * 100

    def validate_dates(self) -> Tuple[bool, str]:
        if self.planned_start and self.planned_end:
            if self.planned_end < self.planned_start:
                return False, "计划结束日期不能早于计划开始日期"
        if self.actual_start and self.actual_end:
            if self.actual_end < self.actual_start:
                return False, "实际结束日期不能早于实际开始日期"
        return True, ""

    def validate_values(self) -> Tuple[bool, str]:
        if self.completion_percent < 0 or self.completion_percent > 100:
            return False, "完成百分比必须在 0-100 之间"
        if self.cost.purchased_parts < 0:
            return False, "外购件费用不能为负数"
        if self.cost.standard_parts < 0:
            return False, "标准件费用不能为负数"
        if self.cost.machining_fee < 0:
            return False, "机加工费不能为负数"
        if self.cost.labor_hours < 0:
            return False, "工时不能为负数"
        if self.cost.labor_hour_rate < 0:
            return False, "工时单价不能为负数"
        if self.budget.purchased_parts < 0:
            return False, "预算外购件费用不能为负数"
        if self.budget.standard_parts < 0:
            return False, "预算标准件费用不能为负数"
        if self.budget.machining_fee < 0:
            return False, "预算机加工费不能为负数"
        if self.budget.labor_cost < 0:
            return False, "预算人工成本不能为负数"
        return True, ""

    def validate_all(self) -> Tuple[bool, str]:
        ok, msg = self.validate_dates()
        if not ok:
            return False, msg
        ok, msg = self.validate_values()
        if not ok:
            return False, msg
        return True, ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "owner": self.owner,
            "completion_percent": self.completion_percent,
            "cost": self.cost.to_dict(),
            "budget": self.budget.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Phase":
        def parse_date(s: Optional[str]) -> Optional[date]:
            if not s:
                return None
            return datetime.strptime(s, "%Y-%m-%d").date()

        return cls(
            name=d["name"],
            planned_start=parse_date(d.get("planned_start")),
            planned_end=parse_date(d.get("planned_end")),
            actual_start=parse_date(d.get("actual_start")),
            actual_end=parse_date(d.get("actual_end")),
            owner=d.get("owner", ""),
            completion_percent=d.get("completion_percent", 0.0),
            cost=PhaseCost.from_dict(d.get("cost", {})),
            budget=PhaseBudget.from_dict(d.get("budget", {})),
        )


@dataclass
class Project:
    id: str
    name: str
    contract_amount: float
    target_delivery_date: Optional[date]
    phases: List[Phase] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not self.phases:
            self.phases = [Phase(name=pname) for pname in PHASE_NAMES]

    @property
    def total_budget(self) -> float:
        return sum(p.budget.total for p in self.phases)

    @property
    def total_cost(self) -> float:
        return sum(p.cost.total for p in self.phases)

    @property
    def budget_variance(self) -> float:
        return self.total_cost - self.total_budget

    @property
    def budget_variance_percent(self) -> float:
        if self.total_budget == 0:
            return 0.0
        return (self.budget_variance / self.total_budget) * 100

    @property
    def is_over_budget(self) -> bool:
        if self.total_budget == 0:
            return False
        return self.total_cost > self.total_budget

    @property
    def gross_profit(self) -> float:
        return self.contract_amount - self.total_cost

    @property
    def gross_margin(self) -> float:
        if self.contract_amount == 0:
            return 0.0
        return (self.gross_profit / self.contract_amount) * 100

    @property
    def overall_completion(self) -> float:
        if not self.phases:
            return 0.0
        return sum(p.completion_percent for p in self.phases) / len(self.phases)

    @property
    def is_delayed(self) -> bool:
        return any(p.is_delayed() for p in self.phases)

    @property
    def max_delay_days(self) -> int:
        delayed = self.get_delayed_phases()
        if not delayed:
            return 0
        return max(p.delay_days() for p in delayed)

    @property
    def days_to_delivery(self) -> Optional[int]:
        if not self.target_delivery_date:
            return None
        delta = self.target_delivery_date - date.today()
        return delta.days

    def get_delayed_phases(self, min_days: int = 0) -> List[Phase]:
        return [p for p in self.phases if p.is_delayed() and p.delay_days() > min_days]

    def get_over_budget_phases(self) -> List[Phase]:
        return [p for p in self.phases if p.is_over_budget()]

    def get_all_owners(self) -> List[str]:
        owners = set()
        for p in self.phases:
            if p.owner and p.owner.strip():
                owners.add(p.owner.strip())
        return sorted(list(owners))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "contract_amount": self.contract_amount,
            "target_delivery_date": self.target_delivery_date.isoformat() if self.target_delivery_date else None,
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        def parse_date(s: Optional[str]) -> Optional[date]:
            if not s:
                return None
            return datetime.strptime(s, "%Y-%m-%d").date()

        return cls(
            id=d["id"],
            name=d["name"],
            contract_amount=d["contract_amount"],
            target_delivery_date=parse_date(d.get("target_delivery_date")),
            phases=[Phase.from_dict(pd) for pd in d.get("phases", [])],
            created_at=d.get("created_at", datetime.now().isoformat()),
        )
