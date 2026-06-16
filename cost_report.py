from typing import List, Dict
from models import Project, Phase


class CostReport:
    def __init__(self, project: Project, budget_multiplier: float = 1.0):
        self.project = project
        self.budget_multiplier = budget_multiplier

    def _get_budget(self, phase: Phase) -> float:
        planned_days = 0
        if phase.planned_start and phase.planned_end:
            planned_days = (phase.planned_end - phase.planned_start).days
        return planned_days * 8 * phase.cost.labor_hour_rate * self.budget_multiplier

    def generate(self) -> str:
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append(f"  成本偏差报告 - {self.project.name}")
        lines.append("=" * 80)
        lines.append(f"\n  合同金额: ¥{self.project.contract_amount:,.2f}")
        lines.append(f"  总成本:   ¥{self.project.total_cost:,.2f}")
        lines.append(f"  毛利:     ¥{self.project.gross_profit:,.2f}")
        lines.append(f"  毛利率:   {self.project.gross_margin:.2f}%")
        lines.append("")
        lines.append("-" * 80)

        header = f"  {'阶段':<6} {'外购件':>10} {'标准件':>10} {'机加费':>10} {'人工成本':>10} {'合计':>12} {'偏差':>10}"
        lines.append(header)
        lines.append("-" * 80)

        total_purchased = 0.0
        total_standard = 0.0
        total_machining = 0.0
        total_labor = 0.0
        total_actual = 0.0

        for phase in self.project.phases:
            cost = phase.cost
            actual = cost.total
            budget = self._get_budget(phase)
            variance = actual - budget

            total_purchased += cost.purchased_parts
            total_standard += cost.standard_parts
            total_machining += cost.machining_fee
            total_labor += cost.labor_cost
            total_actual += actual

            variance_str = f"¥{variance:,.2f}"
            if variance > 0:
                variance_str = f"+¥{variance:,.2f}"

            lines.append(
                f"  {phase.name:<6} "
                f"¥{cost.purchased_parts:>9,.2f} "
                f"¥{cost.standard_parts:>9,.2f} "
                f"¥{cost.machining_fee:>9,.2f} "
                f"¥{cost.labor_cost:>9,.2f} "
                f"¥{actual:>11,.2f} "
                f"{variance_str:>10}"
            )

        lines.append("-" * 80)
        lines.append(
            f"  {'合计':<6} "
            f"¥{total_purchased:>9,.2f} "
            f"¥{total_standard:>9,.2f} "
            f"¥{total_machining:>9,.2f} "
            f"¥{total_labor:>9,.2f} "
            f"¥{total_actual:>11,.2f}"
        )
        lines.append("")

        lines.append("  成本构成比例:")
        if total_actual > 0:
            lines.append(f"    外购件: {total_purchased/total_actual*100:.1f}%  -  ¥{total_purchased:,.2f}")
            lines.append(f"    标准件: {total_standard/total_actual*100:.1f}%  -  ¥{total_standard:,.2f}")
            lines.append(f"    机加费: {total_machining/total_actual*100:.1f}%  -  ¥{total_machining:,.2f}")
            lines.append(f"    人工成本: {total_labor/total_actual*100:.1f}%  -  ¥{total_labor:,.2f}")
        lines.append("")

        return "\n".join(lines)

    def get_cost_breakdown(self) -> Dict[str, Dict[str, float]]:
        breakdown = {}
        for phase in self.project.phases:
            breakdown[phase.name] = {
                "外购件": phase.cost.purchased_parts,
                "标准件": phase.cost.standard_parts,
                "机加工费": phase.cost.machining_fee,
                "人工成本": phase.cost.labor_cost,
                "合计": phase.cost.total,
            }
        return breakdown
