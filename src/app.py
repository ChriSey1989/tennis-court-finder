"""
Simple mobile-friendly web page for checking tennis court availability.

Runs as a small, always-on web server on the same machine that already
runs check_courts.py (see spec.md). You open its address in your phone's
browser, tick which days and times of day you want, enter the shared
password, and get the same results check_courts.py would print - but as
a web page instead of a terminal command.

No login system, no database - just one shared password (set below) so
random visitors on the internet can't use your server to spam the booking
pages. Because the server was set up without SSL (see spec.md), this
password travels over plain HTTP, not encrypted - fine for something
this low-stakes, but don't reuse a password you care about elsewhere.
"""

from __future__ import annotations

import os
from datetime import date

from flask import Flask, render_template_string, request

from check_courts import check
from time_windows import TIME_OF_DAY_RANGES

# ---------------------------------------------------------------------------
# EDIT THIS before running on your server - pick your own shared password.
PASSWORD = "changeme"
# ---------------------------------------------------------------------------

# Set TENNIS_USE_FIXTURES=1 only for local testing without real internet
# access (mirrors check_courts.py's --fixtures flag).
USE_FIXTURES = os.environ.get("TENNIS_USE_FIXTURES") == "1"

app = Flask(__name__)

DAY_OPTIONS = [
    ("today", "Today"),
    ("tomorrow", "Tomorrow"),
    ("monday", "Monday"),
    ("tuesday", "Tuesday"),
    ("wednesday", "Wednesday"),
    ("thursday", "Thursday"),
    ("friday", "Friday"),
    ("saturday", "Saturday"),
    ("sunday", "Sunday"),
]

TIME_OPTIONS = [(name, name.capitalize()) for name in TIME_OF_DAY_RANGES]

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tennis Court Finder</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 480px;
           margin: 0 auto; padding: 16px; background: #f6f7f9; color: #1a1a1a; }
    h1 { font-size: 1.3rem; }
    fieldset { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 16px;
               background: white; padding: 12px; }
    legend { font-weight: 600; padding: 0 4px; }
    label { display: block; padding: 6px 0; font-size: 1rem; }
    input[type=checkbox] { margin-right: 8px; transform: scale(1.2); }
    input[type=password] { width: 100%; padding: 8px; font-size: 1rem;
                            box-sizing: border-box; border: 1px solid #ccc;
                            border-radius: 6px; }
    button { width: 100%; padding: 12px; font-size: 1.1rem; background: #1a7f37;
             color: white; border: none; border-radius: 8px; margin-top: 8px; }
    .error { color: #b00020; font-weight: 600; }
    .results { background: white; border-radius: 8px; padding: 12px;
               white-space: pre-wrap; font-size: 0.95rem; margin-top: 16px; }
  </style>
</head>
<body>
  <h1>Tennis Court Finder</h1>
  <form method="post">
    <fieldset>
      <legend>Which day(s)?</legend>
      {% for value, text in days %}
      <label><input type="checkbox" name="day" value="{{ value }}"
        {% if value in selected_days %}checked{% endif %}> {{ text }}</label>
      {% endfor %}
    </fieldset>
    <fieldset>
      <legend>Which time(s) of day?</legend>
      {% for value, text in times %}
      <label><input type="checkbox" name="time" value="{{ value }}"
        {% if value in selected_times %}checked{% endif %}> {{ text }}</label>
      {% endfor %}
    </fieldset>
    <fieldset>
      <legend>Password</legend>
      <input type="password" name="password" placeholder="Password" required>
    </fieldset>
    <button type="submit">Check availability</button>
  </form>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  {% if result %}<div class="results">{{ result }}</div>{% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
    selected_days: list[str] = []
    selected_times: list[str] = []

    if request.method == "POST":
        selected_days = request.form.getlist("day")
        selected_times = request.form.getlist("time")
        submitted_password = request.form.get("password", "")

        if submitted_password != PASSWORD:
            error = "Wrong password."
        elif not selected_days or not selected_times:
            error = "Pick at least one day and one time of day."
        else:
            pairs = [(day, time) for day in selected_days for time in selected_times]
            try:
                result = check(day_time_pairs=pairs, today=date.today(), use_fixtures=USE_FIXTURES)
            except Exception as exc:  # noqa: BLE001 - show the user something actionable
                error = f"Something went wrong while checking: {exc}"

    return render_template_string(
        PAGE,
        days=DAY_OPTIONS,
        times=TIME_OPTIONS,
        selected_days=selected_days,
        selected_times=selected_times,
        error=error,
        result=result,
    )


if __name__ == "__main__":
    # host="0.0.0.0" so it's reachable from your phone, not just the server
    # itself. Port 80 is the normal web port, so you don't need to type a
    # port number in the browser - just the server's IP address.
    app.run(host="0.0.0.0", port=80)
