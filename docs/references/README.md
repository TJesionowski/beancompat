# Reference Index

Primary sources and existing resources that inform beancompat's design and test coverage.

## Community discussion

- **Spec process thread** — The discussion that demonstrated normative spec work won't happen top-down.
  https://groups.google.com/g/beancount/c/EOoD755XNP0

## Existing test resources

- **Simon Guest's extracted parser tests** — Language-independent test cases extracted from OG beancount. Input as standalone .beancount files, expected output as text protobuf. Covers parsing, not semantics.
  https://github.com/tesujimath/beancount-parser-lima/tree/main/test-cases

- **Simon Guest's booking tests** — Rust booking tests adapted from Martin's originals.
  https://github.com/tesujimath/limabean/blob/main/rust/limabean-booking/src/tests/booking.rs

- **rustledger specs** — AI-assisted spec documents for beancount format.
  - Format spec: https://github.com/rustledger/pta-standards/tree/main/formats/beancount
  - Spec docs: https://github.com/rustledger/rustledger/tree/main/spec

- **pta-generator** — Cross-PTA-app test data generator.
  https://github.com/tackler-ng/pta-generator

## Implementation documentation

- **Martin's vNext document** — Describes planned changes for beancount v3. TurboBean implements some of these, creating known divergence points.
  https://beancount.github.io/docs/beancount_v3.html

- **plaintextaccounting.org references** — Feature comparison and quick reference across PTA tools.
  - Features: https://plaintextaccounting.org/#features
  - Quick ref: https://plaintextaccounting.org/quickref

## Implementations in scope

| Implementation | Language | Author | Notes |
|---|---|---|---|
| beancount | Python | Martin Blais | Reference implementation (v3) |
| limabean | Rust | Simon Guest | Aims for compatibility |
| TurboBean | Zig | Moritz Drexl | https://github.com/themoritz/turbobean; vNext inventory divergence; no structured output yet (protobuf planned but unimplemented) |
| rustledger | Rust | AI-assisted | Includes spec documents; crates published at v0.14.0; CAP_PARSE adapter wired up |
