# CodeAI Platform

An AI-powered platform specifically designed for software development projects. Provides intelligent code analysis, generation, and review capabilities to enhance developer productivity.

## 🚀 Features

- **Code Analysis**: Analyze code quality, complexity, and potential issues
- **Code Generation**: Generate functions, classes, and boilerplate code
- **Code Review**: Automated code review with actionable suggestions
- **Multi-Language Support**: Python, JavaScript, Java, C++, C#, Go, Rust
- **Configurable**: Customizable settings for different project types

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Beer-mann/BeermannCode.git
cd BeermannCode

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🎯 Quick Start

### Using the Python API

```python
from codeai_platform import CodeAIConfig, CodeAnalyzer, CodeReviewer, CodeGenerator

# Create configuration
config = CodeAIConfig(
    project_name="my_project",
    supported_languages=["python", "javascript"]
)

# Analyze code
analyzer = CodeAnalyzer(config)
result = analyzer.analyze_file("myfile.py")
print(f"Quality Score: {result.quality_score}/100")

# Review code
reviewer = CodeReviewer(config)
review = reviewer.review_file("myfile.py")
print(f"Rating: {review.overall_rating}")

# Generate code
generator = CodeGenerator(config)
code = generator.generate_function("process_data", ["input"], "dict", "python")
print(code)
```

### Using the CLI

```bash
# Analyze a file
python codeai_cli.py analyze --file myfile.py

# Review code
python codeai_cli.py review myfile.py --depth comprehensive

# Generate a function
python codeai_cli.py generate --language python --function --name calculate_sum --params a b

# Generate a class
python codeai_cli.py generate --language javascript --class --name UserManager --methods create update delete

# Show configuration
python codeai_cli.py config --show
```

## 📚 Examples

Run the examples to see all features in action:

```bash
python examples.py
```

## ⚙️ Configuration

Create a `config.json` file based on `config.example.json`:

```json
{
  "project_name": "my_software_project",
  "project_type": "web",
  "supported_languages": ["python", "javascript", "java"],
  "review_depth": "standard",
  "generation_style": "clean",
  "include_tests": true
}
```

## 🏗️ Platform Components

### Code Analyzer
- Calculates code complexity
- Detects potential issues
- Provides quality metrics
- Generates improvement suggestions

### Code Generator
- Generates functions with proper signatures
- Creates class structures
- Includes documentation comments
- Optional test generation

### Code Reviewer
- Style checking
- Performance analysis
- Security vulnerability detection
- Maintainability assessment

## 🎨 Use Cases

- **Code Quality Assurance**: Automatically review code for quality issues
- **Rapid Prototyping**: Generate boilerplate code quickly
- **Technical Debt Management**: Identify and track code issues
- **Developer Onboarding**: Help new developers understand code quality standards
- **CI/CD Integration**: Automate code quality checks in pipelines

## 📖 Documentation

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| project_name | string | "default_project" | Name of your project |
| project_type | string | "general" | Type: general, web, mobile, data_science |
| supported_languages | list | ["python", "javascript", "java"] | Languages to analyze |
| review_depth | string | "standard" | Review depth: basic, standard, comprehensive |
| generation_style | string | "clean" | Code style: minimal, clean, verbose |

### Supported Languages

- Python (.py)
- JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
- Java (.java)
- C/C++ (.c, .cpp, .h, .hpp)
- C# (.cs)
- Go (.go)
- Rust (.rs)

## 🌐 REST API (Port 5004)

### Start the server

```bash
./start.sh
# or
python3 app.py
```

### Endpoints

#### GET /health
```bash
curl http://localhost:5004/health
# {"status": "ok", "service": "BeermannCode"}
```

#### GET /languages
```bash
curl http://localhost:5004/languages
# {"languages": ["python", "javascript", "java", "cpp", "c", "csharp", "go", "rust"]}
```

#### POST /analyze
Analyze code quality, complexity, and issues.

```bash
curl -X POST http://localhost:5004/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello():\n    print(\"hello\")\n", "language": "python"}'
```

Response: `language`, `lines_of_code`, `complexity_score`, `quality_score`, `issues`, `suggestions`

#### POST /review
Review code for style, performance, security, and maintainability.

```bash
curl -X POST http://localhost:5004/review \
  -H "Content-Type: application/json" \
  -d '{"code": "password = \"secret123\"\neval(user_input)\n", "language": "python"}'
```

Response: `overall_rating` (excellent/good/fair/poor), `comments`, `summary`, `metrics`

#### POST /generate
Generate code from a description or function name.

```bash
# Generate by description
curl -X POST http://localhost:5004/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "function to sort a list", "language": "python"}'

# Generate a specific function
curl -X POST http://localhost:5004/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "calculate sum", "function_name": "calculate_sum", "args": ["a", "b"], "language": "python"}'
```

Response: `code`, `language`, `description` (and `includes_tests`, `metadata` for description-based generation)

---

## 🤝 Contributing

Contributions are welcome! This platform is designed for software projects and can be extended with additional features.

## 📄 License

Open source software for programming and software development projects.

## 🔗 Links

- Repository: [Beer-mann/BeermannCode](https://github.com/Beer-mann/BeermannCode)
- Issues: [Report bugs or request features](https://github.com/Beer-mann/BeermannCode/issues)
