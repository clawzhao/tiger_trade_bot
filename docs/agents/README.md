# Observability & Operations Agents

This directory documents the autonomous agents/components that provide operational capabilities for the Tiger Trade Bot. Each "agent" is a self-contained module responsible for a specific concern.

## Agents

- [Health Agent](health_agent.md) - FastAPI-based health check endpoints
- [Metrics Agent](metrics_agent.md) - Prometheus metrics exposition
- [Logger Agent](logger_agent.md) - Structured JSON logging
- [Database Agent](database_agent.md) - ORM models and migrations
- [Kubernetes Agent](k8s_agent.md) - Deployment manifests and autoscaling

These agents compose the Phase 8 Observability & Polish layer.

## Usage

See the main [README.md](../README.md) for configuration and deployment instructions. Each agent's document references the source code file and provides quick examples.

## Development

When modifying an agent, update both the implementation and its corresponding documentation in this folder.

## OpenClaw Agent Conventions

For general conventions about OpenClaw agents and skills, refer to the top-level `AGENTS.md` in the workspace root.
