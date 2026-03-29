# Fixture Capture Scripts

Temporary scripts used to capture real SIA responses for tests.

## Capture Fixtures

From repository root:

```bash
PYTHONPATH=src python3 scripts/capture_sia_fixtures.py
```

The script reads `scripts/capture_config.yaml` and writes fixtures under:

- `tests/fixtures/html/`
- `tests/fixtures/xml/`
- `tests/fixtures/json/`

Behavior configured for this project:

- Captures CS career (`0-2-8-3`)
- Captures 5 regular courses
- Captures 2 electives
- Captures timeout error fixture
- Sanitizes tokens/cookies
- Keeps only latest fixture set for each logical file
