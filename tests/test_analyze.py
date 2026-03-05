from main import analyze_price


def test_empty_history_returns_empty():
    assert analyze_price(50000.0, []) == ""


def test_single_item_history_returns_empty():
    assert analyze_price(50000.0, [50000.0]) == ""


def test_zero_oldest_price_returns_empty():
    # Guard against division by zero
    assert analyze_price(100.0, [0.0, 50.0]) == ""


def test_flat_price():
    history = [50000.0] * 10
    result = analyze_price(50000.0, history)
    assert "flat" in result


def test_upward_move():
    history = [49000.0, 49500.0]
    result = analyze_price(50000.0, history)
    assert "up" in result.lower()


def test_downward_move():
    history = [51000.0, 50500.0]
    result = analyze_price(49500.0, history)
    assert "down" in result.lower()


def test_sharp_move():
    # >1% change → "sharply"
    history = [50000.0, 50100.0]
    result = analyze_price(50600.0, history)
    assert "sharply" in result.lower()


def test_slight_move():
    # <0.3% change → "slightly" or "flat"
    history = [50000.0, 50050.0]
    result = analyze_price(50100.0, history)
    assert "slightly" in result.lower() or "flat" in result.lower()


def test_accelerating_trend():
    # Second half move is much larger than first half → "accelerating"
    history = [50000.0, 50100.0, 50500.0]
    result = analyze_price(51500.0, history)
    assert "accelerating" in result


def test_reversing_trend():
    # Going up then sharply down → "reversing"
    history = [50000.0, 50500.0, 50000.0]
    result = analyze_price(49000.0, history)
    assert "reversing" in result


def test_result_contains_pct():
    history = [50000.0, 50500.0]
    result = analyze_price(51000.0, history)
    assert "%" in result


def test_result_contains_tick_count():
    history = [50000.0, 50200.0, 50400.0]
    result = analyze_price(50600.0, history)
    assert "3 ticks" in result
