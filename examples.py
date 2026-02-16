"""
Example usage of CodeAI Platform for software projects.
Demonstrates the main features and capabilities.
"""

from codeai_platform import CodeAIConfig, CodeAnalyzer, CodeGenerator, CodeReviewer
from codeai_platform.generator import GenerationRequest


def demo_code_analysis():
    """Demonstrate code analysis capabilities."""
    print("\n" + "="*60)
    print("DEMO: Code Analysis")
    print("="*60 + "\n")

    config = CodeAIConfig(supported_languages=["python"])
    analyzer = CodeAnalyzer(config)

    # Analyze this example file
    result = analyzer.analyze_file(__file__)

    print(f"File: {result.file_path}")
    print(f"Language: {result.language}")
    print(f"Lines of code: {result.lines_of_code}")
    print(f"Complexity score: {result.complexity_score}/100")
    print(f"Quality score: {result.quality_score}/100")
    print(f"\nIssues found: {len(result.issues)}")
    for issue in result.issues[:3]:  # Show first 3
        print(f"  - Line {issue.get('line')}: {issue['message']}")

    if result.suggestions:
        print(f"\nSuggestions:")
        for suggestion in result.suggestions[:3]:
            print(f"  - {suggestion}")


def demo_code_generation():
    """Demonstrate code generation capabilities."""
    print("\n" + "="*60)
    print("DEMO: Code Generation")
    print("="*60 + "\n")

    config = CodeAIConfig()
    generator = CodeGenerator(config)

    # Generate a function
    print("Generated Python function:")
    print("-" * 60)
    code = generator.generate_function(
        name="calculate_average",
        parameters=["numbers"],
        return_type="float",
        language="python"
    )
    print(code)

    # Generate a class
    print("\nGenerated JavaScript class:")
    print("-" * 60)
    code = generator.generate_class(
        name="DataProcessor",
        attributes=["data", "config"],
        methods=["process", "validate", "export"],
        language="javascript"
    )
    print(code)


def demo_code_review():
    """Demonstrate code review capabilities."""
    print("\n" + "="*60)
    print("DEMO: Code Review")
    print("="*60 + "\n")

    config = CodeAIConfig(review_depth="comprehensive")
    reviewer = CodeReviewer(config)

    # Sample code with issues
    sample_code = '''
def process_data(data, user_id):
    result = ""
    for item in data:
        result += str(item) + ","
    password = "hardcoded123"
    query = "SELECT * FROM users WHERE id=" + user_id
    return result
'''

    result = reviewer.review_code(sample_code, "python")

    print(f"Overall Rating: {result.overall_rating.upper()}")
    print(f"\n{result.summary}")

    print("\nDetailed Comments:")
    for comment in result.comments:
        severity_icon = {
            "critical": "🔴",
            "warning": "⚠️",
            "info": "ℹ️"
        }.get(comment.severity, "•")

        print(f"\n{severity_icon} [{comment.severity.upper()}] {comment.category.upper()}")
        print(f"   {comment.message}")
        if comment.suggestion:
            print(f"   💡 Suggestion: {comment.suggestion}")


def demo_custom_config():
    """Demonstrate custom configuration."""
    print("\n" + "="*60)
    print("DEMO: Custom Configuration")
    print("="*60 + "\n")

    # Create custom config
    config = CodeAIConfig(
        project_name="web_application",
        project_type="web",
        supported_languages=["python", "javascript"],
        review_depth="comprehensive",
        generation_style="verbose",
        include_tests=True
    )

    print("Custom configuration created:")
    print(f"  Project: {config.project_name}")
    print(f"  Type: {config.project_type}")
    print(f"  Languages: {', '.join(config.supported_languages)}")
    print(f"  Review depth: {config.review_depth}")
    print(f"  Generation style: {config.generation_style}")

    # Validate configuration
    try:
        config.validate()
        print("\n✓ Configuration is valid")
    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("CodeAI Platform - Software Project Assistant")
    print("="*60)

    try:
        demo_custom_config()
        demo_code_generation()
        demo_code_analysis()
        demo_code_review()

        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nError during demo: {e}")


if __name__ == "__main__":
    main()
