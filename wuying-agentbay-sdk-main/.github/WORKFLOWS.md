# GitHub Workflows for Wuying AgentBay SDK

This directory contains GitHub Actions workflows for automating testing and quality checks for the Wuying AgentBay SDK.

## Available Workflows

### PR Tests (`pr-tests.yml`)

Main workflow that runs on all pull requests to main branches. It:
1. Runs linting checks for all languages
2. Triggers language-specific test workflows

### Python Tests (`python-tests.yml`)

Runs Python unit and integration tests:
- Tests on multiple Python versions (3.10, 3.11, 3.12)
- Runs linting checks with flake8
- Automatically formats code with black
- Runs unit tests for all PRs
- Runs integration tests only if API key is available

### TypeScript Tests (`typescript-tests.yml`)

Runs TypeScript unit and integration tests:
- Tests on multiple Node.js versions (16, 18, 20)
- Lints code with ESLint and automatically fixes issues
- Automatically formats code with Prettier
- Runs unit tests for all PRs
- Generates code coverage reports
- Runs integration tests only if API key is available


## Configuration

### Setting Up API Keys for Integration Tests

To enable integration tests in CI, set up the following secret in your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add a secret with name `AGENTBAY_API_KEY` and your API key as value

### Customizing Workflow Triggers

Each workflow is configured to run on pull requests to main branches (`main`, `master`, `develop`). You can customize these triggers by editing the `on` section in each workflow file.

### Adding More Tests

To add more test types or modify existing ones:

1. Edit the relevant workflow file
2. Add new steps or modify existing ones
3. Commit and push your changes

## Best Practices

- Keep unit tests fast and independent of external services
- Use mocks for external dependencies in unit tests
- Reserve integration tests for verifying interactions with actual services
- Add appropriate test coverage for new features and bug fixes