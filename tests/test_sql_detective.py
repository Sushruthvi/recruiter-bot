"""Checks the Part 2 answers against the dataset (in-memory SQLite)."""
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def results():
    """Run each query in sql_detective.sql; return {question number: rows}."""
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "sql_detective_data.sql").read_text(encoding="utf-8"))

    out, buffer = {}, ""
    for line in (ROOT / "sql_detective.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        buffer += line
        if not sqlite3.complete_statement(buffer):
            continue
        number = next(
            int(l[4:].split(".")[0]) for l in buffer.splitlines() if l.startswith("-- Q")
        )
        out[number] = conn.execute(buffer).fetchall()
        buffer = ""
    return out


def test_all_five_questions_are_answered(results):
    assert sorted(results) == [1, 2, 3, 4, 5]


def test_q1_open_postings_with_recruiter(results):
    assert [(r[0], r[4]) for r in results[1]] == [
        (1, "Priya Shah"),
        (2, "Daniel Ortiz"),
        (4, "Priya Shah"),
        (5, "Wei Zhang"),
    ]


def test_q2_finalists_per_posting_including_zeros(results):
    assert [(r[0], r[2]) for r in results[2]] == [
        (1, 2), (2, 2), (3, 1), (4, 2), (5, 0), (6, 0), (7, 2),
    ]


def test_q3_finds_people_applying_to_multiple_postings_despite_duplicate_rows(results):
    assert [r[0] for r in results[3]] == ["Ananya Rao", "Ben Turner", "Elena Popescu"]
    assert all(r[2] == 2 for r in results[3])


def test_q4_conversion_rates_use_decimal_division_and_the_three_final_minimum(results):
    assert [(r[1], r[2], r[3], r[4]) for r in results[4]] == [
        ("Priya Shah", 4, 3, 0.75),
        ("Daniel Ortiz", 4, 2, 0.5),
    ]


def test_q5_top_recruiter_per_department_with_window_function(results):
    assert results[5] == [
        ("Data", "Fatima Al-Sayed", 1),
        ("Engineering", "Priya Shah", 3),
        ("Infrastructure", "Wei Zhang", 0),
    ]
