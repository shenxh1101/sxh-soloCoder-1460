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

        delayed_phases = p.get_delayed_phases()
        over_budget_phases = p.get_over_budget_phases()

        warning_section = ""
        if delayed_phases or over_budget_phases:
            warning_items = ""
            if delayed_phases:
                for ph in delayed_phases:
                    warning_items += f"""
                    <div class="warning-item delayed-item">
                        <span class="warning-icon">⏰</span>
                        <span class="warning-text"><strong>{ph.name}</strong> 阶段延期 {ph.delay_days()} 天</span>
                        <span class="warning-owner">负责人：{ph.owner or '未指派'}</span>
                        <span class="warning-completion">完成度：{ph.completion_percent:.1f}%</span>
                    </div>
                    """
            if over_budget_phases:
                for ph in over_budget_phases:
                    warning_items += f"""
                    <div class="warning-item over-budget-item">
                        <span class="warning-icon">💰</span>
                        <span class="warning-text"><strong>{ph.name}</strong> 阶段超支 ¥{ph.budget_variance():,.2f} ({ph.budget_variance_percent():.2f}%)</span>
                        <span class="warning-owner">负责人：{ph.owner or '未指派'}</span>
                    </div>
                    """

            warning_section = f"""
            <div class="warning-section">
                <h3 class="warning-title">⚠️ 需关注事项</h3>
                {warning_items}
            </div>
            """

        summary_section = self._generate_summary_section(delayed_phases, over_budget_phases)

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

        budget_cost_rows = ""
        total_b_purchased = 0.0
        total_b_standard = 0.0
        total_b_machining = 0.0
        total_b_labor = 0.0
        total_b_total = 0.0
        total_a_purchased = 0.0
        total_a_standard = 0.0
        total_a_machining = 0.0
        total_a_labor = 0.0
        total_a_total = 0.0

        for phase in p.phases:
            b = phase.budget
            c = phase.cost

            total_b_purchased += b.purchased_parts
            total_b_standard += b.standard_parts
            total_b_machining += b.machining_fee
            total_b_labor += b.labor_cost
            total_b_total += b.total

            total_a_purchased += c.purchased_parts
            total_a_standard += c.standard_parts
            total_a_machining += c.machining_fee
            total_a_labor += c.labor_cost
            total_a_total += c.total

            var = phase.budget_variance()
            var_pct = phase.budget_variance_percent()
            var_class = "over-budget" if var > 0 else "under-budget"
            var_sign = "+" if var > 0 else ""

            budget_cost_rows += f"""
            <tr class="phase-row">
                <td class="phase-name" rowspan="2">{phase.name}</td>
                <td class="sub-header">预算</td>
                <td>¥{b.purchased_parts:,.2f}</td>
                <td>¥{b.standard_parts:,.2f}</td>
                <td>¥{b.machining_fee:,.2f}</td>
                <td>¥{b.labor_cost:,.2f}</td>
                <td><strong>¥{b.total:,.2f}</strong></td>
                <td rowspan="2" class="var-cell {var_class}">
                    <div>{var_sign}¥{var:,.2f}</div>
                    <div style="font-size: 11px;">({var_sign}{var_pct:.2f}%)</div>
                </td>
            </tr>
            <tr class="phase-row actual-row">
                <td class="sub-header">实际</td>
                <td>¥{c.purchased_parts:,.2f}</td>
                <td>¥{c.standard_parts:,.2f}</td>
                <td>¥{c.machining_fee:,.2f}</td>
                <td>¥{c.labor_cost:,.2f}</td>
                <td><strong>¥{c.total:,.2f}</strong></td>
            </tr>
            """

        total_var = total_a_total - total_b_total
        total_var_pct = 0.0
        if total_b_total > 0:
            total_var_pct = (total_var / total_b_total) * 100
        total_var_class = "over-budget" if total_var > 0 else "under-budget"
        total_var_sign = "+" if total_var > 0 else ""

        gantt_html = self._generate_gantt_chart()
        budget_chart_html = self._generate_budget_chart()
        cost_breakdown_html = self._generate_cost_breakdown_chart(total_a_purchased, total_a_standard, total_a_machining, total_a_labor, total_a_total)
        progress_chart_html = self._generate_progress_chart()

        profit_status = "positive" if p.gross_profit >= 0 else "negative"
        budget_status = "over" if p.is_over_budget else "under"
        budget_sign = "+" if p.budget_variance > 0 else ""

        days_delivery = p.days_to_delivery
        delivery_text = "已到期"
        delivery_class = "delayed"
        if days_delivery is not None:
            if days_delivery > 0:
                delivery_text = f"还剩 {days_delivery} 天"
                delivery_class = "normal" if days_delivery > 30 else "warning"
            elif days_delivery == 0:
                delivery_text = "今天交付"
                delivery_class = "warning"
            else:
                delivery_text = f"已逾期 {-days_delivery} 天"
                delivery_class = "delayed"

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
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
        }}
        .summary-box h2 {{
            color: white;
            margin: 0 0 15px 0;
            border-bottom: 1px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
            font-size: 18px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .summary-item {{
            background: rgba(255,255,255,0.15);
            padding: 12px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        .summary-item-label {{
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        .summary-item-value {{
            font-size: 20px;
            font-weight: 600;
        }}
        .summary-item-sub {{
            font-size: 11px;
            opacity: 0.85;
            margin-top: 3px;
        }}
        .delayed-summary {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.5);
        }}
        .warning-section {{
            background: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 25px;
        }}
        .warning-title {{
            font-size: 15px;
            color: #c2410c;
            margin-bottom: 12px;
        }}
        .warning-item {{
            display: flex;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px dashed #fed7aa;
            font-size: 14px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .warning-item:last-child {{ border-bottom: none; }}
        .warning-item.delayed-item .warning-icon {{ color: #dc2626; }}
        .warning-item.over-budget-item .warning-icon {{ color: #ea580c; }}
        .warning-icon {{
            font-size: 18px;
            margin-right: 10px;
        }}
        .warning-text {{ flex: 1; min-width: 200px; }}
        .warning-owner {{
            color: #666;
            font-size: 13px;
            background: #f3f4f6;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .warning-completion {{
            color: #0891b2;
            font-size: 13px;
            background: #cffafe;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }}
        .summary-cards.row2 {{
            grid-template-columns: repeat(4, 1fr);
        }}
        .card {{
            background: #f8f9fa;
            padding: 18px;
            border-radius: 10px;
            border-left: 4px solid #4361ee;
        }}
        .card.profit {{ border-left-color: #2ecc71; }}
        .card.cost {{ border-left-color: #e74c3c; }}
        .card.budget {{ border-left-color: #8b5cf6; }}
        .card.progress {{ border-left-color: #f39c12; }}
        .card.delivery {{ border-left-color: #06b6d4; }}
        .card.delivery.warning {{ border-left-color: #f59e0b; }}
        .card.delivery.delayed {{ border-left-color: #ef4444; }}
        .card-label {{
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 22px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .card-value.positive {{ color: #2ecc71; }}
        .card-value.negative {{ color: #e74c3c; }}
        .card-value.over {{ color: #e74c3c; }}
        .card-sub {{
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }}
        h2 {{
            font-size: 20px;
            color: #1a1a2e;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        h3 {{
            font-size: 16px;
            color: #1a1a2e;
            margin: 20px 0 12px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            font-size: 12px;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .phase-name {{ font-weight: 600; color: #1a1a2e; }}
        .sub-header {{
            font-size: 12px;
            color: #888;
            font-weight: 500;
        }}
        .actual-row {{ background: #fafafa; }}
        .var-cell {{
            text-align: right;
            font-weight: 600;
            font-size: 13px;
        }}
        .var-cell.over-budget {{ color: #e74c3c; }}
        .var-cell.under-budget {{ color: #2ecc71; }}
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
        .chart-container {{
            padding: 20px 0;
            margin-bottom: 20px;
        }}
        .chart-row {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }}
        .chart-label {{
            width: 80px;
            font-size: 13px;
            font-weight: 500;
            flex-shrink: 0;
        }}
        .chart-bars {{
            flex: 1;
            height: 28px;
            position: relative;
            margin: 0 10px;
        }}
        .chart-bar {{
            position: absolute;
            top: 0;
            height: 28px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: 500;
        }}
        .chart-bar.budget {{
            background: rgba(139, 92, 246, 0.5);
            border: 1px solid #8b5cf6;
            top: 14px;
            height: 14px;
        }}
        .chart-bar.actual {{
            background: #4361ee;
            top: 0;
            height: 14px;
        }}
        .chart-bar.actual.over {{ background: #e74c3c; }}
        .chart-value {{
            width: 100px;
            font-size: 12px;
            text-align: right;
            color: #666;
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
        .cost-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .cost-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .cost-item-title {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }}
        .cost-item-budget {{
            font-size: 13px;
            color: #8b5cf6;
            margin-bottom: 3px;
        }}
        .cost-item-actual {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .cost-item-var {{
            font-size: 11px;
            margin-top: 5px;
        }}
        .cost-item-var.over {{ color: #e74c3c; }}
        .cost-item-var.under {{ color: #2ecc71; }}
        .progress-ring-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 30px;
            padding: 20px 0;
        }}
        .progress-ring {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: conic-gradient(#4361ee var(--progress), #e9ecef 0);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        .progress-ring::before {{
            content: '';
            position: absolute;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: white;
        }}
        .progress-ring-text {{
            position: relative;
            z-index: 1;
            text-align: center;
        }}
        .progress-ring-value {{
            font-size: 24px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .progress-ring-label {{
            font-size: 11px;
            color: #666;
            margin-top: 2px;
        }}
        .cost-breakdown {{
            display: flex;
            align-items: center;
            gap: 40px;
            padding: 20px 0;
        }}
        .cost-pie {{
            width: 180px;
            height: 180px;
            border-radius: 50%;
            flex-shrink: 0;
            position: relative;
        }}
        .cost-pie::after {{
            content: '';
            position: absolute;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: white;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }}
        .cost-pie-center {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            z-index: 1;
        }}
        .cost-pie-value {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .cost-pie-label {{
            font-size: 11px;
            color: #666;
        }}
        .cost-legend {{
            flex: 1;
        }}
        .cost-legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .cost-legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            flex-shrink: 0;
        }}
        .cost-legend-text {{
            flex: 1;
            font-size: 13px;
        }}
        .cost-legend-amount {{
            font-size: 13px;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .cost-legend-pct {{
            font-size: 12px;
            color: #666;
            width: 60px;
            text-align: right;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .chart-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{p.name}</h1>
        <p class="subtitle">项目ID: {p.id} | 目标交付日期: {p.target_delivery_date.strftime('%Y-%m-%d') if p.target_delivery_date else '未设置'} | 报告生成时间: {date.today().strftime('%Y-%m-%d')}</p>

        {summary_section}

        {warning_section}

        <div class="chart-grid">
            <div>
                <h3>📈 整体进度</h3>
                {progress_chart_html}
            </div>
            <div>
                <h3>💰 成本构成</h3>
                {cost_breakdown_html}
            </div>
        </div>

        <div class="summary-cards">
            <div class="card">
                <div class="card-label">合同金额</div>
                <div class="card-value">¥{p.contract_amount:,.2f}</div>
            </div>
            <div class="card budget">
                <div class="card-label">总预算</div>
                <div class="card-value">¥{p.total_budget:,.2f}</div>
                <div class="card-sub">预算偏差: {budget_sign}¥{p.budget_variance:,.2f} ({budget_sign}{p.budget_variance_percent:.2f}%)</div>
            </div>
            <div class="card cost">
                <div class="card-label">实际总成本</div>
                <div class="card-value {budget_status}">¥{p.total_cost:,.2f}</div>
                <div class="card-sub">{"超支" if p.is_over_budget else "节余"}</div>
            </div>
        </div>

        <div class="summary-cards row2">
            <div class="card profit">
                <div class="card-label">毛利 / 毛利率</div>
                <div class="card-value {profit_status}">¥{p.gross_profit:,.2f}</div>
                <div class="card-sub">{p.gross_margin:.2f}%</div>
            </div>
            <div class="card progress">
                <div class="card-label">整体进度</div>
                <div class="card-value">{p.overall_completion:.1f}%</div>
                <div class="card-sub">{len(delayed_phases)} 个阶段延期</div>
            </div>
            <div class="card delivery {delivery_class}">
                <div class="card-label">距离交付</div>
                <div class="card-value">{delivery_text}</div>
                <div class="card-sub">目标: {p.target_delivery_date.strftime('%Y-%m-%d') if p.target_delivery_date else '未设置'}</div>
            </div>
            <div class="card">
                <div class="card-label">超支阶段</div>
                <div class="card-value {'over' if over_budget_phases else 'positive'}">{len(over_budget_phases)} 个</div>
                <div class="card-sub">共 {len(p.phases)} 个阶段</div>
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

        <h2>💰 预算 vs 实际成本对比</h2>

        <h3>按成本类别汇总</h3>
        <div class="cost-grid">
            <div class="cost-item">
                <div class="cost-item-title">外购件</div>
                <div class="cost-item-budget">预算 ¥{total_b_purchased:,.0f}</div>
                <div class="cost-item-actual">¥{total_a_purchased:,.0f}</div>
                <div class="cost-item-var {'over' if total_a_purchased > total_b_purchased else 'under'}">
                    {"+" if total_a_purchased > total_b_purchased else ""}{total_a_purchased - total_b_purchased:,.0f} ({(total_a_purchased - total_b_purchased)/total_b_purchased*100 if total_b_purchased > 0 else 0:+.2f}%)
                </div>
            </div>
            <div class="cost-item">
                <div class="cost-item-title">标准件</div>
                <div class="cost-item-budget">预算 ¥{total_b_standard:,.0f}</div>
                <div class="cost-item-actual">¥{total_a_standard:,.0f}</div>
                <div class="cost-item-var {'over' if total_a_standard > total_b_standard else 'under'}">
                    {"+" if total_a_standard > total_b_standard else ""}{total_a_standard - total_b_standard:,.0f} ({(total_a_standard - total_b_standard)/total_b_standard*100 if total_b_standard > 0 else 0:+.2f}%)
                </div>
            </div>
            <div class="cost-item">
                <div class="cost-item-title">机加工费</div>
                <div class="cost-item-budget">预算 ¥{total_b_machining:,.0f}</div>
                <div class="cost-item-actual">¥{total_a_machining:,.0f}</div>
                <div class="cost-item-var {'over' if total_a_machining > total_b_machining else 'under'}">
                    {"+" if total_a_machining > total_b_machining else ""}{total_a_machining - total_b_machining:,.0f} ({(total_a_machining - total_b_machining)/total_b_machining*100 if total_b_machining > 0 else 0:+.2f}%)
                </div>
            </div>
            <div class="cost-item">
                <div class="cost-item-title">人工成本</div>
                <div class="cost-item-budget">预算 ¥{total_b_labor:,.0f}</div>
                <div class="cost-item-actual">¥{total_a_labor:,.0f}</div>
                <div class="cost-item-var {'over' if total_a_labor > total_b_labor else 'under'}">
                    {"+" if total_a_labor > total_b_labor else ""}{total_a_labor - total_b_labor:,.0f} ({(total_a_labor - total_b_labor)/total_b_labor*100 if total_b_labor > 0 else 0:+.2f}%)
                </div>
            </div>
            <div class="cost-item" style="background: #f0fdf4; border: 1px solid #bbf7d0;">
                <div class="cost-item-title" style="font-weight: 600;">总计</div>
                <div class="cost-item-budget">预算 ¥{total_b_total:,.0f}</div>
                <div class="cost-item-actual" style="color: {'#e74c3c' if total_a_total > total_b_total else '#1a1a2e'};">¥{total_a_total:,.0f}</div>
                <div class="cost-item-var {'over' if total_a_total > total_b_total else 'under'}">
                    {total_var_sign}{total_var:,.0f} ({total_var_sign}{total_var_pct:.2f}%)
                </div>
            </div>
        </div>

        <h3>各阶段预算对比图</h3>
        {budget_chart_html}

        <h3>各阶段预算明细表</h3>
        <table>
            <thead>
                <tr>
                    <th>阶段</th>
                    <th>类型</th>
                    <th>外购件</th>
                    <th>标准件</th>
                    <th>机加工费</th>
                    <th>人工成本</th>
                    <th>合计</th>
                    <th>偏差</th>
                </tr>
            </thead>
            <tbody>
                {budget_cost_rows}
                <tr style="font-weight: 600; background: #f0fdf4;">
                    <td class="phase-name" rowspan="2">总计</td>
                    <td class="sub-header">预算</td>
                    <td>¥{total_b_purchased:,.2f}</td>
                    <td>¥{total_b_standard:,.2f}</td>
                    <td>¥{total_b_machining:,.2f}</td>
                    <td>¥{total_b_labor:,.2f}</td>
                    <td>¥{total_b_total:,.2f}</td>
                    <td rowspan="2" class="var-cell {total_var_class}">
                        <div>{total_var_sign}¥{total_var:,.2f}</div>
                        <div style="font-size: 11px;">({total_var_sign}{total_var_pct:.2f}%)</div>
                    </td>
                </tr>
                <tr style="font-weight: 600; background: #f0fdf4;">
                    <td class="sub-header">实际</td>
                    <td>¥{total_a_purchased:,.2f}</td>
                    <td>¥{total_a_standard:,.2f}</td>
                    <td>¥{total_a_machining:,.2f}</td>
                    <td>¥{total_a_labor:,.2f}</td>
                    <td>¥{total_a_total:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="footer">
            本报告由项目进度与成本跟踪系统自动生成
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_summary_section(self, delayed_phases: List[Phase], over_budget_phases: List[Phase]) -> str:
        p = self.project

        delayed_html = ""
        if delayed_phases:
            items = []
            for ph in delayed_phases:
                items.append(
                    f"{ph.name}({ph.delay_days()}天, {ph.completion_percent:.0f}%, {ph.owner or '未指派'})"
                )
            delayed_html = f'<div class="summary-item delayed-summary"><div class="summary-item-label">延期阶段 ({len(delayed_phases)}个)</div><div class="summary-item-value">{len(delayed_phases)} 个</div><div class="summary-item-sub">{"，".join(items)}</div></div>'

        over_budget_html = ""
        if over_budget_phases:
            items = []
            for ph in over_budget_phases:
                items.append(f"{ph.name}(+¥{ph.budget_variance():,.0f})")
            over_budget_html = f'<div class="summary-item"><div class="summary-item-label">超支阶段 ({len(over_budget_phases)}个)</div><div class="summary-item-value">{len(over_budget_phases)} 个</div><div class="summary-item-sub">{"，".join(items)}</div></div>'

        days_delivery = p.days_to_delivery
        delivery_value = "未设置"
        delivery_sub = ""
        if days_delivery is not None:
            if days_delivery < 0:
                delivery_value = f"已逾期 {-days_delivery} 天"
                delivery_sub = f"原计划: {p.target_delivery_date.strftime('%Y-%m-%d')}"
            elif days_delivery == 0:
                delivery_value = "今天交付"
                delivery_sub = f"目标: {p.target_delivery_date.strftime('%Y-%m-%d')}"
            else:
                delivery_value = f"还剩 {days_delivery} 天"
                delivery_sub = f"目标: {p.target_delivery_date.strftime('%Y-%m-%d')}"

        completed_phases = sum(1 for ph in p.phases if ph.completion_percent >= 100)
        in_progress_phases = sum(1 for ph in p.phases if 0 < ph.completion_percent < 100)
        not_started_phases = sum(1 for ph in p.phases if ph.completion_percent <= 0)

        return f"""
        <div class="summary-box">
            <h2>📋 项目摘要</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-item-label">整体进度</div>
                    <div class="summary-item-value">{p.overall_completion:.1f}%</div>
                    <div class="summary-item-sub">已完成{completed_phases}个 · 进行中{in_progress_phases}个 · 未开始{not_started_phases}个</div>
                </div>
                <div class="summary-item">
                    <div class="summary-item-label">距离交付</div>
                    <div class="summary-item-value">{delivery_value}</div>
                    <div class="summary-item-sub">{delivery_sub}</div>
                </div>
                {delayed_html}
                {over_budget_html}
            </div>
        </div>
        """

    def _generate_progress_chart(self) -> str:
        p = self.project

        phases_html = ""
        for phase in p.phases:
            status_class = "normal"
            if phase.is_delayed():
                status_class = "delayed"
            elif phase.completion_percent >= 100:
                status_class = "completed"
            elif phase.completion_percent > 0:
                status_class = "in-progress"

            phases_html += f"""
            <div class="chart-row">
                <div class="chart-label">{phase.name}</div>
                <div class="chart-bars">
                    <div class="chart-bar actual" style="left: 0; width: {phase.completion_percent}%; background: var(--color, #4361ee); --color: {'#e74c3c' if phase.is_delayed() else ('#2ecc71' if phase.completion_percent >= 100 else '#4361ee')};">
                        {f"{phase.completion_percent:.0f}%" if phase.completion_percent > 10 else ""}
                    </div>
                </div>
                <div class="chart-value">
                    <div>{phase.completion_percent:.1f}%</div>
                    <div style="font-size: 11px; color: {'#e74c3c' if phase.is_delayed() else '#666'};">
                        {f"延期{phase.delay_days()}天" if phase.is_delayed() else (phase.owner or "未指派")}
                    </div>
                </div>
            </div>
            """

        legend_html = """
        <div class="chart-legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #2ecc71;"></div>
                <span>已完成</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #4361ee;"></div>
                <span>正常进行</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f39c12;"></div>
                <span>进行中</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #e74c3c;"></div>
                <span>延期</span>
            </div>
        </div>
        """

        return legend_html + f'<div class="chart-container">{phases_html}</div>'

    def _generate_cost_breakdown_chart(self, purchased: float, standard: float, machining: float, labor: float, total: float) -> str:
        if total == 0:
            return "<p>暂无成本数据</p>"

        colors = ["#4361ee", "#8b5cf6", "#f39c12", "#2ecc71"]
        labels = ["外购件", "标准件", "机加工费", "人工成本"]
        values = [purchased, standard, machining, labor]

        pcts = []
        for v in values:
            pcts.append((v / total * 100) if total > 0 else 0)

        conic_gradient = ""
        current_deg = 0
        for i, pct in enumerate(pcts):
            if pct > 0:
                next_deg = current_deg + pct * 3.6
                conic_gradient += f"{colors[i]} {current_deg}deg {next_deg}deg, "
                current_deg = next_deg
        conic_gradient = conic_gradient.rstrip(", ")

        legend_html = ""
        for i in range(4):
            if pcts[i] > 0:
                legend_html += f"""
                <div class="cost-legend-item">
                    <div class="cost-legend-color" style="background: {colors[i]};"></div>
                    <div class="cost-legend-text">{labels[i]}</div>
                    <div class="cost-legend-amount">¥{values[i]:,.0f}</div>
                    <div class="cost-legend-pct">{pcts[i]:.1f}%</div>
                </div>
                """

        return f"""
        <div class="cost-breakdown">
            <div class="cost-pie" style="background: conic-gradient({conic_gradient});">
                <div class="cost-pie-center">
                    <div class="cost-pie-value">¥{total:,.0f}</div>
                    <div class="cost-pie-label">总成本</div>
                </div>
            </div>
            <div class="cost-legend">
                {legend_html}
            </div>
        </div>
        """

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
                today = date.today()
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

    def _generate_budget_chart(self) -> str:
        p = self.project

        max_val = 0
        for phase in p.phases:
            max_val = max(max_val, phase.budget.total, phase.cost.total)

        if max_val == 0:
            max_val = 1

        chart_html = '<div class="chart-container">'

        for phase in p.phases:
            b = phase.budget.total
            a = phase.cost.total

            b_pct = (b / max_val) * 100
            a_pct = (a / max_val) * 100

            a_class = "over" if phase.is_over_budget() else ""
            var = phase.budget_variance()
            var_pct = phase.budget_variance_percent()
            var_sign = "+" if var > 0 else ""

            chart_html += f"""
            <div class="chart-row">
                <div class="chart-label">{phase.name}</div>
                <div class="chart-bars">
                    <div class="chart-bar budget" style="left: 0; width: {b_pct}%;">
                        {"¥{:,.0f}".format(b) if b > 0 else ""}
                    </div>
                    <div class="chart-bar actual {a_class}" style="left: 0; width: {a_pct}%;">
                        {"¥{:,.0f}".format(a) if a > 0 else ""}
                    </div>
                </div>
                <div class="chart-value">
                    <div style="color: #8b5cf6; font-size: 11px;">预算 ¥{b:,.0f}</div>
                    <div>实际 ¥{a:,.0f}</div>
                    <div style="color: {'#e74c3c' if var > 0 else '#2ecc71'}; font-size: 11px;">
                        {var_sign}¥{var:,.0f} ({var_sign}{var_pct:.1f}%)
                    </div>
                </div>
            </div>
            """

        chart_html += "</div>"

        legend_html = """
        <div class="chart-legend">
            <div class="legend-item">
                <div class="legend-color" style="background: rgba(139, 92, 246, 0.5); border: 1px solid #8b5cf6;"></div>
                <span>预算</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #4361ee;"></div>
                <span>实际</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #e74c3c;"></div>
                <span>超支</span>
            </div>
        </div>
        """

        return legend_html + chart_html
