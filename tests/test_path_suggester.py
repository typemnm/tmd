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
    """Typing a bare "~" expands to the full home directory, whose basename
    (e.g. "typemann") is unrelated in length to what was actually typed
    ("~", one character) — there is no "/" separating a literal typed head
    from the segment being completed, so the expanded basename isn't a
    literal tail of value. Matching entries in the home directory's parent
    (here "typemann2", which shares a string prefix with "typemann") must
    not be turned into ghost text that doesn't literally extend "~" (e.g.
    "typemann2/" with the tilde silently dropped). get_suggestion must
    return None rather than corrupt output in this case."""
    home = tmp_path / "typemann"
    sibling = tmp_path / "typemann2"
    sibling.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~")
    assert suggestion is None


@pytest.mark.asyncio
async def test_home_dir_completion_does_not_call_path_home(tmp_path, monkeypatch):
    """get_suggestion builds suggestions from the literal typed prefix, not
    by reversing a ~-expansion via Path.home() — so a "~/..." completion
    must succeed even in the (realistic, e.g. some containers) case where
    Path.home() itself would raise RuntimeError because the process's home
    directory can't be determined via the passwd database. Path.expanduser()
    resolves "~" via the HOME env var directly, independent of Path.home(),
    so the completion should work and Path.home() should never be called."""
    (tmp_path / "readme.md").write_text("", encoding="utf-8")

    def raise_runtime_error():
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", staticmethod(raise_runtime_error))

    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~/rea")
    assert suggestion == "~/readme.md"


@pytest.mark.asyncio
async def test_completes_into_other_users_resolvable_home(tmp_path, monkeypatch):
    """~root-style completions to a real, resolvable OTHER user's home
    directory must work — the old rewrite-based approach only ever rewrote
    matches under the CURRENT user's home (via Path.home()), so anything
    resolving under someone else's home was dropped even though it's a
    perfectly valid completion. Simulate a resolvable other-user home
    without needing a second real user account by monkeypatching
    Path.expanduser to redirect "~otheruser" exactly like the real
    os.path.expanduser would for an existing other user."""
    other_home = tmp_path / "otherhome"
    other_home.mkdir()
    (other_home / "project").mkdir()

    real_expanduser = Path.expanduser

    def fake_expanduser(self):
        text = str(self)
        if text == "~otheruser" or text.startswith("~otheruser/"):
            return Path(str(other_home) + text[len("~otheruser") :])
        return real_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", fake_expanduser)

    suggester = PathSuggester()
    suggestion = await suggester.get_suggestion("~otheruser/pro")
    assert suggestion == "~otheruser/project/"


@pytest.mark.asyncio
async def test_unicode_casefold_length_mismatch_does_not_corrupt_suggestion(tmp_path):
    """"straße".casefold() == "strasse" (7 chars vs the raw 6-char "straße"),
    so a needle like "stras" can match inside the casefolded name at a point
    that has no corresponding raw character boundary. Textual renders ghost
    text as suggestion[len(value):], a RAW index — if get_suggestion built a
    suggestion assuming the casefolded and raw lengths line up, that slice
    would land mid-fold and corrupt the display (e.g. ".../strase/" instead
    of the real ".../Straße/"). get_suggestion must not return a suggestion
    string that would render corrupted; here that means declining to
    complete rather than fabricating a raw index that doesn't exist."""
    (tmp_path / "Straße").mkdir()
    suggester = PathSuggester()
    value = str(tmp_path / "stras")
    suggestion = await suggester.get_suggestion(value)
    if suggestion is not None:
        # If a suggestion is ever returned here, it must be safe to render:
        # value + suggestion[len(value):] must reconstruct a string that
        # doesn't corrupt the real (raw, non-casefolded) directory name.
        ghost = suggestion[len(value) :]
        assert value + ghost == str(tmp_path / "Straße") + "/"
    else:
        assert suggestion is None
