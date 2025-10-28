# Development Guide

This guide covers the simple development workflow for the wuying-agentbay-sdk project.

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Build package
make build
```

## Commands

### Development

```bash
# Install dependencies
make install

# Format code
make format

# Run tests
make test

# Clean build artifacts
make clean
```

### Publishing

```bash
# Build package (includes format + test + clean)
make build

# Publish to Test PyPI
make publish-test

# Publish to PyPI
make publish
```

## Workflow

### Daily Development

```bash
make format     # Format code
make test       # Run tests
```

### Release

```bash
# Update version in pyproject.toml manually, then:
make publish-test

# Test installation:
pip install -i https://test.pypi.org/simple/ wuying-agentbay-sdk
python -c "from agentbay import AgentBay; print('Import successful')"

# If testing successful:
make publish
```

## Best Practices

1. **Always test locally** before releasing
2. **Use Test PyPI** for verification
3. **Follow semantic versioning** strictly
4. **Keep release notes** updated
5. **Test installation** from fresh environment
6. **Coordinate major releases** with team

## Release Checklist

- [ ] All tests pass (`poetry run pytest`)
- [ ] Version number updated
- [ ] Package builds successfully
- [ ] Test PyPI upload works
- [ ] Installation from Test PyPI works
- [ ] Import verification passes
- [ ] Production PyPI upload successful
- [ ] Production installation verified
- [ ] Documentation updated (if needed)
- [ ] Release notes updated (if needed)

## Troubleshooting

1. **Poetry not found**: Install Poetry first
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -

   ```
2. **Configure PyPI credentials** (one-time setup):
   ```bash
   # For production PyPI
   poetry config pypi-token.pypi your-pypi-token
   
   # For Test PyPI (optional but recommended)
   poetry config pypi-token.test-pypi your-test-pypi-token
   ```

3. **Dependencies issues**: Reinstall dependencies
   ```bash
   make clean
   make install
   ``` 