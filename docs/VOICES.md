# Voice files

Where voices live, how to add one you already have, and how to move your voices between computers. To make a new voice, see [TRAINING.md](TRAINING.md).

## Add a voice you already have

Put each RVC voice in its own folder under `voices/`:

```
voices/
  my-voice/
    model.pth      required
    model.index    optional, improves voice match
```

The folder name is the voice name shown in the app. Use any file names you like; the first `.pth` and the first `.index` in the folder are used.

## Keep your voice in a GitHub Release

Voice files are too big for git (the `.index` file is often near GitHub's 100 MB limit) and `voices/` is in `.gitignore`. To move a voice between computers, upload it once as a release asset. Use a **private** repo: anyone who has your model can sound like you.

```bash
gh repo create your-name/your-voices-repo --private
gh api -X PUT repos/your-name/your-voices-repo/contents/README.md -f message="Initial commit" -f content="$(printf '# Voices\n' | base64)"
gh release create voice-my-voice-v1 voices/my-voice/my-voice.pth voices/my-voice/my-voice.index --repo your-name/your-voices-repo --title "my-voice v1" --notes "RVC voice model"
```

The second command adds a first commit, because GitHub cannot create a release in an empty repo. After you retrain, replace the files with `gh release upload voice-my-voice-v1 <files> --clobber --repo your-name/your-voices-repo`.

To get the voice on another computer, pick one of these. Each one ends with the files in `voices/my-voice/`.

**In the browser.** Open the release page on GitHub while signed in, download `my-voice.pth` and `my-voice.index` from **Assets**, and copy them into `voices/my-voice/`.

**With the GitHub CLI.** Run `gh auth login` once, then:

```bash
gh release download voice-my-voice-v1 --repo your-name/your-voices-repo --dir voices/my-voice
```

**With curl (no GitHub CLI).** Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new) with read-only **Contents** access to the voices repo, then run this in a macOS or Linux terminal (or Git Bash on Windows):

```bash
TOKEN=github_pat_your_token
REPO=your-name/your-voices-repo
TAG=voice-my-voice-v1
mkdir -p voices/my-voice
curl -fsSL -H "Authorization: Bearer $TOKEN" "https://api.github.com/repos/$REPO/releases/tags/$TAG" \
  | python3 -c 'import json, sys; [print(a["id"], a["name"]) for a in json.load(sys.stdin)["assets"]]' \
  | while read -r id name; do
      curl -fL -H "Authorization: Bearer $TOKEN" -H "Accept: application/octet-stream" \
        -o "voices/my-voice/$name" "https://api.github.com/repos/$REPO/releases/assets/$id"
    done
```

The `Accept: application/octet-stream` header makes GitHub send the file itself instead of its details. For a public repo you can skip the token and download each file directly: `curl -fL -o voices/my-voice/my-voice.pth https://github.com/$REPO/releases/download/$TAG/my-voice.pth`.
