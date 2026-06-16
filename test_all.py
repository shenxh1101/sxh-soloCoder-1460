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
    print(f"     预算: ¥{project.phases[0].budget.total:,.2f}")
    print(f"     实际: ¥{project.phases[0].cost.total:,.2f}")
    print(f"     偏差: ¥{project.phases[0].budget_variance():,.2f} ({project.phases[0].budget_variance_percent():.2f}%)")

    over_budget_phases = project.get_over_budget_phases()
    assert len(over_budget_phases) == 1
    print("  ✅ 超支阶段筛选正确")

    assert project.is_over_budget == False
    print("  ✅ 项目整体未超支判断正确")

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

    phase.planned_start = date(2025, 1, 1)
    phase.planned_end = date(2025, 1, 31)
    phase.actual_start = None
    phase.actual_end = None
    phase.completion_percent = 50.0
    phase.cost = PhaseCost.__new__(PhaseCost)
    phase.cost.purchased_parts = 0.0
    phase.cost.standard_parts = 0.0
    phase.cost.machining_fee = 0.0
    phase.cost.labor_hours = 0.0
    phase.cost.labor_hour_rate = 0.0
    phase.budget = PhaseBudget()

    ok, msg = phase.validate_all()
    assert ok
    print("  ✅ 全部校验通过时返回正确")

    print("\n  🎉 数据校验测试全部通过！\n")


def test_cost_report_with_budget():
    print("=" * 60)
    print("测试 3: 成本报告 (含预算对比)")
    print("=" * 60)

    project = Project(
        id="cost-budget-test",
        name="成本预算对比测试",
        contract_amount=1000000.0,
        target_delivery_date=date.today() + timedelta(days=200),
    )

    for i, phase in enumerate(project.phases):
        phase.budget.purchased_parts = 20000 * (i + 1)
        phase.budget.standard_parts = 8000 * (i + 1)
        phase.budget.machining_fee = 5000 * (i + 1)
        phase.budget.labor_cost = 15000 * (i + 1)

        phase.cost.purchased_parts = 22000 * (i + 1)
        phase.cost.standard_parts = 8500 * (i + 1)
        phase.cost.machining_fee = 5500 * (i + 1)
        phase.cost.labor_hours = 100 * (i + 1)
        phase.cost.labor_hour_rate = 160.0

    report = CostReport(project)
    output = report.generate()

    assert "预算" in output
    assert "偏差" in output
    assert "偏差率" in output
    assert "超支" in output
    print("  ✅ 成本报告包含预算对比相关内容")

    breakdown = report.get_cost_breakdown()
    assert "设计" in breakdown
    assert "预算_合计" in breakdown["设计"]
    assert "实际_合计" in breakdown["设计"]
    assert "偏差" in breakdown["设计"]
    assert "偏差率" in breakdown["设计"]
    print("  ✅ 成本分解数据包含预算和实际对比")

    summary = report.get_project_summary()
    assert "总预算" in summary
    assert "预算偏差" in summary
    assert "预算偏差率" in summary
    print("  ✅ 项目汇总数据包含预算信息")

    print("\n成本报告预览 (部分):")
    lines = output.split("\n")
    for line in lines[:20]:
        print("  " + line)

    print("\n  🎉 成本报告(含预算)测试通过！\n")


def test_html_report_with_budget():
    print("=" * 60)
    print("测试 4: HTML报告 (含预算对比和延期首页)")
    print("=" * 60)

    project = Project(
        id="html-budget-test",
        name="HTML预算对比测试项目",
        contract_amount=800000.0,
        target_delivery_date=date.today() + timedelta(days=90),
    )

    for i, phase in enumerate(project.phases):
        phase.planned_start = date.today() + timedelta(days=i * 20)
        phase.planned_end = date.today() + timedelta(days=i * 20 + 15)
        phase.completion_percent = 25 * i
        phase.owner = f"工程师{i+1}"

        phase.budget.purchased_parts = 15000 * (i + 1)
        phase.budget.standard_parts = 5000 * (i + 1)
        phase.budget.machining_fee = 4000 * (i + 1)
        phase.budget.labor_cost = 10000 * (i + 1)

        phase.cost.purchased_parts = 16000 * (i + 1)
        phase.cost.standard_parts = 5500 * (i + 1)
        phase.cost.machining_fee = 4200 * (i + 1)
        phase.cost.labor_hours = 60 * (i + 1)
        phase.cost.labor_hour_rate = 180.0

    project.phases[1].actual_start = date.today() - timedelta(days=30)
    project.phases[1].actual_end = date.today() - timedelta(days=5)
    project.phases[1].completion_percent = 100.0

    exporter = HtmlExporter(project)
    filepath = exporter.export(".")

    assert os.path.exists(filepath)
    print(f"  ✅ HTML文件已生成: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "需关注事项" in content or "warning" in content.lower()
    print("  ✅ HTML包含首页警示区域")

    assert "预算" in content
    assert "预算vs" in content or "预算 vs" in content or "预算对比" in content
    print("  ✅ HTML包含预算对比模块")

    assert "超支" in content or "over-budget" in content.lower()
    print("  ✅ HTML包含超支标记")

    assert "延期" in content
    print("  ✅ HTML包含延期相关内容")

    if os.path.exists(filepath):
        os.remove(filepath)

    print("\n  🎉 HTML报告(含预算和延期首页)测试通过！\n")


def test_dashboard():
    print("=" * 60)
    print("测试 5: 多项目汇总看板")
    print("=" * 60)

    projects = []

    p1 = Project(
        id="dash-001",
        name="项目A - 自动化生产线",
        contract_amount=1200000.0,
        target_delivery_date=date.today() + timedelta(days=10),
    )
    p1.phases[0].completion_percent = 100.0
    p1.phases[0].owner = "张工"
    p1.phases[1].completion_percent = 80.0
    p1.phases[1].owner = "李工"
    p1.phases[1].planned_end = date.today() - timedelta(days=5)
    for i in range(5):
        p1.phases[i].budget.purchased_parts = 50000
        p1.phases[i].cost.purchased_parts = 45000
    projects.append(p1)

    p2 = Project(
        id="dash-002",
        name="项目B - 检测设备",
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
        id="dash-003",
        name="项目C - 包装机",
        contract_amount=300000.0,
        target_delivery_date=date.today() + timedelta(days=120),
    )
    p3.phases[0].completion_percent = 30.0
    p3.phases[0].owner = "李工"
    projects.append(p3)

    dashboard = Dashboard(projects)

    stats = dashboard.get_overall_stats()
    assert stats["project_count"] == 3
    assert stats["total_contract"] == 2000000.0
    print(f"  ✅ 总体统计正确: 共 {stats['project_count']} 个项目")
    print(f"     总合同额: ¥{stats['total_contract']:,.2f}")
    print(f"     平均毛利率: {stats['avg_margin']:.2f}%")
    print(f"     延期项目: {stats['delayed_count']} 个")
    print(f"     超支项目: {stats['over_budget_count']} 个")

    upcoming = dashboard.get_upcoming_deliveries(30)
    assert len(upcoming) >= 1
    print(f"  ✅ 即将到期项目筛选正确: {len(upcoming)} 个项目在30天内交付")

    delayed = dashboard.get_delayed_projects()
    assert len(delayed) >= 1
    print(f"  ✅ 延期项目筛选正确: {len(delayed)} 个延期项目")

    normal_projects = dashboard.filter_by_status("normal")
    delayed_projects = dashboard.filter_by_status("delayed")
    over_budget_projects = dashboard.filter_by_status("over_budget")
    print(f"  ✅ 状态筛选正常: normal={len(normal_projects)}, delayed={len(delayed_projects)}, over_budget={len(over_budget_projects)}")

    owner_projects = dashboard.filter_by_owner("张工")
    assert len(owner_projects) == 2
    print(f"  ✅ 负责人筛选正确: 张工参与 {len(owner_projects)} 个项目")

    all_owners = dashboard.get_all_owners()
    assert "张工" in all_owners
    assert "李工" in all_owners
    assert "王工" in all_owners
    print(f"  ✅ 所有负责人列表正确: {', '.join(all_owners)}")

    output = dashboard.render()
    assert "多项目汇总看板" in output
    assert "项目A" in output
    assert "项目B" in output
    assert "项目C" in output
    print("  ✅ 看板渲染包含所有项目")

    print("\n看板预览 (部分):")
    lines = output.split("\n")
    for line in lines[:15]:
        print("  " + line)

    print("\n  🎉 多项目汇总看板测试通过！\n")


def test_project_properties():
    print("=" * 60)
    print("测试 6: 项目扩展属性")
    print("=" * 60)

    project = Project(
        id="prop-test",
        name="属性测试项目",
        contract_amount=500000.0,
        target_delivery_date=date.today() + timedelta(days=45),
    )

    assert project.days_to_delivery is not None
    assert project.days_to_delivery >= 44
    print(f"  ✅ 交付倒计时计算正确: {project.days_to_delivery} 天")

    assert not project.is_delayed
    print("  ✅ 未延期时 is_delayed = False")

    project.phases[0].planned_end = date.today() - timedelta(days=10)
    project.phases[0].completion_percent = 50.0
    assert project.is_delayed
    assert project.max_delay_days >= 10
    print(f"  ✅ 延期时 is_delayed = True，最大延期 {project.max_delay_days} 天")

    owners = project.get_all_owners()
    assert len(owners) == 0
    print("  ✅ 无负责人时返回空列表")

    project.phases[0].owner = "  张工  "
    project.phases[1].owner = "张工"
    project.phases[2].owner = "李工"
    owners = project.get_all_owners()
    assert len(owners) == 2
    assert "张工" in owners
    assert "李工" in owners
    print(f"  ✅ 负责人去重和去空格处理正确: {owners}")

    print("\n  🎉 项目扩展属性测试通过！\n")


def run_all_tests():
    print("\n" + "=" * 60)
    print("  🚀 开始运行所有测试")
    print("=" * 60 + "\n")

    try:
        test_budget_model()
        test_validation()
        test_cost_report_with_budget()
        test_html_report_with_budget()
        test_dashboard()
        test_project_properties()

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
