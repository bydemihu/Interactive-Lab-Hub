#!/bin/bash

# Greet me by name using eSpeak
espeak "Hello Demi! I am talking to you with eSpeak." --stdout | aplay -D plughw:CARD=Device,DEV=0
