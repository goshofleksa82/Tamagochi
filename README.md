# Tamagotchi

A small Tamagotchi-style game with a Python backend, JavaScript frontend, and SQLite database.

## Run

```powershell
python server.py
```

Open:

```text
http://127.0.0.1:8000
```

The app creates `tamagotchi.db` automatically the first time it runs.

To run on another port:

```powershell
$env:PORT = "8001"
python server.py
```

## Features

- Create or reset a pet
- Choose whether to continue saved progress or start a new game
- Every new pet gets a random saved animal design
- Time factor: stats decay every 30 seconds
- End state when a care stat reaches zero
- Feed, play, sleep, and clean actions
- Stats decrease over time
- Pet data persists in SQLite
- Frontend uses vanilla JavaScript, HTML, and CSS

## API

- `GET /api/pet`
- `POST /api/pet` with `{ "name": "Pixel" }`
- `POST /api/pet/name` with `{ "name": "New name" }`
- `POST /api/action` with `{ "action": "feed" }`
