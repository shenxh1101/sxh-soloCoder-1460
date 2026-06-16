import sys
import os
from datetime import date, datetime
from typing import Optional

from models import Project, Phase, PHASE_NAMES
from repository import ProjectRepository
from gantt import GanttChart
from cost_report import CostReport
from html_exporter import HtmlExporter
from reminder import Reminder


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


def parse_float_input(prompt: str, default: float = 0.0) -> float:
    while True:
        s = input(prompt).strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            print("  ❌ 请输入有效的数字")


def parse_int_input(prompt: str, default: int = 0) -> int:
    while True:
        s = input(prompt).strip()
        if not s:
            return default
        try:
            return int(s)
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
            print(f"当前系统中共有 {len(projects)} 个项目")
            print()

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
                self._show_gantt_chart()
            elif choice == "6":
                self._show_cost_report()
            elif choice == "7":
                self._export_html_report()
            elif choice == "8":
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
        print()
        print("  【数据录入与查看】")
        print("    5. 查看甘特图")
        print("    6. 查看成本报告")
        print("    7. 导出HTML报告")
        print("    8. 查看所有延期项目")
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
            print("    2. 编辑阶段成本")
            print("    3. 查看甘特图")
            print("    4. 查看成本报告")
            print("    5. 导出HTML报告")
            print("    6. 查看延期详情")
            print("    0. 返回主菜单")
            print("-" * 80)

            choice = input("请选择操作: ").strip()

            if choice == "1":
                self._edit_phase_progress()
            elif choice == "2":
                self._edit_phase_cost()
            elif choice == "3":
                self._show_gantt_for_project(p)
            elif choice == "4":
                self._show_cost_for_project(p)
            elif choice == "5":
                self._export_html_for_project(p)
            elif choice == "6":
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
        print(f"  编辑【{phase.name}】阶段")
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
            phase.completion_percent
        )
        phase.completion_percent = min(100.0, max(0.0, completion))

        if phase.actual_end:
            phase.completion_percent = 100.0

        print("\n  ✅ 阶段信息已更新")
        if phase.is_delayed():
            print(f"     ⚠️  注意: 该阶段已延期 {phase.delay_days()} 天")
        pause()

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

        print("  请输入新值（直接回车保留当前值）:")
        print()

        pp = parse_float_input(f"  外购件费用 (当前: ¥{c.purchased_parts:,.2f}): ", c.purchased_parts)
        c.purchased_parts = pp

        sp = parse_float_input(f"  标准件费用 (当前: ¥{c.standard_parts:,.2f}): ", c.standard_parts)
        c.standard_parts = sp

        mf = parse_float_input(f"  机加工费 (当前: ¥{c.machining_fee:,.2f}): ", c.machining_fee)
        c.machining_fee = mf

        lh = parse_float_input(f"  工时 (小时) (当前: {c.labor_hours:.1f}): ", c.labor_hours)
        c.labor_hours = lh

        hr = parse_float_input(f"  工时单价 (¥/小时) (当前: ¥{c.labor_hour_rate:.2f}): ", c.labor_hour_rate)
        c.labor_hour_rate = hr

        print(f"\n  ✅ 成本信息已更新")
        print(f"     新的总成本: ¥{c.total:,.2f}")
        print(f"     其中人工成本: ¥{c.labor_cost:,.2f}")
        pause()

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


def main():
    try:
        app = ProjectTrackerApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n已退出系统")
        sys.exit(0)


if __name__ == "__main__":
    main()
