from scripts.lint_commit import validate_commit_msg


def test_validate_commit_msg_success() -> None:
    valid_msgs = [
        "feat: add commit linting",
        "fix(parser): resolve issue with null values",
        "docs: update readme",
        "release: v1.2.3",
        "feat!: breaking change description",
        "chore(deps): bump dependencies",
    ]
    for msg in valid_msgs:
        assert validate_commit_msg(msg) is True


def test_validate_commit_msg_failure() -> None:
    invalid_msgs = [
        "update code",
        "feat : space before colon",
        "Release: v1.0.0",
        "feat(parser) lacking colon",
        "",
        "   ",
        "random commit message without type",
    ]
    for msg in invalid_msgs:
        assert validate_commit_msg(msg) is False
