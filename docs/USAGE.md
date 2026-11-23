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

These settings are on the **Advanced** tab, with the noise gate. Change one at a time: Stop, change it, Start, and listen.

| Setting | Default | What it does |
| --- | --- | --- |
| Index voice (%) | 50 | How much of the trained voice (the `.index` file) to use. Higher sounds more like the voice but less clear. Needs a `.index` file. |
| Protect consonants (%) | 67 | Keeps consonants (s, t, k, ch) from your live voice, so words stay clear when Index is high. 0 = off. |
| Follow mic volume (%) | 50 | 0 = the model sets the volume. 100 = the output gets louder and quieter the way you speak. |
| Pitch smoothing (ms) | 30 | Removes short pitch jumps that sound like a wobble. 0 = off. |

The defaults are a good place to start. If the voice should sound more like the trained voice, raise Index to 75. On a fast computer, try Context 1500. At the bottom of the Advanced tab, "Reset Advanced settings to defaults" puts every Advanced setting back: voice match, speed and delay, and the noise gate.

## Performance presets

On the **Simple** tab, **Performance** sets the speed settings to fit the computer:

| Preset | For | Context | Block size | Crossfade |
| --- | --- | --- | --- | --- |
| Light | laptop or older GPU (e.g. GeForce MX), or no GPU | 300 | 600 | 60 |
| Balanced (default) | mid-range GPU or Apple M-series | 1000 | 400 | 80 |
| High | fast GPU | 1500 | 300 | 80 |
| Ultra | high-end GPU | 2000 | 200 | 60 |

A higher preset gives less delay and clearer words, but needs a faster computer. If the app says "Too slow for this computer", pick a lighter one. Changing any of these three values on the Advanced tab shows **Custom**.

## Speed and delay

These are on the **Advanced** tab, under **Speed and delay**.

| Setting | Default | What it does |
| --- | --- | --- |
| Context (ms) | 1000 | How much earlier audio the model hears. More gives clearer words and adds no delay, but needs more CPU/GPU. If the app says it is too slow, lower it. |
| Block size (ms) | 400 | The voice is converted in blocks this long. Smaller means less delay but more CPU/GPU work per second. If the app says it is too slow, raise it or lower Context. |
| Crossfade (ms) | 80 | How long one block blends into the next. Raise it if you hear clicks between blocks. It can't be longer than a block. |
| Hum filter (Hz) | 90 | Cuts mains hum and rumble below this pitch. 0 turns it off. |

## If the voice lags, drops or comes late

The voice must be converted faster than you speak. On a weak graphics card (for example a laptop GeForce MX series) or on the CPU, the defaults can be too slow. The app then says "Too slow for this computer" while it runs. To fix it:

1. Stop and set **Performance** on the Simple tab to **Light**. If that keeps up, try **Balanced** later.
2. On a laptop, plug in the charger and set Windows power mode to **Best performance**.
3. In the NVIDIA Control Panel (Manage 3D settings → Program settings), set Python to use the **High-performance NVIDIA processor**.
4. Close other programs that use the graphics card (games, browsers with many video tabs).

Some delay always remains: the voice is converted in blocks (0.4 seconds by default), so expect about 0.5 to 1 second. A smaller **Block size** lowers it if the computer is fast enough.

## Logs

The app never prints to the terminal. Logs are written to the user log folder:

- macOS: `~/Library/Logs/voice-clone/voice-clone.log`
- Windows: `%LOCALAPPDATA%\voice-clone\Logs\voice-clone.log`
