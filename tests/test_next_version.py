import pytest

from scripts.next_version import bump, notes, parse


@pytest.mark.parametrize("msg,expected", [
    ("feat: add thing", ("feat", None, "add thing", False)),
    ("fix(osc): handle nan", ("fix", "osc", "handle nan", False)),
    ("feat!: drop old api", ("feat", None, "drop old api", True)),
    ("refactor(x)!: y", ("refactor", "x", "y", True)),
    ("chore: x\n\nBREAKING CHANGE: gone", ("chore", None, "x", True)),
    ("chore: x\n\nBREAKING-CHANGE: gone", ("chore", None, "x", True)),
    ("FEAT: upper", ("feat", None, "upper", False)),
])
def test_parse(msg, expected):
    assert parse(msg) == expected


@pytest.mark.parametrize("msg", ["Add thing", "Merge pull request #1", "feat:nospace", "feat: ", ""])
def test_parse_non_conventional(msg):
    assert parse(msg) is None


@pytest.mark.parametrize("current,msgs,expected", [
    ((1, 2, 3), ["fix: a"], (1, 2, 4)),
    ((1, 2, 3), ["perf: a"], (1, 2, 4)),
    ((1, 2, 3), ["fix: a", "feat: b"], (1, 3, 0)),
    ((1, 2, 3), ["feat: b", "fix: a", "feat!: c"], (2, 0, 0)),
    ((1, 2, 3), ["chore: a\n\nBREAKING CHANGE: x"], (2, 0, 0)),
    ((1, 2, 3), ["docs: a", "ci: b", "chore: c", "test: d", "refactor: e", "style: f", "build: g"], None),
    ((1, 2, 3), ["Add something", "Merge branch x"], None),
    ((1, 2, 3), [], None),
    (None, ["feat: first"], (0, 1, 0)),
    (None, ["fix: first"], (0, 1, 0)),
    (None, ["docs: only"], None),
    ((0, 1, 0), ["fix: a"], (0, 1, 1)),
])
def test_bump(current, msgs, expected):
    assert bump(current, msgs) == expected


def test_notes_groups_and_lists_everything():
    text = notes(["feat(display): fades", "fix: nan", "feat!: new api", "Add old style", "docs: readme"])
    assert "### Breaking changes\n- new api" in text
    assert "### Features\n- **display:** fades" in text
    assert "### Bug fixes\n- nan" in text
    assert "- Add old style" in text and "- readme" in text
    assert text.index("Breaking") < text.index("Features") < text.index("Bug fixes") < text.index("Other")
