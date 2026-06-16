from datetime import date, timedelta
from typing import List, Optional, Tuple

from models import Project, Phase
from repository import ProjectRepository


DELIVERY_WARNING_DAYS = 15
DELIVERY_CRITICAL_DAYS = 7
LOW_MARGIN_THRESHOLD = 20.0
HIGH_OVER_BUDGET_THRESHOLD = 10.0


class Dashboard:
    def __init__(self, projects: List[Project]):
        self.projects = projects

    def get_overall_stats(self, projects: Optional[List[Project]] = None) -> dict:
        target_projects = projects if projects is not None else self.projects
        total_contract = sum(p.contract_amount for p in target_projects)
        total_cost = sum(p.total_cost for p in target_projects)
        total_budget = sum(p.total_budget for p in target_projects)
        total_profit = total_contract - total_cost
        avg_progress = sum(p.overall_completion for p in target_projects) / len(target_projects) if target_projects else 0.0

        delayed_count = sum(1 for p in target_projects if p.is_delayed)
        over_budget_count = sum(1 for p in target_projects if p.is_over_budget)

        return {
            "project_count": len(target_projects),
            "total_contract": total_contract,
            "total_budget": total_budget,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "avg_margin": (total_profit / total_contract * 100) if total_contract > 0 else 0.0,
            "avg_progress": avg_progress,
            "delayed_count": delayed_count,
            "over_budget_count": over_budget_count,
        }

    def get_upcoming_deliveries(self, days: int = DELIVERY_WARNING_DAYS) -> List[Project]:
        today = date.today()
        warning_date = today + timedelta(days=days)

        upcoming = []
        for p in self.projects:
            if p.target_delivery_date:
                if today <= p.target_delivery_date <= warning_date:
                    upcoming.append(p)

        upcoming.sort(key=lambda x: x.target_delivery_date or date.max)
        return upcoming

    def get_delayed_projects(self) -> List[Project]:
        delayed = [p for p in self.projects if p.is_delayed]
        delayed.sort(key=lambda x: x.max_delay_days, reverse=True)
        return delayed

    def filter_by_status(self, status: str, projects: Optional[List[Project]] = None) -> List[Project]:
        target = projects if projects is not None else self.projects
        if status == "all":
            return target
        elif status == "delayed":
            return [p for p in target if p.is_delayed]
        elif status == "normal":
            return [p for p in target if not p.is_delayed]
        elif status == "over_budget":
            return [p for p in target if p.is_over_budget]
        else:
            return target

    def filter_by_owner(self, owner: str, projects: Optional[List[Project]] = None) -> List[Project]:
        target = projects if projects is not None else self.projects
        if not owner or owner == "all":
            return target
        owner_lower = owner.strip().lower()
        return [p for p in target if any(ph.owner and ph.owner.strip().lower() == owner_lower for ph in p.phases)]

    def get_all_owners(self) -> List[str]:
        owners = set()
        for p in self.projects:
            for owner in p.get_all_owners():
                owners.add(owner)
        return sorted(list(owners))

    def _get_project_risk_score(self, project: Project) -> Tuple[int, List[str], str]:
        risks = []
        score = 0

        days_delivery = project.days_to_delivery
        if days_delivery is not None:
            if days_delivery < 0:
                score += 50
                risks.append("已逾期")
            elif days_delivery <= DELIVERY_CRITICAL_DAYS:
                score += 40
                risks.append("交期紧急")
            elif days_delivery <= DELIVERY_WARNING_DAYS:
                score += 20
                risks.append("即将交付")

        if project.is_delayed:
            score += min(project.max_delay_days * 3, 30)
            risks.append(f"延期{project.max_delay_days}天")

        if project.is_over_budget:
            over_pct = project.budget_variance_percent
            score += min(int(over_pct * 2), 30)
            if over_pct >= HIGH_OVER_BUDGET_THRESHOLD:
                risks.append(f"超支严重({over_pct:.1f}%)")
            else:
                risks.append(f"超支{over_pct:.1f}%")

        margin = project.gross_margin
        if margin < LOW_MARGIN_THRESHOLD:
            score += max(0, int((LOW_MARGIN_THRESHOLD - margin) * 3))
            if margin < 0:
                risks.append("亏损")
            else:
                risks.append(f"低毛利({margin:.1f}%)")

        risk_level = "🔴" if score >= 60 else ("🟠" if score >= 30 else "🟢")

        return score, risks, risk_level

    def get_priority_projects(self, top_n: int = 5) -> List[Tuple[Project, int, List[str], str]]:
        scored = []
        for p in self.projects:
            score, risks, level = self._get_project_risk_score(p)
            if score > 0:
                scored.append((p, score, risks, level))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def render(self, status_filter: str = "all", owner_filter: str = "all") -> str:
        lines = []

        filtered = self.filter_by_status(status_filter)
        filtered = [p for p in filtered if (owner_filter == "all" or any(ph.owner and ph.owner.strip() == owner_filter for ph in p.phases))]

        lines.append("\n" + "=" * 100)
        lines.append("  📊 多项目经营看板")
        lines.append("=" * 100)

        stats = self.get_overall_stats(filtered)
        lines.append(f"\n  【总体统计】  共 {stats['project_count']} 个项目")
        lines.append(f"    总合同额:  ¥{stats['total_contract']:>14,.2f}")
        lines.append(f"    总预算:    ¥{stats['total_budget']:>14,.2f}")
        lines.append(f"    实际总成本: ¥{stats['total_cost']:>14,.2f}")
        lines.append(f"    总毛利:    ¥{stats['total_profit']:>14,.2f}  (毛利率: {stats['avg_margin']:.2f}%)")
        lines.append(f"    平均进度:  {stats['avg_progress']:>13.1f}%")
        lines.append(f"    延期项目:  {stats['delayed_count']:>4} 个    超支项目: {stats['over_budget_count']:>4} 个")

        lines.append("\n" + "-" * 100)
        lines.append(f"  当前筛选: 状态={status_filter} | 负责人={owner_filter}")
        lines.append(f"  显示项目数: {len(filtered)} 个")
        lines.append("-" * 100)

        priority_projects = self.get_priority_projects()
        if priority_projects:
            lines.append("\n  【🎯 重点关注项目】")
            lines.append("  " + "-" * 96)
            for p, score, risks, level in priority_projects:
                risk_tags = "  ".join(f"[{r}]" for r in risks)
                name = p.name[:18] + "..." if len(p.name) > 18 else p.name
                lines.append(
                    f"    {level} {name:<20} "
                    f"进度:{p.overall_completion:>5.1f}%  "
                    f"毛利:{p.gross_margin:>6.1f}%  "
                    f"交付:{p.days_to_delivery or '-':>3}天  "
                )
                lines.append(f"       风险: {risk_tags}")
            lines.append("")

        lines.append(
            f"\n  {'项目名称':<18} {'合同额':>12} {'预算':>12} {'实际成本':>12} "
            f"{'进度':>8} {'毛利率':>8} {'延期':>6} {'超支':>6} {'交付倒计时':>10}"
        )
        lines.append("  " + "-" * 96)

        for p in sorted(filtered, key=lambda x: x.target_delivery_date or date.max):
            name = p.name[:16] + "..." if len(p.name) > 16 else p.name

            delayed_mark = "❌" if p.is_delayed else "✅"
            over_budget_mark = "❌" if p.is_over_budget else "✅"

            days_delivery = p.days_to_delivery
            if days_delivery is None:
                delivery_str = "未设置"
            elif days_delivery < 0:
                delivery_str = f"逾期{-days_delivery}天"
            elif days_delivery == 0:
                delivery_str = "今天"
            else:
                delivery_str = f"还剩{days_delivery}天"

            lines.append(
                f"  {name:<18} "
                f"¥{p.contract_amount:>11,.0f} "
                f"¥{p.total_budget:>11,.0f} "
                f"¥{p.total_cost:>11,.0f} "
                f"{p.overall_completion:>7.1f}% "
                f"{p.gross_margin:>7.2f}% "
                f"{delayed_mark:^6} "
                f"{over_budget_mark:^6} "
                f"{delivery_str:>10}"
            )

        lines.append("")

        upcoming = self.get_upcoming_deliveries()
        if upcoming:
            lines.append("  【⚡ 即将到期项目】")
            for p in upcoming:
                days_left = p.days_to_delivery or 0
                urgent = "🔥" if days_left <= 7 else "⏰"
                lines.append(
                    f"    {urgent} {p.name:<20} "
                    f"目标交付: {p.target_delivery_date.strftime('%Y-%m-%d') if p.target_delivery_date else '未设置'} "
                    f"({days_left}天后) "
                    f"进度: {p.overall_completion:.1f}%"
                )
            lines.append("")

        delayed_projects = self.get_delayed_projects()
        if delayed_projects:
            lines.append("  【⚠️  延期项目 Top 5】")
            for p in delayed_projects[:5]:
                delayed_phases = p.get_delayed_phases()
                phase_names = "、".join(ph.name for ph in delayed_phases[:3])
                if len(delayed_phases) > 3:
                    phase_names += f"等{len(delayed_phases)}个阶段"
                lines.append(
                    f"    ❌ {p.name:<20} "
                    f"延期最多: {p.max_delay_days}天 "
                    f"| 延期阶段: {phase_names}"
                )
            lines.append("")

        owners = self.get_all_owners()
        if owners:
            lines.append(f"  【👥 所有负责人】 共 {len(owners)} 人")
            lines.append("    " + "  ".join(owners))
            lines.append("")

        lines.append("  操作提示:")
        lines.append("    输入 s=状态筛选 (all/delayed/normal/over_budget)")
        lines.append("    输入 o=负责人筛选 (all/具体姓名)")
        lines.append("    输入 0=返回主菜单")

        return "\n".join(lines)
