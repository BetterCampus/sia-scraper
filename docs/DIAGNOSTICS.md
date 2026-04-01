# Parser Diagnostics Guide

This guide explains how to use and configure parser diagnostics for debugging SIA scraping issues.

## Logging Configuration

Parser diagnostics use `loguru` for Python and the standard `log` crate for Rust. Logging is controlled by the `SIA_DEBUG` environment variable:

```bash
# Enable debug logging
export SIA_DEBUG=1

# Run your scraper
python your_script.py
```

### Log Levels

- **DEBUG**: Structure deviations (e.g., groups with fewer divs than expected)
- **WARNING**: Missing elements, unexpected structures  
- **ERROR**: Fatal parsing failures

By default (without SIA_DEBUG=1), no diagnostic logs are emitted to keep output clean.

## Python Parser Diagnostics

### Error Messages

Parser errors include detailed diagnostic information:

#### Example: Missing Credits Element

```
ValueError: Credits element not found in XML.
Searched for: <span class='detass-creditos'>
Found 15 span elements with classes: ['af_output_text', 'af_panelGroupLayout', ...]
```

#### Example: Group with Partial Data

When a group has fewer divs than expected (e.g., 5 instead of 6), the parser logs at DEBUG level:

```python
# With SIA_DEBUG=1:
DEBUG: Group 0 in course 'CALCULO DIFERENCIAL' has 5 divs (expected 6 for full data). 
       Fields: ['Profesor: JUAN PEREZ', 'Facultad: CIENCIAS', 'Horarios: LU 10:00', ...]
DEBUG: Spots info missing in group 0 of course 'CALCULO DIFERENCIAL' (div count: 5)
```

#### Example: Missing Field at Index

```python
ValueError: Failed to extract 'faculty' for group 0 in course 'CALCULO':
expected element at index 1, but only 1 elements present.
Available elements:
  [0]: Profesor: JUAN PEREZ
```

### Course Name Errors

```python
ValueError: Course name element not found in XML.
```

### Credits Parse Errors

```python
ValueError: Failed to parse credits value.
Expected integer, got: 'invalid'
Parse error: invalid literal for int() with base 10: 'invalid'
```

## Rust Parser Diagnostics

Rust parser diagnostics are separate from Python logging. Configure via Python:

```python
import sia_scraper_rust

# Enable debug logging
sia_scraper_rust.init_rust_logging("debug")

# Or via environment variable (checked automatically)
import os
os.environ["SIA_DEBUG"] = "1"
```

### Rust Log Output

Rust diagnostics appear on stderr:

```
WARN:  Credits element not found. Found 15 span elements total
DEBUG: Group 0 in course 'CALCULO' has 5 divs (expected 6 for full data). Fields: [...]
```

## Troubleshooting

### Common Issues

1. **Credits element not found**: SIA may have changed their HTML structure
2. **Group has fewer divs than expected**: Partial data scenario (handled gracefully)
3. **Prerequisite condition has wrong number of headers**: Structure change detected

### Getting Help

When reporting issues, include:
- The full error message
- The XML/HTML that caused the error (truncate if large)
- The value of `SIA_DEBUG` environment variable
- Any relevant logs from debug output

### Debug Session Example

```bash
$ export SIA_DEBUG=1
$ python -c "
from sia_scraper.parsers import scrape_info
xml = '''
<h2>TEST</h2>
<span class=\"detass-creditos\"><span>3</span></span>
<div class=\"af_showDetailHeader_content0\">
    <div class=\"af_panelGroupLayout\">
        <div><span>Profesor: </span><span>Test</span></div>
    </div>
</div>
'''
result = scrape_info(xml)
print(f'Groups: {len(result.groups)}')
"
```

Output:
```
DEBUG: Group 0 in course 'TEST' has 1 divs (expected 6 for full data). 
       Fields: ['Profesor: Test']
DEBUG: Spots info missing in group 0 of course 'TEST' (div count: 1)
Groups: 1
```

## Diagnostic Context in Errors

All error messages include:
- **Expected**: What the parser was looking for (element type, index, etc.)
- **Actual**: What was found (element count, content samples)
- **Context**: Course name, group index, field being extracted

This makes it easy to identify:
1. Which field failed to extract
2. Why it failed (structure change, missing data, etc.)
3. What data IS available (helpful for debugging)