import os
import pytest
import pandas as pd
from pathlib import Path
from src.mypackage.get_player_stats import load_env_file, get_cache_filename, load_from_cache, save_to_cache, call_api, clean_column_names




@pytest.fixture(autouse=True)
def isolate_env_and_cache(tmp_path, monkeypatch):
    """Redirect project_root and clear env vars before each test."""
    # Point project_root to a temp directory
    monkeypatch.setenv("API_KEY", "DUMMYKEY")
    # Ensure any .env load uses tmp_path
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    # Create an empty cache folder
    cache_dir = tmp_path / "api_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup environment
    for k in list(os.environ):
        if k.startswith("API_") or k == "OTHER":
            del os.environ[k]


def test_load_env_file(tmp_path):
    # write a fake .env
    env = tmp_path / ".env"
    env.write_text("API_KEY=HELLO123\nOTHER=FOO\n# comment ignored\n")
    # should load both variables
    load_env_file(str(env))
    assert os.getenv("API_KEY") == "HELLO123"
    assert os.getenv("OTHER") == "FOO"


def test_load_env_file_missing():
    with pytest.raises(FileNotFoundError):
        load_env_file("/no/such/.env")


def test_cache_filename_deterministic(tmp_path):
    cache1 = get_cache_filename("players", {"id":"10", "season":"2022"})
    cache2 = get_cache_filename("players", {"season":"2022", "id":"10"})
    assert cache1 == cache2
    assert cache1.suffix == ".json"
    assert "api_cache" in str(cache1.parent)


def test_save_and_load_cache(tmp_path):
    data = {"response": [{"foo": "bar"}]}
    cache_file = tmp_path / "api_cache" / "test.json"
    save_to_cache(cache_file, data)
    loaded = load_from_cache(cache_file)
    assert loaded == data


def test_load_from_cache_corrupted(tmp_path, capsys):
    cache_file = tmp_path / "api_cache" / "bad.json"
    cache_file.write_text("not valid json")
    result = load_from_cache(cache_file)
    # warn message and file deletion
    captured = capsys.readouterr()
    assert "corrupted" in captured.out
    assert result is None
    assert not cache_file.exists()


def test_clean_column_names():
    # simulate API-normalized DataFrame
    df = pd.DataFrame({
        "statistics_goals": [1],
        "statistics_assists": [2],
        "games_played": [10],
        "player_id": [99],
        "league_name": ["Premier"],
        "country_logo": ["flag.png"]
    })
    cleaned = clean_column_names(df)
    # prefixes removed
    assert "goals" in cleaned.columns
    assert "assists" in cleaned.columns
    # explicit renames applied
    assert "competition_name" in cleaned.columns
    assert "country_flag" in cleaned.columns


class DummyResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status
    def json(self):
        return self._json
    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

@pytest.fixture
def fake_requests(monkeypatch):
    """Monkeypatch requests.get for call_api tests."""
    import requests
    def fake_get(url, headers, params):
        # Return a dummy but correctly structured payload
        payload = {
            "response": [
                {
                    "player": {"id": 1, "name": "Foo"},
                    "team": {"id": 10, "name": "Bar"},
                    "statistics": [{"games": {"appearences": 5}, "goals": {"total": 2}}]
                }
            ]
        }
        return DummyResponse(payload)
    monkeypatch.setattr("requests.get", fake_get)
    return fake_get

def test_call_api_and_json_normalize(fake_requests):
    df = call_api("players", {"id": "1", "season": "2022"})
    # Should produce a DataFrame with flattened columns
    assert not df.empty
    # Check nested fields have been normalized
    assert "player_id" in df.columns or "player_id" in df.columns
    assert "statistics_games_appearences" in df.columns
    assert df["statistics_goals_total"].iloc[0] == 2


def test_get_player_stats(fake_requests):
    # This should call call_api and then clean_column_names
    df = get_player_stats("1", "2022")
    # Should contain at least player and competition columns
    assert "player_id" in df.columns
    assert "competition_name" in df.columns
