"""Composable prompt templates with variable substitution."""

from __future__ import annotations

import re


class PromptTemplate:
    """A reusable prompt template with {variable} placeholders.

    Example::

        t = PromptTemplate("Research {topic} and write {style}")
        prompt = t.render(topic="AI safety", style="concisely")

    Templates can be composed with ``+``::

        system = PromptTemplate("You are a {role}.")
        user = PromptTemplate("Task: {query}")
        combined = system + "\\n\\n" + user
    """

    _VAR_PATTERN = re.compile(r"\{(\w+)\}")

    def __init__(self, template: str, **defaults: str) -> None:
        self._template = template
        self._defaults: dict[str, str] = dict(defaults)

    @property
    def template(self) -> str:
        """Return the raw template string."""
        return self._template

    @property
    def variables(self) -> set[str]:
        """Return set of variable names found in the template."""
        return set(self._VAR_PATTERN.findall(self._template))

    def render(self, **kwargs: str) -> str:
        """Render the template by substituting variables.

        Raises:
            KeyError: If a required variable is not provided and has no default.
        """
        merged = {**self._defaults, **kwargs}
        return self._template.format(**merged)

    def partial(self, **kwargs: str) -> PromptTemplate:
        """Return a new template with some variables pre-filled as defaults."""
        new_defaults = {**self._defaults, **kwargs}
        return PromptTemplate(self._template, **new_defaults)

    def __add__(self, other: PromptTemplate | str) -> PromptTemplate:
        """Compose two templates or a template and a string."""
        if isinstance(other, PromptTemplate):
            merged_defaults = {**self._defaults, **other._defaults}
            return PromptTemplate(self._template + other._template, **merged_defaults)
        return PromptTemplate(self._template + other, **self._defaults)

    def __radd__(self, other: str) -> PromptTemplate:
        """Support string + PromptTemplate."""
        return PromptTemplate(other + self._template, **self._defaults)

    def __repr__(self) -> str:
        return f"PromptTemplate({self._template!r})"
