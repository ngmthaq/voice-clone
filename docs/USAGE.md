# Use the voice changer

Install the app first ([INSTALL.md](INSTALL.md)). Then start it:

```bash
python -m voice_clone run
```

The app opens on a start screen with three choices: **Voice changer**, **Train a voice** and **Check setup**. Press `esc` to come back to it.

## Change your voice

You need at least one voice: train one (see [TRAINING.md](TRAINING.md)) or [add a voice you already have](VOICES.md#add-a-voice-you-already-have).

1. Choose **Voice changer** on the start screen. On the **Simple** tab, pick your microphone, the output device (BlackHole 2ch or CABLE Input), and a voice.
2. Set the pitch with `-` and `+` (in semitones, -12 to +12).
3. Press Start (or the space bar). Loading the voice can take about 30 seconds the first time.
4. In Zoom, Discord or any other app, choose "BlackHole 2ch" (macOS) or "CABLE Output" (Windows) as the microphone.

Use headphones, so the converted voice does not feed back into your microphone.

While the voice is running, all settings are locked. Press Stop to change them, then Start again.

Keys: `space` start or stop, `esc` back to the start screen (this stops the voice), `q` quit. Your choices are saved and restored on the next start.

## Make the voice match better

"Index voice" is on the **Simple** tab. The other settings are on the **Advanced** tab, with the noise gate. Change one at a time: Stop, change it, Start, and listen.

| Setting | Default | What it does |
| --- | --- | --- |
| Index voice (%) | 50 | How much of the trained voice (the `.index` file) to use. Higher sounds more like the voice but less clear. Needs a `.index` file. |
| Protect consonants (%) | 67 | Keeps consonants (s, t, k, ch) from your live voice, so words stay clear when Index is high. 0 = off. |
| Follow mic volume (%) | 50 | 0 = the model sets the volume. 100 = the output gets louder and quieter the way you speak. |
| Pitch smoothing (ms) | 30 | Removes short pitch jumps that sound like a wobble. 0 = off. |
| Context (ms) | 1000 | How much earlier audio the model hears. More gives clearer words and adds no delay, but needs more CPU/GPU. If the log says blocks were dropped, lower it. |

The defaults are a good place to start. If the voice should sound more like the trained voice, raise Index to 75. On a fast computer, try Context 1500. On the Advanced tab, "Reset voice match to defaults" puts the four advanced settings back (Index voice keeps its value).

## Logs

The app never prints to the terminal. Logs are written to the user log folder:

- macOS: `~/Library/Logs/voice-clone/voice-clone.log`
- Windows: `%LOCALAPPDATA%\voice-clone\Logs\voice-clone.log`
