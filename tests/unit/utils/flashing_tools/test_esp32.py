from PySide6.QtWidgets import QProgressBar, QTextEdit

from fixtures.toml_samples import write_tool_toml
from utils.flashing_tools.esp32 import ESP32


def _make_tool(tmp_path) -> ESP32:
	tool_path = write_tool_toml(tmp_path, tool_name="esp32", tool_type="PYTHON", supported_boards=["ESPIDF"])
	tool = ESP32(str(tool_path))
	tool.set_log_box(QTextEdit())
	tool.set_progress_bar(QProgressBar())
	return tool


def test_flash_happy_path_drives_esptool_functions_in_order(qapp, tmp_path, mocker):
	tool = _make_tool(tmp_path)

	fake_esp = mocker.MagicMock()
	fake_esp.CHIP_NAME = "ESP32-C6"
	fake_stubbed_esp = mocker.MagicMock()

	fake_detect_chip_cm = mocker.MagicMock()
	fake_detect_chip_cm.__enter__.return_value = fake_esp
	fake_detect_chip_cm.__exit__.return_value = False

	detect_chip_mock = mocker.patch(
		"utils.flashing_tools.esp32.detect_chip", return_value=fake_detect_chip_cm
	)
	run_stub_mock = mocker.patch("utils.flashing_tools.esp32.run_stub", return_value=fake_stubbed_esp)
	write_flash_mock = mocker.patch("utils.flashing_tools.esp32.write_flash")
	run_mock = mocker.patch("utils.flashing_tools.esp32.run")

	# board is never actually read by ESP32.flash().
	result = tool.flash(board=None, port="COM5", file="firmware.bin")

	assert result is True
	detect_chip_mock.assert_called_once_with(port="COM5")
	run_stub_mock.assert_called_once_with(fake_esp)
	# write_flash/run operate on the stubbed esp (esp = run_stub(esp)), not
	# the one detect_chip originally yielded.
	write_flash_mock.assert_called_once_with(fake_stubbed_esp, [(0x10000, "firmware.bin")])
	run_mock.assert_called_once_with(fake_stubbed_esp)
	assert "ESP32-C6" in tool.log_box.toPlainText()


def test_flash_returns_false_and_logs_on_any_exception(qapp, tmp_path, mocker):
	tool = _make_tool(tmp_path)
	mocker.patch("utils.flashing_tools.esp32.detect_chip", side_effect=RuntimeError("no device found"))

	result = tool.flash(board=None, port="COM5", file="firmware.bin")

	assert result is False
