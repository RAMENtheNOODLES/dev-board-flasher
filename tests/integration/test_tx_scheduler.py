import pytest
from PySide6.QtCore import QEventLoop, QTimer

from tools.can import TxMessageConfig
from utils.wiz_utils.stored_settings import StoredSettings
from utils.wiz_utils.tx_scheduler import TxScheduler

pytestmark = pytest.mark.integration


class _FakeWorker:
	def __init__(self):
		self.sent = []

	def enqueue_send(self, message_name, signal_values):
		self.sent.append((message_name, signal_values))


def _run_event_loop_for(qapp, milliseconds):
	"""Pumps the Qt event loop for `milliseconds`, so timers scheduled via `QTimer.start()` actually fire."""
	loop = QEventLoop()
	QTimer.singleShot(milliseconds, loop.quit)
	loop.exec()


def test_get_configs_reflects_the_last_set_configs(qapp, isolated_paths):
	scheduler = TxScheduler()
	configs = [TxMessageConfig(message_name="M1", rate_ms=100, enabled=True, signal_values={})]

	scheduler.set_configs(configs)

	assert scheduler.get_configs() == configs


def test_set_configs_before_start_does_not_send_anything(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=True, signal_values={})])
	worker = _FakeWorker()

	assert worker.sent == []


def test_start_sends_enabled_messages_at_their_configured_rate(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([
		TxMessageConfig(message_name="M1", rate_ms=20, enabled=True, signal_values={"S": 1.0}),
	])
	worker = _FakeWorker()

	scheduler.start(worker)
	_run_event_loop_for(qapp, 90)
	scheduler.stop()

	assert len(worker.sent) >= 2
	assert all(call == ("M1", {"S": 1.0}) for call in worker.sent)


def test_start_does_not_send_disabled_messages(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=False, signal_values={})])
	worker = _FakeWorker()

	scheduler.start(worker)
	_run_event_loop_for(qapp, 60)
	scheduler.stop()

	assert worker.sent == []


def test_stop_prevents_further_sends(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=True, signal_values={})])
	worker = _FakeWorker()
	scheduler.start(worker)
	_run_event_loop_for(qapp, 30)

	scheduler.stop()
	sent_at_stop = len(worker.sent)
	_run_event_loop_for(qapp, 60)

	assert len(worker.sent) == sent_at_stop


def test_set_configs_while_running_stops_a_removed_message(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=True, signal_values={})])
	worker = _FakeWorker()
	scheduler.start(worker)
	_run_event_loop_for(qapp, 30)

	scheduler.set_configs([])
	sent_after_removal = len(worker.sent)
	_run_event_loop_for(qapp, 60)

	assert len(worker.sent) == sent_after_removal


def test_set_configs_while_running_stops_a_now_disabled_message(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=True, signal_values={})])
	worker = _FakeWorker()
	scheduler.start(worker)
	_run_event_loop_for(qapp, 30)

	scheduler.set_configs([TxMessageConfig(message_name="M1", rate_ms=20, enabled=False, signal_values={})])
	sent_after_disable = len(worker.sent)
	_run_event_loop_for(qapp, 60)

	assert len(worker.sent) == sent_after_disable


def test_set_configs_persists_them_for_the_next_scheduler_instance(qapp, isolated_paths):
	configs = [
		TxMessageConfig(message_name="M1", rate_ms=250, enabled=True, signal_values={"S": 1.5}),
		TxMessageConfig(message_name="M2", rate_ms=500, enabled=False, signal_values={}),
	]
	TxScheduler().set_configs(configs)

	restored = TxScheduler()

	assert restored.get_configs() == configs


def test_a_fresh_scheduler_starts_empty_when_nothing_is_persisted(qapp, isolated_paths):
	scheduler = TxScheduler()

	assert scheduler.get_configs() == []


def test_a_fresh_scheduler_starts_empty_when_the_persisted_value_is_corrupted(qapp, isolated_paths):
	StoredSettings.CAN_TX_MESSAGES.set("not valid json")

	scheduler = TxScheduler()

	assert scheduler.get_configs() == []
