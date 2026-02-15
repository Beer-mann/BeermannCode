#!/usr/bin/env python3
"""
Main CLI interface for CodeAI Platform.
Provides command-line access to all platform features.
"""

import argparse
import json
import sys
from pathlib import Path

from codeai_platform import CodeAIConfig, CodeAnalyzer, CodeGenerator, CodeReviewer
from codeai_platform.generator import GenerationRequest


def analyze_command(args):
    """Handle analyze command."""
    config = CodeAIConfig()
    analyzer = CodeAnalyzer(config)
    
    if args.file:
        print(f"Analyzing file: {args.file}")
        result = analyzer.analyze_file(args.file)
        if result:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print("File type not supported for analysis")
    elif args.project:
        print(f"Analyzing project: {args.project}")
        results = analyzer.analyze_project(args.project)
        output = [r.to_dict() for r in results]
        print(json.dumps(output, indent=2))
    else:
        print("Error: Either --file or --project must be specified")
        sys.exit(1)


def review_command(args):
    """Handle review command."""
    config = CodeAIConfig(review_depth=args.depth)
    reviewer = CodeReviewer(config)
    
    print(f"Reviewing file: {args.file}")
    result = reviewer.review_file(args.file)
    
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Code Review: {result.file_path}")
        print(f"Language: {result.language}")
        print(f"Rating: {result.overall_rating.upper()}")
        print(f"{'='*60}\n")
        print(result.summary)
        print(f"\n{'='*60}")
        print("Comments:")
        print(f"{'='*60}\n")
        for comment in result.comments:
            severity_icon = {
                "critical": "🔴",
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️"
            }.get(comment.severity, "•")
            
            line_info = f"Line {comment.line_number}: " if comment.line_number else ""
            print(f"{severity_icon} {line_info}{comment.message}")
            if comment.suggestion:
                print(f"   → {comment.suggestion}")
            print()


def generate_command(args):
    """Handle generate command."""
    config = CodeAIConfig()
    generator = CodeGenerator(config)
    
    if args.function:
        print(f"Generating function in {args.language}")
        code = generator.generate_function(
            args.name or "generated_function",
            args.params or [],
            args.return_type or "void",
            args.language
        )
        print(code)
    elif args.class_:
        print(f"Generating class in {args.language}")
        code = generator.generate_class(
            args.name or "GeneratedClass",
            args.attributes or [],
            args.methods or [],
            args.language
        )
        print(code)
    else:
        # General generation
        request = GenerationRequest(
            language=args.language,
            description=args.description,
            include_comments=args.comments,
            include_tests=args.tests
        )
        result = generator.generate(request)
        print(result.code)


def config_command(args):
    """Handle config command."""
    if args.show:
        config = CodeAIConfig()
        print("Current Configuration:")
        print(json.dumps(config.to_dict(), indent=2))
    elif args.validate:
        config = CodeAIConfig()
        try:
            config.validate()
            print("✓ Configuration is valid")
        except ValueError as e:
            print(f"✗ Configuration error: {e}")
            sys.exit(1)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="CodeAI Platform - AI-powered software development assistant"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code files or projects")
    analyze_parser.add_argument("--file", help="Analyze a single file")
    analyze_parser.add_argument("--project", help="Analyze entire project directory")
    analyze_parser.set_defaults(func=analyze_command)
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review code quality")
    review_parser.add_argument("file", help="File to review")
    review_parser.add_argument("--depth", choices=["basic", "standard", "comprehensive"],
                              default="standard", help="Review depth")
    review_parser.add_argument("--format", choices=["text", "json"], default="text",
                              help="Output format")
    review_parser.set_defaults(func=review_command)
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate code")
    generate_parser.add_argument("--language", required=True, help="Programming language")
    generate_parser.add_argument("--description", help="Description of code to generate")
    generate_parser.add_argument("--function", action="store_true", help="Generate function")
    generate_parser.add_argument("--class", dest="class_", action="store_true",
                                help="Generate class")
    generate_parser.add_argument("--name", help="Name for function/class")
    generate_parser.add_argument("--params", nargs="*", help="Function parameters")
    generate_parser.add_argument("--attributes", nargs="*", help="Class attributes")
    generate_parser.add_argument("--methods", nargs="*", help="Class methods")
    generate_parser.add_argument("--return-type", help="Return type")
    generate_parser.add_argument("--comments", action="store_true", default=True,
                                help="Include comments")
    generate_parser.add_argument("--tests", action="store_true", help="Include tests")
    generate_parser.set_defaults(func=generate_command)
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.add_argument("--validate", action="store_true", help="Validate config")
    config_parser.set_defaults(func=config_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
