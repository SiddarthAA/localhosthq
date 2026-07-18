"""The durable outbox — the core of edge resilience. Must survive reopen (crash),
dedup, and hand back un-acked rows in order excluding in-flight."""

from ridewme.outbox import Outbox


def test_put_count_and_dedup(tmp_path):
    ob = Outbox(str(tmp_path / "o.db"))
    ob.put("s", 0, "a")
    ob.put("s", 1, "b")
    ob.put("s", 0, "a-dup")     # same (session, seq) -> ignored
    assert ob.count() == 2


def test_ack_removes(tmp_path):
    ob = Outbox(str(tmp_path / "o.db"))
    ob.put("s", 0, "a")
    ob.put("s", 1, "b")
    ob.ack("s", 0)
    assert ob.count() == 1
    assert [r[1] for r in ob.pending(10, set())] == [1]


def test_pending_order_and_exclude(tmp_path):
    ob = Outbox(str(tmp_path / "o.db"))
    for i in range(3):
        ob.put("s", i, f"e{i}")
    assert [r[1] for r in ob.pending(10, set())] == [0, 1, 2]      # oldest-first
    assert [r[1] for r in ob.pending(10, {("s", 0)})] == [1, 2]    # in-flight excluded
    assert len(ob.pending(2, set())) == 2                          # limit respected


def test_durable_across_reopen(tmp_path):
    path = str(tmp_path / "o.db")
    ob = Outbox(path)
    ob.put("s", 0, "a")
    ob.put("s", 1, "b")
    ob.close()
    reopened = Outbox(path)          # simulate a daemon crash + restart
    assert reopened.count() == 2     # nothing lost
    assert [r[1] for r in reopened.pending(10, set())] == [0, 1]
