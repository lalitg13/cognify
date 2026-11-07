# Cognify

A small Flask study app. Paste lecture notes and it builds concept cards, flip flashcards, a 5-question quiz, and charts from saved scores.

It runs with no Gemini API key. That path is demo mode: the header badge says **Zero-Config Mode**, and the pack comes from built-in examples instead of a model.

![Cognify home screen. The header badge reads Zero-Config Mode.](assets/overview.png)

## Study workspace

![Studio after loading the calculus sample in demo mode. Notes are on the left and concept cards are on the right.](assets/study-workspace.png)

The shot above is demo mode. The calculus sample was loaded, then **Architect Study Pack** was clicked. No API key was set.

The label "Gemini 2.5 Flash" on the input card is fixed text in the page. The header badge is the mode that is actually running. **4 Saved** is the three sample packs that ship with a new database, plus the calculus pack just created.

| Flashcards | Quiz |
| --- | --- |
| ![Flipped calculus flashcard with Again, Hard, Good, and Easy rating buttons.](assets/flashcards.png) | ![Quiz question graded correct, with the explanation shown.](assets/quiz.png) |

What those screens actually do:

- **Concepts.** A summary, term cards with exam tips, formulas, and a few common mistakes.
- **Flashcards.** Click the card or press Space to flip it. The rating buttons are labeled Again (1m), Hard (6m), Good (1d), and Easy (4d). The rating is saved in SQLite. The app does not bring the card back later on that timer.
- **Quiz.** Five multiple-choice questions. Keys 1–4 select an answer and Enter grades it. The speaker button uses the browser's speech synthesis. At the end, the score is saved and tagged Mastery (80%+), Proficient (65–79%), or At-Risk (under 65%).
- **Study protocol.** A three-step list stored with the pack.
- **Export.** Markdown file, Anki tab-separated text, copy to clipboard, or print.

## Charts

![Mastery bar chart and score curve drawn by Matplotlib from the sample quiz history.](assets/analytics.png)

`GET /api/analytics.png` draws this with Pandas and Matplotlib (`Agg`, so it works without a display). A new database includes three sample study packs and twelve sample quiz attempts, so the chart is not empty. The percentages in the picture are that seed data.

The other toggle, **Diagnostics & Pace**, shows which subtopics were missed and a scatter of time spent versus score.

## How a pack is built

![Flow from the browser, through Flask, to either a demo pack or Gemini, then SQLite.](assets/flow.png)

Demo mode looks for calculus, biology, or computer-science words in the notes and returns a matching built-in pack. The check is a simple substring, so an unrelated note can match too. Notes that do not match get a shorter generic pack built from the first lines of the text.

If `GEMINI_API_KEY` is set, or a key is pasted into the API key dialog, `ai_engine.py` calls `gemini-2.5-flash` and checks the JSON with a Pydantic model. If that call fails, it falls back to the demo pack.

The page itself loads Tailwind and fonts from a CDN, so the browser still needs network access for styling.

## Run it

```bash
git clone https://github.com/lalitg13/cognify.git
cd cognify
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate with `venv\Scripts\activate`.

A key is optional. To use Gemini later:

```bash
cp .env.example .env
# Put your key in GEMINI_API_KEY
```

Start the app:

```bash
python app.py
```

Open [http://localhost:5001](http://localhost:5001). The server listens on port 5001.

The SQLite file is created at `data/cognify.db` and is gitignored.

## Project layout

```text
cognify/
├── app.py              # Flask routes, exports, port 5001
├── ai_engine.py        # Gemini call, Pydantic schema, demo packs
├── database.py         # SQLite sessions, quiz attempts, card ratings
├── analytics.py        # Matplotlib charts
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
├── assets/             # README screenshots
├── requirements.txt
└── .env.example
```

## API

| Endpoint | Method | What it does |
| --- | --- | --- |
| `/api/dashboard` | GET | Counts, mode, recent sessions and attempts |
| `/api/generate` | POST | Builds a study pack and saves it |
| `/api/session/<id>` | GET | Loads one saved pack |
| `/api/session/<id>` | DELETE | Deletes that pack and its quiz rows |
| `/api/submit_quiz` | POST | Saves a quiz score and weak subtopics |
| `/api/flashcard/review` | POST | Saves a card rating (`again`, `hard`, `good`, `easy`) |
| `/api/analytics.png` | GET | Chart image. `?view=mastery` or `?view=diagnostics` |
| `/api/export/<id>/markdown` | GET | Downloads a Markdown study guide |
| `/api/export/<id>/anki` | GET | Downloads an Anki text file |
| `/api/reset_demo` | POST | Deletes the database and loads the sample rows again |

## Checks

```bash
python database.py
python analytics.py
python ai_engine.py

python -c "
from app import app
client = app.test_client()
assert client.get('/api/dashboard').status_code == 200
assert client.get('/api/analytics.png?view=mastery').status_code == 200
assert client.get('/api/analytics.png?view=diagnostics').status_code == 200
assert client.get('/api/export/1/markdown').status_code == 200
assert client.get('/api/export/1/anki').status_code == 200
print('All core API integration tests passed.')
"
```
