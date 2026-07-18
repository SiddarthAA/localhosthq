"""Dispatch invariant (design §3, §8): emergency services are contacted ONLY on a
verified crash.confirmed — never on unconfirmed, cancelled, unverified, or drowsiness."""

from ridewme_backend.dispatch import Dispatcher, should_dispatch


def crash(status):
    return {"type": "crash", "driver_id": "d1",
            "payload": {"incident_id": "c1", "status": status, "severity": "severe",
                        "location": {"lat": 1.0, "lon": 2.0}}}


def test_should_dispatch_only_on_confirmed():
    assert should_dispatch(crash("confirmed"), verified=True) is True
    assert should_dispatch(crash("unconfirmed"), verified=True) is False
    assert should_dispatch(crash("cancelled"), verified=True) is False


def test_never_dispatch_unverified():
    assert should_dispatch(crash("confirmed"), verified=False) is False


def test_never_dispatch_drowsiness():
    ev = {"type": "drowsiness", "payload": {"level": "alarm", "status": "confirmed"}}
    assert should_dispatch(ev, verified=True) is False


def test_dispatcher_records_and_logs(capsys):
    d = Dispatcher()
    rec = d.notify(crash("confirmed")["payload"], driver_id="d1")
    assert rec["incident_id"] == "c1" and rec["driver_id"] == "d1"
    assert rec["dispatched_at"] > 0
    assert len(d.dispatched) == 1
    assert "DISPATCH" in capsys.readouterr().out
