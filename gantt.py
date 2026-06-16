from datetime import date, timedelta
from typing import List, Tuple

from models import Project, Phase


class GanttChart:
    def __init__(self, project: Project):
        self.project = project
        self.chart_width = 60

    def _get_date_range(self) -> Tuple[date, date]:
        all_dates = []
        for phase in self.project.phases:
            if phase.planned_start:
                all_dates.append(phase.planned_start)
            if phase.planned_end:
                all_dates.append(phase.planned_end)
            if phase.actual_start:
                all_dates.append(phase.actual_start)
            if phase.actual_end:
                all_dates.append(phase.actual_end)

        if not all_dates:
            today = date.today()
            return today, today + timedelta(days=30)

        return min(all_dates), max(all_dates)

    def _date_to_col(self, d: date, start: date, end: date) -> float:
        total_days = (end - start).days
        if total_days == 0:
            return 0
        days_offset = (d - start).days
        return (days_offset / total_days) * self.chart_width

    def _format_date(self, d: date) -> str:
        return d.strftime("%m-%d")

    def render(self) -> str:
        lines = []
        project_name = self.project.name
        lines.append(f"\n{'=' * 80}")
        lines.append(f"  项目甘特图: {project_name}")
        lines.append(f"{'=' * 80}")

        start_date, end_date = self._get_date_range()
        total_days = (end_date - start_date).days
        if total_days < 7:
            end_date = start_date + timedelta(days=7)
            total_days = 7

        lines.append(f"\n  时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        lines.append(f"  总天数: {total_days} 天\n")

        header = " " * 10
        markers = []
        interval = max(1, total_days // 8)
        for i in range(0, total_days + 1, interval):
            d = start_date + timedelta(days=i)
            col = int(self._date_to_col(d, start_date, end_date))
            markers.append((col, self._format_date(d)))

        ruler = " " * 10
        prev_col = 0
        for col, label in markers:
            spaces = col - prev_col
            ruler += " " * spaces + "|"
            prev_col = col + 1
        lines.append(ruler)

        date_labels = " " * 10
        prev_col = 0
        for col, label in markers:
            spaces = col - prev_col
            date_labels += " " * max(0, spaces - len(label) // 2) + label
            prev_col = col + len(label)
        lines.append(date_labels)
        lines.append("")

        lines.append("  " + "-" * (self.chart_width + 12))
        lines.append("  图例: [-- 计划 --]  <== 实际 ==>  黄色:进行中  红色:延期")
        lines.append("  " + "-" * (self.chart_width + 12))
        lines.append("")

        for phase in self.project.phases:
            phase_line = self._render_phase_line(phase, start_date, end_date)
            lines.append(phase_line)

        lines.append("")
        lines.append(f"  整体进度: {self.project.overall_completion:.1f}%")
        lines.append(f"  目标交付: {self.project.target_delivery_date.strftime('%Y-%m-%d') if self.project.target_delivery_date else '未设置'}")
        lines.append("")

        return "\n".join(lines)

    def _render_phase_line(self, phase: Phase, start: date, end: date) -> str:
        name_label = phase.name.ljust(6)

        bar = [" "] * (self.chart_width + 2)

        if phase.planned_start and phase.planned_end:
            s_col = int(self._date_to_col(phase.planned_start, start, end))
            e_col = int(self._date_to_col(phase.planned_end, start, end))
            s_col = max(0, min(s_col, self.chart_width))
            e_col = max(0, min(e_col, self.chart_width))
            for i in range(s_col, e_col + 1):
                if 0 <= i < len(bar):
                    if bar[i] == " ":
                        bar[i] = "-"

        has_actual = False
        actual_s = actual_e = 0
        if phase.actual_start and phase.actual_end:
            actual_s = int(self._date_to_col(phase.actual_start, start, end))
            actual_e = int(self._date_to_col(phase.actual_end, start, end))
            has_actual = True
        elif phase.actual_start and not phase.actual_end:
            actual_s = int(self._date_to_col(phase.actual_start, start, end))
            today_col = int(self._date_to_col(date.today(), start, end))
            actual_e = int(actual_s + (today_col - actual_s) * (phase.completion_percent / 100))
            has_actual = True

        if has_actual:
            actual_s = max(0, min(actual_s, self.chart_width))
            actual_e = max(0, min(actual_e, self.chart_width))
            is_delayed = phase.is_delayed()
            for i in range(actual_s, actual_e + 1):
                if 0 <= i < len(bar):
                    if is_delayed:
                        bar[i] = "#"
                    else:
                        bar[i] = "="

        status_marker = ""
        if phase.is_delayed():
            status_marker = "  !! 延期 " + str(phase.delay_days()) + "天"
        elif phase.completion_percent >= 100:
            status_marker = "  已完成"
        elif phase.completion_percent > 0:
            status_marker = f"  进行中 {phase.completion_percent:.0f}%"
        else:
            status_marker = "  未开始"

        return f"  {name_label} |{''.join(bar)}|{status_marker}"
