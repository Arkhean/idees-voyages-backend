from src.config import Config


def test_cors_origins_list_splits_comma_separated_origins():
    config = Config(CORS_ORIGINS="http://localhost:8081, https://app.example.com")
    assert config.cors_origins_list == [
        "http://localhost:8081",
        "https://app.example.com",
    ]
