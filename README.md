# Dynatrace Dashboard Factory

Dynatrace Dashboard Factory is a reusable, AI-assisted, GitOps framework for generating, validating, and deploying standardized Dynatrace dashboards from application requirements.

ParcelPlus is the first reference application. The framework is intentionally application-agnostic: another application can onboard by supplying an application manifest and dashboard request without changing the core generator or Terraform renderer.

## Why this exists

Teams often build Dynatrace dashboards manually. That creates duplicated effort, inconsistent layouts, weak governance, and difficult promotion between environments.

This framework turns the dashboard lifecycle into:

```text
Application manifest + dashboard request
        ↓
AI or template generator
        ↓
Validated dashboard specification
        ↓
Deterministic Terraform rendering
        ↓
GitHub pull request and plan
        ↓
GitHub Actions deployment to Dynatrace
```

The AI is responsible for interpreting intent and selecting content. It does not receive permission to deploy directly. Validation and Terraform remain the deployment boundary.

## Current status

This repository contains the framework foundation:

- Application onboarding manifest schema
- Dashboard request schema
- Deterministic template generator
- Terraform renderer for `dynatrace_json_dashboard`
- ParcelPlus example manifest and payment dashboard request
- CLI validation, generation, and rendering commands
- GitHub Actions validation workflow

The AI provider adapter, Dynatrace post-deployment verification, SLO rendering, and production promotion workflow are the next implementation increments.

## Repository structure

```text
src/dashboard_factory/       Framework CLI and reusable modules
schemas/                     Input and output contracts
examples/parcelplus/         First application onboarding package
templates/                   Approved dashboard patterns
generated/                   Local generated artifacts; ignored by Git
terraform/                   Provider and deployment examples
.github/workflows/           GitHub Actions automation
```

## Requirements

- Python 3.9+
- Terraform 1.5+
- A Dynatrace SaaS environment
- GitHub repository and GitHub Actions

Install the local framework:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Generate a dashboard specification

Validate the ParcelPlus onboarding inputs:

```bash
dashboard-factory validate \
  --application examples/parcelplus/application.yaml \
  --request examples/parcelplus/requests/payment-journey.yaml
```

Generate a specification:

```bash
dashboard-factory generate \
  --application examples/parcelplus/application.yaml \
  --request examples/parcelplus/requests/payment-journey.yaml \
  --output generated/payment-journey.yaml
```

Render Terraform:

```bash
dashboard-factory render \
  --spec generated/payment-journey.yaml \
  --output generated/payment-journey.tf
```

The generated Terraform is reviewed and deployed by GitHub Actions. It should not be applied manually from a developer laptop for shared environments.

## Application onboarding contract

Every onboarded application supplies an `application.yaml` containing:

- Application name and owner
- Service names and technologies
- Business metrics
- Business journeys
- Initial SLO candidates

Every dashboard request contains:

- Dashboard name
- Audience
- Services to include
- Metrics to visualize
- Tags and business context

This contract is what makes the framework reusable for applications other than ParcelPlus.

## Terraform provider

The framework targets the Dynatrace Terraform provider:

```hcl
terraform {
  required_providers {
    dynatrace = {
      source  = "dynatrace-oss/dynatrace"
      version = "~> 1.104"
    }
  }
}

provider "dynatrace" {}
```

Configure the provider through environment variables in GitHub Actions:

```text
DYNATRACE_ENV_URL
DYNATRACE_API_TOKEN
```

For the first dashboard MVP, use a token with the least permissions required by `dynatrace_json_dashboard`: `ReadConfig` and `WriteConfig`. Add SLO permissions only when SLO resources are enabled.

## GitHub Actions lifecycle

The intended workflow is:

```text
Pull request
  → validate manifest and request
  → generate specification
  → render Terraform
  → terraform fmt and validate
  → terraform plan
  → review and merge
  → apply to Demo environment
  → verify dashboard and data
  → promote or revert
```

Use GitHub Environments for `demo`, `uat`, and `production`. Keep the Dynatrace token in environment secrets and require approval for production.

## Design principles

1. AI generates a specification; deterministic code renders Terraform.
2. No AI output is applied without schema validation and Terraform plan review.
3. Standards are encoded in schemas and templates, not only in prompts.
4. Application telemetry and dashboard configuration remain separate repositories or concerns.
5. Git is the source of truth and rollback mechanism.
6. Environment URLs and secrets never appear in generated dashboard files.

## Roadmap

1. Add the AI adapter interface and structured-output prompt.
2. Add dashboard specification schema validation.
3. Add SLO and alert Terraform renderers.
4. Add Dynatrace post-deployment verification.
5. Add GitHub Actions plan/apply workflows.
6. Add dashboard preview and Terraform plan summary to pull requests.
7. Add drift detection and recommendations as optional features.
