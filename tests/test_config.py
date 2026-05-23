from pathlib import Path

from stars_to_kbs.config import Config, default_config_path, resolve_kbs_note_path


def test_example_config_does_not_contain_private_paths_or_tokens():
    text = Path("config.example.toml").read_text()
    assert "ghp_" not in text
    assert "gho_" not in text
    assert "/Users/" not in text
    assert "CloudStorage" not in text


def test_resolve_kbs_directory_to_default_note():
    note = resolve_kbs_note_path("/tmp/personal-notes")
    assert str(note) == "/tmp/personal-notes/GitHub Stars Index.md"


def test_load_config_from_toml(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[github]
username = "alice"
max_repos = 10

[agent]
provider = "hermes"
batch_size = 5

[kbs]
path = "/tmp/kbs"
""".strip())
    config = Config.load(config_file)
    assert config.github.username == "alice"
    assert config.github.max_repos == 10
    assert config.agent.provider == "hermes"
    assert config.agent.batch_size == 5
    assert str(config.kbs.note_path) == "/tmp/kbs/GitHub Stars Index.md"


def test_load_config_rejects_invalid_batch_size(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[agent]
batch_size = 0
""".strip())
    try:
        Config.load(config_file)
    except ValueError as exc:
        assert "batch_size" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_load_config_rejects_unknown_key(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[agent]
batch_siz = 20
""".strip())
    try:
        Config.load(config_file)
    except ValueError as exc:
        assert "Unknown config key" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_default_config_path_uses_home_config(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert default_config_path() == tmp_path / ".config" / "stars-to-kbs" / "config.toml"
