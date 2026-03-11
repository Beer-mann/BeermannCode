import unittest
from pathlib import Path
from codeai_platform.modules.analyzer import CodeAnalyzer, AnalysisResult

class TestCodeAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = CodeAnalyzer()

    def test_analyze_file(self):
        # Create a temporary file with some code
        with open("test_file.py", "w") as file:
            file.write("def add(a, b): return a + b")

        # Analyze the file
        result = self.analyzer.analyze_file("test_file.py")

        # Clean up the temporary file
        Path("test_file.py").unlink()

        # Check if the result is not None
        self.assertIsNotNone(result)

        # Check if the result contains the expected data
        self.assertIn("add", result.functions)
        self.assertIn("a", result.functions["add"].parameters)
        self.assertIn("b", result.functions["add"].parameters)

if __name__ == '__main__':
    unittest.main()
