import os
import tempfile
from flask import Flask, request, jsonify, render_template

from codeai_platform import CodeAIConfig, CodeAnalyzer, CodeReviewer, CodeGenerator
from codeai_platform.modules.generator import GenerationRequest

app = Flask(__name__)

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "java": ".java",
    "cpp": ".cpp",
    "c": ".c",
    "csharp": ".cs",
    "go": ".go",
    "rust": ".rs",
}

config = CodeAIConfig(
    project_name="BeermannCode",
    supported_languages=list(LANGUAGE_EXTENSIONS.keys()),
)

analyzer = CodeAnalyzer(config)
reviewer = CodeReviewer(config)
generator = CodeGenerator(config)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "BeermannCode"})


@app.route("/languages")
def languages():
    return jsonify({"languages": list(LANGUAGE_EXTENSIONS.keys())})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    code = data["code"]
    language = data.get("language", "python")

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    ext = LANGUAGE_EXTENSIONS[language]

    with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = analyzer.analyze_file(tmp_path)
        if result is None:
            return jsonify({"error": "Could not analyze code for this language"}), 422
        d = result.to_dict()
        d.pop("file_path", None)
        return jsonify(d)
    finally:
        os.unlink(tmp_path)


@app.route("/review", methods=["POST"])
def review():
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    code = data["code"]
    language = data.get("language", "python")

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    result = reviewer.review_code(code, language)
    d = result.to_dict()
    d.pop("file_path", None)
    return jsonify(d)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or "description" not in data:
        return jsonify({"error": "Missing 'description' field"}), 400

    language = data.get("language", "python")
    description = data["description"]
    function_name = data.get("function_name")
    args = data.get("args", [])
    include_comments = data.get("include_comments", True)
    include_tests = data.get("include_tests", False)

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    if function_name:
        code = generator.generate_function(function_name, args, "None", language)
        return jsonify({"code": code, "language": language, "description": description})

    req = GenerationRequest(
        language=language,
        description=description,
        style=config.generation_style,
        include_comments=include_comments,
        include_tests=include_tests,
    )
    result = generator.generate(req)
    return jsonify(result.to_dict())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=False)
