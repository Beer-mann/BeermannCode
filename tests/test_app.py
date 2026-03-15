"""Tests for Flask API request validation."""

import app as app_module


def make_client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


class TestAnalyzeEndpoint:
    def test_rejects_non_json_payload(self):
        response = make_client().post("/analyze", data="code=print(1)")

        assert response.status_code == 400
        assert response.get_json() == {"error": "Expected a JSON object payload"}

    def test_rejects_empty_code_string(self):
        response = make_client().post("/analyze", json={"code": "   ", "language": "python"})

        assert response.status_code == 400
        assert response.get_json() == {"error": "'code' must be a non-empty string"}


class TestGenerateEndpoint:
    def test_rejects_invalid_args_payload(self):
        response = make_client().post(
            "/generate",
            json={
                "description": "sum two numbers",
                "function_name": "add",
                "args": ["a", ""],
                "language": "python",
            },
        )

        assert response.status_code == 400
        assert response.get_json() == {"error": "'args' must be a list of non-empty strings"}

    def test_generates_function_for_valid_request(self):
        response = make_client().post(
            "/generate",
            json={
                "description": "sum two numbers",
                "function_name": "add",
                "args": ["a", "b"],
                "language": "python",
            },
        )

        payload = response.get_json()
        assert response.status_code == 200
        assert payload["language"] == "python"
        assert "def add(a, b):" in payload["code"]
