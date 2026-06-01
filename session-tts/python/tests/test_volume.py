"""Tests for `resolve_playback_volume()`: file-backed afplay --volume coefficient."""
from __future__ import annotations


class TestResolvePlaybackVolume:
    def test_missing_file_returns_default(self, say_response, monkeypatch, tmp_path):
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(tmp_path / "absent"))
        assert say_response.resolve_playback_volume() == "0.80"

    def test_valid_value_within_range(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("0.5\n")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.50"

    def test_value_with_surrounding_whitespace(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("  0.3  \n")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.30"

    def test_boundary_zero(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("0.0")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.00"

    def test_boundary_one(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("1.0")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "1.00"

    def test_above_range_falls_back_to_default(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("1.5")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.80"

    def test_negative_falls_back_to_default(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("-0.1")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.80"

    def test_unparseable_falls_back_to_default(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("loud")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.80"

    def test_empty_file_falls_back_to_default(self, say_response, monkeypatch, tmp_path):
        f = tmp_path / "volume"
        f.write_text("")
        monkeypatch.setattr(say_response, "VOLUME_FILE", str(f))
        assert say_response.resolve_playback_volume() == "0.80"
