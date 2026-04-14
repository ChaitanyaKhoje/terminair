"""Tests for command palette argument validation."""

from airterm.widgets.command_palette import CommandExecutor


def test_parse_empty():
    cmd, args = CommandExecutor.parse("")
    assert cmd is None
    assert args == []


def test_parse_simple_command():
    cmd, args = CommandExecutor.parse("pools")
    assert cmd == "pools"
    assert args == []


def test_parse_command_with_arg():
    cmd, args = CommandExecutor.parse("dag my_dag_id")
    assert cmd == "dag"
    assert args == ["my_dag_id"]


def test_unknown_command_rejected():
    assert CommandExecutor.validate("unknown_cmd", []) is False


def test_known_command_no_args_valid():
    assert CommandExecutor.validate("pools", []) is True


def test_dag_command_requires_arg():
    assert CommandExecutor.validate("dag", []) is False
    assert CommandExecutor.validate("dag", ["my_dag"]) is True


def test_ctx_command_requires_arg():
    assert CommandExecutor.validate("ctx", []) is False
    assert CommandExecutor.validate("ctx", ["prod"]) is True


def test_no_arg_commands_reject_extra_args():
    assert CommandExecutor.validate("pools", ["extra"]) is False
    assert CommandExecutor.validate("health", ["extra"]) is False
