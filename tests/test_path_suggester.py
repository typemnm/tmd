from pathlib import Path

import pytest

from tmd_cli.app import PathSuggester


@pytest.mark.asyncio
async def test_suggests_matching_file(tmp_path):
    (tmp_path / "readme.md").write_text("", encoding="utf-8")
    (tmp_path / "report.txt").write_text("", encoding="utf-8")
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "rea"))
    assert suggestion == str(tmp_path / "readme.md")


@pytest.mark.asyncio
async def test_suggestion_is_case_insensitive_but_preserves_real_case(tmp_path):
    (tmp_path / "Documents").mkdir()
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "doc"))
    assert suggestion == str(tmp_path / "Documents") + "/"


@pytest.mark.asyncio
async def test_directory_suggestion_has_trailing_slash(tmp_path):
    (tmp_path / "notes").mkdir()
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "not"))
    assert suggestion is not None
    assert suggestion.endswith("/")


@pytest.mark.asyncio
async def test_no_match_returns_none(tmp_path):
    (tmp_path / "readme.md").write_text("", encoding="utf-8")
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "zzz"))
    assert suggestion is None


@pytest.mark.asyncio
async def test_nonexistent_parent_returns_none(tmp_path):
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "no-such-dir" / "x"))
    assert suggestion is None


@pytest.mark.asyncio
async def test_trailing_slash_lists_directory_itself(tmp_path):
    (tmp_path / "alpha.md").write_text("", encoding="utf-8")
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path) + "/")
    assert suggestion == str(tmp_path / "alpha.md")


@pytest.mark.asyncio
async def test_unresolvable_tilde_user_returns_none_without_raising():
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~this-user-does-not-exist-xyz")
    assert suggestion is None


@pytest.mark.asyncio
async def test_empty_prefix_skips_dotfiles(tmp_path):
    (tmp_path / ".bash_history").write_text("", encoding="utf-8")
    (tmp_path / "alpha.md").write_text("", encoding="utf-8")
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path) + "/")
    assert suggestion == str(tmp_path / "alpha.md")


@pytest.mark.asyncio
async def test_sort_is_case_insensitive(tmp_path):
    (tmp_path / "Apricot.md").write_text("", encoding="utf-8")
    (tmp_path / "apple.md").write_text("", encoding="utf-8")
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion(str(tmp_path / "a"))
    assert suggestion == str(tmp_path / "apple.md")


@pytest.mark.asyncio
async def test_tilde_rewrite_does_not_corrupt_sibling_home_dir(tmp_path, monkeypatch):
    """A suggestion under /home/typemann2 must not be mangled into ~2/... just
    because it shares a string prefix with home ("/home/typemann"). Since the
    tilde rewrite doesn't apply here (the match isn't actually under home),
    the raw absolute suggestion also fails the "extends what was typed"
    guard (value is "~"), so get_suggestion must return None rather than
    either the mangled "~2/..." form or the un-rewritten absolute path
    (which would itself render as corrupted ghost text)."""
    home = tmp_path / "typemann"
    sibling = tmp_path / "typemann2"
    sibling.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~")
    assert suggestion is None


@pytest.mark.asyncio
async def test_unresolvable_home_dir_returns_none_without_raising(tmp_path, monkeypatch):
    """Path.home() can raise RuntimeError when the process's home directory
    cannot be determined (no HOME env var, no passwd entry for the uid —
    realistic in some containerized environments). The tilde-rewrite branch
    in get_suggestion calls Path.home() AFTER a match is found; that call
    must be covered by the same try/except as the rest of the method, or
    the RuntimeError escapes get_suggestion and crashes the whole app via
    Textual's Input worker (exit_on_error=True by default)."""
    (tmp_path / "readme.md").write_text("", encoding="utf-8")

    def raise_runtime_error():
        raise RuntimeError("Could not determine home directory.")

    # Path.expanduser() resolves "~" via os.path.expanduser, which reads
    # the HOME env var directly (not via Path.home()), so setting HOME
    # here lets get_suggestion reach the actual tilde-rewrite call site
    # while Path.home() itself is forced to raise.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", staticmethod(raise_runtime_error))

    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~/rea")
    assert suggestion is None
