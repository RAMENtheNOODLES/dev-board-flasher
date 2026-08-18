import threading

import pytest

from utils.wiz_utils.can_worker import CanWorker

pytestmark = pytest.mark.integration


class _FakeCan:
	"""Duck-typed stand-in for tools.can.CAN, needing no real Kvaser hardware."""

	def __init__(self, dbc_data=None, frames=None):
		self.dbc_data = dbc_data or {}
		self._frames = list(frames or [])
		self.is_open = True
		self.opened = False
		self.closed = False

	def dbc_message_signals(self):
		return self.dbc_data

	def open(self):
		self.opened = True

	def receive(self, timeout):
		if not self._frames:
			self.is_open = False
			return None
		return self._frames.pop(0)

	def close(self):
		self.closed = True
		self.is_open = False


def _collect_events(worker):
	events = []
	worker.signals.dbc_ready.connect(lambda data: events.append(("dbc_ready", data)))
	worker.signals.connected.connect(lambda: events.append(("connected",)))
	worker.signals.frame_received.connect(lambda msg: events.append(("frame_received", msg)))
	worker.signals.disconnected.connect(lambda: events.append(("disconnected",)))
	worker.signals.error.connect(lambda msg: events.append(("error", msg)))
	return events


def test_run_happy_path_emits_signals_in_order(qapp):
	fake_can = _FakeCan(dbc_data={0x100: ("Engine", [])}, frames=["frame1", "frame2"])
	worker = CanWorker("can-task", threading.Event(), fake_can, receive_timeout=10)
	events = _collect_events(worker)

	worker.run()

	assert events == [
		("dbc_ready", {0x100: ("Engine", [])}),
		("connected",),
		("frame_received", "frame1"),
		("frame_received", "frame2"),
		("disconnected",),
	]
	assert fake_can.opened is True
	assert fake_can.closed is True


def test_run_emits_error_and_stops_early_when_dbc_message_signals_raises(qapp):
	class _RaisingCan(_FakeCan):
		def dbc_message_signals(self):
			raise RuntimeError("dbc walk failed")

	fake_can = _RaisingCan()
	worker = CanWorker("can-task", threading.Event(), fake_can)
	events = _collect_events(worker)

	worker.run()

	assert events == [("error", "dbc walk failed")]
	assert fake_can.opened is False


def test_run_emits_error_when_open_raises(qapp):
	class _RaisingOpenCan(_FakeCan):
		def open(self):
			raise RuntimeError("device not found")

	fake_can = _RaisingOpenCan()
	worker = CanWorker("can-task", threading.Event(), fake_can)
	events = _collect_events(worker)

	worker.run()

	assert events == [("dbc_ready", {}), ("error", "device not found")]


def test_run_still_closes_and_disconnects_when_receive_raises(qapp):
	class _RaisingReceiveCan(_FakeCan):
		def receive(self, timeout):
			raise RuntimeError("bus error")

	fake_can = _RaisingReceiveCan(frames=["would-be-frame"])
	worker = CanWorker("can-task", threading.Event(), fake_can)
	events = _collect_events(worker)

	worker.run()

	assert events == [("dbc_ready", {}), ("connected",), ("error", "bus error"), ("disconnected",)]
	assert fake_can.closed is True


def test_run_stops_the_receive_loop_once_the_stop_event_is_set(qapp):
	stop_event = threading.Event()

	class _StopAfterOneCan(_FakeCan):
		def receive(self, timeout):
			stop_event.set()
			return "one-frame"

	fake_can = _StopAfterOneCan()
	worker = CanWorker("can-task", stop_event, fake_can)
	events = _collect_events(worker)

	worker.run()

	assert events == [
		("dbc_ready", {}),
		("connected",),
		("frame_received", "one-frame"),
		("disconnected",),
	]
