#!/usr/bin/env python3
"""CLI script for running RAG evaluations."""

import asyncio
import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.dataset import create_sample_dataset, EvaluationDataset
from src.evaluation.runner import EvaluationRunner


async def run_evaluation(args):
    """Run the evaluation."""
    print("\n" + "=" * 60)
    print("🔍 GenAI Auto - RAG Evaluation Pipeline")
    print("=" * 60)
    
    # Load or create dataset
    if args.dataset:
        print(f"\n📂 Loading dataset from: {args.dataset}")
        dataset = EvaluationDataset.load(args.dataset)
    else:
        print("\n📂 Using sample dataset")
        dataset = create_sample_dataset()
    
    print(f"   Total test cases: {len(dataset)}")
    
    # Filter if specified
    categories = args.categories.split(",") if args.categories else None
    difficulties = args.difficulties.split(",") if args.difficulties else None
    
    if categories:
        print(f"   Filtering categories: {categories}")
    if difficulties:
        print(f"   Filtering difficulties: {difficulties}")
    
    # Run evaluation
    print(f"\n🚀 Starting evaluation: {args.name}")
    print(f"   Top-K: {args.k}")
    print(f"   Max concurrent: {args.concurrent}")
    print()
    
    runner = EvaluationRunner()
    
    report = await runner.run_dataset(
        dataset=dataset,
        name=args.name,
        k=args.k,
        max_concurrent=args.concurrent,
        categories=categories,
        difficulties=difficulties,
    )
    
    # Print summary
    print(report.summary())
    
    # Save report
    if args.output:
        report.save(args.output)
        print(f"\n💾 Report saved to: {args.output}")
    else:
        default_path = f"evaluation_report_{args.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report.save(default_path)
        print(f"\n💾 Report saved to: {default_path}")
    
    # Print recommendations
    print("\n📋 Recommendations:")
    
    if report.avg_retrieval_precision < 0.6:
        print("   ⚠️  Low retrieval precision - consider:")
        print("      • Adding more relevant documents to knowledge base")
        print("      • Adjusting chunking strategy")
        print("      • Fine-tuning embedding model")
    
    if report.avg_faithfulness < 0.7:
        print("   ⚠️  Low faithfulness - consider:")
        print("      • Improving prompt to emphasize grounding in context")
        print("      • Reducing temperature in generation")
    
    if report.avg_answer_relevance < 0.7:
        print("   ⚠️  Low answer relevance - consider:")
        print("      • Improving query understanding")
        print("      • Better prompt engineering")
    
    if report.avg_total_latency_ms > 5000:
        print("   ⚠️  High latency - consider:")
        print("      • Reducing top-K value")
        print("      • Enabling caching")
        print("      • Using faster model")
    
    if report.avg_overall_score >= 0.8:
        print("   ✅ Overall score is good!")
    
    return report


async def compare_evaluations(args):
    """Compare multiple evaluation reports."""
    import json
    
    print("\n" + "=" * 60)
    print("📊 GenAI Auto - Evaluation Comparison")
    print("=" * 60)
    
    reports = []
    for path in args.reports:
        with open(path, 'r') as f:
            data = json.load(f)
        
        from src.evaluation.runner import EvaluationReport
        report = EvaluationReport(**data)
        reports.append(report)
        print(f"\n📄 Loaded: {path} ({report.name})")
    
    runner = EvaluationRunner()
    comparison = await runner.compare_runs(reports)
    
    print("\n" + "-" * 60)
    print("COMPARISON RESULTS")
    print("-" * 60)
    
    for metric, data in comparison["metrics"].items():
        print(f"\n{metric}:")
        for i, (name, value) in enumerate(zip(comparison["runs"], data["values"])):
            marker = "👑" if value == data["best"] else "  "
            print(f"  {marker} {name}: {value:.4f}")
        
        improvement = data["improvement"]
        if improvement > 0:
            print(f"  📈 Improvement: +{improvement:.1f}%")
        elif improvement < 0:
            print(f"  📉 Regression: {improvement:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="GenAI Auto RAG Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run evaluation with sample dataset
  python run_evaluation.py run --name my-eval

  # Run with specific categories
  python run_evaluation.py run --name my-eval --categories specifications,maintenance

  # Run with custom dataset
  python run_evaluation.py run --name my-eval --dataset custom_dataset.json

  # Compare multiple runs
  python run_evaluation.py compare report1.json report2.json
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run evaluation")
    run_parser.add_argument(
        "--name", "-n",
        default=f"eval-{datetime.now().strftime('%Y%m%d-%H%M')}",
        help="Evaluation name",
    )
    run_parser.add_argument(
        "--dataset", "-d",
        help="Path to custom dataset JSON file",
    )
    run_parser.add_argument(
        "--categories", "-c",
        help="Comma-separated list of categories to evaluate",
    )
    run_parser.add_argument(
        "--difficulties",
        help="Comma-separated list of difficulties (easy,medium,hard)",
    )
    run_parser.add_argument(
        "--k", "-k",
        type=int,
        default=5,
        help="Number of documents to retrieve (default: 5)",
    )
    run_parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="Max concurrent evaluations (default: 3)",
    )
    run_parser.add_argument(
        "--output", "-o",
        help="Output path for report JSON",
    )
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare evaluation reports")
    compare_parser.add_argument(
        "reports",
        nargs="+",
        help="Paths to report JSON files to compare",
    )
    
    # Dataset command
    dataset_parser = subparsers.add_parser("dataset", help="Dataset operations")
    dataset_parser.add_argument(
        "--export",
        help="Export sample dataset to JSON file",
    )
    
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(run_evaluation(args))
    elif args.command == "compare":
        asyncio.run(compare_evaluations(args))
    elif args.command == "dataset":
        if args.export:
            dataset = create_sample_dataset()
            dataset.save(args.export)
            print(f"✅ Sample dataset exported to: {args.export}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
