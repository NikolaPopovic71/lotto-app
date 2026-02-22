## Lotto Draw Generator - Flask App
## Generates a draw result that never matches any user-submitted combinations

import sys
import random
from flask import Flask, render_template, request, jsonify

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

MAX_COMBINATIONS = 200
LOTTO_MIN = 1
LOTTO_MAX = 36
NUMBERS_PER_COMBINATION = 7


def generate_unique_draw(combinations: list[frozenset]) -> list[int]:
    """
    Generate 7 unique random numbers (1-36) that do NOT match
    any combination submitted by the user.

    Uses frozensets for O(1) lookup against submitted combinations.
    The total possible draws from 36 choose 7 = 8,347,680,
    so collision resolution is near-instant even with 200 submissions.
    """
    submitted_sets = {frozenset(c) for c in combinations}
    max_attempts = 10_000  # Safety cap (should never be needed)

    for _ in range(max_attempts):
        draw = random.sample(range(LOTTO_MIN, LOTTO_MAX + 1), NUMBERS_PER_COMBINATION)
        if frozenset(draw) not in submitted_sets:
            return sorted(draw)

    raise RuntimeError("Could not generate a non-matching draw after 10,000 attempts.")


def validate_combination(numbers: list) -> tuple[bool, str]:
    """Validate a single combination of 7 numbers."""
    if len(numbers) != NUMBERS_PER_COMBINATION:
        return False, f"Each combination must have exactly {NUMBERS_PER_COMBINATION} numbers."

    seen = set()
    for n in numbers:
        if not isinstance(n, int):
            return False, "All numbers must be integers."
        if not (LOTTO_MIN <= n <= LOTTO_MAX):
            return False, f"All numbers must be between {LOTTO_MIN} and {LOTTO_MAX}."
        if n in seen:
            return False, "Numbers within a combination must be unique."
        seen.add(n)

    return True, ""


def analyse_hits(combinations: list[list[int]], draw_set: frozenset) -> dict:
    """
    For each submitted combination, count how many numbers match the draw.
    Returns a summary of combos with 4, 5, or 6 hits, plus details for each.
    """
    summary = {4: 0, 5: 0, 6: 0}
    details = []

    for i, combo in enumerate(combinations):
        hits = len(set(combo) & draw_set)
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

    details.sort(key=lambda x: x["hits"], reverse=True)

    return {
        "six_hits":  summary[6],
        "five_hits": summary[5],
        "four_hits": summary[4],
        "total_with_hits": sum(summary.values()),
        "details": details,
    }


@app.route("/")
def index():
    return render_template("index.html",
                           max_combinations=MAX_COMBINATIONS,
                           lotto_min=LOTTO_MIN,
                           lotto_max=LOTTO_MAX,
                           numbers_per_combination=NUMBERS_PER_COMBINATION)


@app.route("/draw", methods=["POST"])
def draw():
    data = request.get_json()

    if not data or "combinations" not in data:
        return jsonify({"error": "No combinations provided."}), 400

    combinations = data["combinations"]

    if not isinstance(combinations, list) or len(combinations) == 0:
        return jsonify({"error": "Please provide at least one combination."}), 400

    if len(combinations) > MAX_COMBINATIONS:
        return jsonify({"error": f"Maximum {MAX_COMBINATIONS} combinations allowed."}), 400

    # Validate each combination
    validated = []
    for i, combo in enumerate(combinations):
        if not isinstance(combo, list):
            return jsonify({"error": f"Combination {i + 1} is not a valid list."}), 400
        try:
            numbers = [int(n) for n in combo]
        except (ValueError, TypeError):
            return jsonify({"error": f"Combination {i + 1} contains non-integer values."}), 400

        valid, msg = validate_combination(numbers)
        if not valid:
            return jsonify({"error": f"Combination {i + 1}: {msg}"}), 400

        validated.append(numbers)

    # Remove exact duplicates (same numbers regardless of order)
    unique_combinations = list({frozenset(c) for c in validated})

    try:
        result = generate_unique_draw(unique_combinations)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    # Analyse hits per combination
    draw_set = frozenset(result)
    hit_report = analyse_hits(validated, draw_set)

    return jsonify({
        "draw": result,
        "combinations_submitted": len(validated),
        "unique_combinations": len(unique_combinations),
        "message": f"Draw generated! It does not match any of your {len(unique_combinations)} unique combination(s).",
        "hit_report": hit_report
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)