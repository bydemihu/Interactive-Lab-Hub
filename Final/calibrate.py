import pi_servo_hat

servo = pi_servo_hat.PiServoHat()
servo.restart()
servo.set_pwm_frequency(50)

try:
    for duty in [7.5, 7.0, 8.0, 7.5]:
        input(f"\nPress Enter to send {duty}% duty cycle...")
        servo.set_duty_cycle(0, duty)
        print(f"Sent {duty}%")

    input("\nPress Enter to finish...")

finally:
    servo.sleep()