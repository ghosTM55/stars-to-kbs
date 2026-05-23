from stars_to_kbs.agent_runner import AgentRunner


def test_none_agent_groups_without_subprocess(tmp_path):
    runner = AgentRunner(provider="none", work_dir=tmp_path)
    output = runner.summarize(prompt="", batch_name="batch", repos=[])
    assert "分类目录" in output


def test_codex_command_uses_output_file(tmp_path):
    runner = AgentRunner(provider="codex", work_dir=tmp_path)
    cmd = runner.build_command("hello", tmp_path / "out.md")
    assert cmd[:2] == ["codex", "exec"]
    assert "--skip-git-repo-check" in cmd
    assert "-o" in cmd


def test_hermes_command_uses_quiet_mode(tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    cmd = runner.build_command("hello", tmp_path / "out.md")
    assert cmd[:2] == ["hermes", "chat"]
    assert "-Q" in cmd


def test_hermes_output_drops_session_id(tmp_path):
    runner = AgentRunner(provider="hermes", work_dir=tmp_path)
    assert runner.clean_output("session_id: 123\n## 分类目录") == "## 分类目录"


def test_unsupported_agent_raises(tmp_path):
    runner = AgentRunner(provider="bad", work_dir=tmp_path)
    try:
        runner.build_command("hello", tmp_path / "out.md")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("expected ValueError")
