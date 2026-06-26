# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0rc0] - 2026-06-26

### Added
- AsrEngine Protocol for ASR engine plugins
- SenseVoiceEngine implementing AsrEngine Protocol
- PluginRegistry ASR engine support
- --asr-engine CLI option
- --list-plugins shows ASR engines

## [2.0.0b0] - 2026-06-26

### Added
- AntiCrawlerHandler Protocol for anti-crawler plugins
- BilibiliAntiCrawlerHandler for B站 412 bypass
- PluginRegistry anticrawler support
- --list-plugins shows anticrawler handlers

## [1.5.0] - 2026-06-26

### Bug Fixes
- Fix integration test Unicode errors

### Features
- Add configurable network timeout
- Add TTL support to cache
- Add batch progress indicator