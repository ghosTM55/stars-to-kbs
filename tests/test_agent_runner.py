import subprocess

import pytest

from stars_to_kbs.agent_runner import AgentRunner


def test_none_agent_groups_without_subprocess(tmp_path):
    runner = AgentRunner(provider="none", work_dir=tmp_path)
    output = runner.summarize(prompt="", batch_name="batch", repos=[])
    assert "分类目录" in output


def test_codex_command_uses_stdin_and_output_file(tmp_path):
    runner = AgentRunner(provider="codex", work_dir=tmp_path)
    cmd = runner.build_command(tmp_path / "prompt.md", tmp_path / "out.md")
    assert cmd[:2] == ["codex", "exec"]
    assert "--skip-git-repo-check" in cmd
    assert "-o" in cmd
    assert cmd[-1] == "-"


def test_hermes_command_uses_quiet_mode_and_file_reference(tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    cmd = runner.build_command(tmp_path / "prompt.md", tmp_path / "out.md")
    assert cmd[:2] == ["hermes", "chat"]
    assert "-Q" in cmd
    assert '@file:"' in cmd[-1]


def test_hermes_output_drops_session_id(tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    assert runner.clean_output("session_id: 123\n## 分类目录") == "## 分类目录"


def test_resume_reuses_existing_summary_file_when_manifest_matches(tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    (tmp_path / "batch.summary.md").write_text("session_id: cached\n## 分类目录\n")
    runner.write_manifest("batch", "prompt", [])
    assert runner.summarize("prompt", "batch", [], use_cache=True) == "## 分类目录"


def test_resume_ignores_existing_summary_file_when_manifest_differs(monkeypatch, tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    (tmp_path / "batch.summary.md").write_text("stale")
    runner.write_manifest("batch", "old prompt", [])

    def fake_run(*args, **kwargs):
        (tmp_path / "batch.summary.md").write_text("fresh")
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert runner.summarize("new prompt", "batch", [], use_cache=True) == "fresh"


def test_timeout_raises_runtime_error(monkeypatch, tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path, timeout_seconds=1)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out"):
        runner.summarize("prompt", "batch", [])


def test_unsupported_agent_raises(tmp_path):
    runner = AgentRunner(provider="bad", work_dir=tmp_path)
    try:
        runner.build_command(tmp_path / "prompt.md", tmp_path / "out.md")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("expected ValueError")
