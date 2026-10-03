# Validation Update — 3 October 2026

The current application includes three modes: Vulnerable, Mitigated and Mitigated Final.

A review of the cleaned project archive completed all **131 automated tests successfully**. The included SQLite database passed its integrity check, and the CSV matched the database contents.

These automated tests use mocked model responses and HTTP interactions. This review did not run live Ollama inference or repeat the Promptfoo campaigns.

A separate grading issue was identified: the normal-question checker compares the expected revenue as text, so `136,446.2` is rejected while `136,446.20` is accepted. This requires a numeric-comparison correction and regression tests. It was not covered by the existing 131 tests.

Later application campaigns contain 110 entries per mode. Their results are separate from the initial ten-case evaluation described below.

## Historical Record — 23 September 2026

The following record is preserved as evidence of the earlier implementation. Its references to 58 tests, two security modes and campaigns not yet performed describe the state on that date, not the current project.