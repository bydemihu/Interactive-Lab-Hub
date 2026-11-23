
#!/usr/bin/env python3
"""Automatic AMG8833 heat-seeking servo scanner."""


# behavior: sweeps 0-120-0, saves angle of highest temp detected, holds at that angle.
# future: instead of holding cam at that angle, turn robot body to that angle instead.
# camera should be constantly scanning and updating. 

import time
import board
import busio
import adafruit_amg88xx
import pi_servo_hat
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

SERVO_CH = 0
SERVO_MIN = 0
SERVO_MAX = 120

SWEEP_STEP = 4
SWEEP_DELAY = 0.12
MOVE_DELAY = 0.015
SETTLE_TIME = 0.3

LOCK_TIME = 5.0


# ============================================================
# INITIALIZE HARDWARE
# ============================================================

print("Initializing AMG8833...")
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_amg88xx.AMG88XX(i2c)
time.sleep(0.5)

print("Initializing SparkFun Pi Servo pHAT...")
servo = pi_servo_hat.PiServoHat()
servo.restart()

current_angle = None


# ============================================================
# SERVO CONTROL
# ============================================================

def move_servo(angle):
    """Move servo to specified angle."""
    global current_angle

    angle = int(max(SERVO_MIN, min(SERVO_MAX, angle)))
    servo.move_servo_position(SERVO_CH, angle)
    current_angle = angle


def move_smooth(target, delay=MOVE_DELAY):
    """Move smoothly to target angle."""
    target = int(max(SERVO_MIN, min(SERVO_MAX, target)))

    if current_angle is None:
        move_servo(target)
        time.sleep(SETTLE_TIME)
        return

    step = 1 if target > current_angle else -1

    for angle in range(current_angle, target + step, step):
        move_servo(angle)
        time.sleep(delay)


# ============================================================
# THERMAL CAMERA
# ============================================================

def read_thermal():
    return np.array(sensor.pixels, dtype=float)


def center_temperature(pixels):
    """Highest temperature of the four center pixels."""
    return float(np.max(pixels[3:5, 3:5]))


# ============================================================
# HEAT SEEKING
# ============================================================

def scan_for_heat():
    best_angle = None
    best_temp = float("-inf")

    print("\n" + "=" * 50)
    print("SCANNING FOR HEAT")
    print("=" * 50)

    move_smooth(SERVO_MIN)
    time.sleep(SETTLE_TIME)

    forward = list(
        range(SERVO_MIN, SERVO_MAX + 1, SWEEP_STEP)
    )

    backward = list(
        range(
            SERVO_MAX - SWEEP_STEP,
            SERVO_MIN - 1,
            -SWEEP_STEP
        )
    )

    for angle in forward + backward:
        move_servo(angle)
        time.sleep(SWEEP_DELAY)

        pixels = read_thermal()
        temp = center_temperature(pixels)

        if temp > best_temp:
            best_temp = temp
            best_angle = angle

        print(
            f"Angle: {angle:3d}° | "
            f"Center: {temp:5.1f}°C | "
            f"Best: {best_temp:5.1f}°C "
            f"at {best_angle}°"
        )

    print("\nSCAN COMPLETE")
    print(f"Hottest angle: {best_angle}°")
    print(f"Highest temperature: {best_temp:.1f}°C")

    return best_angle, best_temp


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    cycle = 0

    try:
        while True:
            cycle += 1
            print(f"\n========== CYCLE {cycle} ==========")

            # Scan
            best_angle, best_temp = scan_for_heat()

            # Orient toward heat
            print(f"\nOrienting to {best_angle}°...")
            move_smooth(best_angle)

            # Hold position
            print(
                f"LOCKED: {best_angle}° | "
                f"{best_temp:.1f}°C"
            )
            print(f"Holding for {LOCK_TIME} seconds...")

            time.sleep(LOCK_TIME)

            # Automatically repeat

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        servo.sleep()
        print("Servo disabled.")


if __name__ == "__main__":
    main()
