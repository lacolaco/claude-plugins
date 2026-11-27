"""Tests for per-session stereo panning: resolve_pan() and apply_pan()."""
from __future__ import annotations

import array
import io
import math
import wave

import pytest


def _mono_wav(samples: list[int], rate: int = 24000) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(array.array("h", samples).tobytes())
    return out.getvalue()


def _read(wav_bytes: bytes) -> tuple[int, int, int, array.array]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        frames = array.array("h", r.readframes(r.getnframes()))
        return r.getnchannels(), r.getsampwidth(), r.getframerate(), frames


class TestApplyPan:
    def test_output_is_stereo_with_same_rate_and_length(self, say_response):
        samples = [0, 1000, -1000, 32767, -32768]
        channels, width, rate, frames = _read(
            say_response.apply_pan(_mono_wav(samples, rate=22050), 0.0)
        )
        assert (channels, width, rate) == (2, 2, 22050)
        assert len(frames) == 2 * len(samples)

    @pytest.mark.parametrize("pan", [-0.8, -0.3, 0.0, 0.5, 0.8])
    def test_constant_power_gains(self, say_response, pan):
        _, _, _, frames = _read(say_response.apply_pan(_mono_wav([20000] * 4), pan))
        left, right = frames[0::2], frames[1::2]
        theta = (pan + 1) * math.pi / 4
        assert all(abs(s - 20000 * math.cos(theta)) <= 1 for s in left)
        assert all(abs(s - 20000 * math.sin(theta)) <= 1 for s in right)
        # Constant power: L² + R² equals the mono power at every position.
        assert left[0] ** 2 + right[0] ** 2 == pytest.approx(20000**2, rel=1e-3)

    def test_negative_pan_is_louder_on_the_left(self, say_response):
        _, _, _, frames = _read(say_response.apply_pan(_mono_wav([10000]), -0.8))
        assert frames[0] > frames[1] > 0

    def test_full_scale_samples_do_not_overflow(self, say_response):
        _, _, _, frames = _read(say_response.apply_pan(_mono_wav([32767, -32768]), 1.0))
        assert frames[1] == 32767 and frames[3] == -32768
        assert abs(frames[0]) <= 1 and abs(frames[2]) <= 1

    def test_non_mono_input_is_returned_unchanged(self, say_response):
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(array.array("h", [1, 2, 3, 4]).tobytes())
        data = out.getvalue()
        assert say_response.apply_pan(data, 0.5) is data


class TestResolvePan:
    def _set(self, say_response, monkeypatch, tmp_path, content: str | None):
        f = tmp_path / "pan"
        if content is not None:
            f.write_text(content)
        monkeypatch.setattr(say_response, "PAN_FILE", str(f))

    @pytest.mark.parametrize(
        ("content", "position"),
        [("0.5\n", 0.5), ("-1.000\n", -1.0), ("1.0", 1.0), ("0", 0.0), (" -0.25 ", -0.25)],
    )
    def test_valid_position_is_scaled_by_range(
        self, say_response, monkeypatch, tmp_path, content, position
    ):
        self._set(say_response, monkeypatch, tmp_path, content)
        assert say_response.resolve_pan() == pytest.approx(position * say_response.PAN_RANGE)

    @pytest.mark.parametrize("content", [None, "", "left", "1.5", "-2", "nan"])
    def test_invalid_falls_back_to_center(self, say_response, monkeypatch, tmp_path, content):
        self._set(say_response, monkeypatch, tmp_path, content)
        assert say_response.resolve_pan() == 0.0

    def test_range_keeps_both_ears_audible(self, say_response):
        assert 0.0 < say_response.PAN_RANGE < 1.0
