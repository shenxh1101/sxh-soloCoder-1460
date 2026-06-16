import sys
import os
from datetime import date, datetime
from typing import Optional, Tuple

from models import Project, Phase, PHASE_NAMES
from repository import ProjectRepository
from gantt import GanttChart
from cost_report import CostReport
from html_exporter import HtmlExporter
from reminder import Reminder
from dashboard import Dashboard


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\n按回车键继续...")


def parse_date_input(prompt: str) -> Optional[date]:
    while True:
        s = input(prompt).strip()
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            print("  ❌ 日期格式错误，请使用 YYYY-MM-DD 格式，或留空跳过")


def parse_float_input(prompt: str, default: float = 0.0, allow_negative: bool = True) -> float:
    while True:
        s = input(prompt).strip()
        if not s:
            return default
        try:
            val = float(s)
            if not allow_negative and val < 0:
                print("  ❌ 不能输入负数，请重新输入")
                continue
            return val
        except ValueError:
            print("  ❌ 请输入有效的数字")


def parse_int_input(prompt: str, default: int = 0, allow_negative: bool = True) -> int:
    while True:
        s = input(prompt).strip()
        if not s:
            return default
        try:
            val = int(s)
            if not allow_negative and val < 0:
                print("  ❌ 不能输入负数，请重新输入")
                continue
            return val
        except ValueError:
            print("  ❌ 请输入有效的整数")


class ProjectTrackerApp:
    def __init__(self):
        self.repo = ProjectRepository()
        self.reminder = Reminder()
        self.current_project: Optional[Project] = None

    def run(self):
        clear_screen()
        projects = self.repo.get_all()
        self.reminder.show_reminder(projects)

        if projects:
            pause()
            self._show_dashboard()

        while True:
            self._show_main_menu()
            choice = input("请选择操作: ").strip()
            if choice == "1":
                self._create_project()
            elif choice == "2":
                self._list_projects()
            elif choice == "3":
                self._select_project()
            elif choice == "4":
                self._delete_project()
            elif choice == "5":
                self._show_dashboard()
            elif choice == "6":
                self._show_gantt_chart()
            elif choice == "7":
                self._show_cost_report()
            elif choice == "8":
                self._export_html_report()
            elif choice == "9":
                self._show_all_delayed()
            elif choice == "0":
                print("\n感谢使用，再见！")
                break
            else:
                print("  ❌ 无效选项，请重新选择")
                pause()

    def _show_main_menu(self):
        print("\n" + "=" * 60)
        print("  非标自动化设备 - 项目进度与成本跟踪系统")
        print("=" * 60)
        if self.current_project:
            print(f"  当前项目: {self.current_project.name} ({self.current_project.id})")
            print(f"  进度: {self.current_project.overall_completion:.1f}%  |  "
                  f"成本: ¥{self.current_project.total_cost:,.2f}  |  "
                  f"毛利率: {self.current_project.gross_margin:.2f}%")
            print("-" * 60)
        print()
        print("  【项目管理】")
        print("    1. 创建新项目")
        print("    2. 列出所有项目")
        print("    3. 选择/进入项目")
        print("    4. 删除项目")
        print("    5. 多项目汇总看板")
        print()
        print("  【数据录入与查看】")
        print("    6. 查看甘特图")
        print("    7. 查看成本报告")
        print("    8. 导出HTML报告")
        print("    9. 查看所有延期项目")
        print()
        print("    0. 退出系统")
        print("-" * 60)

    def _create_project(self):
        clear_screen()
        print("\n" + "=" * 60)
        print("  创建新项目")
        print("=" * 60)
        print()

        name = input("  项目名称: ").strip()
        if not name:
            print("  ❌ 项目名称不能为空")
            pause()
            return

        contract_amount = parse_float_input("  合同金额 (¥): ", 0.0)
        target_date = parse_date_input("  目标交付日期 (YYYY-MM-DD，可选): ")

        project_id = self.repo.generate_id()
        project = Project(
            id=project_id,
            name=name,
            contract_amount=contract_amount,
            target_delivery_date=target_date,
        )

        self.repo.add(project)
        self.current_project = project

        print(f"\n  ✅ 项目创建成功！")
        print(f"     项目ID: {project_id}")
        print(f"     项目名称: {name}")

        pause()

    def _list_projects(self):
        clear_screen()
        projects = self.repo.get_all()

        print("\n" + "=" * 80)
        print("  项目列表")
        print("=" * 80)

        if not projects:
            print("\n  暂无项目，请先创建一个项目")
            print()
            pause()
            return

        print(f"\n  {'ID':<10} {'项目名称':<20} {'合同金额':>12} {'进度':>8} {'总成本':>12} {'毛利率':>8} {'状态':<10}")
        print("-" * 80)

        for p in projects:
            delayed = len(p.get_delayed_phases()) > 0
            status = "延期" if delayed else "正常"
            status_color = "❌" if delayed else "✅"

            print(
                f"  {p.id:<10} {p.name:<20} ¥{p.contract_amount:>11,.2f} "
                f"{p.overall_completion:>7.1f}% ¥{p.total_cost:>11,.2f} "
                f"{p.gross_margin:>7.2f}% {status_color} {status}"
            )

        print()
        pause()

    def _select_project(self):
        clear_screen()
        projects = self.repo.get_all()

        if not projects:
            print("\n  暂无项目，请先创建一个项目")
            pause()
            return

        print("\n  选择要进入的项目：")
        for i, p in enumerate(projects, 1):
            print(f"    {i}. {p.name} (ID: {p.id})")

        choice = input("\n  请输入序号 (0 取消): ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(projects):
                self.current_project = projects[idx - 1]
                self._project_detail_menu()
            else:
                print("  ❌ 无效的序号")
                pause()
        except ValueError:
            print("  ❌ 请输入数字")
            pause()

    def _project_detail_menu(self):
        while True:
            clear_screen()
            p = self.current_project
            if not p:
                break

            p = self.repo.get_by_id(p.id)
            if not p:
                print("  ❌ 项目不存在")
                self.current_project = None
                pause()
                break
            self.current_project = p

            print("\n" + "=" * 80)
            print(f"  项目详情: {p.name}")
            print("=" * 80)
            print(f"  项目ID: {p.id}")
            print(f"  合同金额: ¥{p.contract_amount:,.2f}")
            print(f"  目标交付日期: {p.target_delivery_date.strftime('%Y-%m-%d') if p.target_delivery_date else '未设置'}")
            print(f"  整体进度: {p.overall_completion:.1f}%")
            print(f"  总成本: ¥{p.total_cost:,.2f}")
            print(f"  毛利: ¥{p.gross_profit:,.2f} ({p.gross_margin:.2f}%)")
            print()

            print("  各阶段概览:")
            for i, phase in enumerate(p.phases, 1):
                status = ""
                if phase.is_delayed():
                    status = f"❌ 延期{phase.delay_days()}天"
                elif phase.completion_percent >= 100:
                    status = "✅ 已完成"
                elif phase.completion_percent > 0:
                    status = "🔄 进行中"
                else:
                    status = "⏳ 未开始"

                print(
                    f"    {i}. {phase.name:<6} | "
                    f"进度: {phase.completion_percent:>5.1f}% | "
                    f"负责人: {phase.owner or '未指派':<8} | "
                    f"成本: ¥{phase.cost.total:>10,.2f} | "
                    f"{status}"
                )

            print()
            print("-" * 80)
            print("  操作选项:")
            print("    1. 编辑阶段进度")
            print("    2. 编辑阶段预算")
            print("    3. 编辑阶段成本")
            print("    4. 查看甘特图")
            print("    5. 查看成本报告")
            print("    6. 导出HTML报告")
            print("    7. 查看延期详情")
            print("    0. 返回主菜单")
            print("-" * 80)

            choice = input("请选择操作: ").strip()

            if choice == "1":
                self._edit_phase_progress()
            elif choice == "2":
                self._edit_phase_budget()
            elif choice == "3":
                self._edit_phase_cost()
            elif choice == "4":
                self._show_gantt_for_project(p)
            elif choice == "5":
                self._show_cost_for_project(p)
            elif choice == "6":
                self._export_html_for_project(p)
            elif choice == "7":
                self._show_delayed_for_project(p)
            elif choice == "0":
                break
            else:
                print("  ❌ 无效选项")
                pause()

    def _edit_phase_progress(self):
        p = self.current_project
        if not p:
            return

        clear_screen()
        print("\n" + "=" * 60)
        print("  编辑阶段进度")
        print("=" * 60)
        print()

        for i, phase in enumerate(p.phases, 1):
            print(f"    {i}. {phase.name}")

        choice = input("\n  选择要编辑的阶段 (0 取消): ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(p.phases):
                phase = p.phases[idx - 1]
                self._edit_single_phase(phase)
                self.repo.update(p)
            else:
                print("  ❌ 无效的阶段序号")
                pause()
        except ValueError:
            print("  ❌ 请输入数字")
            pause()

    def _edit_single_phase(self, phase: Phase):
        clear_screen()
        print("\n" + "=" * 60)
        print(f"  编辑【{phase.name}】阶段进度")
        print("=" * 60)
        print()

        print(f"  当前信息:")
        print(f"    计划开始: {phase.planned_start.strftime('%Y-%m-%d') if phase.planned_start else '未设置'}")
        print(f"    计划结束: {phase.planned_end.strftime('%Y-%m-%d') if phase.planned_end else '未设置'}")
        print(f"    实际开始: {phase.actual_start.strftime('%Y-%m-%d') if phase.actual_start else '未设置'}")
        print(f"    实际结束: {phase.actual_end.strftime('%Y-%m-%d') if phase.actual_end else '未设置'}")
        print(f"    负责人: {phase.owner or '未指派'}")
        print(f"    完成度: {phase.completion_percent:.1f}%")
        print()

        print("  请输入新值（直接回车保留当前值）:")
        print()

        old_planned_start = phase.planned_start
        old_planned_end = phase.planned_end
        old_actual_start = phase.actual_start
        old_actual_end = phase.actual_end
        old_owner = phase.owner
        old_completion = phase.completion_percent

        ps = parse_date_input(f"  计划开始日期 (当前: {phase.planned_start or '无'}): ")
        if ps:
            phase.planned_start = ps

        pe = parse_date_input(f"  计划结束日期 (当前: {phase.planned_end or '无'}): ")
        if pe:
            phase.planned_end = pe

        a_s = parse_date_input(f"  实际开始日期 (当前: {phase.actual_start or '无'}): ")
        if a_s:
            phase.actual_start = a_s

        ae = parse_date_input(f"  实际结束日期 (当前: {phase.actual_end or '无'}): ")
        if ae:
            phase.actual_end = ae

        owner = input(f"  负责人 (当前: {phase.owner or '无'}): ").strip()
        if owner:
            phase.owner = owner

        completion = parse_float_input(
            f"  完成百分比 (当前: {phase.completion_percent:.1f}%): ",
            phase.completion_percent,
            allow_negative=False
        )
        phase.completion_percent = min(100.0, max(0.0, completion))

        if phase.actual_end:
            phase.completion_percent = 100.0

        ok, msg = phase.validate_all()
        if not ok:
            print(f"\n  ❌ 数据校验失败: {msg}")
            print("     已取消本次修改，恢复原值")
            phase.planned_start = old_planned_start
            phase.planned_end = old_planned_end
            phase.actual_start = old_actual_start
            phase.actual_end = old_actual_end
            phase.owner = old_owner
            phase.completion_percent = old_completion
            pause()
            return False

        changed = False
        changes = []
        if phase.planned_start != old_planned_start:
            changes.append(f"计划开始: {old_planned_start} → {phase.planned_start}")
            changed = True
        if phase.planned_end != old_planned_end:
            changes.append(f"计划结束: {old_planned_end} → {phase.planned_end}")
            changed = True
        if phase.actual_start != old_actual_start:
            changes.append(f"实际开始: {old_actual_start} → {phase.actual_start}")
            changed = True
        if phase.actual_end != old_actual_end:
            changes.append(f"实际结束: {old_actual_end} → {phase.actual_end}")
            changed = True
        if phase.owner != old_owner:
            changes.append(f"负责人: {old_owner or '无'} → {phase.owner}")
            changed = True
        if abs(phase.completion_percent - old_completion) > 0.01:
            changes.append(f"完成度: {old_completion:.1f}% → {phase.completion_percent:.1f}%")
            changed = True

        if not changed:
            print("\n  ℹ️  未检测到任何修改，数据未变动")
            pause()
            return False
        else:
            print(f"\n  ✅ 保存成功！已修改 {len(changes)} 项:")
            for c in changes:
                print(f"     - {c}")

        print()
        print("  " + "-" * 50)
        print(f"  📊 【{phase.name}】阶段最新状态:")
        print(f"     完成度: {phase.completion_percent:.1f}%")

        if phase.is_delayed():
            delay_days = phase.delay_days()
            print(f"     延期状态: ❌ 已延期 {delay_days} 天")
            if phase.planned_end:
                print(f"     计划完成: {phase.planned_end.strftime('%Y-%m-%d')}")
            if phase.actual_end:
                print(f"     实际完成: {phase.actual_end.strftime('%Y-%m-%d')}")
        else:
            print(f"     延期状态: ✅ 正常（未延期）")

        if phase.budget.total > 0:
            if phase.is_over_budget():
                var = phase.budget_variance()
                var_pct = phase.budget_variance_percent()
                print(f"     预算状态: ❌ 已超支 +¥{var:,.2f} (+{var_pct:.2f}%)")
                print(f"     预算合计: ¥{phase.budget.total:,.2f}")
                print(f"     实际成本: ¥{phase.cost.total:,.2f}")
            else:
                remaining = phase.budget.total - phase.cost.total
                print(f"     预算状态: ✅ 正常（未超支）")
                print(f"     剩余预算: ¥{remaining:,.2f}")
        else:
            print(f"     预算状态: ℹ️  未设置预算")

        if phase.owner:
            print(f"     负责人: {phase.owner}")

        pause()
        return True

    def _edit_phase_cost(self):
        p = self.current_project
        if not p:
            return

        clear_screen()
        print("\n" + "=" * 60)
        print("  编辑阶段成本")
        print("=" * 60)
        print()

        for i, phase in enumerate(p.phases, 1):
            print(f"    {i}. {phase.name} - 当前成本: ¥{phase.cost.total:,.2f}")

        choice = input("\n  选择要编辑的阶段 (0 取消): ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(p.phases):
                phase = p.phases[idx - 1]
                self._edit_single_phase_cost(phase)
                self.repo.update(p)
            else:
                print("  ❌ 无效的阶段序号")
                pause()
        except ValueError:
            print("  ❌ 请输入数字")
            pause()

    def _edit_single_phase_cost(self, phase: Phase):
        clear_screen()
        print("\n" + "=" * 60)
        print(f"  编辑【{phase.name}】阶段成本")
        print("=" * 60)
        print()

        c = phase.cost
        print(f"  当前成本明细:")
        print(f"    外购件: ¥{c.purchased_parts:,.2f}")
        print(f"    标准件: ¥{c.standard_parts:,.2f}")
        print(f"    机加工费: ¥{c.machining_fee:,.2f}")
        print(f"    工时: {c.labor_hours:.1f} 小时")
        print(f"    工时单价: ¥{c.labor_hour_rate:.2f}/小时")
        print(f"    人工成本: ¥{c.labor_cost:,.2f}")
        print(f"    合计: ¥{c.total:,.2f}")
        print()

        if phase.budget.total > 0:
            b = phase.budget
            over = "超支" if phase.is_over_budget() else "节余"
            var_sign = "+" if phase.budget_variance() > 0 else ""
            print(f"  预算对比:")
            print(f"    预算合计: ¥{b.total:,.2f}")
            print(f"    偏差: {var_sign}¥{phase.budget_variance():,.2f} ({var_sign}{phase.budget_variance_percent():.2f}%) - {over}")
            print()

        print("  请输入新值（直接回车保留当前值）:")
        print()

        old_purchased = c.purchased_parts
        old_standard = c.standard_parts
        old_machining = c.machining_fee
        old_labor_hours = c.labor_hours
        old_labor_rate = c.labor_hour_rate
        old_total = c.total

        pp = parse_float_input(f"  外购件费用 (当前: ¥{c.purchased_parts:,.2f}): ", c.purchased_parts, allow_negative=False)
        c.purchased_parts = pp

        sp = parse_float_input(f"  标准件费用 (当前: ¥{c.standard_parts:,.2f}): ", c.standard_parts, allow_negative=False)
        c.standard_parts = sp

        mf = parse_float_input(f"  机加工费 (当前: ¥{c.machining_fee:,.2f}): ", c.machining_fee, allow_negative=False)
        c.machining_fee = mf

        lh = parse_float_input(f"  工时 (小时) (当前: {c.labor_hours:.1f}): ", c.labor_hours, allow_negative=False)
        c.labor_hours = lh

        hr = parse_float_input(f"  工时单价 (¥/小时) (当前: ¥{c.labor_hour_rate:.2f}): ", c.labor_hour_rate, allow_negative=False)
        c.labor_hour_rate = hr

        ok, msg = phase.validate_all()
        if not ok:
            print(f"\n  ❌ 数据校验失败: {msg}")
            print("     已取消本次修改，恢复原值")
            c.purchased_parts = old_purchased
            c.standard_parts = old_standard
            c.machining_fee = old_machining
            c.labor_hours = old_labor_hours
            c.labor_hour_rate = old_labor_rate
            pause()
            return False

        new_total = c.total
        if abs(new_total - old_total) < 0.01:
            print("\n  ℹ️  未检测到成本变化，数据未变动")
            pause()
            return False
        else:
            print(f"\n  ✅ 保存成功！")
            print(f"     总成本变化: ¥{old_total:,.2f} → ¥{new_total:,.2f}")
            diff = new_total - old_total
            diff_sign = "+" if diff > 0 else ""
            print(f"     差额: {diff_sign}¥{diff:,.2f}")

        print()
        print("  " + "-" * 50)
        print(f"  📊 【{phase.name}】阶段成本状态:")
        print(f"     外购件: ¥{c.purchased_parts:,.2f}")
        print(f"     标准件: ¥{c.standard_parts:,.2f}")
        print(f"     机加工费: ¥{c.machining_fee:,.2f}")
        print(f"     人工: {c.labor_hours:.1f}小时 × ¥{c.labor_hour_rate:.2f} = ¥{c.labor_cost:,.2f}")
        print(f"     成本合计: ¥{new_total:,.2f}")

        if phase.is_delayed():
            print(f"     延期状态: ❌ 已延期 {phase.delay_days()} 天")
        else:
            print(f"     延期状态: ✅ 正常（未延期）")

        if phase.budget.total > 0:
            if phase.is_over_budget():
                var = phase.budget_variance()
                var_pct = phase.budget_variance_percent()
                print(f"     预算状态: ❌ 已超支 +¥{var:,.2f} (+{var_pct:.2f}%)")
                print(f"     预算合计: ¥{phase.budget.total:,.2f}")
            else:
                remaining = phase.budget.total - phase.cost.total
                print(f"     预算状态: ✅ 正常（未超支）")
                print(f"     预算合计: ¥{phase.budget.total:,.2f}")
                print(f"     剩余预算: ¥{remaining:,.2f}")
        else:
            print(f"     预算状态: ℹ️  未设置预算")

        if phase.owner:
            print(f"     负责人: {phase.owner}")

        pause()
        return True

    def _edit_phase_budget(self):
        p = self.current_project
        if not p:
            return

        clear_screen()
        print("\n" + "=" * 60)
        print("  编辑阶段预算")
        print("=" * 60)
        print()

        for i, phase in enumerate(p.phases, 1):
            status = ""
            if phase.is_over_budget():
                status = " ❌ 超支"
            elif phase.budget.total > 0:
                status = " ✅ 正常"
            print(f"    {i}. {phase.name} - 预算: ¥{phase.budget.total:,.2f}{status}")

        choice = input("\n  选择要编辑的阶段 (0 取消): ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(p.phases):
                phase = p.phases[idx - 1]
                saved = self._edit_single_phase_budget(phase)
                if saved:
                    self.repo.update(p)
            else:
                print("  ❌ 无效的阶段序号")
                pause()
        except ValueError:
            print("  ❌ 请输入数字")
            pause()

    def _edit_single_phase_budget(self, phase: Phase) -> bool:
        clear_screen()
        print("\n" + "=" * 60)
        print(f"  编辑【{phase.name}】阶段预算")
        print("=" * 60)
        print()

        b = phase.budget
        print(f"  当前预算明细:")
        print(f"    外购件预算: ¥{b.purchased_parts:,.2f}")
        print(f"    标准件预算: ¥{b.standard_parts:,.2f}")
        print(f"    机加工费预算: ¥{b.machining_fee:,.2f}")
        print(f"    人工成本预算: ¥{b.labor_cost:,.2f}")
        print(f"    预算合计: ¥{b.total:,.2f}")
        print()

        if phase.cost.total > 0:
            over = "超支" if phase.is_over_budget() else "节余"
            var_sign = "+" if phase.budget_variance() > 0 else ""
            print(f"  实际成本: ¥{phase.cost.total:,.2f}")
            print(f"  偏差: {var_sign}¥{phase.budget_variance():,.2f} ({var_sign}{phase.budget_variance_percent():.2f}%) - {over}")
            print()

        print("  请输入新值（直接回车保留当前值）:")
        print()

        old_pp = b.purchased_parts
        old_sp = b.standard_parts
        old_mf = b.machining_fee
        old_lc = b.labor_cost
        old_total = b.total

        pp = parse_float_input(f"  外购件预算 (当前: ¥{b.purchased_parts:,.2f}): ", b.purchased_parts, allow_negative=False)
        b.purchased_parts = pp

        sp = parse_float_input(f"  标准件预算 (当前: ¥{b.standard_parts:,.2f}): ", b.standard_parts, allow_negative=False)
        b.standard_parts = sp

        mf = parse_float_input(f"  机加工费预算 (当前: ¥{b.machining_fee:,.2f}): ", b.machining_fee, allow_negative=False)
        b.machining_fee = mf

        lc = parse_float_input(f"  人工成本预算 (当前: ¥{b.labor_cost:,.2f}): ", b.labor_cost, allow_negative=False)
        b.labor_cost = lc

        ok, msg = phase.validate_all()
        if not ok:
            print(f"\n  ❌ 数据校验失败: {msg}")
            print("     已取消本次修改，恢复原值")
            b.purchased_parts = old_pp
            b.standard_parts = old_sp
            b.machining_fee = old_mf
            b.labor_cost = old_lc
            pause()
            return False

        new_total = b.total
        if abs(new_total - old_total) < 0.01:
            print("\n  ℹ️  未检测到预算变化，数据未变动")
            pause()
            return False
        else:
            print(f"\n  ✅ 保存成功！")
            print(f"     预算合计: ¥{old_total:,.2f} → ¥{new_total:,.2f}")
            diff = new_total - old_total
            diff_sign = "+" if diff > 0 else ""
            print(f"     差额: {diff_sign}¥{diff:,.2f}")

        print()
        print("  " + "-" * 50)
        print(f"  📊 【{phase.name}】阶段预算状态:")
        print(f"     外购件预算: ¥{b.purchased_parts:,.2f}")
        print(f"     标准件预算: ¥{b.standard_parts:,.2f}")
        print(f"     机加工费预算: ¥{b.machining_fee:,.2f}")
        print(f"     人工成本预算: ¥{b.labor_cost:,.2f}")
        print(f"     预算合计: ¥{new_total:,.2f}")

        if phase.cost.total > 0:
            print(f"     实际成本: ¥{phase.cost.total:,.2f}")
            if phase.is_over_budget():
                var = phase.budget_variance()
                var_pct = phase.budget_variance_percent()
                print(f"     预算状态: ❌ 已超支 +¥{var:,.2f} (+{var_pct:.2f}%)")
            else:
                remaining = phase.budget.total - phase.cost.total
                print(f"     预算状态: ✅ 正常（未超支）")
                print(f"     剩余预算: ¥{remaining:,.2f}")

        if phase.is_delayed():
            print(f"     延期状态: ❌ 已延期 {phase.delay_days()} 天")
        else:
            print(f"     延期状态: ✅ 正常（未延期）")

        if phase.owner:
            print(f"     负责人: {phase.owner}")

        pause()
        return True

    def _show_gantt_chart(self):
        if self.current_project:
            self._show_gantt_for_project(self.current_project)
        else:
            projects = self.repo.get_all()
            if not projects:
                print("\n  暂无项目")
                pause()
                return
            print("\n  请先选择一个项目，或进入项目详情查看甘特图")
            pause()

    def _show_gantt_for_project(self, project: Project):
        clear_screen()
        chart = GanttChart(project)
        print(chart.render())
        pause()

    def _show_cost_report(self):
        if self.current_project:
            self._show_cost_for_project(self.current_project)
        else:
            projects = self.repo.get_all()
            if not projects:
                print("\n  暂无项目")
                pause()
                return
            print("\n  请先选择一个项目，或进入项目详情查看成本报告")
            pause()

    def _show_cost_for_project(self, project: Project):
        clear_screen()
        report = CostReport(project)
        print(report.generate())
        pause()

    def _export_html_report(self):
        if self.current_project:
            self._export_html_for_project(self.current_project)
        else:
            projects = self.repo.get_all()
            if not projects:
                print("\n  暂无项目")
                pause()
                return
            print("\n  请先选择一个项目，或进入项目详情导出报告")
            pause()

    def _export_html_for_project(self, project: Project):
        exporter = HtmlExporter(project)
        filepath = exporter.export(".")
        print(f"\n  ✅ HTML报告已导出: {os.path.abspath(filepath)}")
        print(f"     请在浏览器中打开查看")
        pause()

    def _delete_project(self):
        clear_screen()
        projects = self.repo.get_all()

        if not projects:
            print("\n  暂无项目可删除")
            pause()
            return

        print("\n" + "=" * 60)
        print("  删除项目")
        print("=" * 60)
        print()

        for i, p in enumerate(projects, 1):
            print(f"    {i}. {p.name} (ID: {p.id})")

        choice = input("\n  请输入要删除的项目序号 (0 取消): ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(projects):
                project = projects[idx - 1]
                confirm = input(f"\n  ⚠️  确定要删除项目【{project.name}】吗？(y/N): ").strip().lower()
                if confirm == "y":
                    self.repo.delete(project.id)
                    if self.current_project and self.current_project.id == project.id:
                        self.current_project = None
                    print(f"\n  ✅ 项目【{project.name}】已删除")
                else:
                    print("\n  已取消删除")
            else:
                print("  ❌ 无效的序号")
        except ValueError:
            print("  ❌ 请输入数字")

        pause()

    def _show_all_delayed(self):
        clear_screen()
        projects = self.repo.get_all()

        print("\n" + "=" * 80)
        print("  所有延期项目总览")
        print("=" * 80)

        has_delayed = False
        for project in projects:
            delayed_phases = project.get_delayed_phases()
            if delayed_phases:
                has_delayed = True
                print(f"\n  📁 项目: {project.name} (ID: {project.id})")
                for phase in delayed_phases:
                    print(
                        f"     ❌ {phase.name} - 延期 {phase.delay_days()} 天 | "
                        f"负责人: {phase.owner or '未指派'} | "
                        f"完成度: {phase.completion_percent:.1f}%"
                    )

        if not has_delayed:
            print("\n  ✅ 很好！目前没有延期的项目")

        print()
        pause()

    def _show_delayed_for_project(self, project: Project):
        clear_screen()
        print("\n" + "=" * 60)
        print(f"  延期详情 - {project.name}")
        print("=" * 60)

        delayed = project.get_delayed_phases()
        if not delayed:
            print("\n  ✅ 该项目没有延期的阶段")
        else:
            print()
            for phase in delayed:
                print(f"  ❌ {phase.name} 阶段")
                print(f"     计划完成: {phase.planned_end.strftime('%Y-%m-%d') if phase.planned_end else '未设置'}")
                if phase.actual_end:
                    print(f"     实际完成: {phase.actual_end.strftime('%Y-%m-%d')}")
                else:
                    print(f"     实际完成: 尚未完成")
                print(f"     延期天数: {phase.delay_days()} 天")
                print(f"     负责人: {phase.owner or '未指派'}")
                print(f"     完成度: {phase.completion_percent:.1f}%")
                print()

        pause()

    def _show_dashboard(self):
        status_filter = "all"
        owner_filter = "all"

        while True:
            clear_screen()
            projects = self.repo.get_all()
            dashboard = Dashboard(projects)

            print(dashboard.render(status_filter, owner_filter))
            print("-" * 100)

            cmd = input("请输入操作 (s=状态筛选 / o=负责人筛选 / 0=返回): ").strip().lower()

            if cmd == "0":
                break
            elif cmd.startswith("s="):
                status = cmd[2:].strip()
                if status in ["all", "delayed", "normal", "over_budget"]:
                    status_filter = status
                else:
                    print("  ❌ 无效的状态筛选值，可选: all/delayed/normal/over_budget")
                    pause()
            elif cmd == "s":
                print("\n  状态筛选选项:")
                print("    all - 全部项目")
                print("    delayed - 延期项目")
                print("    normal - 正常项目（未延期）")
                print("    over_budget - 超支项目")
                s = input("\n  请输入状态筛选值: ").strip().lower()
                if s in ["all", "delayed", "normal", "over_budget"]:
                    status_filter = s
                else:
                    print("  ❌ 无效的状态")
                    pause()
            elif cmd.startswith("o="):
                owner = cmd[2:].strip()
                owners = dashboard.get_all_owners()
                if owner == "all" or owner in owners:
                    owner_filter = owner
                else:
                    print(f"  ❌ 未找到负责人 '{owner}'")
                    print(f"  可用负责人: {', '.join(owners) if owners else '无'}")
                    pause()
            elif cmd == "o":
                owners = dashboard.get_all_owners()
                print(f"\n  负责人列表 (共 {len(owners)} 人):")
                if owners:
                    for i, owner in enumerate(owners, 1):
                        print(f"    {i}. {owner}")
                    print(f"    0. 显示全部")
                else:
                    print("    暂无负责人数据")

                choice = input("\n  请选择负责人序号: ").strip()
                if choice == "0":
                    owner_filter = "all"
                else:
                    try:
                        idx = int(choice)
                        if 1 <= idx <= len(owners):
                            owner_filter = owners[idx - 1]
                        else:
                            print("  ❌ 无效的序号")
                            pause()
                    except ValueError:
                        print("  ❌ 请输入数字")
                        pause()
            elif cmd:
                print("  ❌ 无效的操作")
                pause()


def main():
    try:
        app = ProjectTrackerApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n已退出系统")
        sys.exit(0)


if __name__ == "__main__":
    main()
