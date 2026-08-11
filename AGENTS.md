# AGENTS.md: AI Assistant & Developer Guidelines for ais-area-notice

This document provides guidelines, conventions, and architectural context for AI
assistants and developers contributing to `ais-area-notice`.

## 1. Project Overview & Architecture

`ais-area-notice` is a Python reference implementation for encoding, decoding,
and manipulating Automatic Identification System (AIS) Application-Specific
Binary Broadcast Messages (BBMs) as defined in the IMO SN.1/Circ.289
specification and related USCG variants (8:366:22 and 8:367:22).

- **Supported Messages**:
  - **IMO SN.1/Circ.289 Area Notice (BBM 8:1:22)**: Encodes spatial shapes
    (circles, rectangles, sectors, polylines, polygons, free text) into binary
    broadcast messages with GeoJSON and KML visualization capabilities.
  - **IMO SN.1/Circ.289 Environmental Report (BBM 8:1:26)**: Handles sensor
    reports including site location, station ID, wind, water level,
    2D/3D/horizontal current flow, sea state, salinity, weather, and air gap.
  - **IMO SN.1/Circ.289 Meteorological and Hydrographic Data (BBM 8:1:31)**:
    Broad-spectrum weather and oceanographic data transmission.
  - **USCG Area Notices (BBM 8:366:22 & 8:367:22)**: USCG specific 96-bit and
    93-bit subarea message variants.
- **Python Target**: Requires Python `>=3.14`. Employs modern Python features
  including type annotations (`Self`, `Sequence`), advanced f-strings, and clean
  modular structures.

## 2. Repository & File Layout

The project repository is structured as a modern Python package:

- **`ais_area_notice/`**: Core package directory.
  - `__init__.py`: Package initialization and version definition (`0.5`).
  - `imo_001_22_area_notice.py`: IMO SN.1/Circ.289 Area Notice (8:1:22)
    implementation, NMEA regex parsing, KML & GeoJSON export.
  - `imo_001_26_environment.py`: IMO Environmental Message (8:1:26) &
    constituent `SensorReport` classes.
  - `imo_001_31_met_hydro.py`: IMO Meteorological and Hydrographic Data message
    (8:1:31).
  - `m366_22.py`: USCG specific Area Notice Version 23 (8:366:22).
  - `m367_22.py`: USCG specific Area Notice (8:367:22).
  - `binary.py`: 6-bit NMEA VDM ASCII armoring, BitVector payload
    packing/unpacking helpers.
  - `ais_string.py`: 6-bit AIS character string encoding, decoding, stripping,
    and padding.
  - `an_util.py`: `BuildBits` and `DecodeBits` bitstream bit-packing helper
    classes.
  - `BitVector.py`: Packed bit array data structure and bitwise manipulation
    utilities.
  - `build_samples.py`: Helper script to generate standard NMEA test datasets.
- **`tests/`**: Automated test suite executed via `pytest`.
  - `ais_string_test.py`: Unit tests for AIS 6-bit string operations.
  - `binary_test.py`: Unit tests for 6-bit VDM character armoring and bitvector
    math.
  - `imo_001_22_area_notice_test.py`: Tests for Area Notice (8:1:22) encoding,
    decoding, rotations, GeoJSON, and KML output.
  - `imo_001_26_environment_test.py`: Unit and fuzz tests for Environmental
    reports (8:1:26).
  - `imo_001_31_met_hydro_test.py`: Tests for Met/Hydro messages (8:1:31).
  - `m366_22_test.py` & `m367_22_test.py`: Tests for USCG Area Notice variants.
  - `an_util_test.py`: Utility test placeholder.
- **`docs/`**: Reference specification PDFs (IMO SN.1/Circ.289, USCG Area Notice
  v23, USCG Environmental Message v15).
- **`pyproject.toml`**: Modern project configuration defining package metadata,
  build system (`setuptools`), and dependency groups (`pytest`, `uv`).
- **`Makefile`**: Command shortcuts for testing, building distributions
  (`sdist`), and sample generation.
- **`README.md` & `LICENSE`**: Project documentation and Apache-2.0 license
  file.

## 3. Structure & API Summary

The core functionality of `ais-area-notice` is encoding binary payload
structures into NMEA 0183 `!AIVDM` / `!AIVDO` sentences and decoding incoming
NMEA sentences back into rich Python objects.

### Internal Storage & Representation

- **`BBM` Base Class**: Common base class for Broadcast Binary Messages managing
  message ID (8), DAC (Designated Area Code), FI (Function Identifier), MMSI,
  and sentence sequence generation (`get_aivdm`).
- **Bit Manipulation**: Messages build bitstreams using `BitVector` objects
  combined with 6-bit NMEA ASCII armoring (`ais_area_notice.binary`).
- **Bitstream Streamers**: `BuildBits` and `DecodeBits` in `an_util.py` provide
  sequential bit packing and unpacking for integer, signed integer, and text
  fields.

### Constructors & Data Input (`__init__`)

- **Message Objects** (`AreaNotice`, `Environment`, `MetHydro31`): Can be
  constructed by:
  1. Specifying field parameters directly (`area_type`, `when`, `duration_min`,
     `link_id`, `source_mmsi`).
  1. Passing raw `BitVector` objects via `bits=...`.
  1. Passing lists of NMEA 0183 sentence strings via `nmea_strings=[...]`.
- **Subareas** (`AreaNoticeCirclePt`, `AreaNoticeRectangle`, `AreaNoticeSector`,
  `AreaNoticePolyline`, `AreaNoticePolygon`, `AreaNoticeFreeText`): Instantiated
  with spatial coordinates and scales, or unpacked from binary bit
  representations.
- **Sensor Reports** (`SensorReportLocation`, `SensorReportWind`,
  `SensorReportWaterLevel`, `SensorReportCurrent2d`, `SensorReportCurrent3d`,
  `SensorReportCurrentHorz`, `SensorReportSeaState`, `SensorReportSalinity`,
  `SensorReportWeather`, `SensorReportAirGap`): Constructed with domain specific
  sensor fields or unpacked from `bits`.

### Core Operations & Methods

- **`add_subarea(subarea)` / `add_sensor_report(report)`**: Appends subareas or
  sensor reports to messages.
- **`get_bits(include_bin_hdr=True, include_dac_fi=True)`**: Serializes the
  message into a packed `BitVector`.
- **`get_aivdm(...)`**: Generates ordered, checksummed NMEA `!AIVDM` / `!AIVDO`
  sentences ready for AIS broadcast.
- **`__geo_interface__` & `kml()`**: Export `AreaNotice` objects to GeoJSON
  dictionaries and KML markup strings.

## 4. Development Environment & Tooling

We use modern Python tooling for dependency management, building, linting, and
static analysis:

- **Dependency Management (`uv`)**: Use `uv` for all virtual environments and
  package installations.
  ```bash
  uv sync
  ```
- **Linting & Formatting (`ruff`, `pylint`)**: Enforces code style, import
  sorting, formatting, and code quality checks.
  ```bash
  uv run ruff check --fix
  uv run ruff format
  uv run pylint ais_area_notice tests
  ```
- **Static Type Checking (`ty`, `mypy`, `pyrefly`, & `pyright`)**: Enforces
  strict type annotations across all modules.
  ```bash
  uv run ty check
  uv run mypy .
  uv run pyrefly check
  uv run pyright
  ```
- **Markdown Formatting (`mdformat`)**: Enforces 80-column line wrapping and
  standard GFM formatting across Markdown files.
  ```bash
  uv run mdformat --wrap 80 .
  ```
- **Spelling (`codespell`)**: Checks for typos and misspelled identifiers.
  ```bash
  uv run codespell
  ```
- **Static Analysis & Security Scanning (`semgrep`, `bandit`)**: Enforces static
  analysis and security rules.
  ```bash
  uv run semgrep scan --config p/default
  uv run bandit -c pyproject.toml -r ais_area_notice tests
  ```
- **Pre-commit Hooks**: Enforces standards prior to commits. Must be installed
  when setting up a workspace:
  ```bash
  uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
  uv run pre-commit run --all-files
  ```

## 5. Testing Conventions & Standards

All testing is orchestrated via `pytest`.

- **Running Tests**:
  ```bash
  uv run pytest
  ```
- **Best Pytest Form**:
  - **CRITICAL RULE**: Write all new and refactored tests in the **best modern
    `pytest` form** using standard Python `assert` statements.
  - **Do NOT use legacy `unittest` style** assertions (`self.assertEqual`,
    `self.assertTrue`, `self.assertRaises`, etc.) or inherit from
    `unittest.TestCase`.
  - Use `pytest.raises(...)` for expected exceptions.
  - Use `pytest.approx(...)` for floating-point comparisons.
  - Use `@pytest.mark.parametrize` to cleanly test multiple input combinations
    without repetitive boilerplate.
  - Use standard pytest fixtures (like `tmp_path` for temporary files) instead
    of manual cleanup or `tempfile`.

## 6. Code & Docstring Style

- **Docstrings**:
  - **CRITICAL RULE**: All module, class, method, and function docstrings must
    strictly follow **Standard Google Python Docstring Style**.
  - Include clearly formatted `Args:`, `Returns:`, `Raises:`, `Yields:`, and
    `Attributes:` sections as applicable.
  - Avoid unstructured, verbose, or legacy docstring formatting.
- **String Formatting**:
  - Always use modern Python **f-strings** (`f"Value: {val}"`) for string
    concatenation and formatting. Never use legacy `%` formatting or
    `.format()`.
- **Type Annotations**:
  - Provide precise, tight type annotations for all function signatures and
    return types.
  - Avoid generic `Any` types; prefer specific types such as `Sequence[int]`,
    `Buffer`, `Self`, or `Literal`.
  - Avoid explicit `Union`/`Optional` types. Use '|'.

## 7. Version Control & Commit Messages

- **Feature Branches**:
  - **CRITICAL RULE**: All code changes and refactoring work MUST be performed
    on dedicated git feature branches (e.g., `git checkout -b <branch-name>`).
  - Never make direct commits on the `main` branch.
- **Code Review**:
  - Always do a code review before committing. In addition to finding and
    suggesting fixes to issues, try to create 1-3 suggestions for improvement to
    the code based on the current changes.
  - See if there needs to be any changes to `AGENTS.md` based on the current
    changes and propose improvements.
- **Conventional Commits**:
  - All git commit messages MUST adhere to the **Conventional Commits**
    specification (`<type>(<optional scope>): <subject>`).
  - Examples:
    - `feat(dunder): enable modern __add__ and __iadd__ support`
    - `refactor(tests): switch test_init.py from unittest to pytest`
    - `chore(license): replace __copyright__ variable with SPDX header`
    - `docs: import legacy manuals into docs/ directory`
- **NO Tag or Conversation ID Entries**:
  - **CRITICAL RULE**: Commit messages must **NEVER** contain `TAG=` or `CONV=`
    lines or entries. These are reserved for internal Piper/CL tools and must be
    omitted from all git commits in this repository.
