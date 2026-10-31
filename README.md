# Physics Chronicles · GitHub Pages

This package runs the Python/Tkinter game in a browser with its gameplay logic in Python and a Canvas renderer. It uses Pyodide 0.27.7 and a small Tkinter compatibility layer. The page waits for **게임 시작** before advancing the simulation. Keyboard letters are read by physical key position, so they work with a Korean keyboard layout.

Default controls: **←/→** move, **Space** jump/double jump, **Z** roll, **A** basic attack, **Shift** parry, **F** ranged attack, **↑** interact, **M** settings, and **I** stats. Settings let players remap controls and restore the defaults.

## Publish on GitHub Pages

Upload the contents of this folder to the root of a GitHub repository. Then open **Settings → Pages**, choose **Deploy from a branch**, select the `main` branch and `/ (root)`, and save. GitHub Pages will serve `index.html`; the Python runtime and game then run in each visitor's browser. No Streamlit server or Python installation is needed for players.

The first load downloads Pyodide from its official CDN, so the visitor needs an internet connection. The game source, Tkinter adapter, and music file are served from the GitHub Pages repository.

## Run locally

Do not open `index.html` directly with `file://`; browsers block the Python and music file requests from local files. From this folder, run:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000` in a current browser.

## Files

- `index.html`: GitHub Pages entry point, browser input/audio, Canvas renderer, and Pyodide bootstrap
- `original_game.py`: Python game logic and gameplay rules
- `tkinter.py`: browser implementation of the Tk root, Canvas drawing API, and `after()` timer
- `physics_chronicles.wav`: background music used by the original game

Pyodide does not ship Tkinter, so the adapter implements the Canvas and event methods this game calls. The adapter intentionally stays next to the original source; the game does not import or depend on Streamlit.
