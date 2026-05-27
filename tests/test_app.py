from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


@patch("app.ollama.chat")
@patch("app.run_lapmatch")
@patch("app.DDGS")
def test_recommend_endpoint(mock_ddgs, mock_run_lapmatch, mock_ollama_chat):
    # 1. Mock Ollama responses
    # Call 1 (extraction): Returns JSON of laptop requirements
    mock_response_1 = {"message": {"content": '{"budget": 70000, "q_perf": "B", "q_port": "B", "q_batt": "B"}'}}
    # Call 2 (rationales): Returns JSON list of reviews
    mock_response_2 = {
        "message": {"content": '{"reviews": ["Excellent balanced notebook.", "Solid budget keyboard."]}'}
    }
    mock_ollama_chat.side_effect = [mock_response_1, mock_response_2]

    # 2. Mock run_lapmatch TOPSIS output
    mock_results_df = pd.DataFrame(
        [
            {
                "name": "Laptop Premium X",
                "price": 65000,
                "Match_Score": 0.88,
                "Weight_Proxy": 1.6,
                "Battery_Proxy": 6.0,
            },
            {"name": "Laptop Budget Y", "price": 68000, "Match_Score": 0.81, "Weight_Proxy": 1.9, "Battery_Proxy": 5.0},
        ]
    )
    mock_run_lapmatch.return_value = mock_results_df

    # 3. Mock DuckDuckGo Image scraping API
    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.images.return_value = [{"image": "https://test-image.url/laptop.png"}]
    mock_ddgs.return_value = mock_ddgs_instance

    # Send post request to /api/recommend
    response = client.post("/api/recommend", json={"prompt": "I need a standard work laptop under 70000"})

    assert response.status_code == 200
    data = response.json()

    # Assertions on returned recommendations structure
    assert "results" in data
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "Laptop Premium X"
    assert data["results"][0]["pitch"] == "Excellent balanced notebook."
    assert data["results"][0]["image_url"] == "https://test-image.url/laptop.png"
    assert "calculations" in data
    assert data["calculations"]["extracted_intent"]["budget"] == 70000
