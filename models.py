from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


PHASE_NAMES = ["设计", "采购", "机加", "装配", "调试"]


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
    def total_cost(self) -> float:
        return sum(p.cost.total for p in self.phases)

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

    def get_delayed_phases(self, min_days: int = 0) -> List[Phase]:
        return [p for p in self.phases if p.is_delayed() and p.delay_days() > min_days]

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
