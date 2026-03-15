import unittest

from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.analyzer import AnalysisResult, CodeAnalyzer


class TestCodeAnalyzer(unittest.TestCase):
    def setUp(self):
        config = CodeAIConfig()
        config.get_openai_client = lambda use_real=False: None
        self.analyzer = CodeAnalyzer(config)

    def test_analyze_file(self):
        with open("test_file.py", "w", encoding="utf-8") as file:
            file.write("def add(a, b):\n    return a + b\n")

        self.addCleanup(lambda: __import__("pathlib").Path("test_file.py").unlink(missing_ok=True))

        result = self.analyzer.analyze_file("test_file.py")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.language, "python")
        self.assertGreater(result.lines_of_code, 0)


if __name__ == "__main__":
    unittest.main()
