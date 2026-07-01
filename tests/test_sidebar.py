"""Smoke tests for tmd.sidebar — lightweight structural checks.

Full integration tests are deferred to Task 6 (app-level tests).
"""
from textual.message import Message
from textual.widget import Widget

from tmd.sidebar import Sidebar


def test_import():
    """Sidebar can be imported without error."""
    assert Sidebar is not None


def test_sidebar_is_widget_subclass():
    """Sidebar must be a Textual Widget subclass."""
    assert issubclass(Sidebar, Widget)


def test_file_selected_is_message_subclass():
    """Sidebar.FileSelected must be a Textual Message subclass."""
    assert issubclass(Sidebar.FileSelected, Message)


def test_file_selected_has_path_attribute():
    """Sidebar.FileSelected instances expose a .path attribute."""
    msg = Sidebar.FileSelected(path="/tmp/note.md")
    assert msg.path == "/tmp/note.md"


def test_sidebar_default_root_is_cwd(tmp_path, monkeypatch):
    """When root is omitted, Sidebar._root defaults to the current working dir."""
    import os
    monkeypatch.chdir(tmp_path)
    sb = Sidebar()
    assert sb._root == str(tmp_path)


def test_sidebar_accepts_explicit_root(tmp_path):
    """When root is provided, Sidebar._root stores it exactly."""
    sb = Sidebar(root=str(tmp_path))
    assert sb._root == str(tmp_path)
