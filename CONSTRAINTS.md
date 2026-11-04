# Engineering constraints

Python 3.12; typed public boundaries; small functions and explicit failures.
Use `python -m unittest discover -s tests -v` locally and in CI. No skipped tests.
No real dataset/model metrics without rights and reproducible run artifacts.
No network in tests. No API keys, private data, recordings or model weights in Git.
No production deployment or paid requests in this change.
Unknown rights/identity/invalid model output fail closed. No language translation
or diagnosis claims. Model confidence is uncalibrated unless measured otherwise.
Future public API work requires authentication, shared rate limits and privacy review.
