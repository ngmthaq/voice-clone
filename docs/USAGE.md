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

Keys: `space` start or stop, `esc` back to the start screen (this stops the voice), `r` restart the app (this stops the voice and finds microphones or voices added since it started), `q` quit. Your choices are saved and restored on the next start.

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

On the **Simple** tab, **Performance** sets every setting on the Advanced tab to fit the computer.

The easiest way to pick one: on the start screen choose **Check setup**, then **Measure speed**. It converts made-up speech with each preset (up to a minute) and saves the heaviest one your computer keeps up with. On a computer without a usable GPU, the voice changer starts on **Minimal** until you choose something else.


| Setting | Minimal | Light | Balanced (default) | High | Ultra |
| --- | --- | --- | --- | --- | --- |
| For | no GPU, or Light is still too slow | laptop or older GPU (e.g. GeForce MX) | mid-range GPU | fast GPU or Apple M-series | high-end GPU |
| Index voice (%) | 0 | 40 | 50 | 55 | 60 |
| Protect consonants (%) | 80 | 75 | 67 | 60 | 50 |
| Follow mic volume (%) | 60 | 60 | 50 | 45 | 40 |
| Pitch smoothing (ms) | 60 | 50 | 30 | 25 | 20 |
| Context (ms) | 200 | 300 | 1000 | 1500 | 2000 |
| Block size (ms) | 1000 | 600 | 400 | 300 | 200 |
| Crossfade (ms) | 40 | 60 | 80 | 80 | 60 |
| Hum filter (Hz) | 90 | 90 | 90 | 90 | 90 |
| Hold (ms) | 200 | 300 | 500 | 500 | 600 |
| Open early (ms) | 100 | 100 | 100 | 100 | 100 |
| Above noise (dB) | 10 | 8 | 6 | 6 | 5 |

Context, Block size and Crossfade decide most of the speed. Index voice adds a search on every block; at 0 (Minimal) the search is skipped. While the noise gate is closed the model does not run, so a shorter Hold and a higher Above noise save work in pauses. With less context, pitch and consonants are less steady, so lighter presets smooth pitch more and keep more of your live consonants. Hum filter and Open early cost the same at any value, so they are the same in every preset.

A higher preset gives less delay and clearer words, but needs a faster computer. If the app says "Too slow for this computer", pick a lighter one. Picking a preset replaces any Advanced settings you changed. Changing any value on the Advanced tab afterwards shows **Custom**.

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

1. Stop and run **Check setup → Measure speed** to pick the preset this computer keeps up with. Or set **Performance** on the Simple tab to **Light** yourself; if it still says too slow, pick **Minimal** (more delay, and the `.index` file is not used).
2. On a laptop, plug in the charger and set Windows power mode to **Best performance**.
3. In the NVIDIA Control Panel (Manage 3D settings → Program settings), set Python to use the **High-performance NVIDIA processor**.
4. Close other programs that use the graphics card (games, browsers with many video tabs).

Some delay always remains: the voice is converted in blocks (0.4 seconds by default), so expect about 0.5 to 1 second. A smaller **Block size** lowers it if the computer is fast enough.

### Measure the speed

To see which preset your computer can run, without a microphone:

```bash
python -m voice_clone bench
```

It converts made-up speech with each preset and prints the **Load** (time to convert a block ÷ block length). Under 1.0 keeps up; pick the heaviest preset with a Load under about 0.7, so there is room for pauses in your computer's other work. `p95` is the load of the slowest blocks, and `Slow` counts blocks that took longer than real time. The last column shows where the time goes (encode, index, pitch, synth). Add `--cpu` to test without the graphics card, or `--preset light` to test one preset.

On an NVIDIA card from the GeForce 16 or RTX series on, the voice model runs in half precision (fp16), which is faster and uses less graphics memory. Older cards (GeForce 10 series and before) stay at full precision (fp32), because fp16 is slow on them. **Check setup** shows which one your card uses. To choose yourself, add `precision = "fp16"` or `precision = "fp32"` to the settings file (below); `"auto"` is the default. `fp16` also works on Apple GPUs (a little faster there); the CPU always uses fp32. To compare, run `python -m voice_clone bench --precision fp16` and `--precision fp32`.

On the CPU, the app leaves one core free for the audio and the screen. To set the number of CPU threads yourself, add `cpu_threads = 4` (for example) to the settings file while the app is closed; `0` means automatic. The settings file is `~/Library/Application Support/voice-clone/settings.toml` on macOS and `%LOCALAPPDATA%\voice-clone\voice-clone\settings.toml` on Windows.

## Logs

The app never prints to the terminal. Logs are written to the user log folder:

- macOS: `~/Library/Logs/voice-clone/voice-clone.log`
- Windows: `%LOCALAPPDATA%\voice-clone\Logs\voice-clone.log`
