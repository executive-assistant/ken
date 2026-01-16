from cassey.channels.management_commands import _parse_mem_add_args


def test_parse_mem_add_args_keeps_full_content():
    content, mem_type, key = _parse_mem_add_args(["add", "i", "love", "my", "wife", "Jing"])
    assert content == "i love my wife Jing"
    assert mem_type is None
    assert key is None


def test_parse_mem_add_args_with_explicit_type():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "I", "prefer", "tea", "over", "coffee", "type=preference"]
    )
    assert content == "I prefer tea over coffee"
    assert mem_type == "preference"
    assert key is None


def test_parse_mem_add_args_with_explicit_key():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "My", "office", "timezone", "is", "EST", "key=timezone"]
    )
    assert content == "My office timezone is EST"
    assert mem_type is None
    assert key == "timezone"


def test_parse_mem_add_args_with_type_and_key_flags():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "Working", "late", "type=task", "key=shift"]
    )
    assert content == "Working late"
    assert mem_type == "task"
    assert key == "shift"


def test_parse_mem_add_args_with_positional_type():
    content, mem_type, key = _parse_mem_add_args(["add", "Update", "resume", "profile"])
    assert content == "Update resume"
    assert mem_type == "profile"
    assert key is None


def test_parse_mem_add_args_with_positional_type_and_key():
    content, mem_type, key = _parse_mem_add_args(["add", "Prefers", "tea", "preference", "beverage"])
    assert content == "Prefers tea"
    assert mem_type == "preference"
    assert key == "beverage"


def test_parse_mem_add_args_with_common_key_fallback():
    content, mem_type, key = _parse_mem_add_args(["add", "User", "timezone"])
    assert content == "User"
    assert mem_type is None
    assert key == "timezone"


def test_parse_mem_add_args_without_content():
    content, mem_type, key = _parse_mem_add_args(["add"])
    assert content == ""
    assert mem_type is None
    assert key is None


def test_parse_mem_add_args_with_unicode_emoji():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "I", "love", "coding", "🚀", "and", "coffee", "☕"]
    )
    assert content == "I love coding 🚀 and coffee ☕"
    assert mem_type is None
    assert key is None


def test_parse_mem_add_args_with_chinese_characters():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "我", "喜欢", "编程", "type=preference"]
    )
    assert content == "我 喜欢 编程"
    assert mem_type == "preference"
    assert key is None


def test_parse_mem_add_args_with_long_content():
    long_content = ["add"] + [f"word{i}" for i in range(100)]
    content, mem_type, key = _parse_mem_add_args(long_content)
    assert content.startswith("word0 word1 word2 word3")
    assert content.endswith("word97 word98 word99")
    assert len(content.split()) == 100
    assert mem_type is None
    assert key is None


def test_parse_mem_add_args_with_invalid_type_value():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "Some", "content", "type=invalid_type_not_in_list"]
    )
    assert content == "Some content"
    assert mem_type == "invalid_type_not_in_list"  # Parser accepts any value
    assert key is None


def test_parse_mem_add_args_duplicate_type_last_wins():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "Test", "content", "type=preference", "type=fact"]
    )
    assert content == "Test content"
    assert mem_type == "fact"  # Last type= wins
    assert key is None


def test_parse_mem_add_args_duplicate_key_last_wins():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "Test", "content", "key=timezone", "key=language"]
    )
    assert content == "Test content"
    assert mem_type is None
    assert key == "language"  # Last key= wins


def test_parse_mem_add_args_duplicate_type_and_key():
    content, mem_type, key = _parse_mem_add_args(
        ["add", "Test", "content", "type=task", "key=old", "key=new", "type=fact"]
    )
    assert content == "Test content"
    assert mem_type == "fact"  # Last type= wins
    assert key == "new"  # Last key= wins
