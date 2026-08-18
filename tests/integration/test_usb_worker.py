import threading

import pytest

from utils.wiz_utils.usb_worker import USBWorker

pytestmark = pytest.mark.integration


def test_run_wires_usbmonitor_callbacks_to_qt_signals(qapp, mocker):
	fake_monitor = mocker.MagicMock()
	mocker.patch("utils.wiz_utils.usb_worker.USBMonitor", return_value=fake_monitor)

	# Pre-set so run()'s self.stop_event.wait() returns immediately instead
	# of blocking - the monitor itself is fully mocked anyway, so there's no
	# real background polling thread whose lifetime needs to be waited out.
	stop_event = threading.Event()
	stop_event.set()

	worker = USBWorker("usb-task", stop_event)

	connected_devices = []
	disconnected_devices = []
	worker.signals.device_connected.connect(connected_devices.append)
	worker.signals.device_disconnected.connect(disconnected_devices.append)

	worker.run()

	fake_monitor.start_monitoring.assert_called_once()
	_, kwargs = fake_monitor.start_monitoring.call_args
	on_connect = kwargs["on_connect"]
	on_disconnect = kwargs["on_disconnect"]

	# Invoke the callbacks USBWorker registered, as USBMonitor's real
	# background thread would when a device plugs/unplugs.
	on_connect("dev1", {"name": "Keyboard"})
	on_disconnect("dev1", {"name": "Keyboard"})

	assert connected_devices == [{"name": "Keyboard"}]
	assert disconnected_devices == [{"name": "Keyboard"}]
	fake_monitor.stop_monitoring.assert_called_once()
