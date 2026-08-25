import json
import logging

from PySide6.QtCore import QObject, QTimer

from tools.can import TxMessageConfig

from .can_worker import CanWorker
from .stored_settings import StoredSettings


class TxScheduler(QObject):
	"""Periodically transmits enabled TX message configs onto the bus while connected.

	Owns one `QTimer` per enabled config's message name (see
	:meth:`set_configs`), each queuing a send through the currently active
	`CanWorker` at its configured rate - never by calling `CAN.send_message`
	directly, since the channel is only safe to touch from the worker's own
	background thread once connected (see `CanWorker`'s docstring).

	Call :meth:`start` with the just-connected `CanWorker` once
	``CanWorker.signals.connected`` fires, and :meth:`stop` once
	``disconnected`` fires; :meth:`set_configs` can be called at any time
	(e.g. from :class:`can_tx_settings.TxSettingsDialog` on accept) and
	takes effect immediately if already running. The configured messages
	are also persisted to :data:`StoredSettings.CAN_TX_MESSAGES` on every
	:meth:`set_configs` call and restored from there on construction, so
	they (including which were left enabled) survive across app restarts,
	same as the CAN Viewer's DBC file / J1939 name-CSV choices.
	"""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.logger = logging.getLogger(__name__)
		self._timers: dict[str, QTimer] = {}
		self._worker: CanWorker | None = None
		self._configs: dict[str, TxMessageConfig] = {
			config.message_name: config for config in self._load_persisted_configs()
		}

	def _load_persisted_configs(self) -> list[TxMessageConfig]:
		"""Best-effort: a corrupted or old-format stored value just logs a warning and starts empty, rather than blocking construction."""
		raw = StoredSettings.CAN_TX_MESSAGES.get(None)
		if not raw:
			return []

		try:
			entries = json.loads(raw)
			return [
				TxMessageConfig(
					message_name=entry["message_name"],
					rate_ms=entry["rate_ms"],
					enabled=entry["enabled"],
					signal_values=entry["signal_values"],
				)
				for entry in entries
			]
		except (json.JSONDecodeError, KeyError, TypeError) as e:
			self.logger.warning("Could not restore persisted TX messages: %s", e)
			return []

	def _persist_configs(self) -> None:
		entries = [
			{
				"message_name": config.message_name,
				"rate_ms": config.rate_ms,
				"enabled": config.enabled,
				"signal_values": config.signal_values,
			}
			for config in self._configs.values()
		]
		StoredSettings.CAN_TX_MESSAGES.set(json.dumps(entries))

	def get_configs(self) -> list[TxMessageConfig]:
		"""Returns the currently configured TX messages, used to prefill a reopened `TxSettingsDialog`."""
		return list(self._configs.values())

	def set_configs(self, configs: list[TxMessageConfig]) -> None:
		"""Replaces the full set of configured messages, persisting them and syncing timers immediately if already running."""
		self._configs = {config.message_name: config for config in configs}
		self._persist_configs()
		if self._worker is not None:
			self._sync_timers()

	def start(self, worker: CanWorker) -> None:
		"""Starts sending currently-enabled messages through `worker` - call once its channel is open."""
		self._worker = worker
		self._sync_timers()

	def stop(self) -> None:
		"""Stops all timers - call once the channel has closed."""
		self._worker = None
		for timer in self._timers.values():
			timer.stop()
		self._timers.clear()

	def _sync_timers(self) -> None:
		stale_names = self._timers.keys() - self._configs.keys()
		for name in stale_names:
			self._timers.pop(name).stop()

		for name, config in self._configs.items():
			if not config.enabled:
				timer = self._timers.pop(name, None)
				if timer is not None:
					timer.stop()
				continue

			timer = self._timers.get(name)
			if timer is None:
				timer = QTimer(self)
				timer.timeout.connect(lambda name=name: self._send(name))
				self._timers[name] = timer
			timer.start(config.rate_ms)

	def _send(self, name: str) -> None:
		config = self._configs.get(name)
		if config is None or self._worker is None:
			return
		self._worker.enqueue_send(config.message_name, config.signal_values)
