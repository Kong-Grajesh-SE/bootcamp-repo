# Table of Contents

- [Table of Contents](#table-of-contents)
  - [v0.1.0](#v010)
  - [v0.1.1](#v011)
  - [v0.1.2](#v012)
  - [v0.1.3](#v013)
  - [v0.1.4](#v014)
  - [v0.2.0](#v020)

## [v0.1.0]

> Release date: 2025/03/24

### Summary

First version released.

## [v0.1.1]

> Release date: 2025/04/14

### Summary

Updated Dockfile: pre-downloads `en_core_web_lg` NLP model

## [v0.1.2]

> Release date: 2025/04/16

### Summary

1. Updated Dockfile: supported building docker images containing different NLP models
2. Fixed an issue where UTF-8 string was not handled correctly 

## [v0.1.3]

> Release date: 2025/07/31

### Summary

1. Fixed an issue where a runtime error would be thrown when using stanza NLP engine.
2. Fixed an issue where a runtime error could occur when initializing a Faker instance with some certain languages due to a lack of support for those ones.

## [v0.1.4]

> Release date: 2025/08/06

### Summary

1. Fixed an issue where a runtime error would be thrown when there is no corresponding function to generate synthetic content for particular entity.

## [v0.2.0]

> Release date: 2026/02/25

### Summary

1. bump python to 3.12.
2. bump pytorch to 2.91.
3. bump flask to 3.1.3.
4. bump Faker to 40.0.
5. bump presidio to 2.2.361
6. bump pyyaml to 6.0.3
7. improvement of pii recoginition.
   [#25](https://github.com/Kong/ai-pii-service/pull/25)
8. fixed an issue where credential entity recognition would be unexpectly applied even if it was not specified in requests.
   [#24](https://github.com/Kong/ai-pii-service/pull/24)

[v0.1.0]: https://github.com/Kong/ai-pii-service/compare/9e0317...v0.1.0
[v0.1.1]: https://github.com/Kong/ai-pii-service/compare/v0.1.0...v0.1.1
[v0.1.2]: https://github.com/Kong/ai-pii-service/compare/v0.1.1...v0.1.2
[v0.1.3]: https://github.com/Kong/ai-pii-service/compare/v0.1.2...v0.1.3
[v0.1.4]: https://github.com/Kong/ai-pii-service/compare/v0.1.3...v0.1.4
[v0.2.0]: https://github.com/Kong/ai-pii-service/compare/v0.1.4...v0.2.0
