# How to Build a Lottery Draw Generator That Never Matches Your Tickets — A Python & Flask Tutorial

*Published by ponITech · Educational Series*

---

> **⚠️ Important Disclaimer**
> This project is built entirely for **educational purposes** — to demonstrate Python logic, set theory, probability, and web development with Flask. It is **not** a tool for manipulating real lottery results, deceiving any person or organisation, or gaining unfair advantage in any game of chance. Real lottery draws are conducted by licensed authorities under strict regulations. Attempting to manipulate, predict, or interfere with actual lottery systems is **illegal** in most jurisdictions. Use this code only to learn programming concepts.

---

## Introduction

Have you ever wondered: *"What would a lottery draw look like if it was guaranteed to miss every ticket I've played?"* It's a fun thought experiment, and it turns out building it is a great excuse to explore some genuinely useful programming concepts — set theory, randomness, combinatorics, and full-stack web development.

In this article we'll walk through how I built a Flask web application that:

1. Accepts up to 200 lottery ticket combinations from a user (7 numbers, each between 1 and 36)
2. Generates a completely random draw result
3. **Guarantees** that the result doesn't match any submitted ticket
4. Produces a hit report showing how many of your numbers came close (4, 5, or 6 hits)

It's a small project, but it touches surprisingly deep territory.

---

## The Math Behind It: Why This Works

The Serbian lottery (*7 od 36*) asks players to pick 7 numbers from 1 to 36. The total number of possible combinations is calculated using the binomial coefficient:

```
C(36, 7) = 36! / (7! × 29!) = 8,347,680
```

That's over **eight million** possible draws. Even if a user submits the maximum of 200 combinations, those represent just **0.0024%** of all possible outcomes. The vast majority of the number space remains available, which means generating a draw that avoids all submitted tickets is trivially fast — almost always on the very first attempt.

This is the key insight: the problem sounds hard ("avoid all these combinations!") but is computationally trivial because the excluded space is vanishingly small.

---

## The Original Code and Its Problem

The original Python script had a clever idea but a subtle bug in its draw logic:

```python
# Original approach — flawed
izvlacenje = []
while len(izvlacenje) < 7:
    broj = random.randint(1, 36)
    for podlista in prociscena_lista:
        if broj in podlista and len(set(izvlacenje + podlista)) < 7:
            break
    else:
        izvlacenje.append(broj)
```

The problem here is that it tried to exclude individual *numbers* that appeared in submitted tickets. But a lottery combination is defined by the **full set of 7 numbers together**, not by individual numbers. Number `5` might appear in a submitted ticket, but that doesn't mean a draw containing `5` is invalid — only a draw containing the *exact same 7 numbers* as a ticket would be a problem.

This approach also creates a bias: numbers that appear frequently across many tickets effectively get "blocked," skewing the randomness of the generated draw.

### The Correct Approach

```python
def generate_unique_draw(combinations):
    submitted_sets = {frozenset(c) for c in combinations}
    
    for _ in range(10_000):  # safety cap, almost never needed
        draw = random.sample(range(1, 37), 7)
        if frozenset(draw) not in submitted_sets:
            return sorted(draw)
    
    raise RuntimeError("Could not generate a valid draw.")
```

The fix is elegant: generate a fully random draw of 7 numbers using `random.sample()` (which handles uniqueness automatically), then check the entire draw as a set against all submitted tickets. If it matches, throw it away and try again. Given the maths above, you almost never need to try more than once.

**Using `frozenset` is the key performance trick.** Sets in Python have O(1) average-case lookup, so checking 200 combinations takes the same amount of time as checking 1 from a big-O perspective.

---

## Also Fixed: The UnicodeEncodeError

Running the original code on Windows produced this error:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u010d'
```

The character `č` (in "Pročišćena") is a UTF-8 character not supported by `cp1252`, the default Windows console encoding. The fix is one line at the top of the script:

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

This forces Python to use UTF-8 for standard output regardless of the system default — essential for any application dealing with non-ASCII characters, especially in languages like Serbian, Croatian, or other languages using diacritics.

---

## Building the Flask Web Application

Flask is a lightweight Python web framework perfect for small applications like this. The project structure is minimal:

```
lotto_app/
├── app.py              # Flask backend
├── requirements.txt    # Dependencies (just Flask)
└── templates/
    └── index.html      # Frontend (HTML + CSS + JS, single file)
```

### The Backend: `app.py`

The backend has three responsibilities:

**1. Input validation** — each submitted combination must have exactly 7 numbers, all unique, all between 1 and 36. This is enforced both client-side (in JavaScript) and server-side (in Python), which is always the right approach for web applications.

**2. Draw generation** — using the `generate_unique_draw()` function described above.

**3. Hit analysis** — after generating the draw, the backend compares each submitted combination against the draw and counts how many numbers match:

```python
def analyse_hits(combinations, draw_set):
    summary = {4: 0, 5: 0, 6: 0}
    details = []

    for i, combo in enumerate(combinations):
        hits = len(set(combo) & draw_set)   # set intersection = matching numbers
        if hits in summary:
            summary[hits] += 1
        if hits >= 4:
            details.append({
                "index": i + 1,
                "combination": sorted(combo),
                "hits": hits,
                "hit_numbers": sorted(set(combo) & draw_set),
                "miss_numbers": sorted(set(combo) - draw_set),
            })

    return {
        "six_hits":  summary[6],
        "five_hits": summary[5],
        "four_hits": summary[4],
        "details":   sorted(details, key=lambda x: x["hits"], reverse=True),
    }
```

The `&` operator between two Python sets computes the **intersection** — numbers present in both. The `-` operator computes the **difference** — numbers in the combo that weren't drawn. This is set theory in action, and it's one of the cleaner parts of the codebase.

### The Frontend

The frontend is a single HTML file with embedded CSS and JavaScript. Key design decisions:

- **No framework** — vanilla JavaScript handles all the interactivity. For a project this size, React or Vue would be overkill.
- **Circular number inputs** — styled to look like lottery balls, reinforcing the visual metaphor.
- **Real-time validation** — inputs turn green when valid, red when out of range or duplicated within the same row.
- **Keyboard navigation** — pressing `Enter` moves focus to the next input; at the last input of a row, it automatically adds a new row.

All communication between frontend and backend happens via a single `POST /draw` endpoint that accepts and returns JSON.

---

## The Hit Report: Reading the Results

After the draw is generated, the app shows a hit report. Here's how to interpret it:

| Hit Count | Meaning |
|-----------|---------|
| **7 hits** | Impossible — the draw is guaranteed not to match any ticket exactly |
| **6 hits** | Your ticket shared 6 numbers with the draw — very close! |
| **5 hits** | 5 numbers matched — still an impressive near-miss |
| **4 hits** | 4 numbers matched |
| **0–3 hits** | Not shown in detail, but counted in totals |

In the detailed view, **golden balls** indicate numbers that hit; grey balls indicate misses. This makes it visually immediate which numbers from each ticket appeared in the draw.

---

## What This Teaches Us

This small project is a useful vehicle for several important programming concepts:

**Set theory in Python** — `frozenset`, `&` (intersection), `-` (difference), and O(1) lookup are all put to practical use. Sets are one of Python's most underused data structures.

**Combinatorics and probability** — understanding *why* the brute-force retry approach works requires knowing C(36, 7) = 8,347,680. The maths justifies the implementation choice.

**Input validation at two layers** — both the browser (for UX) and the server (for security) validate the same data. Never trust client-side validation alone.

**Flask routing and JSON APIs** — the app demonstrates a clean separation between a data endpoint (`/draw`) and a render endpoint (`/`), which is the foundation of any REST-style architecture.

**Encoding issues in Python** — the `UnicodeEncodeError` is a classic Windows Python problem. Knowing how to fix it with `sys.stdout.reconfigure()` will save you hours of frustration.

---

## Conclusion

What started as a fun question — *"can we generate a draw that misses all our tickets?"* — turned into a clean demonstration of how Python's built-in data structures, combined with a little probability theory, can make seemingly complex problems trivial to solve.

The full source code for this project (Flask backend + single-file HTML frontend) is available and ready to run with nothing more than `pip install flask`.

To run it yourself:

```bash
pip install flask
python app.py
# Open http://127.0.0.1:5000
```

Happy coding — and remember, this is for learning, not for lottery strategy.

PS

Complete old project (just .py file) in Serbian language:

```python
# Program za loto sa neizvučenim brojevima 1
import sys
sys.stdout.reconfigure(encoding='utf-8')
import random

# Kreiraj listu uplata
uplata = []
for i in range(10):
    podlista = []
    while len(podlista) < 7:
        broj = random.randint(1, 36)
        if broj not in podlista:
            podlista.append(broj)
    uplata.append(podlista)



# Procisti duplikate u listi uplata
prociscena_lista = []
for podlista in uplata:
    if podlista not in prociscena_lista:
        prociscena_lista.append(podlista)


# Generiraj listu izvlačenja
izvlacenje = []
while len(izvlacenje) < 7:
    broj = random.randint(1, 36)
    for podlista in prociscena_lista:
        if broj in podlista and len(set(izvlacenje + podlista)) < 7:
            break
    else:
        izvlacenje.append(broj)

print("Lista uplata:")
for podlista in uplata:
    print(podlista)

print('\n')
print('\n')

print("Pročišćena lista:")
for podlista in prociscena_lista:
    print(podlista)

print('\n')
print('\n')

print("Izvlačenje:")
print(izvlacenje)
```

