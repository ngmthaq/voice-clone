# Third-Party Notices

voice-clone uses the following third-party code and models. Check each source for the current license terms.

## RVC-Project (Retrieval-based Voice Conversion WebUI)

Parts of the voice conversion code in `src/voice_clone/domain/engine/vendor/` come from RVC-Project. It is released under the MIT License. The license text is in `src/voice_clone/domain/engine/vendor/LICENSE`.

Source: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

## ContentVec

The content encoder weights are downloaded on first start from the Hugging Face repository `lengyue233/content-vec-best`. They are not included in this repository. For the license terms, see the source page: https://huggingface.co/lengyue233/content-vec-best

## RMVPE

The pitch extractor weights (`rmvpe.pt`) are downloaded on first start from the Hugging Face repository `lj1995/VoiceConversionWebUI`. They are not included in this repository. For the license terms, see the source page: https://huggingface.co/lj1995/VoiceConversionWebUI

## Python dependencies

Python packages (PyTorch, Textual, sounddevice, and others) are installed by `pip install -e .` and keep their own licenses.
