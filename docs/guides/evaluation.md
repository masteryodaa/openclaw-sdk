# Evaluation

The OpenClaw SDK includes a lightweight evaluation framework for testing agent
outputs against expected results. Use `EvalSuite` to define test cases with
built-in or custom evaluators, then run them against any agent.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient, EvalSuite, EvalCase, ContainsEvaluator

async def main():
    suite = EvalSuite()
    suite.add_case(EvalCase(
        query="What is the capital of France?",
        expected="Paris",
        evaluators=[ContainsEvaluator("Paris")],
    ))

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        report = await suite.run(agent)

        print(f"Passed: {report.passed}/{report.total}")
        for result in report.results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.case.query}")

asyncio.run(main())
```

## Defining Eval Cases

Each `EvalCase` combines a query, an expected output (for reference), and one or
more evaluators that determine pass/fail:

```python
from openclaw_sdk import EvalCase, ContainsEvaluator, LengthEvaluator

case = EvalCase(
    query="List three primary colors",
    expected="red, blue, yellow",
    evaluators=[
        ContainsEvaluator("red"),
        ContainsEvaluator("blue"),
        LengthEvaluator(min_length=10, max_length=500),
    ],
)
```

A case passes only when **all** of its evaluators pass.

!!! note "The `expected` field"
    The `expected` string is metadata for your reference. It is not
    automatically compared to the output. Use `ExactMatchEvaluator` if you
    need a strict string comparison.

## Built-in Evaluators

### ContainsEvaluator

Checks whether the output contains a given substring (case-insensitive by default):

```python
from openclaw_sdk import ContainsEvaluator

evaluator = ContainsEvaluator("Python")
```

### ExactMatchEvaluator

Checks whether the output exactly matches the expected string:

```python
from openclaw_sdk import ExactMatchEvaluator

evaluator = ExactMatchEvaluator("42")
```

!!! warning "Whitespace sensitivity"
    `ExactMatchEvaluator` compares strings exactly, including leading/trailing
    whitespace and casing. Strip and normalize your expected value if needed.

### RegexEvaluator

Checks whether the output matches a regular expression pattern:

```python
from openclaw_sdk import RegexEvaluator

# Match an email-like pattern anywhere in the output
evaluator = RegexEvaluator(r"[\w.+-]+@[\w-]+\.[\w.]+")
```

### LengthEvaluator

Checks whether the output length falls within a range:

```python
from openclaw_sdk import LengthEvaluator

# At least 50 characters, no more than 1000
evaluator = LengthEvaluator(min_length=50, max_length=1000)

# Only enforce a minimum
evaluator = LengthEvaluator(min_length=10)

# Only enforce a maximum
evaluator = LengthEvaluator(max_length=280)
```

## Evaluating a Single Result

You can evaluate a single `ExecutionResult` against a case without running the
full suite:

```python
import asyncio
from openclaw_sdk import OpenClawClient, EvalSuite, EvalCase, ContainsEvaluator

async def main():
    suite = EvalSuite()
    case = EvalCase(
        query="What is 2 + 2?",
        expected="4",
        evaluators=[ContainsEvaluator("4")],
    )
    suite.add_case(case)

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        result = await agent.execute(case.query)

        eval_result = suite.evaluate(result, case)
        print(f"Passed: {eval_result.passed}")
        for detail in eval_result.details:
            print(f"  {detail.evaluator}: {'PASS' if detail.passed else 'FAIL'}")

asyncio.run(main())
```

## Running the Full Suite

`suite.run(agent)` executes every case sequentially against the agent and
returns an `EvalReport`:

```python
report = await suite.run(agent)

print(f"Total:  {report.total}")
print(f"Passed: {report.passed}")
print(f"Failed: {report.failed}")
```

The `EvalReport` contains:

| Field     | Type                | Description                       |
|-----------|---------------------|-----------------------------------|
| `total`   | `int`               | Total number of cases             |
| `passed`  | `int`               | Number of cases that passed       |
| `failed`  | `int`               | Number of cases that failed       |
| `results` | `list[CaseResult]`  | Per-case results with details     |

## Full Example

```python
import asyncio
from openclaw_sdk import (
    OpenClawClient,
    EvalSuite,
    EvalCase,
    ContainsEvaluator,
    RegexEvaluator,
    LengthEvaluator,
)

async def main():
    suite = EvalSuite()

    suite.add_case(EvalCase(
        query="What is the boiling point of water in Celsius?",
        expected="100",
        evaluators=[ContainsEvaluator("100")],
    ))

    suite.add_case(EvalCase(
        query="Write a Python hello world one-liner",
        expected='print("Hello, world!")',
        evaluators=[
            ContainsEvaluator("print"),
            RegexEvaluator(r"print\s*\("),
            LengthEvaluator(max_length=200),
        ],
    ))

    suite.add_case(EvalCase(
        query="Give me a one-sentence summary of machine learning",
        expected="Machine learning is...",
        evaluators=[
            LengthEvaluator(min_length=20, max_length=300),
            ContainsEvaluator("learn"),
        ],
    ))

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        report = await suite.run(agent)

        print(f"\nEval Report: {report.passed}/{report.total} passed\n")
        for r in report.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"[{status}] {r.case.query}")

asyncio.run(main())
```

!!! tip "Use evals in CI"
    Add evaluation suites to your CI pipeline to catch regressions in agent
    behavior. Define a threshold (e.g., 90% pass rate) and fail the build
    if the agent drops below it.
