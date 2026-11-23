# GameVault Copilot Instructions

These instructions apply to all future development of this repository.

## Core principle

GameVault manages a real, manually maintained game collection across multiple genuine consoles. Data correctness and preservation of behavior already validated on real hardware take priority over architectural elegance, aggressive automation, or maximizing automatic match rates.

## Scope and change discipline

- Before changing code, analyze the relevant existing implementation and end-to-end data flow.
- Keep changes small, targeted, and limited to the requested task.
- Do not make incidental changes to working scanners, resolvers, API routes, or UI areas.
- Do not perform unsolicited refactoring, modularization, renaming, or formatting.
- Do not delete or move files unless the task explicitly requires it.
- Preserve existing behavior unless the change is explicitly part of the task.
- Do not treat the large size of `app/main.py` as an automatic reason to restructure it comprehensively.
- Do not introduce new frameworks or dependencies when the existing architecture and dependencies solve the problem adequately.
- Prefer established repository patterns and local APIs over introducing a new abstraction.
- Only broaden a change when the task or a safety constraint requires it.

## Project architecture

- GameVault is a FastAPI and SQLAlchemy application backed by PostgreSQL and deployed with Docker or Portainer.
- `app/main.py` contains the main data models, API routes, library cache, import/export behavior, metadata orchestration, and embedded frontend.
- Platform inventory implementations live under `app/providers/consoles/`.
- Metadata and title resolvers live under `app/providers/`.
- The frontend is embedded HTML, CSS, and JavaScript; do not introduce a separate frontend framework without an explicit requirement.
- Preserve the separation between library records, console inventory records, packages, physical ownership, and installed or hosted content.

## Metadata source-of-truth hierarchy

- Prefer reliable console-native data and identifiers.
- Prefer platform-specific resolvers and data sources over general metadata providers.
- Use general providers such as IGDB for enrichment and metadata resolution, not as unconditional truth.
- Do not overwrite established native values with weaker external matches.
- Title IDs, serials, and other stable native identifiers take priority over normalized title comparison or fuzzy matching.
- Preserve existing field source tracking and manual overrides. Manual values must not be silently replaced by catalog refreshes.
- Resolver names and canonical forms should be distinguishable from the original console title and should not be silently written over console facts.

## Resolver rules

- Identify PlayStation titles by Title ID or serial whenever possible.
- SerialStation is the preferred source for canonicalizing PlayStation identifiers.
- Resolve Xbox Classic and Xbox 360 titles through their Title IDs whenever possible.
- `app/providers/xbox_resolver.py` is the central platform-specific Xbox resolver.
- Prefer a successful ID-based resolution over title search or fuzzy matching.
- Preserve existing Nintendo and Retro matching behavior.
- Normalize region, language, revision, and dump additions for matching only. Do not merge different games or distinguishable versions without sufficient evidence.
- Preserve an existing confirmed provider ID and refresh by that ID before searching anew.
- Existing confirmed IGDB IDs take priority over title searches.
- Missing resolver data is legitimate. Fall back to console/native data rather than inventing a match.

## Conservative matching

- A false automatic match is worse than `review` or `not_found`.
- Do not lower match thresholds merely to increase the match rate.
- Uncertain matches must remain in `review` for manual verification.
- `not_found` is a legitimate result. Do not avoid it with guessed or weakly supported associations.
- Do not merge regional variants without sufficient evidence.
- Preserve existing result statistics, including `checked`, `resolved`, `applied`, `review`, `not_found`, and `errors`, wherever such diagnostics are relevant.
- Keep original titles, platform editions, and separate regional or media variants intact unless a requested merge has a clear identity match.
- Retro or No-Intro-style variants require conservative handling and platform constraints.
- Existing normal acceptance thresholds must not be relaxed without explicitly requested and reviewed evidence.

## Content classification

- Distinguish base games, updates, patches, DLC, homebrew, system software, system entries, tools, emulators, fan ports, physical ownership, digital ownership, and currently installed content.
- Do not merge different content types merely because names or identifiers look similar.
- Read `MATCHING_RULES.md` before changing matching, classification, imports, or resolvers.
- Preserve all documented platform-specific and special cases.
- Preserve the independence of platform edition, original platform, physical ownership, hosted availability, and installation state.
- RetroArch ROM variants remain associated with their normalized platform and title while retaining separate region, language, revision, and dump metadata.
- PS Vita PSPemu and hosted RetroArch content retain their documented host/runtime and library-platform distinctions.

## Scanner safety

- Treat consoles and remote filesystems as read-only by default.
- Never modify or delete files on a console.
- Do not change proven paths, file formats, database parsing, or detection rules based only on an unconfirmed assumption.
- Prefer real console data and native identifiers over inferred metadata.
- Changes to one platform scanner must not alter another platform scanner unexpectedly.
- Preserve scanner diagnostics and the ability to distinguish games, updates, DLC, applications, and homebrew.
- Preserve manual matching overrides from prior scans when the task is not explicitly replacing that behavior.
- Do not claim real-hardware validation based only on code analysis or local tests.

## Data safety and compatibility

- Never perform destructive database operations without an explicit request.
- No `DROP TABLE`, bulk `DELETE`, reset, or clearing of persistent application data.
- Treat `/data`, covers, imports, packages, console credentials, and database records as persistent user data.
- Database model changes must remain compatible with existing installations and records.
- Follow the project's runtime schema initialization and compatibility procedure.
- Do not delete caches or persistent files unless the task explicitly requires it.
- Preserve existing package, import, export, and JSON compatibility unless a task explicitly changes the format.
- Avoid silent migrations or destructive compatibility fallbacks.

## Frontend behavior

- Preserve the existing desktop library behavior and responsive mobile behavior.
- Keep the complete library available client-side after the initial load.
- Do not add pagination, infinite-scroll incremental loading, or lazy library-entry loading unless explicitly required.
- Prioritize smooth scrolling through a fully loaded library over a faster first screen that renders only a page.
- Preserve existing platform filtering, manufacturer data, metadata states, platform styling, and selection behavior.
- Do not introduce React, Vue, or another frontend framework unless explicitly requested.
- Consider the library read cache and every invalidation or rebuild path when changing data mutations or API responses.
- Database mutations that change the library response must preserve cache invalidation and direct-fallback behavior.
- Performance changes must not silently alter the semantic API response.

## Cache and API behavior

- Preserve the precomputed full-library read cache and its fallback behavior.
- Rebuild or invalidate cache data after database mutations that affect API library output.
- Do not return an empty or misleading library payload merely because a cache rebuild failed.
- Preserve the direct PostgreSQL fallback and cache diagnostics where they exist.
- Keep API response fields and existing route behavior stable unless the task explicitly changes the contract.
- Never hide failures behind an empty result or a broad silent fallback.

## Git, versioning, and releases

- Do not create commits, push changes, create tags or releases, or merge branches without explicit instruction.
- Do not change version numbers automatically.
- Never use destructive Git commands such as `git reset --hard`, `git clean`, force-push, or discarding local changes without explicit instruction.
- Respect existing changes in the worktree, including changes not created by Copilot.
- Change only files required for the explicitly requested task.
- For an explicitly requested release, keep version references, README documentation, container builds, and release documentation consistent.
- Do not amend, squash, or rewrite history unless explicitly requested.

## Validation and reporting

- After changes, validate at least syntax, imports, and directly affected workflows when the environment permits.
- Add focused tests for new independently testable rules without creating unnecessary test infrastructure.
- Clearly distinguish static analysis, locally executed tests, and validation on real hardware.
- Do not hide errors behind silent broad fallbacks.
- After every implementation task, report:
  - which files changed,
  - what behavior changed,
  - which checks were executed,
  - which checks were not possible,
  - the next useful manual or hardware test.
- Do not claim that a task is fully validated while required real-hardware validation remains unavailable.
- If a change could affect scanning or matching, prefer a targeted fixture, diagnostic test, or dry-run over broad assumptions.

## Project documentation authority

- `MATCHING_RULES.md` is authoritative for matching, classification, and special-platform rules.
- `BACKLOG.md` records possible future work but is not an instruction to implement it automatically.
- `README.md` describes documented product behavior and user-facing information.
- The current code represents the actual implementation state.
- If documentation and code appear inconsistent, do not perform comprehensive unsolicited cleanup.
- Report the inconsistency and limit changes to the explicitly requested area.

## Working method

1. Read the relevant code, existing tests or nearby call sites, and the applicable project documentation before editing.
2. State or internally verify a local hypothesis and a cheap discriminating check.
3. Make the smallest implementation that tests or satisfies that hypothesis.
4. Run the narrowest relevant validation immediately after the first substantive edit.
5. Extend validation only when the touched behavior requires it.
6. Preserve existing behavior outside the requested scope.
7. Finish with an accurate status and a clear account of remaining validation gaps.
