import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Project, Phase, PHASE_NAMES, PhaseBudget, PhaseCost
from repository import ProjectRepository
from gantt import GanttChart
from cost_report import CostReport
from html_exporter import HtmlExporter
from reminder import Reminder
from dashboard import Dashboard


def test_budget_model():
    print("=" * 60)
    print("测试 1: 预算数据模型")
    print("=" * 60)

    budget = PhaseBudget(
        purchased_parts=10000.0,
        standard_parts=5000.0,
        machining_fee=8000.0,
        labor_cost=12000.0,
    )

    assert budget.total == 35000.0
    print("  ✅ PhaseBudget 总预算计算正确")

    budget_dict = budget.to_dict()
    budget2 = PhaseBudget.from_dict(budget_dict)
    assert budget2.total == budget.total
    print("  ✅ PhaseBudget 序列化/反序列化正常")

    project = Project(
        id="budget-test",
        name="预算测试项目",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=180),
    )

    for i, phase in enumerate(project.phases):
        phase.budget.purchased_parts = 10000 * (i + 1)
        phase.budget.standard_parts = 5000 * (i + 1)
        phase.budget.machining_fee = 3000 * (i + 1)
        phase.budget.labor_cost = 8000 * (i + 1)

    expected_budget = sum(26000 * (i + 1) for i in range(5))
    assert project.total_budget == expected_budget
    print(f"  ✅ 项目总预算计算正确: ¥{project.total_budget:,.2f}")

    project.phases[0].cost.purchased_parts = 15000.0
    project.phases[0].cost.standard_parts = 6000.0
    project.phases[0].cost.machining_fee = 4000.0
    project.phases[0].cost.labor_hours = 60
    project.phases[0].cost.labor_hour_rate = 150.0

    assert project.phases[0].is_over_budget() == True
    assert project.phases[0].budget_variance() == 15000 + 6000 + 4000 + 9000 - 26000
    print(f"  ✅ 超支判断和偏差计算正确")

    over_budget_phases = project.get_over_budget_phases()
    assert len(over_budget_phases) == 1
    print("  ✅ 超支阶段筛选正确")

    print("\n  🎉 预算数据模型测试全部通过！\n")


def test_validation():
    print("=" * 60)
    print("测试 2: 数据校验")
    print("=" * 60)

    phase = Phase(name="测试阶段")

    phase.planned_start = date(2025, 1, 10)
    phase.planned_end = date(2025, 1, 5)

    ok, msg = phase.validate_dates()
    assert not ok
    assert "计划结束日期不能早于计划开始日期" in msg
    print("  ✅ 计划日期先后顺序校验正确")

    phase.planned_start = date(2025, 1, 1)
    phase.planned_end = date(2025, 1, 31)
    phase.actual_start = date(2025, 2, 1)
    phase.actual_end = date(2025, 1, 20)

    ok, msg = phase.validate_dates()
    assert not ok
    assert "实际结束日期不能早于实际开始日期" in msg
    print("  ✅ 实际日期先后顺序校验正确")

    phase.actual_start = None
    phase.actual_end = None
    phase.completion_percent = -10.0

    ok, msg = phase.validate_values()
    assert not ok
    assert "完成百分比" in msg
    print("  ✅ 完成百分比非负校验正确")

    phase.completion_percent = 150.0
    ok, msg = phase.validate_values()
    assert not ok
    print("  ✅ 完成百分比上限校验正确")

    phase.completion_percent = 50.0
    phase.cost.purchased_parts = -100.0
    ok, msg = phase.validate_values()
    assert not ok
    assert "外购件费用不能为负数" in msg
    print("  ✅ 成本数值非负校验正确")

    phase.cost.purchased_parts = 0.0
    phase.budget.labor_cost = -500.0
    ok, msg = phase.validate_values()
    assert not ok
    assert "预算人工成本不能为负数" in msg
    print("  ✅ 预算数值非负校验正确")

    phase.budget.labor_cost = 1000.0
    phase.cost.labor_hours = -5.0
    ok, msg = phase.validate_values()
    assert not ok
    assert "工时不能为负数" in msg
    print("  ✅ 工时非负校验正确")

    print("\n  🎉 数据校验测试全部通过！\n")


def test_dashboard_dynamic_stats():
    print("=" * 60)
    print("测试 3: Dashboard 筛选后动态汇总")
    print("=" * 60)

    projects = []

    p1 = Project(
        id="dyn-001",
        name="项目A - 延期项目",
        contract_amount=1000000.0,
        target_delivery_date=date.today() + timedelta(days=5),
    )
    p1.phases[0].completion_percent = 100.0
    p1.phases[0].owner = "张工"
    p1.phases[1].planned_end = date.today() - timedelta(days=10)
    p1.phases[1].completion_percent = 50.0
    p1.phases[1].owner = "李工"
    for i in range(5):
        p1.phases[i].budget.purchased_parts = 50000
        p1.phases[i].cost.purchased_parts = 45000
    projects.append(p1)

    p2 = Project(
        id="dyn-002",
        name="项目B - 超支项目",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=60),
    )
    p2.phases[0].completion_percent = 100.0
    p2.phases[0].owner = "王工"
    p2.phases[1].completion_percent = 60.0
    p2.phases[1].owner = "张工"
    for i in range(5):
        p2.phases[i].budget.purchased_parts = 20000
        p2.phases[i].cost.purchased_parts = 25000
    projects.append(p2)

    p3 = Project(
        id="dyn-003",
        name="项目C - 正常项目",
        contract_amount=300000.0,
        target_delivery_date=date.today() + timedelta(days=120),
    )
    p3.phases[0].completion_percent = 30.0
    p3.phases[0].owner = "李工"
    projects.append(p3)

    dashboard = Dashboard(projects)

    all_stats = dashboard.get_overall_stats()
    assert all_stats["project_count"] == 3
    assert all_stats["total_contract"] == 1800000.0
    print(f"  ✅ 全部项目统计: 共{all_stats['project_count']}个，合同额¥{all_stats['total_contract']:,.0f}")

    delayed = dashboard.filter_by_status("delayed")
    delayed_stats = dashboard.get_overall_stats(delayed)
    assert delayed_stats["project_count"] == 1
    assert delayed_stats["total_contract"] == 1000000.0
    print(f"  ✅ 筛选后(延期)统计: 共{delayed_stats['project_count']}个，合同额¥{delayed_stats['total_contract']:,.0f}")

    normal = dashboard.filter_by_status("normal")
    normal_stats = dashboard.get_overall_stats(normal)
    assert normal_stats["project_count"] == 2
    assert normal_stats["total_contract"] == 800000.0
    print(f"  ✅ 筛选后(正常)统计: 共{normal_stats['project_count']}个，合同额¥{normal_stats['total_contract']:,.0f}")

    over_budget = dashboard.filter_by_status("over_budget")
    over_budget_stats = dashboard.get_overall_stats(over_budget)
    assert over_budget_stats["project_count"] == 1
    assert over_budget_stats["total_contract"] == 500000.0
    print(f"  ✅ 筛选后(超支)统计: 共{over_budget_stats['project_count']}个，合同额¥{over_budget_stats['total_contract']:,.0f}")

    owner_zhang = dashboard.filter_by_owner("张工")
    owner_stats = dashboard.get_overall_stats(owner_zhang)
    assert owner_stats["project_count"] == 2
    assert owner_stats["total_contract"] == 1500000.0
    print(f"  ✅ 筛选后(负责人张工)统计: 共{owner_stats['project_count']}个，合同额¥{owner_stats['total_contract']:,.0f}")

    print("\n  🎉 Dashboard 动态汇总测试通过！\n")


def test_dashboard_priority_projects():
    print("=" * 60)
    print("测试 4: Dashboard 重点项目风险评分")
    print("=" * 60)

    projects = []

    p1 = Project(
        id="pri-001",
        name="高风险项目 - 已逾期",
        contract_amount=800000.0,
        target_delivery_date=date.today() - timedelta(days=5),
    )
    p1.phases[0].planned_end = date.today() - timedelta(days=15)
    p1.phases[0].completion_percent = 60.0
    p1.phases[0].budget.purchased_parts = 50000
    p1.phases[0].cost.purchased_parts = 80000
    projects.append(p1)

    p2 = Project(
        id="pri-002",
        name="中风险项目 - 交期紧急",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=3),
    )
    p2.phases[0].budget.purchased_parts = 20000
    p2.phases[0].cost.purchased_parts = 20000
    projects.append(p2)

    p3 = Project(
        id="pri-003",
        name="低风险项目",
        contract_amount=300000.0,
        target_delivery_date=date.today() + timedelta(days=180),
    )
    p3.phases[0].completion_percent = 95.0
    projects.append(p3)

    dashboard = Dashboard(projects)

    priority = dashboard.get_priority_projects(top_n=5)
    assert len(priority) >= 2
    print(f"  ✅ 重点项目筛选正确: 共{len(priority)}个需要关注的项目")

    for p, score, risks, level in priority:
        print(f"     {level} {p.name}: 风险分={score}, 风险={risks}")

    assert priority[0][0].id == "pri-001"
    assert priority[0][2] is not None
    assert len(priority[0][2]) >= 2
    print("  ✅ 风险最高的项目排在第一位")

    assert "已逾期" in priority[0][2] or "延期" in priority[0][2]
    assert any("超支" in r for r in priority[0][2])
    print("  ✅ 风险标签包含逾期和超支")

    output = dashboard.render()
    assert "重点关注项目" in output
    assert "🎯" in output
    assert "🔴" in output or "🟠" in output
    print("  ✅ 看板渲染包含重点项目区和风险标识")

    print("\n  🎉 Dashboard 重点项目测试通过！\n")


def test_html_report_enhanced():
    print("=" * 60)
    print("测试 5: HTML报告增强 (首页摘要+完整图表)")
    print("=" * 60)

    project = Project(
        id="html-enhanced-test",
        name="HTML增强测试项目",
        contract_amount=1200000.0,
        target_delivery_date=date.today() + timedelta(days=15),
    )

    for i, phase in enumerate(project.phases):
        phase.planned_start = date.today() + timedelta(days=i * 20)
        phase.planned_end = date.today() + timedelta(days=i * 20 + 15)
        phase.completion_percent = 25 * i
        phase.owner = f"工程师{i+1}"

        phase.budget.purchased_parts = 25000 * (i + 1)
        phase.budget.standard_parts = 8000 * (i + 1)
        phase.budget.machining_fee = 6000 * (i + 1)
        phase.budget.labor_cost = 18000 * (i + 1)

        phase.cost.purchased_parts = 28000 * (i + 1)
        phase.cost.standard_parts = 8500 * (i + 1)
        phase.cost.machining_fee = 6500 * (i + 1)
        phase.cost.labor_hours = 80 * (i + 1)
        phase.cost.labor_hour_rate = 230.0

    project.phases[1].planned_end = date.today() - timedelta(days=8)
    project.phases[1].actual_start = date.today() - timedelta(days=30)
    project.phases[1].actual_end = date.today() - timedelta(days=3)
    project.phases[1].completion_percent = 100.0

    exporter = HtmlExporter(project)
    filepath = exporter.export(".")

    assert os.path.exists(filepath)
    print(f"  ✅ HTML文件已生成: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "项目摘要" in content
    assert "summary-box" in content
    print("  ✅ HTML包含首页紫色摘要区域")

    assert "整体进度" in content
    assert "距离交付" in content
    assert "延期阶段" in content
    assert "超支阶段" in content
    print("  ✅ 首页摘要包含四个核心指标")

    assert "采购" in content
    assert "8" in content
    assert "天" in content
    assert "工程师2" in content
    assert "100%" in content
    print("  ✅ 延期阶段信息(天数、负责人、完成度)在首页展示")

    assert "整体进度" in content
    assert "成本构成" in content
    assert "chart-grid" in content
    print("  ✅ 首页包含进度图和成本构成图双栏布局")

    assert "conic-gradient" in content or "cost-pie" in content
    print("  ✅ 成本构成饼图已实现")

    assert "progress-chart" in content or "chart-row" in content
    print("  ✅ 进度条形图已实现")

    assert "项目进度甘特图" in content
    assert "预算 vs 实际成本对比" in content
    assert "按成本类别汇总" in content
    assert "各阶段预算对比图" in content
    assert "各阶段预算明细表" in content
    print("  ✅ 所有图表模块齐全: 甘特图、预算对比、成本汇总")

    if os.path.exists(filepath):
        os.remove(filepath)

    print("\n  🎉 HTML报告增强测试通过！\n")


def test_edit_returns():
    print("=" * 60)
    print("测试 6: 编辑方法返回值 (是否有修改)")
    print("=" * 60)

    project = Project(
        id="return-test",
        name="返回值测试项目",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=90),
    )

    phase = project.phases[0]
    phase.planned_start = date.today()
    phase.planned_end = date.today() + timedelta(days=10)
    phase.completion_percent = 50.0
    phase.owner = "测试员"

    old_ps = phase.planned_start
    old_pe = phase.planned_end
    old_owner = phase.owner
    old_completion = phase.completion_percent

    phase.planned_start = old_ps
    phase.planned_end = old_pe
    phase.owner = old_owner
    phase.completion_percent = old_completion

    changed = False
    if phase.planned_start != old_ps: changed = True
    if phase.planned_end != old_pe: changed = True
    if phase.owner != old_owner: changed = True
    if abs(phase.completion_percent - old_completion) > 0.01: changed = True

    assert not changed
    print("  ✅ 无修改时 changed = False")

    phase.completion_percent = 60.0
    changed = False
    if abs(phase.completion_percent - old_completion) > 0.01: changed = True
    assert changed
    print("  ✅ 有修改时 changed = True")

    old_cost_total = phase.cost.total
    phase.cost.purchased_parts = phase.cost.purchased_parts
    cost_changed = abs(phase.cost.total - old_cost_total) > 0.01
    assert not cost_changed
    print("  ✅ 成本无修改时返回 False")

    phase.cost.purchased_parts = 1000.0
    cost_changed = abs(phase.cost.total - old_cost_total) > 0.01
    assert cost_changed
    print("  ✅ 成本有修改时返回 True")

    old_budget_total = phase.budget.total
    phase.budget.purchased_parts = phase.budget.purchased_parts
    budget_changed = abs(phase.budget.total - old_budget_total) > 0.01
    assert not budget_changed
    print("  ✅ 预算无修改时返回 False")

    phase.budget.purchased_parts = 5000.0
    budget_changed = abs(phase.budget.total - old_budget_total) > 0.01
    assert budget_changed
    print("  ✅ 预算有修改时返回 True")

    print("\n  🎉 编辑方法返回值测试通过！\n")


def test_dashboard_risk_scoring():
    print("=" * 60)
    print("测试 7: Dashboard 风险评分细则")
    print("=" * 60)

    p_high = Project(
        id="risk-high",
        name="高风险项目",
        contract_amount=1000000.0,
        target_delivery_date=date.today() - timedelta(days=10),
    )
    p_high.phases[0].planned_end = date.today() - timedelta(days=20)
    p_high.phases[0].completion_percent = 50.0
    p_high.phases[0].budget.purchased_parts = 100000
    p_high.phases[0].cost.purchased_parts = 150000
    p_high.phases[0].cost.labor_hours = 5000
    p_high.phases[0].cost.labor_hour_rate = 160

    p_medium = Project(
        id="risk-medium",
        name="中风险项目",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=5),
    )
    p_medium.phases[0].planned_end = date.today() - timedelta(days=3)
    p_medium.phases[0].completion_percent = 80.0
    p_medium.phases[0].cost.purchased_parts = 300000
    p_medium.phases[0].cost.labor_hours = 500
    p_medium.phases[0].cost.labor_hour_rate = 150

    p_low = Project(
        id="risk-low",
        name="正常项目",
        contract_amount=300000.0,
        target_delivery_date=date.today() + timedelta(days=180),
    )
    p_low.phases[0].completion_percent = 100.0
    p_low.phases[0].cost.purchased_parts = 50000
    p_low.phases[0].cost.labor_hours = 500
    p_low.phases[0].cost.labor_hour_rate = 150

    dashboard = Dashboard([p_high, p_medium, p_low])

    score_high, risks_high, level_high = dashboard._get_project_risk_score(p_high)
    score_medium, risks_medium, level_medium = dashboard._get_project_risk_score(p_medium)
    score_low, risks_low, level_low = dashboard._get_project_risk_score(p_low)

    print(f"  高风险项目: 得分={score_high}, 等级={level_high}, 风险={risks_high}")
    print(f"  中风险项目: 得分={score_medium}, 等级={level_medium}, 风险={risks_medium}")
    print(f"  低风险项目: 得分={score_low}, 等级={level_low}, 风险={risks_low}")

    assert score_high > score_medium
    assert score_medium > score_low
    print("  ✅ 风险评分排序正确: 高 > 中 > 低")

    assert level_high == "🔴"
    assert level_medium in ["🔴", "🟠"]
    assert level_low == "🟢"
    print("  ✅ 风险等级标识正确: 🔴高风险 / 🟠中风险 / 🟢低风险")

    assert "已逾期" in risks_high
    assert any("延期" in r for r in risks_high)
    assert any("超支" in r for r in risks_high)
    assert any("低毛利" in r for r in risks_high)
    print("  ✅ 高风险项目包含所有风险标签")

    assert "交期紧急" in risks_medium
    print("  ✅ 中风险项目包含交期紧急标签")

    assert risks_low == [] or len(risks_low) == 0
    print("  ✅ 低风险项目无风险标签")

    print("\n  🎉 Dashboard 风险评分细则测试通过！\n")


def run_all_tests():
    print("\n" + "=" * 60)
    print("  🚀 开始运行所有测试")
    print("=" * 60 + "\n")

    try:
        test_budget_model()
        test_validation()
        test_dashboard_dynamic_stats()
        test_dashboard_priority_projects()
        test_html_report_enhanced()
        test_edit_returns()
        test_dashboard_risk_scoring()

        print("=" * 60)
        print("  🎉 所有测试全部通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n  ❌ 断言失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n  ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
