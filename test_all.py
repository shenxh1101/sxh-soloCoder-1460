import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Project, Phase, PHASE_NAMES
from repository import ProjectRepository
from gantt import GanttChart
from cost_report import CostReport
from html_exporter import HtmlExporter
from reminder import Reminder


def test_models():
    print("=" * 60)
    print("测试 1: 数据模型")
    print("=" * 60)

    today = date.today()

    project = Project(
        id="test-001",
        name="测试自动化设备项目",
        contract_amount=500000.0,
        target_delivery_date=today + timedelta(days=180),
    )

    assert len(project.phases) == 5, f"应该有5个阶段，实际有{len(project.phases)}个"
    assert [p.name for p in project.phases] == PHASE_NAMES

    print("  ✅ 项目创建成功，包含5个阶段")

    design_phase = project.phases[0]
    design_phase.planned_start = today + timedelta(days=10)
    design_phase.planned_end = today + timedelta(days=40)
    design_phase.actual_start = today + timedelta(days=12)
    design_phase.completion_percent = 50.0
    design_phase.owner = "张工"

    assert not design_phase.is_delayed()
    assert design_phase.delay_days() == 0
    print("  ✅ 阶段未延期时判断正确")

    late_phase = project.phases[1]
    late_phase.planned_start = today + timedelta(days=41)
    late_phase.planned_end = today + timedelta(days=68)
    late_phase.actual_start = today + timedelta(days=45)
    late_phase.actual_end = today + timedelta(days=78)
    late_phase.completion_percent = 100.0

    assert late_phase.is_delayed()
    assert late_phase.delay_days() == 10
    print("  ✅ 阶段延期判断正确，延期10天")

    phase_cost = design_phase.cost
    phase_cost.purchased_parts = 10000.0
    phase_cost.standard_parts = 5000.0
    phase_cost.machining_fee = 8000.0
    phase_cost.labor_hours = 80.0
    phase_cost.labor_hour_rate = 150.0

    assert phase_cost.labor_cost == 12000.0
    assert phase_cost.total == 35000.0
    print("  ✅ 成本计算正确")

    assert project.total_cost == 35000.0
    assert project.gross_profit == 465000.0
    assert abs(project.gross_margin - 93.0) < 0.01
    print("  ✅ 项目总成本、毛利、毛利率计算正确")

    overall = (50 + 100 + 0 + 0 + 0) / 5
    assert project.overall_completion == overall
    print("  ✅ 整体进度计算正确")

    delayed = project.get_delayed_phases()
    assert len(delayed) == 1
    assert delayed[0].name == "采购"
    print("  ✅ 延期阶段筛选正确")

    project_dict = project.to_dict()
    project2 = Project.from_dict(project_dict)
    assert project2.name == project.name
    assert project2.total_cost == project.total_cost
    assert project2.phases[0].name == project.phases[0].name
    print("  ✅ 序列化/反序列化正常")

    print("\n  🎉 数据模型测试全部通过！\n")


def test_repository():
    print("=" * 60)
    print("测试 2: 数据存储层")
    print("=" * 60)

    test_file = "test_projects.json"
    if os.path.exists(test_file):
        os.remove(test_file)

    repo = ProjectRepository(".")
    repo.data_file = test_file

    project = Project(
        id="proj-001",
        name="存储测试项目",
        contract_amount=300000.0,
        target_delivery_date=date(2025, 6, 30),
    )

    repo.add(project)
    print("  ✅ 项目添加成功")

    all_projects = repo.get_all()
    assert len(all_projects) == 1
    assert all_projects[0].name == "存储测试项目"
    print("  ✅ 获取所有项目成功")

    p = repo.get_by_id("proj-001")
    assert p is not None
    assert p.contract_amount == 300000.0
    print("  ✅ 按ID获取项目成功")

    p.name = "修改后的项目名"
    p.contract_amount = 350000.0
    result = repo.update(p)
    assert result == True

    p2 = repo.get_by_id("proj-001")
    assert p2.name == "修改后的项目名"
    assert p2.contract_amount == 350000.0
    print("  ✅ 项目更新成功")

    new_id = repo.generate_id()
    assert len(new_id) == 8
    print(f"  ✅ ID生成正常: {new_id}")

    result = repo.delete("proj-001")
    assert result == True
    assert len(repo.get_all()) == 0
    print("  ✅ 项目删除成功")

    if os.path.exists(test_file):
        os.remove(test_file)

    print("\n  🎉 数据存储层测试全部通过！\n")


def test_gantt():
    print("=" * 60)
    print("测试 3: 甘特图")
    print("=" * 60)

    project = Project(
        id="gantt-test",
        name="甘特图测试项目",
        contract_amount=800000.0,
        target_delivery_date=date(2025, 12, 31),
    )

    today = date.today()
    for i, phase in enumerate(project.phases):
        phase.planned_start = today + timedelta(days=i * 15)
        phase.planned_end = today + timedelta(days=i * 15 + 14)
        phase.completion_percent = 20 * i
        phase.owner = f"负责人{i+1}"

    project.phases[0].actual_start = today + timedelta(days=2)
    project.phases[0].actual_end = today + timedelta(days=18)

    chart = GanttChart(project)
    output = chart.render()

    assert "甘特图测试项目" in output
    assert "设计" in output
    assert "采购" in output
    assert "机加" in output
    assert "装配" in output
    assert "调试" in output
    assert "整体进度" in output
    print("  ✅ 甘特图包含项目名称、所有阶段、整体进度")

    print("\n甘特图预览 (部分):")
    lines = output.split("\n")
    for line in lines[:20]:
        print("  " + line)

    print("\n  🎉 甘特图测试通过！\n")


def test_cost_report():
    print("=" * 60)
    print("测试 4: 成本报告")
    print("=" * 60)

    project = Project(
        id="cost-test",
        name="成本测试项目",
        contract_amount=1000000.0,
        target_delivery_date=date(2025, 12, 31),
    )

    for i, phase in enumerate(project.phases):
        c = phase.cost
        c.purchased_parts = 10000 * (i + 1)
        c.standard_parts = 5000 * (i + 1)
        c.machining_fee = 8000 * (i + 1)
        c.labor_hours = 40 * (i + 1)
        c.labor_hour_rate = 200.0

    report = CostReport(project)
    output = report.generate()

    assert "成本偏差报告" in output
    assert "成本测试项目" in output
    assert "合同金额" in output
    assert "总成本" in output
    assert "毛利" in output
    assert "毛利率" in output
    assert "外购件" in output
    assert "标准件" in output
    assert "机加费" in output
    assert "人工成本" in output
    assert "合计" in output
    print("  ✅ 成本报告包含所有必要内容")

    breakdown = report.get_cost_breakdown()
    assert len(breakdown) == 5
    assert "设计" in breakdown
    assert "合计" in breakdown["设计"]
    print("  ✅ 成本分解数据正确")

    total_cost = sum(c["合计"] for c in breakdown.values())
    assert abs(total_cost - project.total_cost) < 0.01
    print(f"  ✅ 成本汇总正确: ¥{total_cost:,.2f}")

    print("\n成本报告预览 (部分):")
    lines = output.split("\n")
    for line in lines[:15]:
        print("  " + line)

    print("\n  🎉 成本报告测试通过！\n")


def test_html_export():
    print("=" * 60)
    print("测试 5: HTML报告导出")
    print("=" * 60)

    project = Project(
        id="html-test",
        name="HTML导出测试项目",
        contract_amount=600000.0,
        target_delivery_date=date(2025, 12, 31),
    )

    today = date.today()
    for i, phase in enumerate(project.phases):
        phase.planned_start = today + timedelta(days=i * 20)
        phase.planned_end = today + timedelta(days=i * 20 + 15)
        phase.completion_percent = 25 * i
        phase.owner = f"工程师{i+1}"

        c = phase.cost
        c.purchased_parts = 15000 * (i + 1)
        c.standard_parts = 3000 * (i + 1)
        c.machining_fee = 6000 * (i + 1)
        c.labor_hours = 30 * (i + 1)
        c.labor_hour_rate = 180.0

    project.phases[1].actual_start = today + timedelta(days=25)
    project.phases[1].actual_end = today + timedelta(days=50)

    exporter = HtmlExporter(project)
    filepath = exporter.export(".")

    assert os.path.exists(filepath)
    print(f"  ✅ HTML文件已生成: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<!DOCTYPE html>" in content
    assert "HTML导出测试项目" in content
    assert "合同金额" in content
    assert "甘特图" in content
    assert "成本明细" in content
    assert "毛利率" in content
    assert "设计" in content
    assert "调试" in content
    print("  ✅ HTML内容包含所有必要部分")

    assert "progress-bar" in content
    assert "gantt" in content
    assert "cost-chart" in content
    print("  ✅ HTML包含图表样式")

    if os.path.exists(filepath):
        os.remove(filepath)

    print("\n  🎉 HTML报告导出测试通过！\n")


def test_reminder():
    print("=" * 60)
    print("测试 6: 逾期催办")
    print("=" * 60)

    reminder = Reminder()
    projects = []

    project1 = Project(
        id="remind-001",
        name="延期项目A",
        contract_amount=200000.0,
        target_delivery_date=date.today(),
    )

    phase = project1.phases[0]
    phase.planned_start = date.today() - timedelta(days=20)
    phase.planned_end = date.today() - timedelta(days=10)
    phase.actual_start = date.today() - timedelta(days=18)
    phase.completion_percent = 50.0
    phase.owner = "李工"

    projects.append(project1)

    project2 = Project(
        id="remind-002",
        name="正常项目B",
        contract_amount=300000.0,
        target_delivery_date=date.today(),
    )
    projects.append(project2)

    overdue = reminder.check_overdue(projects)
    print(f"  发现 {len(overdue)} 个延期超过3天的阶段")

    for proj, ph in overdue:
        print(f"    - {proj.name}: {ph.name} 阶段延期 {ph.delay_days()} 天")

    print("  ✅ 逾期催办检查功能正常")
    print("\n  🎉 逾期催办测试通过！\n")


def run_all_tests():
    print("\n" + "=" * 60)
    print("  🚀 开始运行所有测试")
    print("=" * 60 + "\n")

    try:
        test_models()
        test_repository()
        test_gantt()
        test_cost_report()
        test_html_export()
        test_reminder()

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
