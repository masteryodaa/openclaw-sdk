"""Tests for PromptTemplate."""

import pytest

from openclaw_sdk.prompts import PromptTemplate


def test_basic_template() -> None:
    """Render with one variable."""
    t = PromptTemplate("Hello {name}!")
    assert t.render(name="World") == "Hello World!"


def test_template_with_multiple_vars() -> None:
    """Render with multiple variables."""
    t = PromptTemplate("Research {topic} and write {style}")
    result = t.render(topic="AI safety", style="concisely")
    assert result == "Research AI safety and write concisely"


def test_template_missing_variable_raises() -> None:
    """KeyError on missing variable with no default."""
    t = PromptTemplate("Hello {name}, welcome to {place}!")
    with pytest.raises(KeyError):
        t.render(name="Alice")


def test_template_variables_property() -> None:
    """Variables property returns set of variable names."""
    t = PromptTemplate("Hello {name}, welcome to {place}!")
    assert t.variables == {"name", "place"}


def test_template_variables_empty() -> None:
    """Variables property returns empty set for no placeholders."""
    t = PromptTemplate("No variables here.")
    assert t.variables == set()


def test_template_compose_add() -> None:
    """PromptTemplate + str + PromptTemplate composes correctly."""
    system = PromptTemplate("You are a {role}.")
    user = PromptTemplate("Task: {query}")
    combined = system + "\n\n" + user
    result = combined.render(role="researcher", query="find papers")
    assert result == "You are a researcher.\n\nTask: find papers"


def test_template_compose_two_templates() -> None:
    """PromptTemplate + PromptTemplate merges defaults."""
    a = PromptTemplate("Hello {name}", name="Alice")
    b = PromptTemplate(", welcome to {place}", place="Wonderland")
    combined = a + b
    assert combined.render() == "Hello Alice, welcome to Wonderland"


def test_template_partial() -> None:
    """partial() pre-fills some variables, leaving others for render()."""
    t = PromptTemplate("Research {topic} and write {style}")
    partial = t.partial(style="concisely")
    result = partial.render(topic="AI safety")
    assert result == "Research AI safety and write concisely"


def test_template_partial_override() -> None:
    """render() kwargs override partial defaults."""
    t = PromptTemplate("Hello {name}!", name="default")
    result = t.render(name="override")
    assert result == "Hello override!"


def test_template_repr() -> None:
    """repr shows the template string."""
    t = PromptTemplate("Hello {name}!")
    assert repr(t) == "PromptTemplate('Hello {name}!')"


def test_template_radd() -> None:
    """string + PromptTemplate works via __radd__."""
    t = PromptTemplate("World!")
    combined = "Hello " + t
    assert isinstance(combined, PromptTemplate)
    assert combined.render() == "Hello World!"


def test_template_radd_preserves_defaults() -> None:
    """string + PromptTemplate preserves defaults from the template."""
    t = PromptTemplate("{name}!", name="Alice")
    combined = "Hello " + t
    assert combined.render() == "Hello Alice!"


def test_template_property() -> None:
    """template property returns the raw template string."""
    raw = "Hello {name}!"
    t = PromptTemplate(raw)
    assert t.template == raw


def test_template_defaults_in_constructor() -> None:
    """Defaults passed in constructor are used in render()."""
    t = PromptTemplate("Hello {name}!", name="World")
    assert t.render() == "Hello World!"
