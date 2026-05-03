"""Tests for flash message widget."""

from airterm.widgets.flash import FlashLevel, FlashMessage


def test_flash_message_creation():
    msg = FlashMessage("test error", FlashLevel.ERROR)
    assert msg.text == "test error"
    assert msg.level == FlashLevel.ERROR


def test_flash_message_default_level():
    msg = FlashMessage("info message")
    assert msg.level == FlashLevel.INFO


def test_flash_level_values():
    assert FlashLevel.INFO.value == "info"
    assert FlashLevel.WARN.value == "warn"
    assert FlashLevel.ERROR.value == "error"
