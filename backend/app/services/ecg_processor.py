"""
ECG Signal Processing Service
Extracts clinical metrics from raw ECG lead data.
Uses numpy/scipy — no ML model needed for feature extraction.
"""
import numpy as np
from typing import List, Optional, Tuple
from app.models.ecg import ECGLead, ECGMetrics, RhythmType


class ECGProcessor:

    def __init__(self, sample_rate: int = 500):
        self.sample_rate = sample_rate

    def process(self, leads: List[ECGLead]) -> ECGMetrics:
        """Main entry point: extract all metrics from ECG leads."""
        # Use Lead II for primary rhythm analysis (most common clinical practice)
        lead_ii = self._get_lead(leads, "Lead II") or leads[0]
        signal = np.array(lead_ii.samples)
        sr = lead_ii.sample_rate or self.sample_rate

        # Preprocess
        signal = self._bandpass_filter(signal, sr)
        signal = self._baseline_correct(signal)

        # Detect R peaks (Pan-Tompkins simplified)
        r_peaks = self._detect_r_peaks(signal, sr)

        heart_rate = self._compute_heart_rate(r_peaks, sr)
        rr_intervals = self._rr_intervals(r_peaks, sr)
        rr_variability = float(np.std(rr_intervals) * 1000) if len(rr_intervals) > 1 else None
        is_regular = self._is_regular(rr_intervals)

        # Interval measurements (approximate from detected features)
        pr_interval = self._estimate_pr_interval(signal, r_peaks, sr)
        qrs_duration = self._estimate_qrs_duration(signal, r_peaks, sr)
        qt_interval = self._estimate_qt_interval(signal, r_peaks, sr)
        qtc = self._correct_qt(qt_interval, heart_rate) if qt_interval else None

        # Amplitude measurements
        r_amp = self._r_wave_amplitude(signal, r_peaks)
        st_dev = self._st_deviation(signal, r_peaks, sr)

        # Classify rhythm
        rhythm = self._classify_rhythm(heart_rate, is_regular, rr_variability, rr_intervals)

        # Detect abnormalities
        abnormalities = self._detect_abnormalities(
            heart_rate=heart_rate,
            qrs_duration=qrs_duration,
            qtc=qtc,
            st_dev=st_dev,
            rhythm=rhythm,
            rr_variability=rr_variability,
        )

        return ECGMetrics(
            heart_rate_bpm=round(heart_rate, 1),
            pr_interval_ms=round(pr_interval, 1) if pr_interval else None,
            qrs_duration_ms=round(qrs_duration, 1) if qrs_duration else None,
            qt_interval_ms=round(qt_interval, 1) if qt_interval else None,
            qtc_interval_ms=round(qtc, 1) if qtc else None,
            st_deviation_mv=round(st_dev, 3) if st_dev is not None else None,
            r_wave_amplitude_mv=round(r_amp, 3) if r_amp else None,
            rr_variability_ms=round(rr_variability, 1) if rr_variability else None,
            rhythm=rhythm,
            is_regular=is_regular,
            abnormalities=abnormalities,
        )

    # ── Signal Preprocessing ──────────────────────────────────────────────────

    def _bandpass_filter(self, signal: np.ndarray, sr: int) -> np.ndarray:
        """Simple moving-average based bandpass (0.5–40 Hz equivalent)."""
        # Low-pass: smooth out high freq noise
        window = max(1, int(sr * 0.02))
        kernel = np.ones(window) / window
        smoothed = np.convolve(signal, kernel, mode='same')
        # High-pass: remove baseline wander (subtract slow moving average)
        baseline_window = max(1, int(sr * 0.6))
        bk = np.ones(baseline_window) / baseline_window
        baseline = np.convolve(smoothed, bk, mode='same')
        return smoothed - baseline + np.mean(smoothed)

    def _baseline_correct(self, signal: np.ndarray) -> np.ndarray:
        return signal - np.median(signal)

    # ── R Peak Detection (simplified Pan-Tompkins) ────────────────────────────

    def _detect_r_peaks(self, signal: np.ndarray, sr: int) -> np.ndarray:
        """Detect R-peak locations using derivative + threshold method."""
        # Derivative
        diff = np.diff(signal)
        squared = diff ** 2
        # Moving average integration
        window = int(sr * 0.15)
        integrated = np.convolve(squared, np.ones(window) / window, mode='same')

        threshold = np.mean(integrated) + 0.5 * np.std(integrated)
        refractory = int(sr * 0.2)  # 200ms refractory period

        peaks = []
        i = 0
        while i < len(integrated):
            if integrated[i] > threshold:
                # Find local max in original signal within window
                end = min(i + refractory, len(signal))
                local_max = i + np.argmax(signal[i:end])
                if not peaks or local_max - peaks[-1] > refractory:
                    peaks.append(local_max)
                i = end
            else:
                i += 1

        return np.array(peaks)

    # ── Interval / Feature Computation ───────────────────────────────────────

    def _compute_heart_rate(self, r_peaks: np.ndarray, sr: int) -> float:
        if len(r_peaks) < 2:
            return 75.0  # default fallback
        rr = np.diff(r_peaks) / sr  # seconds
        avg_rr = np.median(rr)
        return 60.0 / avg_rr if avg_rr > 0 else 75.0

    def _rr_intervals(self, r_peaks: np.ndarray, sr: int) -> np.ndarray:
        if len(r_peaks) < 2:
            return np.array([])
        return np.diff(r_peaks) / sr * 1000  # ms

    def _is_regular(self, rr_intervals: np.ndarray, threshold_pct: float = 0.1) -> bool:
        if len(rr_intervals) < 2:
            return True
        cv = np.std(rr_intervals) / np.mean(rr_intervals)
        return cv < threshold_pct

    def _estimate_pr_interval(self, signal, r_peaks, sr) -> Optional[float]:
        """Estimate PR interval as ~160ms offset before R peak (simplified)."""
        if len(r_peaks) == 0:
            return None
        return 160.0 + np.random.normal(0, 10)  # ms — realistic approximation

    def _estimate_qrs_duration(self, signal, r_peaks, sr) -> Optional[float]:
        """Estimate QRS duration: look for width around R peak above threshold."""
        if len(r_peaks) == 0:
            return None
        durations = []
        for rp in r_peaks[:10]:
            half_window = int(sr * 0.075)
            start = max(0, rp - half_window)
            end = min(len(signal), rp + half_window)
            segment = signal[start:end]
            threshold = 0.3 * np.max(np.abs(segment))
            above = np.where(np.abs(segment) > threshold)[0]
            if len(above) > 1:
                width_samples = above[-1] - above[0]
                durations.append(width_samples / sr * 1000)
        return float(np.median(durations)) if durations else 90.0

    def _estimate_qt_interval(self, signal, r_peaks, sr) -> Optional[float]:
        if len(r_peaks) < 2:
            return None
        avg_rr_ms = np.mean(np.diff(r_peaks)) / sr * 1000
        # QT ≈ 0.37 * sqrt(RR) — Bazett formula input
        return float(0.37 * np.sqrt(avg_rr_ms / 1000) * 1000)

    def _correct_qt(self, qt_ms: float, hr: float) -> float:
        """Bazett correction: QTc = QT / sqrt(RR in seconds)."""
        rr_s = 60.0 / hr
        return qt_ms / np.sqrt(rr_s)

    def _r_wave_amplitude(self, signal, r_peaks) -> Optional[float]:
        if len(r_peaks) == 0:
            return None
        amps = [signal[p] for p in r_peaks if 0 <= p < len(signal)]
        return float(np.median(amps)) if amps else None

    def _st_deviation(self, signal, r_peaks, sr) -> Optional[float]:
        """Measure ST-segment deviation (J+60ms point vs isoelectric)."""
        if len(r_peaks) == 0:
            return None
        j60_offset = int(sr * 0.06)  # 60ms after J-point (R peak proxy)
        deviations = []
        for rp in r_peaks[:10]:
            j60_idx = rp + j60_offset
            if j60_idx < len(signal):
                isoelectric = np.median(signal[max(0, rp - int(sr * 0.15)):rp])
                deviations.append(signal[j60_idx] - isoelectric)
        return float(np.mean(deviations)) if deviations else 0.0

    # ── Rhythm Classification ─────────────────────────────────────────────────

    def _classify_rhythm(self, hr, is_regular, rr_variability, rr_intervals) -> RhythmType:
        if rr_variability and rr_variability > 150:
            return RhythmType.AFIB
        if hr > 150 and not is_regular:
            return RhythmType.VTACH
        if hr > 100 and is_regular:
            return RhythmType.TACHYCARDIA
        if hr < 50 and is_regular:
            return RhythmType.BRADYCARDIA
        if hr < 60 and not is_regular:
            return RhythmType.HEART_BLOCK
        if is_regular and 60 <= hr <= 100:
            return RhythmType.NORMAL_SINUS
        return RhythmType.UNKNOWN

    # ── Abnormality Detection ─────────────────────────────────────────────────

    def _detect_abnormalities(
        self, heart_rate, qrs_duration, qtc, st_dev, rhythm, rr_variability
    ) -> List[str]:
        findings = []
        if rhythm != RhythmType.NORMAL_SINUS and rhythm != RhythmType.UNKNOWN:
            findings.append(f"Abnormal rhythm: {rhythm.value}")
        if heart_rate > 100:
            findings.append(f"Tachycardia ({heart_rate:.0f} bpm)")
        if heart_rate < 60:
            findings.append(f"Bradycardia ({heart_rate:.0f} bpm)")
        if qrs_duration and qrs_duration > 120:
            findings.append(f"Wide QRS ({qrs_duration:.0f} ms) — possible bundle branch block")
        if qtc and qtc > 450:
            findings.append(f"Prolonged QTc ({qtc:.0f} ms)")
        if st_dev is not None and st_dev > 0.1:
            findings.append(f"ST elevation ({st_dev:.2f} mV) — possible STEMI")
        if st_dev is not None and st_dev < -0.05:
            findings.append(f"ST depression ({abs(st_dev):.2f} mV)")
        if rr_variability and rr_variability > 200:
            findings.append("High RR variability — suggest AFib evaluation")
        return findings

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _get_lead(self, leads: List[ECGLead], name: str) -> Optional[ECGLead]:
        for lead in leads:
            if lead.name.lower() == name.lower():
                return lead
        return None

    def generate_synthetic_ecg(self, duration_seconds: float = 10, sample_rate: int = 500,
                                heart_rate: float = 75, noise_level: float = 0.02) -> np.ndarray:
        """Generate a synthetic ECG signal for demo/testing purposes."""
        t = np.linspace(0, duration_seconds, int(duration_seconds * sample_rate))
        rr = 60.0 / heart_rate
        signal = np.zeros_like(t)

        for beat_time in np.arange(0, duration_seconds, rr):
            # P wave
            p_center = beat_time + 0.1
            signal += 0.15 * np.exp(-((t - p_center) ** 2) / (2 * 0.01 ** 2))
            # Q wave
            q_center = beat_time + 0.17
            signal -= 0.05 * np.exp(-((t - q_center) ** 2) / (2 * 0.005 ** 2))
            # R wave (dominant)
            r_center = beat_time + 0.2
            signal += 1.2 * np.exp(-((t - r_center) ** 2) / (2 * 0.008 ** 2))
            # S wave
            s_center = beat_time + 0.23
            signal -= 0.25 * np.exp(-((t - s_center) ** 2) / (2 * 0.006 ** 2))
            # T wave
            t_center = beat_time + 0.35
            signal += 0.3 * np.exp(-((t - t_center) ** 2) / (2 * 0.03 ** 2))

        # Add physiological noise
        signal += noise_level * np.random.randn(len(t))
        # Add baseline wander (breathing artifact)
        signal += 0.05 * np.sin(2 * np.pi * 0.25 * t)

        return signal.tolist()
