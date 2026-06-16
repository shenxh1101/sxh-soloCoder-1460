from typing import Dict
from models import Project, Phase


class CostReport:
    def __init__(self, project: Project):
        self.project = project

    def generate(self) -> str:
        lines = []
        p = self.project

        lines.append("\n" + "=" * 100)
        lines.append(f"  成本偏差报告 - {p.name}")
        lines.append("=" * 100)

        lines.append(f"\n  【项目概览】")
        lines.append(f"    合同金额:   ¥{p.contract_amount:,.2f}")
        lines.append(f"    总预算:     ¥{p.total_budget:,.2f}")
        lines.append(f"    实际总成本: ¥{p.total_cost:,.2f}")

        variance = p.budget_variance
        variance_pct = p.budget_variance_percent
        if p.total_budget > 0:
            status = "超支" if variance > 0 else "节余"
            sign = "+" if variance > 0 else ""
            lines.append(f"    预算偏差:   {sign}¥{variance:,.2f} ({sign}{variance_pct:.2f}%) - {status}")
        else:
            lines.append(f"    预算偏差:   尚未设置预算")

        lines.append(f"    毛利:       ¥{p.gross_profit:,.2f}")
        lines.append(f"    毛利率:     {p.gross_margin:.2f}%")

        over_budget_phases = p.get_over_budget_phases()
        if over_budget_phases:
            lines.append(f"\n  ⚠️  超支阶段 ({len(over_budget_phases)} 个:")
            for ph in over_budget_phases:
                lines.append(f"    - {ph.name}: 超支 ¥{ph.budget_variance():,.2f} ({ph.budget_variance_percent():.2f}%)")

        lines.append("")
        lines.append("-" * 100)

        header = (
            f"  {'阶段':<6} "
            f"{'项目':<10} "
            f"{'预算':>12} "
            f"{'实际':>12} "
            f"{'偏差':>12} "
            f"{'偏差率':>10} "
            f"{'状态':<8}"
        )
        lines.append(header)
        lines.append("-" * 100)

        total_budget_total = 0.0
        total_actual_total = 0.0

        for phase in p.phases:
            b = phase.budget
            c = phase.cost

            lines.append(f"  {phase.name:<6} {'外购件':<10} ¥{b.purchased_parts:>11,.2f} ¥{c.purchased_parts:>11,.2f} {self._fmt_var(c.purchased_parts - b.purchased_parts, b.purchased_parts)}")
            lines.append(f"  {'':<6} {'标准件':<10} ¥{b.standard_parts:>11,.2f} ¥{c.standard_parts:>11,.2f} {self._fmt_var(c.standard_parts - b.standard_parts, b.standard_parts)}")
            lines.append(f"  {'':<6} {'机加工费':<10} ¥{b.machining_fee:>11,.2f} ¥{c.machining_fee:>11,.2f} {self._fmt_var(c.machining_fee - b.machining_fee, b.machining_fee)}")
            lines.append(f"  {'':<6} {'人工成本':<10} ¥{b.labor_cost:>11,.2f} ¥{c.labor_cost:>11,.2f} {self._fmt_var(c.labor_cost - b.labor_cost, b.labor_cost)}")

            phase_status = "正常"
            if phase.is_over_budget():
                phase_status = "超支 ⚠️"
            elif b.total == 0:
                phase_status = "未设预算"

            phase_var = phase.budget_variance()
            phase_var_pct = phase.budget_variance_percent()
            var_str = f"¥{phase_var:,.2f}"
            if phase_var > 0:
                var_str = f"+¥{phase_var:,.2f}"

            lines.append(
                f"  {'':<6} {'小计':<10} "
                f"¥{b.total:>11,.2f} "
                f"¥{c.total:>11,.2f} "
                f"{var_str:>12} "
                f"{phase_var_pct:>+9.2f}% "
                f"{phase_status}"
            )

            total_budget_total += b.total
            total_actual_total += c.total

            if phase != p.phases[-1]:
                lines.append(f"  {'':<6} {'':-<94}")

        lines.append("-" * 100)

        total_var = total_actual_total - total_budget_total
        total_var_pct = 0.0
        if total_budget_total > 0:
            total_var_pct = (total_var / total_budget_total) * 100

        total_var_str = f"¥{total_var:,.2f}"
        if total_var > 0:
            total_var_str = f"+¥{total_var:,.2f}"

        lines.append(
            f"  {'合计':<6} {'总计':<10} "
            f"¥{total_budget_total:>11,.2f} "
            f"¥{total_actual_total:>11,.2f} "
            f"{total_var_str:>12} "
            f"{total_var_pct:>+9.2f}%"
        )
        lines.append("")

        lines.append("  【成本构成比例 (按实际成本)】")
        if total_actual_total > 0:
            total_purchased = sum(p.cost.purchased_parts for p in p.phases)
            total_standard = sum(p.cost.standard_parts for p in p.phases)
            total_machining = sum(p.cost.machining_fee for p in p.phases)
            total_labor = sum(p.cost.labor_cost for p in p.phases)

            lines.append(f"    外购件:   {total_purchased/total_actual_total*100:>5.1f}%  -  ¥{total_purchased:,.2f}")
            lines.append(f"    标准件:   {total_standard/total_actual_total*100:>5.1f}%  -  ¥{total_standard:,.2f}")
            lines.append(f"    机加工费: {total_machining/total_actual_total*100:>5.1f}%  -  ¥{total_machining:,.2f}")
            lines.append(f"    人工成本: {total_labor/total_actual_total*100:>5.1f}%  -  ¥{total_labor:,.2f}")
        lines.append("")

        return "\n".join(lines)

    def _fmt_var(self, amount: float, base: float) -> str:
        if base == 0:
            return f"{'':>24}"
        pct = (amount / base) * 100
        var_str = f"¥{amount:,.2f} ({pct:+.2f}%)"
        if amount > 0:
            var_str = f"+¥{amount:,.2f} ({pct:+.2f}%)"
        return f"{var_str:>24}"

    def get_cost_breakdown(self) -> Dict[str, Dict[str, float]]:
        breakdown = {}
        for phase in self.project.phases:
            breakdown[phase.name] = {
                "预算_外购件": phase.budget.purchased_parts,
                "预算_标准件": phase.budget.standard_parts,
                "预算_机加工费": phase.budget.machining_fee,
                "预算_人工成本": phase.budget.labor_cost,
                "预算_合计": phase.budget.total,
                "实际_外购件": phase.cost.purchased_parts,
                "实际_标准件": phase.cost.standard_parts,
                "实际_机加工费": phase.cost.machining_fee,
                "实际_人工成本": phase.cost.labor_cost,
                "实际_合计": phase.cost.total,
                "偏差": phase.budget_variance(),
                "偏差率": phase.budget_variance_percent(),
            }
        return breakdown

    def get_project_summary(self) -> Dict[str, float]:
        p = self.project
        return {
            "合同金额": p.contract_amount,
            "总预算": p.total_budget,
            "实际总成本": p.total_cost,
            "预算偏差": p.budget_variance,
            "预算偏差率": p.budget_variance_percent,
            "毛利": p.gross_profit,
            "毛利率": p.gross_margin,
        }
