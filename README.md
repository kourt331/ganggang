# Physics Chronicles · GitHub Pages

This package runs the Python/Tkinter game in a browser with its original Python gameplay logic and a Canvas renderer. The page uses Pyodide 0.27.7 and a small Tkinter compatibility layer. It waits for **게임 시작** before advancing the simulation. Keyboard letters are read by physical key position, so they work with a Korean keyboard layout.

Default controls: **←/→** move (tap the same direction twice within 0.2 seconds to dash), **C** jump/double jump, **Z** dash, **X** basic attack, **Space** parry, **F** ranged attack, **↑** interact, **M** settings, and **I** stats. Settings allow remapping, restoring defaults, and adjusting music and attack sound volume.

## Publish

Upload the contents of this folder to the root of the GitHub repository, then select **Settings → Pages → Deploy from a branch → main → /(root)**. Open the repository's Pages URL after deployment.

The entry page loads `original_game.py` and `tkinter.py` from Pages without using a cached response. If either asset is missing from the Pages deployment, it retries that file from the repository's `main` branch and reports both HTTP statuses if the retry also fails.

## Run locally

From this folder, start a local static web server:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`, wait for **준비 완료**, and press **게임 시작** or click the game canvas. Do not use `file://`: browsers block the local asset fetches. The first launch needs an internet connection for the Pyodide runtime.

## Files

- `index.html`: page layout, fullscreen and touch controls, Canvas renderer, browser input, audio, and Python runtime setup
- `original_game.py`: Python game logic
- `tkinter.py`: browser-backed Tk window and Canvas adapter
- `physics_chronicles.wav`: game music
- `.nojekyll`: keeps GitHub Pages from filtering files
