# -*- coding: utf-8 -*-
"""
行业月报自动化工作流 - 主入口

支持三种运行模式：
1. CLI模式：指定行业、时间和数据类型
2. 演示模式：使用示例数据演示流程
3. 文件模式：从JSON文件读取数据
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import IndustryReportPipeline
from data_models import PipelineContext
from report_generator import ReportGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="行业月报自动化工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 演示模式
  python main.py --demo
  
  # CLI模式
  python main.py --industry 光伏 --period 2026年3月 --types domestic,competitor
  
  # 文件模式
  python main.py --input data.json
        """
    )
    
    parser.add_argument(
        "--industry", "-i",
        help="行业名称（光伏/锂电/新能源汽车）",
        default="光伏"
    )
    
    parser.add_argument(
        "--period", "-p",
        help="数据周期（如：2026年3月）",
        default=None
    )
    
    parser.add_argument(
        "--types", "-t",
        help="数据类型（逗号分隔，如：domestic,competitor,news）",
        default="domestic,global,competitor,news"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="运行演示模式"
    )
    
    parser.add_argument(
        "--input", "-f",
        help="从JSON文件读取数据",
        default=None
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出报告路径",
        default=None
    )
    
    parser.add_argument(
        "--format", "-F",
        choices=["markdown", "excel", "json", "all"],
        default="markdown",
        help="输出格式"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="启用联网搜集模式（需配合--api-key使用）"
    )
    
    parser.add_argument(
        "--api-key",
        help="搜索API密钥（如SerpAPI key）"
    )
    
    return parser.parse_args()


def run_demo_mode():
    """演示模式"""
    print("=" * 60)
    print("行业月报自动化工作流 - 演示模式")
    print("=" * 60)
    print()
    
    print("正在加载示例数据并执行Pipeline...")
    print()
    
    try:
        context = IndustryReportPipeline.run_demo()
        
        print("✓ Pipeline执行成功！")
        print()
        print(f"  - 行业：{context.industry}")
        print(f"  - 周期：{context.time_period}")
        print(f"  - 国内数据：{len(context.domestic_data)}条")
        print(f"  - 国际数据：{len(context.global_data)}条")
        print(f"  - 竞争对手动态：{len(context.competitor_events)}条")
        print(f"  - 行业资讯：{len(context.industry_news)}条")
        print()
        
        if context.grading_stats:
            stats = context.grading_stats
            print("可信度分布：")
            for grade in ["A", "B", "C", "D"]:
                count = stats.grade_distribution.get(grade, 0)
                pct = stats.grade_percentages.get(grade, 0)
                print(f"  - {grade}级：{count}条 ({pct}%)")
            print()
        
        if context.report_path:
            print(f"报告已生成：{context.report_path}")
        
        return context
        
    except Exception as e:
        print(f"✗ 执行失败：{e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_cli_mode(args):
    """CLI模式"""
    print("=" * 60)
    print("行业月报自动化工作流 - CLI模式")
    print("=" * 60)
    print()
    
    # 解析数据类型
    data_types = [t.strip() for t in args.types.split(",")]
    
    # 解析时间周期
    period = args.period
    if not period:
        period = datetime.now().strftime("%Y年%m月")
    
    # 检查联网模式配置
    live_mode = args.live
    api_key = args.api_key
    
    if live_mode and not api_key:
        print("[提示] 启用联网模式但未提供API key，将使用演示数据")
        print("[提示] 如需真实联网搜集，请提供 --api-key 参数")
        print()
    
    print(f"参数：")
    print(f"  - 行业：{args.industry}")
    print(f"  - 周期：{period}")
    print(f"  - 数据类型：{', '.join(data_types)}")
    print(f"  - 搜集模式：{'联网搜集' if live_mode else '演示数据'}")
    if api_key:
        print(f"  - API密钥：已配置")
    print()
    
    # 构建查询
    query = f"{args.industry} {period} {' '.join(data_types)}"
    
    print("正在执行Pipeline...")
    print()
    
    try:
        # 根据参数创建Pipeline实例
        pipeline = IndustryReportPipeline(api_key=api_key, live_mode=live_mode)
        context = pipeline.run(query)
        
        print("✓ Pipeline执行成功！")
        print()
        print(f"阶段执行结果：")
        for stage, success in context.stage_results.items():
            status = "✓" if success else "✗"
            print(f"  - {stage}：{status}")
        print()
        
        if context.report_path:
            print(f"报告已生成：{context.report_path}")
        
        return context
        
    except Exception as e:
        print(f"✗ 执行失败：{e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_file_mode(args):
    """文件模式"""
    print("=" * 60)
    print("行业月报自动化工作流 - 文件模式")
    print("=" * 60)
    print()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"✗ 文件不存在：{input_path}")
        sys.exit(1)
    
    print(f"正在读取数据文件：{input_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        period = args.period or data.get("time_period", datetime.now().strftime("%Y年%m月"))
        
        print()
        print("正在执行Pipeline...")
        
        pipeline = IndustryReportPipeline()
        context = pipeline.run_with_data(data, period)
        
        print("✓ Pipeline执行成功！")
        print()
        
        if context.report_path:
            print(f"报告已生成：{context.report_path}")
        
        return context
        
    except Exception as e:
        print(f"✗ 执行失败：{e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """主入口"""
    args = parse_args()
    
    if args.demo:
        context = run_demo_mode()
    elif args.input:
        context = run_file_mode(args)
    else:
        context = run_cli_mode(args)
    
    # 输出报告
    if args.output and context.report_content:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(context.report_content)
        
        print(f"\n报告已保存至：{output_path}")
    
    # 生成其他格式
    if args.format in ["excel", "all"] and context.grading_results:
        try:
            from report_generator import ReportGenerator
            rg = ReportGenerator()
            excel_path = rg.generate_excel_template(context.grading_results)
            print(f"\nExcel模板已生成：{excel_path}")
        except ImportError as e:
            print(f"\n⚠ 无法生成Excel：{e}")
    
    if args.format in ["json", "all"] and context.grading_results and context.grading_stats:
        try:
            from report_generator import ReportGenerator
            rg = ReportGenerator()
            json_content = rg.generate_summary_json(context.grading_results, context.grading_stats)
            json_path = Path(__file__).parent.parent / "output" / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            print(f"\nJSON摘要已生成：{json_path}")
        except Exception as e:
            print(f"\n⚠ 无法生成JSON：{e}")
    
    print()


if __name__ == "__main__":
    main()
