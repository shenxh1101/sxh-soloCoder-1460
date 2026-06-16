import os
from datetime import date
from typing import List

from models import Project, Phase


class HtmlExporter:
    def __init__(self, project: Project):
        self.project = project

    def export(self, output_dir: str = ".") -> str:
        filename = f"project_report_{self.project.id}.html"
        filepath = os.path.join(output_dir, filename)

        html = self._generate_html()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return filepath

    def _generate_html(self) -> str:
        p = self.project

        phase_rows = ""
        for phase in p.phases:
            status_class = "normal"
            status_text = "正常"
            if phase.is_delayed():
                status_class = "delayed"
                status_text = f"延期 {phase.delay_days()} 天"
            elif phase.completion_percent >= 100:
                status_class = "completed"
                status_text = "已完成"
            elif phase.completion_percent > 0:
                status_class = "in-progress"
                status_text = f"进行中 {phase.completion_percent:.0f}%"
            else:
                status_text = "未开始"

            phase_rows += f"""
            <tr class="phase-row">
                <td class="phase-name">{phase.name}</td>
                <td>{phase.planned_start.strftime('%Y-%m-%d') if phase.planned_start else '-'}</td>
                <td>{phase.planned_end.strftime('%Y-%m-%d') if phase.planned_end else '-'}</td>
                <td>{phase.actual_start.strftime('%Y-%m-%d') if phase.actual_start else '-'}</td>
                <td>{phase.actual_end.strftime('%Y-%m-%d') if phase.actual_end else '-'}</td>
                <td>{phase.owner or '-'}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill {status_class}" style="width: {phase.completion_percent}%"></div>
                    </div>
                    <span class="progress-text">{phase.completion_percent:.1f}%</span>
                </td>
                <td class="status-{status_class}">{status_text}</td>
            </tr>
            """

        cost_rows = ""
        total_purchased = 0.0
        total_standard = 0.0
        total_machining = 0.0
        total_labor = 0.0
        total_cost = 0.0

        for phase in p.phases:
            c = phase.cost
            total_purchased += c.purchased_parts
            total_standard += c.standard_parts
            total_machining += c.machining_fee
            total_labor += c.labor_cost
            total_cost += c.total

            cost_rows += f"""
            <tr class="phase-row">
                <td class="phase-name">{phase.name}</td>
                <td>¥{c.purchased_parts:,.2f}</td>
                <td>¥{c.standard_parts:,.2f}</td>
                <td>¥{c.machining_fee:,.2f}</td>
                <td>¥{c.labor_cost:,.2f}</td>
                <td><strong>¥{c.total:,.2f}</strong></td>
            </tr>
            """

        gantt_html = self._generate_gantt_chart()

        profit_status = "positive" if p.gross_profit >= 0 else "negative"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>项目报告 - {p.name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f7fa;
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 30px;
        }}
        h1 {{
            font-size: 28px;
            color: #1a1a2e;
            margin-bottom: 5px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #4361ee;
        }}
        .card.profit {{ border-left-color: #2ecc71; }}
        .card.cost {{ border-left-color: #e74c3c; }}
        .card.progress {{ border-left-color: #f39c12; }}
        .card-label {{
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 24px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .card-value.positive {{ color: #2ecc71; }}
        .card-value.negative {{ color: #e74c3c; }}
        h2 {{
            font-size: 20px;
            color: #1a1a2e;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            font-size: 13px;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .phase-name {{ font-weight: 600; color: #1a1a2e; }}
        .progress-bar {{
            width: 100%;
            height: 10px;
            background: #e9ecef;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 5px;
        }}
        .progress-fill {{
            height: 100%;
            transition: width 0.3s ease;
        }}
        .progress-fill.normal {{ background: #4361ee; }}
        .progress-fill.delayed {{ background: #e74c3c; }}
        .progress-fill.completed {{ background: #2ecc71; }}
        .progress-fill.in-progress {{ background: #f39c12; }}
        .progress-text {{
            font-size: 12px;
            color: #666;
        }}
        .status-delayed {{ color: #e74c3c; font-weight: 600; }}
        .status-completed {{ color: #2ecc71; font-weight: 600; }}
        .status-in-progress {{ color: #f39c12; font-weight: 600; }}
        .status-normal {{ color: #666; }}
        .gantt-container {{
            overflow-x: auto;
            padding: 20px 0;
        }}
        .gantt-row {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}
        .gantt-label {{
            width: 60px;
            font-size: 13px;
            font-weight: 500;
            flex-shrink: 0;
        }}
        .gantt-bar-container {{
            flex: 1;
            height: 24px;
            background: #f0f2f5;
            border-radius: 4px;
            position: relative;
            margin-left: 10px;
        }}
        .gantt-bar-planned {{
            position: absolute;
            top: 3px;
            height: 18px;
            background: rgba(67, 97, 238, 0.3);
            border: 1px dashed #4361ee;
            border-radius: 3px;
        }}
        .gantt-bar-actual {{
            position: absolute;
            top: 3px;
            height: 18px;
            background: #4361ee;
            border-radius: 3px;
        }}
        .gantt-bar-actual.delayed {{ background: #e74c3c; }}
        .gantt-bar-actual.completed {{ background: #2ecc71; }}
        .gantt-date-scale {{
            display: flex;
            margin-left: 70px;
            font-size: 11px;
            color: #999;
            margin-bottom: 10px;
        }}
        .gantt-date-scale span {{
            flex: 1;
            text-align: center;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #999;
            text-align: center;
        }}
        .cost-chart {{
            display: flex;
            align-items: flex-end;
            height: 200px;
            gap: 30px;
            padding: 20px 0;
            margin-bottom: 20px;
        }}
        .cost-bar-group {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .cost-bars {{
            display: flex;
            gap: 5px;
            align-items: flex-end;
            height: 180px;
            margin-bottom: 10px;
        }}
        .cost-bar {{
            width: 40px;
            border-radius: 4px 4px 0 0;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            color: white;
            font-size: 11px;
            padding-top: 5px;
        }}
        .cost-bar.purchased {{ background: #4361ee; }}
        .cost-bar.standard {{ background: #7209b7; }}
        .cost-bar.machining {{ background: #f72585; }}
        .cost-bar.labor {{ background: #4cc9f0; }}
        .cost-label {{
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
        .chart-legend {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 20px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #666;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{p.name}</h1>
        <p class="subtitle">项目ID: {p.id} | 目标交付日期: {p.target_delivery_date.strftime('%Y-%m-%d') if p.target_delivery_date else '未设置'} | 报告生成时间: {date.today().strftime('%Y-%m-%d')}</p>

        <div class="summary-cards">
            <div class="card">
                <div class="card-label">合同金额</div>
                <div class="card-value">¥{p.contract_amount:,.2f}</div>
            </div>
            <div class="card cost">
                <div class="card-label">总成本</div>
                <div class="card-value">¥{p.total_cost:,.2f}</div>
            </div>
            <div class="card profit">
                <div class="card-label">毛利 / 毛利率</div>
                <div class="card-value {profit_status}">¥{p.gross_profit:,.2f} ({p.gross_margin:.2f}%)</div>
            </div>
            <div class="card progress">
                <div class="card-label">整体进度</div>
                <div class="card-value">{p.overall_completion:.1f}%</div>
            </div>
        </div>

        <h2>📊 项目进度甘特图</h2>
        {gantt_html}

        <h2>📋 各阶段进度详情</h2>
        <table>
            <thead>
                <tr>
                    <th>阶段</th>
                    <th>计划开始</th>
                    <th>计划结束</th>
                    <th>实际开始</th>
                    <th>实际结束</th>
                    <th>负责人</th>
                    <th>完成度</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                {phase_rows}
            </tbody>
        </table>

        <h2>💰 成本明细</h2>
        <table>
            <thead>
                <tr>
                    <th>阶段</th>
                    <th>外购件</th>
                    <th>标准件</th>
                    <th>机加工费</th>
                    <th>人工成本</th>
                    <th>合计</th>
                </tr>
            </thead>
            <tbody>
                {cost_rows}
                <tr style="font-weight: 600; background: #f8f9fa;">
                    <td class="phase-name">总计</td>
                    <td>¥{total_purchased:,.2f}</td>
                    <td>¥{total_standard:,.2f}</td>
                    <td>¥{total_machining:,.2f}</td>
                    <td>¥{total_labor:,.2f}</td>
                    <td>¥{total_cost:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <h2>📈 成本构成图</h2>
        <div class="chart-legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #4361ee;"></div>
                <span>外购件</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #7209b7;"></div>
                <span>标准件</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f72585;"></div>
                <span>机加工费</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #4cc9f0;"></div>
                <span>人工成本</span>
            </div>
        </div>
        {self._generate_cost_chart()}

        <div class="footer">
            本报告由项目进度与成本跟踪系统自动生成
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_gantt_chart(self) -> str:
        p = self.project

        all_dates = []
        for phase in p.phases:
            if phase.planned_start:
                all_dates.append(phase.planned_start)
            if phase.planned_end:
                all_dates.append(phase.planned_end)
            if phase.actual_start:
                all_dates.append(phase.actual_start)
            if phase.actual_end:
                all_dates.append(phase.actual_end)

        if not all_dates:
            return "<p>暂无进度数据</p>"

        min_date = min(all_dates)
        max_date = max(all_dates)
        total_days = (max_date - min_date).days
        if total_days == 0:
            total_days = 1

        num_ticks = 6
        date_ticks = []
        for i in range(num_ticks):
            d = min_date + (max_date - min_date) * i / (num_ticks - 1)
            date_ticks.append(d.strftime("%m-%d"))

        date_scale_html = '<div class="gantt-date-scale">'
        for d in date_ticks:
            date_scale_html += f"<span>{d}</span>"
        date_scale_html += "</div>"

        rows_html = ""
        for phase in p.phases:
            planned_bar = ""
            actual_bar = ""

            if phase.planned_start and phase.planned_end:
                left_pct = ((phase.planned_start - min_date).days / total_days) * 100
                width_pct = ((phase.planned_end - phase.planned_start).days / total_days) * 100
                planned_bar = f'<div class="gantt-bar-planned" style="left: {left_pct}%; width: {width_pct}%;"></div>'

            actual_class = ""
            if phase.is_delayed():
                actual_class = "delayed"
            elif phase.completion_percent >= 100:
                actual_class = "completed"

            if phase.actual_start and phase.actual_end:
                left_pct = ((phase.actual_start - min_date).days / total_days) * 100
                width_pct = ((phase.actual_end - phase.actual_start).days / total_days) * 100
                actual_bar = f'<div class="gantt-bar-actual {actual_class}" style="left: {left_pct}%; width: {width_pct}%;"></div>'
            elif phase.actual_start and not phase.actual_end:
                from datetime import date as _date
                today = _date.today()
                left_pct = ((phase.actual_start - min_date).days / total_days) * 100
                end_date = min(today, max_date)
                width_pct = max(1, ((end_date - phase.actual_start).days / total_days) * 100) * (phase.completion_percent / 100)
                actual_bar = f'<div class="gantt-bar-actual {actual_class}" style="left: {left_pct}%; width: {width_pct}%;"></div>'

            rows_html += f"""
            <div class="gantt-row">
                <div class="gantt-label">{phase.name}</div>
                <div class="gantt-bar-container">
                    {planned_bar}
                    {actual_bar}
                </div>
            </div>
            """

        return f"""
        <div class="gantt-container">
            {date_scale_html}
            {rows_html}
        </div>
        """

    def _generate_cost_chart(self) -> str:
        p = self.project

        max_cost = max(
            (max(phase.cost.purchased_parts, phase.cost.standard_parts,
                 phase.cost.machining_fee, phase.cost.labor_cost)
             for phase in p.phases),
            default=1
        )
        if max_cost == 0:
            max_cost = 1

        chart_html = '<div class="cost-chart">'

        for phase in p.phases:
            c = phase.cost
            h_purchased = max(2, (c.purchased_parts / max_cost) * 160)
            h_standard = max(2, (c.standard_parts / max_cost) * 160)
            h_machining = max(2, (c.machining_fee / max_cost) * 160)
            h_labor = max(2, (c.labor_cost / max_cost) * 160)

            chart_html += f"""
            <div class="cost-bar-group">
                <div class="cost-bars">
                    <div class="cost-bar purchased" style="height: {h_purchased}px;">
                        {f"¥{c.purchased_parts:,.0f}" if c.purchased_parts > 0 else ""}
                    </div>
                    <div class="cost-bar standard" style="height: {h_standard}px;">
                        {f"¥{c.standard_parts:,.0f}" if c.standard_parts > 0 else ""}
                    </div>
                    <div class="cost-bar machining" style="height: {h_machining}px;">
                        {f"¥{c.machining_fee:,.0f}" if c.machining_fee > 0 else ""}
                    </div>
                    <div class="cost-bar labor" style="height: {h_labor}px;">
                        {f"¥{c.labor_cost:,.0f}" if c.labor_cost > 0 else ""}
                    </div>
                </div>
                <div class="cost-label">{phase.name}</div>
            </div>
            """

        chart_html += "</div>"
        return chart_html
