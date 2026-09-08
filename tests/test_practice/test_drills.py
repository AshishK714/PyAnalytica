"""Tests for practice drills."""

from __future__ import annotations

import pytest
import yaml

from pyanalytica.data.load import load_bundled
from pyanalytica.practice.drills import (
    DrillError,
    DrillProgress,
    list_bundled_drills,
    load_bundled_drill,
    load_drill,
    parse_drill,
)

DRILL = {
    "title": "Test drill",
    "dataset": "tips",
    "questions": [
        {"id": "n", "text": "Rows?", "kind": "numeric", "answer": 244, "tolerance": 1},
        {"id": "m", "text": "Mean?", "kind": "numeric", "answer": 25.29,
         "tolerance": 0.01, "hint": "Look at Profile."},
        {"id": "c", "text": "Which day?", "kind": "multiple_choice",
         "options": ["Thur", "Sat"], "answer": "Sat"},
        {"id": "t", "text": "Name it", "kind": "short_text", "answer": "tips"},
    ],
}


class TestParsing:
    def test_parses(self):
        d = parse_drill(DRILL)
        assert d.size == 4
        assert d.dataset == "tips"

    def test_missing_title_rejected(self):
        with pytest.raises(DrillError, match="title"):
            parse_drill({"dataset": "tips", "questions": []})

    def test_question_without_answer_rejected(self):
        """It would silently mark every attempt wrong."""
        bad = {"title": "t", "dataset": "tips",
               "questions": [{"id": "q", "text": "?", "kind": "numeric"}]}
        with pytest.raises(DrillError, match="needs an 'answer'"):
            parse_drill(bad)

    def test_multiple_choice_without_options_rejected(self):
        bad = {"title": "t", "dataset": "tips",
               "questions": [{"id": "q", "text": "?", "kind": "multiple_choice",
                              "answer": "a"}]}
        with pytest.raises(DrillError, match="needs 'options'"):
            parse_drill(bad)

    def test_unknown_kind_rejected(self):
        bad = {"title": "t", "dataset": "tips",
               "questions": [{"id": "q", "text": "?", "kind": "essay", "answer": "x"}]}
        with pytest.raises(DrillError, match="unknown kind"):
            parse_drill(bad)

    def test_duplicate_ids_rejected(self):
        bad = {"title": "t", "dataset": "tips", "questions": [
            {"id": "q", "text": "?", "kind": "numeric", "answer": 1},
            {"id": "q", "text": "?", "kind": "numeric", "answer": 2},
        ]}
        with pytest.raises(DrillError, match="duplicate"):
            parse_drill(bad)


class TestChecking:
    def test_exact_numeric(self):
        assert parse_drill(DRILL).get("m").check(25.29) is True

    def test_numeric_as_string(self):
        """Text inputs hand back strings; "25.290" is the same number."""
        assert parse_drill(DRILL).get("m").check("25.290") is True

    def test_within_tolerance(self):
        assert parse_drill(DRILL).get("m").check(25.2949) is True

    def test_outside_tolerance(self):
        assert parse_drill(DRILL).get("m").check(25.31) is False

    def test_wrong_numeric(self):
        assert parse_drill(DRILL).get("m").check(19.79) is False

    def test_text_in_numeric_field_is_wrong_not_a_crash(self):
        assert parse_drill(DRILL).get("m").check("twenty-five") is False

    def test_multiple_choice_case_insensitive(self):
        assert parse_drill(DRILL).get("c").check("sat") is True

    def test_multiple_choice_wrong(self):
        assert parse_drill(DRILL).get("c").check("Thur") is False

    def test_short_text_ignores_whitespace_and_case(self):
        assert parse_drill(DRILL).get("t").check("  TIPS ") is True


class TestBundledDrills:
    def test_bundled_drills_exist(self):
        assert set(list_bundled_drills()) >= {"tips_basics", "titanic_basics"}

    def test_every_bundled_drill_loads(self):
        for name in list_bundled_drills():
            drill = load_bundled_drill(name)
            assert drill.size > 0
            assert drill.dataset

    def test_unknown_drill_names_what_is_available(self):
        with pytest.raises(DrillError, match="Available:"):
            load_bundled_drill("no_such_drill")

    @pytest.mark.parametrize("drill_id", ["tips_basics", "titanic_basics"])
    def test_bundled_answers_match_the_bundled_data(self, drill_id):
        """The trap that already bit once.

        hw1_tips shipped asking for the mean of total_bill with the answer
        19.79 -- correct for the real seaborn dataset, wrong for the synthetic
        one that ships here. Every student would have been marked wrong. These
        assertions recompute the answers from the data rather than trusting
        whoever wrote the file.
        """
        drill = load_bundled_drill(drill_id)
        df, _ = load_bundled(drill.dataset)

        # Built per drill: computing both sets eagerly would look up titanic
        # columns in the tips frame.
        if drill_id == "tips_basics":
            expected = {
                "rows": len(df),
                "mean_bill": round(df["total_bill"].mean(), 2),
                "max_bill": round(df["total_bill"].max(), 2),
                "n_days": df["day"].nunique(),
                "busiest": df["day"].value_counts().idxmax(),
                "smokers": int((df["smoker"] == "Yes").sum()),
            }
        else:
            expected = {
                "rows": len(df),
                "missing_age": int(df["Age"].isna().sum()),
                "mean_age": round(df["Age"].mean(), 2),
                "survivors": int(df["Survived"].sum()),
                "female_rate": round(
                    df[df["Sex"] == "female"]["Survived"].mean() * 100, 1
                ),
                "biggest_class": str(df["Pclass"].value_counts().idxmax()),
            }

        for question in drill.questions:
            assert question.id in expected, (
                f"no verification for {drill_id}.{question.id} -- add one"
            )
            assert question.check(expected[question.id]), (
                f"{drill_id}.{question.id}: the drill says {question.answer!r}, "
                f"but the bundled data gives {expected[question.id]!r}"
            )


class TestFileLoading:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "d.yaml"
        path.write_text(yaml.safe_dump(DRILL), encoding="utf-8")
        assert load_drill(path).size == 4

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_drill(tmp_path / "nope.yaml")


class TestProgress:
    def test_counts(self):
        p = DrillProgress("d")
        p.record("a", True)
        p.record("b", False)
        p.record("a", True)   # re-answering does not double count
        assert p.attempted == 2
        assert p.correct == 1


class TestExplanationsAgreeWithAnswers:
    """An explanation that quotes a different number than the answer.

    When the bundled datasets were replaced with the real ones, every numeric
    answer was recomputed and the tests passed -- while the explanations still
    said "69.6% of women survived" and "About $25.29". Nothing checked the
    prose, so a student reading the feedback was told the answer they had just
    got right was something else.
    """

    @pytest.mark.parametrize("drill_id", ["tips_basics", "titanic_basics"])
    def test_a_numeric_explanation_quotes_its_own_answer(self, drill_id):
        import re

        drill = load_bundled_drill(drill_id)
        contradictions = []
        for question in drill.questions:
            if question.kind != "numeric" or not question.explanation:
                continue
            quoted = re.findall(r"\d+(?:\.\d+)?", question.explanation)
            if not quoted:
                continue
            answer = float(question.answer)
            # The explanation may mention other figures -- a comparison, a
            # denominator -- but the answer itself should be among them.
            if not any(abs(float(n) - answer) < 0.011 for n in quoted):
                contradictions.append(
                    f"{drill_id}.{question.id}: answer is {question.answer}, "
                    f"but the explanation quotes {quoted}"
                )
        assert not contradictions, "\n  ".join(contradictions)
