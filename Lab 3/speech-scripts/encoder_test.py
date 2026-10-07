import time
import board
from digitalio import Pull
from adafruit_seesaw import seesaw, rotaryio, digitalio

i2c = board.I2C()
ss = seesaw.Seesaw(i2c, addr=0x36)

# Rotary encoder
encoder = rotaryio.IncrementalEncoder(ss)

# Push button
button = digitalio.DigitalIO(ss, 24)
button.switch_to_input(pull=Pull.UP)

last_position = encoder.position
last_button = button.value

print("Rotary encoder ready!")
print("Turn or press the knob. Ctrl+C to quit.")

while True:
    position = encoder.position

    if position != last_position:
        print(f"Position: {position}")
        last_position = position

    current_button = button.value

    if current_button != last_button:
        if not current_button:
            print("Button pressed!")
        else:
            print("Button released!")

        last_button = current_button

    time.sleep(0.01)