# Physics Chronicles · GitHub Pages

This package runs the existing Python/Tkinter game logic in the browser. `original_game.py` is the game source copied from `해커은신처.py`; its fixed-step update loop and combat logic remain Python. `tkinter.py` supplies the small Tk window and Canvas surface that Pyodide does not include, forwarding the original drawing calls to the browser's HTML Canvas. Keyboard events are forwarded back to the original Python callbacks. The original WAV is played by the browser audio element.

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
- `original_game.py`: the original Python game, renamed for the web package
- `tkinter.py`: browser implementation of the Tk root, Canvas drawing API, and `after()` timer
- `physics_chronicles.wav`: background music used by the original game

Pyodide does not ship Tkinter, so the adapter implements the Canvas and event methods this game calls. The adapter intentionally stays next to the original source; the game does not import or depend on Streamlit.
