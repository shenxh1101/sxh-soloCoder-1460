import sys
import platform
from typing import List, Tuple

from models import Project, Phase


DELAY_THRESHOLD_DAYS = 3


class Reminder:
    def __init__(self):
        self.system = platform.system()

    def beep(self) -> None:
        if self.system == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 500)
                winsound.Beep(800, 300)
                winsound.Beep(1200, 500)
            except ImportError:
                print("\a", end="", flush=True)
        else:
            print("\a", end="", flush=True)
            try:
                import subprocess
                subprocess.run(["echo", "-ne", "\007"], capture_output=True)
            except Exception:
                pass

    def check_overdue(self, projects: List[Project]) -> List[Tuple[Project, Phase]]:
        overdue_items = []
        for project in projects:
            delayed_phases = project.get_delayed_phases(min_days=DELAY_THRESHOLD_DAYS)
            for phase in delayed_phases:
                overdue_items.append((project, phase))
        return overdue_items

    def show_reminder(self, projects: List[Project]) -> bool:
        overdue_items = self.check_overdue(projects)

        if not overdue_items:
            return False

        self.beep()

        print("\n" + "=" * 80)
        print("  ⚠️  逾期催办提醒")
        print("=" * 80)

        current_project = None
        for project, phase in overdue_items:
            if project != current_project:
                current_project = project
                print(f"\n  项目: {project.name} (ID: {project.id})")

            delay_days = phase.delay_days()
            owner = phase.owner or "未指定"

            print(
                f"    ❌ 【{phase.name}】阶段延期 {delay_days} 天"
                f" | 负责人: {owner}"
                f" | 完成度: {phase.completion_percent:.1f}%"
            )

            if phase.planned_end:
                print(f"       计划完成日期: {phase.planned_end.strftime('%Y-%m-%d')}")

        print("\n" + "=" * 80)
        print(f"  共发现 {len(overdue_items)} 个延期超过 {DELAY_THRESHOLD_DAYS} 天的阶段")
        print("=" * 80 + "\n")

        return True
