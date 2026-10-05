

# Chatterboxes

**Demi Hu**



## Prep for Part 1: Get the Latest Content and Pick up Additional Parts

Please check instructions in [prep.md](prep.md) and complete the setup.


# Part 1

## Setup

Create and activate a virtual environment for this lab:

```
pi@ixe00:~$ cd Interactive-Lab-Hub/Lab\ 3
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ python3 -m venv .venv
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ source .venv/bin/activate
(.venv) pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $
```

Install the Python dependencies:

```
(.venv) $ pip install -r requirements.txt
```

This takes a few minutes. If you would like it to take considerably less time, [`uv`](https://docs.astral.sh/uv/) is a drop-in replacement for `pip` that is dramatically faster on the Pi:

```
(.venv) $ pip install uv && uv pip install -r requirements.txt
```

Then run the setup script, which installs the classic speech synthesizers, downloads the voice activity detection model, and pre-fetches a neural voice and a speech recognition model so you are not waiting on downloads during lab:

```
(.venv):~$ cd speech-scripts
(.venv) $ ./setup.sh
```

Check your audio devices before going further. `arecord -l` lists capture devices and `aplay -l` lists playback devices; if your webcam microphone or Bluetooth speaker does not appear, fix that first — every script below assumes the system defaults are the ones you want.

## A. Text to Speech

Your Pi can speak in several quite different ways, and the differences are audible in a way that matters for design. In `speech-scripts/` there are shell scripts for each.

### The classic engines

```
(.venv) $ cd speech-scripts

(.venv) $ sudo apt update
(.venv) $ sudo apt install -y espeak festival festvox-kallpc16k

(.venv) $ ./espeak_demo.sh
(.venv) $ ./festival_demo.sh
```

You can run these `.sh` files by typing `./filename`, and read one with `cat filename`. You can also play audio files directly with `aplay filename` — try `aplay lookdave.wav`.

These are all decades-old technology and they sound like it. `espeak-ng` is a *formant synthesizer*: it generates speech from an acoustic model of the vocal tract, which is why it sounds robotic but also why the whole thing fits in a couple of megabytes and responds instantly. `festival` is *concatenative*: they stitch together recorded fragments of a real speaker, which sounds more human but breaks audibly at the seams.

### Neural TTS with Piper

Note that the Piper command line changed in version 1.x — voices are now downloaded explicitly with `python3 -m piper.download_voices`, and you invoke it as `python3 -m piper`. Tutorials you find online may show the old `echo ... | piper --model ...` form, which no longer works. Browse the [voice samples](https://rhasspy.github.io/piper-samples) and download a different one if you'd like:

```
(.venv) $ python3 -m piper.download_voices en_US-lessac-medium
```

[Piper](https://github.com/OHF-Voice/piper1-gpl) synthesizes speech with a small neural network, runs comfortably on the Pi 5, and sounds markedly better than the above.

```
(.venv) $ ./piper_demo.sh
```

The demo script also shows `--output-raw`, which streams audio to the speaker as it is generated rather than writing a file first. Listen for the difference in how quickly speech begins. In a conversational system this gap is the thing your user experiences as responsiveness.

\*\***Write your own shell file to use your favorite of these TTS engines to have your Pi greet you by name.**\*\*
(This shell file should be saved to your own repo for this lab.)
Saved as hidemi.sh

\*\***Then answer: Is the same greeting, in these different voices, the same greeting? Describe one concrete way the voice changed what the utterance seemed to mean or who seemed to be speaking.**\*\*
No, it's not the same greeting. Espeak seemed to greet me with more of a formal, sharp tone. Festival's greeting was softer, slower, and more gentle, but also more robotic. Espeak almost seemed in a hurry while Festival was more languid.

## B. Speech to Text

We use [faster-whisper](https://github.com/SYSTRAN/faster-whisper), a reimplementation of OpenAI's Whisper model that runs several times faster on CPU and does not require PyTorch. All processing happens on the Pi; nothing is sent to a server.

```
(.venv) $ python transcribe.py lookdave.wav
```

The transcript is not the interesting output here — the timings are. Run it again with a larger model and compare:

```
(.venv) $ python transcribe.py lookdave.wav --model base.en
(.venv) $ python transcribe.py lookdave.wav --model small.en
#  noted that the first run may take longer because the model is downloaded, and that the HF unauthenticated-request warning is expected and not an error.
```

Available sizes, smallest first: `tiny.en`, `base.en`, `small.en`, `medium.en`. The `.en` variants are English-only and faster than their multilingual counterparts at the same size.

\*\***Record a few seconds of your own speech (`arecord -d 5 -f cd -c 1 -r 16000 test.wav`) and transcribe it with at least two model sizes. Report the real-time factor for each. At what point does the accuracy improvement stop being worth the delay, for a system that has to answer you?**\*\*

The real-time factor for the base size is 0.27x, while the real-time factor for the small model size is 0.82x. I tested with both 5 seconds of my speech and 10 seconds. The two models transcribed my speech the same way at both sizes, indicating no clear differences in accuracy, though I also did not say anything particularly complex. I think there were more noticeable differences in transcription time. When I recorded 10 seconds of speech, the small model took noticeably longer than the base model to transcribe (at 5 seconds, transcription took 2.5 and 5.3 seconds, for base and small respectively). I think when the system needs to record more than 10 seconds of speech, the accuracy improvement is no longer worth the delay, because the lag starts feeling like an error rather than a natural time spent waiting for a response. 

```(.venv) pi@demipi:~/Interactive-Lab-Hub/Lab 3/speech-scripts $ python transcribe.py test.wav --model base.en

Hello, I am speaking and testing a new transcription. My name is Demi. Hello, hi, hello, hello, hello.

model            base.en (int8, beam=1)
audio duration   10.00s
model load       2.75s
transcription    2.71s
real-time factor 0.27x

(Model load is a one-time cost per process. In an interactive system you load once and keep the model resident  which is what listen.py does.)
(.venv) pi@demipi:~/Interactive-Lab-Hub/Lab 3/speech-scripts $ arecord -d 10 -f cd -c 1 -r 16000 test.wav
Recording WAVE 'test.wav' : Signed 16 bit Little Endian, Rate 16000 Hz, Mono
(.venv) pi@demipi:~/Interactive-Lab-Hub/Lab 3/speech-scripts $ python transcribe.py test.wav --model small.en

Hello, I am speaking and testing a new transcription. My name is Demi. Hello, hi, hello, hello, hello.

model            small.en (int8, beam=1)
audio duration   10.00s
model load       6.48s
transcription    8.22s
real-time factor 0.82x

(Model load is a one-time cost per process. In an interactive system you load once and keep the model resident  which is what listen.py does.)
```





\*\***Write your own script that verbally asks for a numerical input (a phone number, zipcode, number of pets) and records the answer the respondent provides.**\*\* Numbers are a good stress test — transcription systems make characteristic errors on digit strings, and you will want to know what they are before you design around them.
Saved as numerical_input.sh.
```
Respondent's answer:

3.141592653

model            tiny.en (int8, beam=1)
audio duration   5.00s
model load       0.66s
transcription    0.96s
real-time factor 0.19x
```
I was surprised that the transcription was surprisingly context-aware. The script asks for digits of pi. I verbally said "three point one", and the system was able to interpret that as a decimal point instead of literally the word "point".

## C. Turn-taking: knowing when someone has stopped talking

Everything so far has worked on fixed audio files. A real conversational device does not get told when to start and stop recording — it has to decide. This is the problem that makes speech interfaces hard, and it is mostly not a speech recognition problem.

We use a **voice activity detector** (VAD) to segment the microphone stream into utterances. `listen.py` runs Silero VAD continuously and hands each detected utterance to faster-whisper:

```
(.venv) $ cd speech-scripts
(.venv) $ python listen.py
```
```[2.0s speech, 1.03s to transcribe]  I mean I guess it's not bad. This is...
[2.3s speech, 0.95s to transcribe]  approximately like how I would.
[1.7s speech, 0.87s to transcribe]  talk in real life maybe?
[22.7s speech, 2.70s to transcribe]  If I'm rambling then everything gets counted as one sentence, because one thought flows into the other, like it's a stream of consciousness. Like if I'm talking about my favorite novel or my theories for it, or I have some ideas that I want to share, but if I'm pausing in between a thought and I'm not just like continuously rambling, then this threshold separates it into two separate.
[1.6s speech, 0.83s to transcribe]  out of princess.
[2.4s speech, 0.82s to transcribe]  I said utterances.
```

Speak, pause, and watch it transcribe. Now change the endpointing threshold — the amount of silence the system requires before it decides your turn is over:

```
(.venv) $ python listen.py --min-silence 0.2
(.venv) $ python listen.py --min-silence 1.5
```

\*\***Try both extremes, and something in between. Describe what each one feels like to talk to. Note specifically: at 0.2s, what kinds of normal speech get cut off? At 1.5s, what does the delay make the system seem like?**\*\*
The 0.2 is rather difficult to talk to if I'm pausing to gather my thoughts when giving a longer, thought-out response. It feels like I have no room for error at all if I want to express more than one idea vs a standard small-talk back and forth. I could see it working well for a system that asks and expects responses to questions such as "how are you?" and "what's your name?" but a system that requires the user to answer something like "tell me about your favorite memory" will need a lot more space to allow users to actually complete their thoughts. I think users (or perhaps me especially), tend to use a little bit of filler such as "um" or "like" during pauses when collecting thoughts, naturally indicating to a receiver that the turn is not over. A system that purely uses a time-based threshold to identify end-of-turn doesn't capture that nuance.

The 1.5 starts to feel sluggish and unresponsive no matter what my answer type is. When I ramble to it, at least it fully captures my sentiment before transcribing, so I'm not at risk of having a sentence cut off in the middle like with the 0.2, but when I give short responses, it starts to feel like an unnecessarily long cutoff to the point of frustration.

There is no correct value. A system that takes drink orders and a system that listens to someone think out loud want very different thresholds, and the right one depends on what your users are doing with their pauses.

### The complete loop

`echo_bot.py` puts the pieces together: it listens, endpoints, transcribes, and speaks a reply through Piper. The dialogue policy is deliberately trivial — it repeats what you said — so that everything you notice is a property of the timing rather than the content.

```
(.venv) $ python echo_bot.py
```

## D. Storyboard

Storyboard and/or use a Verplank diagram to design a speech-enabled device. (Stuck? Make a device that talks for dogs. If that is too stupid, find an application that is better than that.)

\*\***Post your storyboard and diagram here.**\*\*
Idea: speech device that translates the user's speech into the most unfiltered version of their honest inner thoughts, like a truth serum. It detects when they're being too shy to confess, too polite to criticize, or too scared to push back, and revises their speech on-the-spot.
<img width="1920" height="1080" alt="Illustration" src="https://github.com/user-attachments/assets/968981b8-3619-4473-8f25-1bc8fc385679" />

Diagram:
<img width="1190" height="318" alt="image" src="https://github.com/user-attachments/assets/e758ffa5-c82e-4cfa-b3af-385b8a36a201" />



Write out what you imagine the dialogue to be. Use cards, post-its, or whatever method helps you develop alternatives or group responses.

**Script:**

In this scenario, the mic only detects the user's speech, not the partner's.

Partner: Oh, hey! How's it going?

User: It's going okay, I guess. I'm a little stressed.

(pause 0.3 seconds)

Device: I'm doing horribly. I am so stressed and busy.

Partner: Oh, uh, I didn't realize? Sorry, do you want to talk about it?

User: It's alright, haha, I'm just a little overwhelmed with work right now.

(pause 0.3 seconds)

Device: It's not alright and I do not want to talk about it. I am so sorry for the rudeness and I know you mean well but I need to go right now.

\*\***Please describe and document your process.**\*\*

Your script should include the pauses. Where does your device wait, and for how long? You now know from Part C that this is a parameter you have to choose, not something that happens for free.

I changed the pause from 0.4s default to 0.3s because in this scenario, the partner isn't going to necessarily wait for the device, and they might try to respond directly to the user. This also assumes a more surface-level conversation where the dialogue can be more direct and back-and-forth, rather than long-winded rambling with someone the user is close to (in which case they wouldn't need the anti-filter device, because they would be conversing with someone they can be more honest with.)

## E. Acting out the dialogue

Find a partner, and *without sharing the script with your partner* try out the dialogue you've designed, where you (as the device designer) act as the device you are designing. Please record this interaction (for example, using Zoom's record feature).
[https://cornell.box.com/s/fy4mtgk98csvx6v1p2nbtepgzyruugh2]




\*\***Describe if the dialogue seemed different than what you imagined when it was acted out, and how.**\*\*
This dialogue was slightly different than what I imagined: my partner was taken aback, as I expected, and she did realize the pattern that seemed to be occuring was that I'd say one thing, then say another, more honest response to her initial question. However, because I was using my own voice to represent both my "own voice" and the "device voice", She couldn't quite figure out if I was pretending to be two different people, two personalities in one person, or simply changing my mind and deciding to be more honest or unhinged the second time around. The back-and-forth went pretty smoothly timing-wise, she was able to differentiate between when I was pausing between my "own voice" and the "device voice" and when I was finished with my response and awaiting hers.

---

# Lab 3 Part 2

For Part 2, you will redesign the interaction with the speech-enabled device using the data collected, as well as feedback from part 1.

## Prep for Part 2

1. What are concrete things that could use improvement in the design of your device? For example: wording, timing, anticipation of misunderstandings.
2. What are other modes of interaction *beyond speech* that you might also use to clarify how to interact? In particular: how does someone know when the device is listening, and when it is thinking? You have a screen and an LED.
3. Make a new storyboard, diagram and/or script based on these reflections.
4. (optional) Integrate [input devices](inputs.md) in the system

## Prototype your system

The system should:
* use the Raspberry Pi
* use one or more sensors
* require participants to speak to it

*Document how the system works.*
**Version 1\\**
Pressing the rotary encoder toggles between the "listening" and "not listening" states. While it's listening, it captures speech until there is 0.4 seconds of silence, until which it transcribes the speech based on what it thinks is the emotionally unfiltered, socially unacceptable version of what the user was truly trying to express. In this version, the user themselves presses the rotary encoded to unfilter their own speech, effectively **outsourcing to an external device the communication of difficult things they truly feel but can't/shouldn't express.** 

**Version 2\\**
The device is always listening. It continously captures and separates speech into chunks based on the 0.4s silence threshold, but only keeps the last one or two. When the rotary encoder is pressed, it "unfilters" the very last speech chunk. Any participant can press the rotary encoder to "unfilter" a piece of speech, so in this version it acts as a **neutral intent decoder for when you doubt your conversational partner is being totally honest with you.**  

In both versions:  
Turning the rotary encoder clockwise increases the "unfiltered-ness", which determines how much the device interprets the speech at face value vs reads deeply into it and makes exaggerated assumptions about intent.  
The screen displays a progress bar that indicates how much unfiltered-ness is applied. The screen pulses from black to grey while it's listening, and turns a different solid color based on the emotion captured. It recognizes the 5 following underlying "socially unacceptable" (or that someone generally would want to suppress in polite conversation) emotions: anger, avoidance, tiredness, jealousy, and desire.  
The LLM prompt states that it should **translate the input into what the user would say if they had no social filter, taking into account their underlying emotion that they might be hiding.** The LLM is told to return a json containing the text translation, as well as a one-word emotion identifier from the list of five emotions. The text translation is processed with TTS and played via the speaker, and the emotion designation determines the screen color. 



*Include videos or screencaptures of both the system and the controller.*
<img width="2880" height="2160" alt="image" src="https://github.com/user-attachments/assets/4413aac7-8635-457b-a383-cc4bf0a3a6aa" />


Version 1 (speaker controls unfiltering device): [https://youtu.be/cdcvRo6nexY]  
Version 2 (unfiltering device is neutral and any party can invoke it): [https://youtu.be/_J7QpAYIBFU]



## Test the system

Try to get at least two people to interact with your system. (Ideally, you would inform them that there is a wizard *after* the interaction, but we recognize that can be hard.)

Answer the following:

### What worked well about the system and what didn't?
What worked well:  
The actual transcription process. The model came up with some hilariously unhinged responses. It translated "Let's clean the apartment" to "The apartment is disgusting. Clean it before the dust starts having to pay rent." It often came up with little quips of jokes that added a lot of character to the unfiltered response, and for the most part interpreted the underlying emotion/intention fairly well.  

What didn't:  
The turn-taking did not work well. There was a lot of difficulty separating the speech into chunks based on who was speaking. I originally wanted the device to always be listening, and only translate the original user's speech and not their conversation partner's, but this proved to be extremely difficult to actually separate. Instead, I implemented a rotary encoder that could be pressed to toggle when the device was listening or not, forcing it to only transcribe certain speech. However, this introduced some awkwardness for actual usage. When the speaker controlled their own unfiltering device, it felt like an awkward movement for them to make in the middle of the conversation, because it felt like they were intentionally trying to playback their unfiltered speech rather than wearing some device that automatically translates all their speech without conscious consent. The latency also made the flow of conversation awkward. The device would often not speak until the other partner had already began talking, and then it didn't seem like the device's speech was an immediate unfiltered correction of the original user's speech. In order to address this, I made a version 2, which instead listens continuously and chunks speech somewhat based on actual speaking turns, upon which either participant can choose to replay an unfiltered version of the last spoken turn. This worked a lot better from a timing perspective, but changed the intention of the device considerably. 

### What worked well about the controller and what didn't?
What worked well:  
The form factor. The rotary knob was pretty easy to understand, and having the rotation map to a continous variable such as "unfiltered-ness", especially paired with a progress bar, was easy to interpret. 

What didn't:  
The responsiveness. Half the time the rotary encoder wouldn't actually sense a press, despite there being an audible click. Sometimes it would also not sense the turning. 


### What lessons can you take away from the WoZ interactions for designing a more autonomous version of the system?
\*\**your answer here*\*\*

### How could you use your system to create a dataset of interaction? What other sensing modalities would make sense to capture?
\*\**your answer here*\*\*

<details>
  <summary><strong>Submission Cleanup Reminder (Click to Expand)</strong></summary>

  **Before submitting your README.md:**
  - This readme.md file has a lot of extra text for guidance.
  - Remove all instructional text and example prompts from this file.
  - You may either delete these sections or use the toggle/hide feature in VS Code to collapse them for a cleaner look.
  - Your final submission should be neat, focused on your own work, and easy to read for grading.
</details>
