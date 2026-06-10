# Table of Contents

- [Table of Contents](#table-of-contents)
  - [v0.0.1](#v001)
  - [v0.0.2](#v002)
  - [v0.0.3](#v003)
  - [v0.0.4](#v004)

## [v0.0.1]

> Release date: 2025/06/04

### Summary

Initial release. Set up the project structure, release pipeline (Cloudsmith, Docker), and CI workflows.

### Changes

- Initial commit with project scaffolding
- Fix whitespace/formatting issues
- Bump NVIDIA base image

## [v0.0.2]

> Release date: 2025/06/04

### Summary

Removed unused libraries to reduce image size.

### Changes

- Remove unused libs (multiple cleanup passes)

## [v0.0.3]

> Release date: 2025/07/09

### Summary

Fixed fallback behavior for unsupported models.

### Changes

- Fix handling of unlisted/unsupported models
- Add logging for model fallback paths

## [v0.0.4]

### Summary

Docker image improvements: non-root user, pre-downloaded tiktoken encodings, LLMLingua installed via Poetry, and additional disk space freed in the release workflow.

### Changes

- Pre-download tiktoken encodings in Dockerfile
- Install LLMLingua with Poetry instead of pip; move tiktoken cache download after `poetry install`
- Build Docker image as non-root user
- Free up additional disk space in the release workflow for Docker image build


[v0.0.1]: https://github.com/Kong/ai-compress-service/compare/2af1fb8...v0.0.1
[v0.0.2]: https://github.com/Kong/ai-compress-service/compare/v0.0.1...v0.0.2
[v0.0.3]: https://github.com/Kong/ai-compress-service/compare/v0.0.2...v0.0.3
[v0.0.4]: https://github.com/Kong/ai-compress-service/compare/v0.0.3...v0.0.4
