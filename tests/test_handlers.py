from unittest.mock import AsyncMock, MagicMock

import pytest

from main import (
    AWAITING,
    AWAITING_DELAY,
    AWAITING_DELTA,
    CFG_DELTA,
    CFG_INTERVAL,
    MIN_INTERVAL_SEC,
    on_text_input,
)


def make_update(text: str) -> MagicMock:
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def make_context(state, **chat_data) -> MagicMock:
    context = MagicMock()
    context.chat_data = {AWAITING: state, **chat_data}
    return context


# ---------------------------------------------------------------------------
# Delay input
# ---------------------------------------------------------------------------

async def test_valid_delay_sets_interval():
    update = make_update("5")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    assert context.chat_data[CFG_INTERVAL] == 300  # 5 * 60
    assert context.chat_data[AWAITING] is None
    update.message.reply_text.assert_called_once()


async def test_delay_enforces_minimum():
    # 1 minute → 60s, but MIN_INTERVAL_SEC floor applies if < floor
    update = make_update("1")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    assert context.chat_data[CFG_INTERVAL] >= MIN_INTERVAL_SEC


async def test_zero_delay_rejected():
    update = make_update("0")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_INTERVAL not in context.chat_data


async def test_negative_delay_rejected():
    update = make_update("-3")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_INTERVAL not in context.chat_data


async def test_non_numeric_delay_rejected():
    update = make_update("abc")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_INTERVAL not in context.chat_data


async def test_float_delay_rejected():
    # Must be integer
    update = make_update("2.5")
    context = make_context(AWAITING_DELAY)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_INTERVAL not in context.chat_data


# ---------------------------------------------------------------------------
# Delta input
# ---------------------------------------------------------------------------

async def test_valid_delta_sets_value():
    update = make_update("10.5")
    context = make_context(AWAITING_DELTA)
    await on_text_input(update, context)
    assert context.chat_data[CFG_DELTA] == 10.5
    assert context.chat_data[AWAITING] is None
    update.message.reply_text.assert_called_once()


async def test_zero_delta_rejected():
    update = make_update("0")
    context = make_context(AWAITING_DELTA)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_DELTA not in context.chat_data


async def test_negative_delta_rejected():
    update = make_update("-5")
    context = make_context(AWAITING_DELTA)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_DELTA not in context.chat_data


async def test_non_numeric_delta_rejected():
    update = make_update("hello")
    context = make_context(AWAITING_DELTA)
    await on_text_input(update, context)
    update.message.reply_text.assert_called_once()
    assert CFG_DELTA not in context.chat_data


# ---------------------------------------------------------------------------
# State guards
# ---------------------------------------------------------------------------

async def test_no_awaiting_state_ignores_text():
    update = make_update("anything")
    context = make_context(None)
    await on_text_input(update, context)
    update.message.reply_text.assert_not_called()


async def test_integer_delta_accepted():
    update = make_update("2")
    context = make_context(AWAITING_DELTA)
    await on_text_input(update, context)
    assert context.chat_data[CFG_DELTA] == 2.0
