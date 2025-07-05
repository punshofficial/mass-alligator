# mass-alligator

## Overview
Приложение упрощает массовую загрузку релизов на MusicAlligator. Оно сопоставляет
пары файлов PNG и WAV, создаёт черновики релизов и заполняет метаданные.

## Installation
Готовая программа распространяется в виде EXE‑файла. Скачайте её и запустите без
установки дополнительных зависимостей. Для разработки используйте:

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## Configuration (`config.yaml` schema)
```yaml
auth_token: YOUR_TOKEN
artists:
  My Artist: 12345
labels:
  My Label: 67890
streaming_platforms: [195, 196, 197]
presets:
  My Artist:
    label_id: 67890
    genre_id: 196
    recording_year: 2024
    language_id: 7
    composers: []
    lyricists: []
```
Файл конфигурации создаётся при первом запуске. Сохраните его для обновлений.

## Usage
1. Запустите программу и введите токен авторизации.
2. Перетащите пары WAV и PNG с одинаковым именем. Другие форматы не поддерживаются.
3. После проверки нажмите *Run upload* и дождитесь завершения.


### Площадки распространения
Ниже приведены идентификаторы стриминговых платформ из примера
`/platform/platforms/streaming` файла `openapi.yaml`.

| id | Площадка |
|---|---|
| 282 | Apple Music |
| 284 | Beatport |
| 220 | Facebook/Instagram |
| 286 | iTunes Music Store |
| 264 | SoundCloud |
| 291 | Spotify |
| 267 | TIDAL |
| 269 | TikTok Fingerprinting |
| 197 | VK Music |
| 200 | YouTube Music |
| 195 | Zvuk |
| 196 | Yandex.Music |
| 206 | 7Digital |
| 202 | ACRCloud |
| 193 | ADV |
| 207 | Amazon |
| 208 | Amazon Video |
| 209 | Ami Entertainment |
| 292 | Anghami |
| 293 | Anghami Video |
| 283 | Apple Video |
| 211 | AudibleMagic |
| 212 | AWA |
| 213 | Beatsource |
| 214 | Bleep |
| 215 | Bmat |
| 205 | Boomplay Video |
| 216 | Bugs! |
| 217 | ClicknClear |
| 285 | Deezer |
| 629 | Digital Stores |
| 218 | Dreamus Company (FLO) |
| 615 | Facebook Fingerprinting |
| 616 | Facebook Video Fingerprinting |
| 222 | fizy |
| 223 | fizy Video |
| 224 | Genie Music |
| 225 | Gracenote |
| 226 | GrooveFox |
| 227 | Hardstyle.com |
| 620 | HighResAudio |
| 278 | Hungama |
| 279 | Hungama Video |
| 229 | iHeartRadio |
| 230 | iMusica |
| 294 | Jaxsta Music |
| 231 | JioSaavn |
| 232 | Joox |
| 233 | Juno Records |
| 234 | Kakao / MelOn |
| 235 | KkBox |
| 236 | Kuack Media |
| 237 | Lickd |
| 238 | LINE Music |
| 240 | LyricFind |
| 241 | MePlaylist |
| 287 | Microsoft (Xbox, Zune) |
| 242 | Mixcloud |
| 288 | MixUpload |
| 243 | MonkingMe |
| 244 | MoodAgent |
| 246 | Music Worx |
| 247 | MUSICAROMA |
| 280 | MusixMatch |
| 249 | Muska |
| 251 | Naver Music |
| 252 | NetEase Cloud Music |
| 254 | Nightlife Music |
| 255 | Nuuday A/S |
| 289 | Pandora |
| 257 | Peloton |
| 258 | Phononet |
| 621 | Pretzel Rocks |
| 259 | Qobuz |
| 261 | Roxi Music Videos |
| 290 | Shazam |
| 262 | Sirius XM |
| 263 | Slacker |
| 265 | Stellar Entertainment |
| 266 | Tencent |
| 268 | TIDAL Video |
| 271 | TouchTunes / PlayNetwork |
| 272 | Traxsource.com |
| 273 | Trebel Music |
| 198 | VK Video |
| 275 | Xite |
| 624 | Yandex.Video |
| 199 | YouTube Content ID |
| 201 | YouTube Video |

## Packaging
Сборка EXE выполняется библиотекой `streamlit-desktop-app`.

```bash
python -m streamlit_desktop_app build
```

## FAQ / Troubleshooting
*Пока пусто.*

## ROADMAP
- Добавление нескольких треков в один релиз
- Массовая отправка релиза на модерацию
- Выбор жанра не по ID, а по названию
- Выбор языка не по ID, а по названию
- Выбор площадок не по ID, а по названию
