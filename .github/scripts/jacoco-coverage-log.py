#!/usr/bin/env python3
"""
JaCoCo XML Coverage Checker
解析 target/site/jacoco/jacoco.xml 并在 GitHub Actions 日志中打印覆盖率。
"""

import xml.etree.ElementTree as ET
import os
import sys
import argparse

def parse_jacoco_xml(xml_path):
    if not os.path.exists(xml_path):
        print(f"❌ Error: File not found at '{xml_path}'")
        print("💡 Hint: Ensure 'mvn verify' (or 'jacoco:report') ran successfully before this step.")
        return None

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ Error: Failed to parse XML: {e}")
        return None

    # 查找整体指令覆盖率 (Instruction Coverage)
    # JaCoCo 的根节点 <report> 下通常直接包含整体的 <counter> 标签
    total_instructions = 0
    covered_instructions = 0

    # 尝试从根节点直接获取 (这是聚合报告或单模块报告的标准位置)
    counter_elem = root.find(".//counter[@type='INSTRUCTION']")

    if counter_elem is not None:
        missed = int(counter_elem.get("missed", 0))
        covered = int(counter_elem.get("covered", 0))
        total_instructions = missed + covered
        covered_instructions = covered
    else:
        # 如果没有找到顶级 counter，可能是多模块未聚合，尝试累加所有叶子节点 (备选方案)
        # 注意：这通常不是最佳实践，最好使用 report-aggregate
        print("⚠️ Warning: No top-level INSTRUCTION counter found. Attempting to sum up all nodes...")
        for counter in root.iter('counter'):
            if counter.get('type') == 'INSTRUCTION':
                missed = int(counter.get("missed", 0))
                covered = int(counter.get("covered", 0))
                # 这里简单累加可能会导致重复计算，取决于 XML 结构，仅作兜底
                # 对于标准单模块项目，上面的 if 块应该已经命中
                pass
        # 如果还是没找到，返回 None
        if total_instructions == 0:
            print("❌ Error: Could not find any INSTRUCTION counters in the XML.")
            return None

    if total_instructions == 0:
        print("⚠️ Warning: Total instructions count is 0. Check your test execution.")
        return 0.0

    percentage = (covered_instructions / total_instructions) * 100
    return {
        "covered": covered_instructions,
        "missed": total_instructions - covered_instructions,
        "total": total_instructions,
        "percentage": percentage
    }

def main():
    parser = argparse.ArgumentParser(description="Check JaCoCo Coverage from XML")
    parser.add_argument("--file", default="target/site/jacoco/jacoco.xml", help="Path to jacoco.xml")
    parser.add_argument("--threshold", type=float, default=0.0, help="Fail if coverage is below this percentage (e.g., 60.0)")

    args = parser.parse_args()

    print(f"\n🔍 Parsing JaCoCo report: {args.file}")
    result = parse_jacoco_xml(args.file)

    if result is None:
        sys.exit(1)

    # 格式化输出
    print("\n" + "="*50)
    print("📊 JaCoCo Coverage Report")
    print("="*50)
    print(f"✅ Covered Instructions: {result['covered']:,}")
    print(f"❌ Missed Instructions:  {result['missed']:,}")
    print(f"📈 Total Instructions:    {result['total']:,}")
    print("-"*50)

    # 根据覆盖率决定颜色表情
    emoji = "🔴"
    if result['percentage'] >= 80:
        emoji = "🟢"
    elif result['percentage'] >= 60:
        emoji = "🟡"

    print(f"{emoji} Coverage Percentage:   {result['percentage']:.2f}%")
    print("="*50 + "\n")

    # GitHub Actions 专用输出格式 (Notice)
    print(f"::notice title=JaCoCo Coverage::{emoji} Coverage is {result['percentage']:.2f}%")

    # 检查阈值
    if result['percentage'] < args.threshold:
        error_msg = f"Coverage {result['percentage']:.2f}% is below the required threshold of {args.threshold}%"
        print(f"::error title=Coverage Threshold Failed::{error_msg}")
        print(f"❌ FAIL: {error_msg}")
        sys.exit(1)

    print("✅ PASS: Coverage threshold met.")
    sys.exit(0)

if __name__ == "__main__":
    main()