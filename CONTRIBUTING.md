# Contributing

Explain the observed failure and the resulting behavior. Preserve the standard-library-only runtime, strict JSON contracts, and cross-platform execution.

## Validate a change

Use Python 3.10 or newer:

```console
python -m pip install -e .
python -m unittest discover -s tests -v
proofcli validate examples/export/good.json
proofcli run examples/export/good.json
proofcli run examples/export/false-success.json --json
```

The false-success export must return 1 even though its child exits 0 and writes valid, nonempty files. Tests should execute real short-lived programs and inspect actual files. Prefer `sys.executable` or `{python}` to platform-specific shell commands.

To test an installed package, install it normally and run the suite with `PROOFCLI_TEST_INSTALLED=1` in the environment. The CLI tests then use the installed `proofcli` command from outside the source tree, matching GitHub Actions. Set that variable with your shell's environment syntax.

For packaging/release changes, install `requirements-build.txt` with `--require-hashes`, run `python -m build --no-isolation`, and run `python tools/verify_dist.py`. That gate rebuilds the sdist and exercises both distributions in fresh environments. Run `python tools/audit_dependencies.py` for the point-in-time PyPI advisory/hash check. Follow [the release procedure](docs/releasing.md); all Windows/macOS gates must pass before releasing.

Signal/link tests skip only when the platform or filesystem cannot supply the feature. Inspect skips rather than calling them passes. Regression tests must reproduce an external behavior or meaningful contract; avoid mocks of the process execution being verified. Do not remove a failing test to make CI green.

Spec/report changes need matching documentation and behavior tests. Preserve separate child process outcomes, assertion failures, and CLI errors. Test fixture staging, failed-content artifact retention, timeouts, Unicode, paths with spaces, and Windows/macOS differences when relevant. Avoid writing tests that simply mirror implementation internals.

Do not claim a platform is verified until its tests have run there. Keep new validators small and motivated by a concrete output contract. The content-validation size limit and lack of a security sandbox must remain explicit.

## Report a bug

Include the Python version, operating system, a minimal spec, a small nonprivate input fixture if needed, the intended result, and ProofCLI's report. Remove credentials and private paths before sharing logs or retained artifacts. For timeout issues, describe whether the command creates child processes.
