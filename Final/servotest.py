
import time
import pi_servo_hat

CHANNEL = 0
FREQUENCY = 50

# Start with 1.0-2.0 ms
MIN_PULSE = 1.0
MAX_PULSE = 2.0

servo = pi_servo_hat.PiServoHat()
servo.restart()
servo.set_pwm_frequency(FREQUENCY)


def set_pulse(ms):
    duty = (ms * FREQUENCY / 10.0)
    servo.set_duty_cycle(CHANNEL, duty)


def sweep(low, high):
    # Start at center
    set_pulse(1.5)
    time.sleep(0.5)

    # Sweep center -> low
    for i in range(51):
        pulse = 1.5 + (low - 1.5) * i / 50
        set_pulse(pulse)
        time.sleep(0.03)

    # Sweep low -> high
    for i in range(101):
        pulse = low + (high - low) * i / 100
        set_pulse(pulse)
        time.sleep(0.03)

    # Sweep high -> center
    for i in range(51):
        pulse = high + (1.5 - high) * i / 50
        set_pulse(pulse)
        time.sleep(0.03)


try:
    while True:
        print(
            f"\nTesting {MIN_PULSE:.2f}–"
            f"{MAX_PULSE:.2f} ms"
        )
        input("Press Enter to sweep...")
        sweep(MIN_PULSE, MAX_PULSE)

        answer = input(
            "Widen range by 0.1 ms each side? (y/n/q): "
        ).strip().lower()

        if answer == "q":
            break
        elif answer == "y":
            MIN_PULSE = max(0.5, MIN_PULSE - 0.1)
            MAX_PULSE = min(2.4, MAX_PULSE + 0.1)

except KeyboardInterrupt:
    pass

finally:
    servo.sleep()
    print("\nStopped")
