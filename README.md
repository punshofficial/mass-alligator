# mass-alligator

Batch uploader for MusicAlligator.  The app reads presets from
`config.yaml` and uploads pairs of PNG covers and WAV files, creating draft
releases automatically.

## Usage

1. Fill in `config.yaml` with your auth token, artist IDs and
   per-artist presets.
2. Start the web UI:

   ```bash
   python -m streamlit run app.py
   ```

3. Drag&drop your files into the app and run the upload.

Track metadata is updated via
`/api/releases/{releaseId}/tracks/{trackId}` which ensures recording year,
language, composers, lyricists and genre are correctly stored.  The request
uses `genre: {"genreId": ...}` and arrays of numeric IDs for
`composers` and `lyricists`.

