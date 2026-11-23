
#!/usr/bin/env python3
"""AMG8833 thermal camera on Adafruit 1.14" Mini PiTFT."""

import time

import board
import busio
import digitalio
import adafruit_amg88xx
from adafruit_rgb_display import st7789

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Display configuration
WIDTH = 135
HEIGHT = 240
ROTATION = 90

# Thermal color range
TEMP_MIN = 20.0
TEMP_MAX = 40.0

# Initialize AMG8833
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_amg88xx.AMG88XX(i2c)
time.sleep(0.5)

# Initialize Mini PiTFT
spi = board.SPI()
cs = None
dc = digitalio.DigitalInOut(board.D25)
reset = None

display = st7789.ST7789(
    spi,
    cs=cs,
    dc=dc,
    rst=reset,
    baudrate=24000000,
    width=WIDTH,
    height=HEIGHT,
    x_offset=53,
    y_offset=40,
    rotation=ROTATION,
)

# Landscape mode: 240 x 135
SCREEN_W = 240
SCREEN_H = 135

# Heatmap size
HEAT_SIZE = 120
HEAT_X = 5
HEAT_Y = 7

font = ImageFont.load_default()


def thermal_color(temp):
    """Map 20-40C to black/purple/red/yellow/white."""
    t = np.clip((temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN), 0, 1)

    stops = [
        (0.00, (0, 0, 0)),
        (0.20, (55, 0, 110)),
        (0.40, (180, 0, 60)),
        (0.65, (255, 70, 0)),
        (0.85, (255, 210, 0)),
        (1.00, (255, 255, 255)),
    ]

    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]

        if t <= p1:
            f = (t - p0) / (p1 - p0)
            return tuple(
                int(c0[j] + f * (c1[j] - c0[j]))
                for j in range(3)
            )

    return (255, 255, 255)


def create_heatmap(pixels):
    """Convert 8x8 temperatures into a smooth heatmap."""
    colors = np.zeros((8, 8, 3), dtype=np.uint8)

    for y in range(8):
        for x in range(8):
            colors[y, x] = thermal_color(pixels[y, x])

    img = Image.fromarray(colors, "RGB")
    return img.resize(
        (HEAT_SIZE, HEAT_SIZE),
        Image.Resampling.BILINEAR
    )


print("AMG8833 thermal camera running on Mini PiTFT.")
print("Press Ctrl+C to stop.")

try:
    while True:
        pixels = np.array(sensor.pixels)

        min_temp = float(pixels.min())
        max_temp = float(pixels.max())
        avg_temp = float(pixels.mean())

        # Create screen
        image = Image.new(
            "RGB", (SCREEN_W, SCREEN_H), (0, 0, 0)
        )
        draw = ImageDraw.Draw(image)

        # Draw thermal image
        heatmap = create_heatmap(pixels)
        image.paste(heatmap, (HEAT_X, HEAT_Y))

        # Draw temperature labels
        draw.text(
            (137, 15), "AMG8833",
            font=font, fill=(255, 255, 255)
        )
        draw.text(
            (137, 40), f"MAX {max_temp:.1f}C",
            font=font, fill=(255, 180, 0)
        )
        draw.text(
            (137, 60), f"MIN {min_temp:.1f}C",
            font=font, fill=(100, 180, 255)
        )
        draw.text(
            (137, 80), f"AVG {avg_temp:.1f}C",
            font=font, fill=(180, 180, 180)
        )

        # Draw hottest pixel marker
        hot_y, hot_x = np.unravel_index(
            np.argmax(pixels), pixels.shape
        )

        marker_x = HEAT_X + int(
            (hot_x + 0.5) * HEAT_SIZE / 8
        )
        marker_y = HEAT_Y + int(
            (hot_y + 0.5) * HEAT_SIZE / 8
        )

        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (
                marker_x - 3, marker_y - 3,
                marker_x + 3, marker_y + 3
            ),
            outline=(0, 255, 0),
            width=2
        )

        # Update display
        display.image(image)

        print(
            f"Min {min_temp:.1f}C | "
            f"Max {max_temp:.1f}C | "
            f"Avg {avg_temp:.1f}C | "
            f"Hotspot ({hot_x}, {hot_y})",
            end="\r",
            flush=True
        )

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped.")
    display.image(
        Image.new("RGB", (SCREEN_W, SCREEN_H), (0, 0, 0))
    )
