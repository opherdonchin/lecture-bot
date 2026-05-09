# Documentation Map

This directory now keeps only current operating and design references. The older audits, one-off plans, prompt worklogs, restart notes, and duplicate rubric prompt were removed so the docs folder can be read from top to bottom without archaeology.

## Start Here

- [`../README.md`](../README.md) - current project overview, commands, routes, environment variables, lecture-package flow, runtime files, and test coverage.
- [`implementation_spec.md`](implementation_spec.md) - current architecture and behavior spec.
- [`deployment_ubuntu.md`](deployment_ubuntu.md) - Ubuntu deployment runbook for the `/stats` and `/stats-admin` production shape.
- [`admin_session_exports_plan.md`](admin_session_exports_plan.md) - implementation plan for admin-side session filtering and multi-session exports.

## Tutor And Grading Design

- [`grading_policy.md`](grading_policy.md) - grading calibration, mastery scale, and backend weighting policy.
- [`tutor_specification.md`](tutor_specification.md) - pedagogical specification for the runtime tutor.
- [`tutor_specification_contract.md`](tutor_specification_contract.md) - authoring contract for tutor specifications.
- [`backend_tutor_contract.md`](backend_tutor_contract.md) - current runtime contract between backend, prompt, and state sanitizer.
- [`error_policy.md`](error_policy.md) - current error-handling and fallback policy.

## Prompt Sources

Prompt files live in [`../prompts`](../prompts), not in this directory.

- Runtime tutor prompt: [`../prompts/tutor_prompt.md`](../prompts/tutor_prompt.md)
- Runtime private artifact schema: [`../prompts/tutor_prompt_private_artifact_schema.json`](../prompts/tutor_prompt_private_artifact_schema.json)
- Tutor prompt generator: [`../prompts/tutor_generator_prompt.md`](../prompts/tutor_generator_prompt.md)
- Minutes generation prompt: [`../prompts/minutes_generation_prompt.md`](../prompts/minutes_generation_prompt.md)
- Rubric generation prompt: [`../prompts/master_rubric_generation_prompt.md`](../prompts/master_rubric_generation_prompt.md)
- Staged log analysis prompt: [`../prompts/log_analysis_prompt.md`](../prompts/log_analysis_prompt.md)
- Student comment analysis prompt: [`../prompts/comment_analysis_prompt.md`](../prompts/comment_analysis_prompt.md)

Generated tutor prompts may have an accompanying `*_private_artifact_schema.json` file. At session creation, the backend snapshots the active schema into the session row; prompt history and schema history are not stored.

The legacy classifier prompts under `prompts/old/` are retained only as prompt history and are not part of the current runtime.
