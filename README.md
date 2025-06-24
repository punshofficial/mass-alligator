# mass-alligator

Batch uploader for MusicAlligator. The tool reads presets from
`config.yaml` and uploads pairs of PNG covers and WAV files. A draft release
is created for each pair and the track metadata is filled in automatically.

## Usage

1. Create `config.yaml` with your authentication token, a mapping of artist
   names to their IDs and per-artist presets (label, genre and other
   defaults).
2. Start the web UI:

   ```bash
   python -m streamlit run app.py
   ```

3. Drag and drop the WAV and PNG files into the page. Each pair must have the
   same base name (e.g. `Artist - Title.wav` and `Artist - Title.png`). Review
   the detected releases, adjust the *Explicit* flag and *Track Date* for each
   track and start the upload.

The application sends requests to the MusicAlligator API to create the draft,
upload the cover and audio file and finally update the track metadata with
recording year, language, composers and lyricists.

### Configuration file

```yaml
auth_token: YOUR_TOKEN
artists:
  My Artist: 12345
labels:
  My Label: 67890
presets:
  My Artist:
    label_id: 67890
    genre_id: 196
    recording_year: 2024
    language_id: 7
    composers: []
    lyricists: []
```

Only the fields above are required in presets. Explicitness and track date are
set for every track directly in the UI.

