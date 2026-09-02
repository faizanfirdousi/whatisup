"""Tests for request-phase timing helper."""

from app.timing import RequestTimer


def test_request_timer_records_phases_and_total():
    timer = RequestTimer()
    timer.mark("db_events", 120.5)
    timer.mark("payload_build", 45.2)

    data = timer.as_dict()
    assert data["db_events"] == 120.5
    assert data["payload_build"] == 45.2
    assert data["total"] >= 0

    header = timer.server_timing_header()
    assert "db_events;dur=120.5" in header
    assert "payload_build;dur=45.2" in header
    assert "total;dur=" in header


def test_request_timer_phase_sync():
    timer = RequestTimer()

    def add(a, b):
        return a + b

    assert timer.phase_sync("compute", add, 2, 3) == 5
    assert timer._phases["compute"] >= 0
