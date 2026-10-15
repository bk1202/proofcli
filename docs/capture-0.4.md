# Output capture changes in 0.4.0

The 0.3.0 capture path decoded invalid UTF-8 with replacement characters and treated the result as complete output. A real command writing the byte `FF` passed a `^\ufffd$` log assertion, even though the command never emitted the UTF-8 encoding of that character.

0.4.0 decodes strictly first. Invalid streams fail the capture check and their regex assertions; the report preserves the captured prefix as base64 and records the first decoder-error offset. Replacement-decoded text remains for inspection, so existing report viewers can display it. Correctly encoded U+FFFD remains valid. This intentionally tightens behavior for binary or non-UTF-8 logs, including file-only contracts.

Handled interruption previously skipped final pipe draining. The supervisor now terminates its owned processes, then drains queued bytes within the existing stream cap and a half-second deadline. A real POSIX child writes to both streams and immediately signals its parent in the regression. The cross-platform signal regression also checks that the emitted startup line survives. No test substitutes mocked subprocess results.

The cap applies to captured bytes, not characters. UTF-8 replacement text and base64 increase report size by a bounded factor; the captured prefix remains at most 1 MiB per stream. A partial multibyte character at an overflow boundary is recorded as both truncation and a decoding error. `output_capture.actual` exposes truncation, incomplete draining, and encoding errors separately.

Bytes buffered within a child and never written to the pipe cannot be recovered. Crashes, forced termination, detached POSIX sessions, and hostile concurrent activity retain the limits in [the earlier audit](audit-0.3.md). Neither report completeness nor a passing regex establishes arbitrary semantic correctness.
