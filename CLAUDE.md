# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`googler` is a command-line tool for Google Search (web, news, videos, site search) written as a single-file Python 3 executable. The project emphasizes being a standalone script with minimal dependencies that can run on headless servers and in constrained environments like Termux.

**Key Architecture Principles:**
- **Single-file executable**: The entire application is in the `googler` file (~3,900 lines)
- **Zero external dependencies**: Only uses Python standard library (readline is optional)
- **Self-contained HTML parsing**: Custom DOM parser and CSS selector engine instead of BeautifulSoup
- **Browser independence**: Can integrate with text-based browsers or GUI browsers

## Development Commands

### Running the Tool
```bash
# Run directly from source
./googler [options] [keywords]

# Example searches
./googler -n 5 python programming
./googler -N "latest news"           # News search
./googler -V "python tutorial"       # Video search
./googler -w stackoverflow.com python  # Site search
```

### Testing
```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest

# Run specific test
pytest tests/test_googler.py::test_default_search

# Run with custom options (if network constraints require proxy/IPv4)
export GOOGLER_PRESET_OPTIONS="--ipv4 --proxy localhost:8080"
pytest
```

### Code Quality
```bash
# The project uses flake8 for style checking (via CI)
# Style check is enforced through .github/workflows/stylecheck.yml
# Run manually if you have flake8 installed:
flake8 googler
```

### Installation/Packaging
```bash
# Install to /usr/local (requires sudo)
sudo make install

# Install to custom location
sudo make install PREFIX=/opt/local

# Uninstall
sudo make uninstall

# Disable self-upgrade (for packagers)
make disable-self-upgrade
```

## Code Architecture

### Core Components (all in single `googler` file)

**HTML Parsing Engine** (lines ~175-1435):
- `TrackedTextwrap`: Text wrapping with position tracking for zero-width sequences
- `Node`, `ElementNode`, `TextNode`: Custom DOM tree implementation
- `DOMBuilder(HTMLParser)`: HTML parser building DOM tree from Google's response
- `SelectorGroup`, `Selector`, `AttributeSelector`: CSS selector query engine
- This custom implementation replaces BeautifulSoup to maintain zero dependencies

**Google API Layer** (lines ~1673-2322):
- `HardenedHTTPSConnection(HTTPSConnection)`: HTTP client with TLS 1.2 enforcement and TCP optimizations
- `GoogleUrl`: URL construction and query parameter management for Google search
- `GoogleConnection`: HTTP connection manager, result fetching, JSON/HTML response handling
- `GoogleConnectionError`: Network error handling

**Result Parsing** (lines ~2322-2750):
- `GoogleParser`: Extracts search results from Google's HTML using custom CSS selectors
- `Result`: Search result data structure (title, URL, abstract, metadata)
- `Sitelink`: Sub-result links structure
- Handles web, news, and video search result formats

**Interactive Shell** (lines ~2785-3260):
- `GooglerCmd(cmd.Cmd)`: Interactive omniprompt with commands (n/p for navigation, o to open URLs, g for new search, etc.)
- Handles browser integration (text-based and GUI browsers)
- Clipboard integration (xsel, xclip, pbcopy, clip, tmux/screen buffers)
- Color output with customizable schemes

**CLI Interface** (lines ~3260-3858):
- `GooglerArgumentParser(argparse.ArgumentParser)`: Argument parsing
- `main()`: Entry point orchestrating search, display, and interactive mode
- Self-upgrade mechanism (can be disabled for packagers)

### Key Design Patterns

1. **Monolithic Single-File Design**: Everything in one file for portability and easy distribution
2. **Graceful Degradation**: Optional dependencies (readline, setproctitle) are handled with try/except
3. **Text Width Awareness**: CJK character handling via monkeypatching `textwrap` module
4. **Browser Agnostic**: Detects text browsers vs GUI browsers, suppresses output appropriately
5. **Platform Independence**: Handles Windows/Linux/macOS differences (clipboard, console modes, browsers)

### Data Flow

```
User Query → GoogleUrl (URL construction)
          → GoogleConnection (HTTP fetch)
          → GoogleParser (HTML parsing with custom DOM/selectors)
          → Result objects (structured data)
          → GooglerCmd or direct output (display/interaction)
```

## Testing Strategy

Tests are in `tests/test_googler.py` using pytest. The test suite:
- Uses `--json` output mode for programmatic result validation
- Respects `GOOGLER_PRESET_OPTIONS` environment variable for network constraints
- Tests multiple search modes (default, news, videos, site search)
- Tests various options (TLD, exact search, time ranges, date ranges)
- **Note**: Some tests may be skipped if Google's HTML format changes (e.g., `test_news_search`)

## Important Constraints

### For Packagers
- Run `make disable-self-upgrade` before packaging to disable self-update mechanism
- The tool expects to be installed via `make install` which handles man pages and documentation
- No configuration file by design - users should use shell aliases for persistent settings

### For Contributors
- **Maintain single-file structure**: All code stays in the `googler` file
- **Preserve zero dependencies**: Only use Python standard library
- **Support Python 3.6+**: Only latest patch of each minor version is supported
- **Handle CJK text**: Test with non-ASCII characters (Chinese, Japanese, Korean)
- **Test in text-mode**: Ensure output works without color (`-C` flag)
- **Cross-platform**: Test on Linux, macOS, Windows WSL if possible

## Special Environment Variables

- `BROWSER`: Set preferred browser (text-based: w3m, lynx, links, elinks)
- `GOOGLER_COLORS`: Six-letter color scheme string (e.g., `GKlgxy`)
- `DISABLE_URL_EXPANSION`: Show domain names only instead of full URLs
- `DISABLE_PROMPT_COLOR`: Force plain omniprompt (if color issues occur)
- `https_proxy`: HTTPS proxy for tunneling traffic
- `GOOGLER_PRESET_OPTIONS`: Used by test suite for network configuration

## Common Gotchas

1. **Fewer results than expected**: Google sometimes returns service results (YouTube, maps) that googler filters out - navigate to next page
2. **Connection issues**: Try `--notweak` to disable TCP optimizations and TLS 1.2 enforcement
3. **Language availability**: Google News not available for `dk`, `fi`, `is` languages - use `-l en`
4. **WSL browser integration**: Must set `BROWSER` to Windows executable path explicitly
