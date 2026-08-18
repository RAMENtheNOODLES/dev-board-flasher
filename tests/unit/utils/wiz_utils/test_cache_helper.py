import json

from utils.wiz_utils.cache_helper import CacheHelper


def test_get_returns_default_and_persists_it_when_cache_file_is_missing(isolated_paths):
	result = CacheHelper.BOARD_CACHE.get({"boards": []})

	assert result == {"boards": []}
	# get() should have called update() with the default, so a second get()
	# (even with a different fallback) now reads that persisted value back.
	assert CacheHelper.BOARD_CACHE.get({"different": "default"}) == {"boards": []}


def test_update_then_get_round_trips_a_value(isolated_paths):
	CacheHelper.BOARD_CACHE.update({"boards": ["esp32", "unor3"]})

	assert CacheHelper.BOARD_CACHE.get() == {"boards": ["esp32", "unor3"]}


def test_get_refuses_a_cache_file_with_no_recorded_hash(isolated_paths, tmp_path):
	# Written directly to disk, bypassing update() - so no hash ever gets
	# recorded for it via StoredSettings.STORED_CACHE_HASHES.
	cache_file = tmp_path / CacheHelper.BOARD_CACHE.value
	cache_file.write_text(json.dumps({"tampered": True}), encoding="utf-8")

	assert CacheHelper.BOARD_CACHE.get({"fallback": True}) == {"fallback": True}


def test_get_refuses_a_cache_file_whose_contents_no_longer_match_the_recorded_hash(isolated_paths, tmp_path):
	CacheHelper.BOARD_CACHE.update({"boards": ["esp32"]})

	# Tamper with the file's contents after its hash was already recorded.
	cache_file = tmp_path / CacheHelper.BOARD_CACHE.value
	cache_file.write_text(json.dumps({"boards": ["malicious"]}), encoding="utf-8")

	assert CacheHelper.BOARD_CACHE.get({"fallback": True}) == {"fallback": True}
