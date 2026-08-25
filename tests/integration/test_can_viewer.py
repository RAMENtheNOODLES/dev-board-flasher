import pytest

from can_viewer import CANViewer

pytestmark = pytest.mark.integration


def test_bus_load_color_is_green_below_the_yellow_threshold():
	assert CANViewer._bus_load_color(0.0) == CANViewer._BUS_LOAD_COLOR_LOW
	assert CANViewer._bus_load_color(CANViewer._BUS_LOAD_YELLOW_THRESHOLD - 0.1) == CANViewer._BUS_LOAD_COLOR_LOW


def test_bus_load_color_is_yellow_between_the_thresholds():
	assert CANViewer._bus_load_color(CANViewer._BUS_LOAD_YELLOW_THRESHOLD) == CANViewer._BUS_LOAD_COLOR_MEDIUM
	assert CANViewer._bus_load_color(CANViewer._BUS_LOAD_RED_THRESHOLD - 0.1) == CANViewer._BUS_LOAD_COLOR_MEDIUM


def test_bus_load_color_is_red_at_or_above_the_red_threshold():
	assert CANViewer._bus_load_color(CANViewer._BUS_LOAD_RED_THRESHOLD) == CANViewer._BUS_LOAD_COLOR_HIGH
	assert CANViewer._bus_load_color(100.0) == CANViewer._BUS_LOAD_COLOR_HIGH
