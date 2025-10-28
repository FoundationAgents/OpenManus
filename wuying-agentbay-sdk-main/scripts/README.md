
# Scripts

This directory contains scripts for code quality checks and repository management.

## Repository Sync

### Handling Squash Merge Conflicts

When using GitHub's "Squash and Merge", the commit history diverges between internal (origin) and external (upstream) repositories. This causes conflicts when syncing back.

**Solution:** After a PR is squash-merged on GitHub, sync from upstream to origin:

```bash
./scripts/sync-from-github.sh
```

This script will:
- Fetch from both remotes
- Reset local main to match upstream/main
- Force push to origin with `--force-with-lease`

**Daily Workflow:**
1. Before starting work: `./scripts/sync-from-github.sh`
2. Develop on feature branches, not main
3. Push feature branch to both remotes
4. Create PR on GitHub, use "Squash and Merge"
5. After PR merges: `./scripts/sync-from-github.sh`

## Code Quality Check

## Usage

### Installing Git Hooks

 After cloning the repository, run the installation script (recommended):：
   ```bash
   chmod +x ./scripts/install-hooks.sh
   ./scripts/install-hooks.sh
   ```

### TypeScript Quality Check

To check TypeScript code quality:

```bash
cd typescript
chmod +x scripts/quality-check.sh
./scripts/quality-check.sh
```

This script will:
1. Run ESLint with auto-fix to fix linting issues
2. Run Prettier to format all TypeScript files
3. Run security scans to check for vulnerabilities
4. Run unit tests to ensure code correctness

Options:
- `--skip-tests`: Skip running tests
- `--skip-security`: Skip security checks
- `--skip-lint`: Skip linting and formatting

### Python Quality Check

To check Python code quality:

```bash
cd python
chmod +x scripts/quality-check.sh
./scripts/quality-check.sh
```

This script will:
1. Run flake8 to check for code issues
2. Run black to format Python files
3. Run bandit to scan for security vulnerabilities
4. Run pip-audit to check for dependency vulnerabilities
5. Run unit tests with coverage reporting

Options:
- `--skip-tests`: Skip running tests
- `--skip-security`: Skip security checks
- `--skip-lint`: Skip linting and formatting

### Golang Quality Check

To check Golang code quality:

```bash
cd golang
chmod +x scripts/quality-check.sh
./scripts/quality-check.sh
```

This script will:
1. Run gofmt and go fmt to format all Go files
2. Run golint to check for style issues
3. Run go vet to analyze code for potential problems
4. Run gosec for security vulnerabilities scanning
5. Run govulncheck for dependency vulnerabilities
6. Run unit tests with coverage

Options:
- `--skip-tests`: Skip running tests
- `--skip-security`: Skip security checks
- `--skip-lint`: Skip linting and formatting
- `--verbose`: Run tests in verbose mode

## CI Integration

These scripts are designed to be run locally before committing changes. They provide the same checks that are run in CI workflows, allowing developers to identify and fix issues before pushing code. It's recommended to run these scripts locally to ensure code meets the project's quality standards.

## Requirements

- For TypeScript: Node.js and npm with required dependencies
- For Python: Python with flake8, black, bandit, and pip-audit
- For Golang: Go with necessary tools (gofmt, golint, gosec, govulncheck)
