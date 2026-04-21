"""
Vision-based follow controller: lateral PID on AprilTag offset_x plus gated forward speed.

Tuning (hardware-dependent)
---------------------------
- Kp_lat, Ki_lat, Kd_lat: Start with PI only (Kd_lat=0). Vision noise makes D noisy; add small Kd
  only if you low-pass or accept twitch risk.
- steer_max: Caps differential (left vs right). Keep moderate so you do not command violent spins.
- steering_sign: +1 or -1 if the robot steers the wrong way for a given tag offset.
- cruise_speed: Base forward command in [0, 1] while inside max_follow_distance.
- max_follow_distance: No forward command beyond this (matches prior STOP_DISTANCE behavior).
- integral_limit: Anti-windup bound on lateral I-term accumulator (not the output).

Lost tag / out of range
-----------------------
When distance is inf (no tag) or distance > max_follow_distance, the controller calls stop(),
resets the lateral PID (integral and derivative state), and returns without integrating.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motors import Motors


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class PID:
    """Discrete PID with output clamp, integral clamp, and saturation anti-windup."""

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        output_min: float,
        output_max: float,
        integral_limit: float = 1.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_limit = integral_limit
        self.integral = 0.0
        self._prev_error: float | None = None

    def reset(self) -> None:
        self.integral = 0.0
        self._prev_error = None

    def update(self, error: float, dt: float) -> float:
        dt = max(dt, 1e-6)
        p_term = self.kp * error

        self.integral += error * dt
        self.integral = _clamp(self.integral, -self.integral_limit, self.integral_limit)

        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        raw = p_term + self.ki * self.integral + d_term
        out = _clamp(raw, self.output_min, self.output_max)

        # If output saturated, undo this step's integral contribution when it pushed further in.
        if raw > self.output_max and error > 0:
            self.integral -= error * dt
            self.integral = _clamp(self.integral, -self.integral_limit, self.integral_limit)
        elif raw < self.output_min and error < 0:
            self.integral -= error * dt
            self.integral = _clamp(self.integral, -self.integral_limit, self.integral_limit)

        return out


# --- Defaults: tune on robot -------------------------------------------------

Kp_lat = 2.5
Ki_lat = 0.15
Kd_lat = 0.0  # PI-first; vision is noisy for raw D

steer_max = 0.45
integral_limit_lat = 0.35

steering_sign = 1.0  # Flip to -1.0 if tag-right still steers the wrong way

cruise_speed = 0.5
max_follow_distance = 2.0  # meters: same role as STOP_DISTANCE in main

# Optional: scale down forward speed when very close (0 disables)
slow_close_distance = 0.0  # set e.g. 0.5 to ramp base down inside this radius
min_comfort_distance = 0.35  # used only if slow_close_distance > 0

# Ignore tiny lateral error to reduce chatter (meters)
offset_deadband = 0.0

# Stop if tag closer than this (meters); 0 disables
min_follow_distance = 0.0


class FollowController:
    """Wraps Motors: one non-blocking step() per vision frame."""

    def __init__(
        self,
        motors: Motors,
        *,
        kp_lat: float = Kp_lat,
        ki_lat: float = Ki_lat,
        kd_lat: float = Kd_lat,
        steer_max: float = steer_max,
        integral_limit_lat: float = integral_limit_lat,
        steering_sign: float = steering_sign,
        cruise_speed: float = cruise_speed,
        max_follow_distance: float = max_follow_distance,
        slow_close_distance: float = slow_close_distance,
        min_comfort_distance: float = min_comfort_distance,
        offset_deadband: float = offset_deadband,
        min_follow_distance: float = min_follow_distance,
    ):
        self.motors = motors
        self.cruise_speed = cruise_speed
        self.max_follow_distance = max_follow_distance
        self.slow_close_distance = slow_close_distance
        self.min_comfort_distance = max(min_comfort_distance, 1e-3)
        self.offset_deadband = offset_deadband
        self.min_follow_distance = min_follow_distance
        self.steering_sign = steering_sign

        self._lateral = PID(
            kp_lat,
            ki_lat,
            kd_lat,
            -steer_max,
            steer_max,
            integral_limit=integral_limit_lat,
        )
        self._last_mono: float | None = None

    def reset(self) -> None:
        self._lateral.reset()
        self._last_mono = None

    def step(self, distance: float, offset_x: float, dt: float | None = None) -> None:
        """
        Compute left/right from distance and lateral offset, then set_speed.

        distance: meters from camera, or inf if no tag.
        offset_x: meters; positive = tag to the right (camera frame).
        dt: seconds since last step; if None, uses time.monotonic() since last call.
        """
        now = time.monotonic()
        if dt is None:
            if self._last_mono is None:
                dt = 0.05
            else:
                dt = now - self._last_mono
            self._last_mono = now
        dt = _clamp(dt, 1e-4, 0.5)

        if not math.isfinite(distance) or distance > self.max_follow_distance:
            self._lateral.reset()
            self.motors.stop()
            return

        if self.min_follow_distance > 0.0 and distance < self.min_follow_distance:
            self._lateral.reset()
            self.motors.stop()
            return

        base = self.cruise_speed
        if self.slow_close_distance > 0.0 and distance < self.slow_close_distance:
            base *= _clamp(
                distance / self.min_comfort_distance,
                0.0,
                1.0,
            )

        lat_meas = offset_x
        if abs(lat_meas) < self.offset_deadband:
            lat_meas = 0.0
        error_lat = 0.0 - lat_meas
        steer = self._lateral.update(error_lat, dt) * self.steering_sign

        left = base - steer
        right = base + steer
        self.motors.set_speed(_clamp(left, -1.0, 1.0), _clamp(right, -1.0, 1.0))
