# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-10

### Added
- TILT=INCLUDE support per LM-63-2019 Annex F
- Type A and Type B photometry support
- File Generation Type support per LM-63-2019
- Comprehensive test suite (318 tests, 83% coverage)
- Division-by-zero protection and safer dict indexing
- Luminous opening support (`LuminousOpening`, `LuminousShape`)
- Dialux compatibility
- IES/LDT write support
- Automated beam angle detection
- LM-63-1995 format support
- Precision detection and preservation for file roundtrips

### Changed
- Lamp data migration into photometry objects
- API cleanup; modern OOP public interface (`IESFile`, `LDTFile`, `Photometry`)
- Export additional classes (`PhotometricType`, `LuminousOpening`, `LuminousShape`)

### Fixed
- Type B/A interpolation bugs
- Variable scope bug in HALF symmetry expansion
- AXIAL expansion bug
- Redundant angles for 360-degree lamps
- LDT file reader fixes

## [0.1.5] - 2025-11-24

### Changed
- Split up monolithic functions into smaller units
- Clean keywords for roundtrips

### Added
- Comparison support for photometric objects

## [0.1.2] - 2025-07-11

### Added
- Windows support

### Changed
- Update cache when scaling

### Fixed
- Indent bug in file parsing

## [0.0.9] - 2025-07-07

### Changed
- Overhaul to OOP architecture (replaced dict-based API with classes)

## [0.0.7] - 2024-10-29

### Added
- Convenience functions for common operations
- Tests and cleanup

### Fixed
- Scaling functions now account for lumen multiplier

## [0.0.6] - 2024-10-07

### Added
- New utility functions

### Fixed
- Suppress spurious warning messages
- File read bugs

## [0.0.4] - 2024-06-24

### Changed
- Renamed project from `ies_utils` to `photompy`
- Vectorized `get_intensity` (faster intensity lookups)
- Vectorized total optical power calculation (osluv solution)
- `plot_ies` accepts multiple datatypes; improved legends
- More flexible file reading interface (file or valdict)
- Polar plot improvements

### Fixed
- Windows carriage return issues in file writing
- Zero values for files where thetas 90-180 not given explicitly
- Candela multiplier and encoding bugs in write path

## [0.0.3] - 2024-04-24

### Added
- Polar plot visualization
- Header writing (without [MORE] feature)

### Fixed
- Lamp area unit conversion

## [0.0.2] - 2024-04-12

### Added
- IES file writing
- Keyword header parsing
- Total optical power calculation
- Lamp area calculation
- Interpolation function cleanup

### Fixed
- Candela multiplier handling
- Division-by-zero in interpolation

## [0.0.1] - 2023-12-13

### Added
- Initial release
- IES file reading

---

*Note: Entries through 0.1.5 were backfilled from commit history.*
