# Python Version Upgrade Guide

## Current Status

⚠️ **Your local environment is using Python 3.9**, which is deprecated by AWS boto3 (support ends April 29, 2026).

**Required:** Python 3.11+ (matching the Lambda runtime)

## Why Upgrade?

1. **AWS boto3 Support**: boto3 will stop supporting Python 3.9 in April 2026
2. **Lambda Runtime Match**: Our Lambdas use Python 3.11, so local development should match
3. **Performance**: Python 3.11 is significantly faster than 3.9 (10-60% speedups)
4. **Features**: Better error messages, exception groups, tomllib, and more

## How to Upgrade (macOS)

### Option 1: Homebrew (Recommended)

```bash
# Install Python 3.11
brew install python@3.11

# Verify installation
python3.11 --version

# Make python3.11 the default python3
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify
python3 --version  # Should show 3.11.x
```

### Option 2: pyenv (For Managing Multiple Versions)

```bash
# Install pyenv
brew install pyenv

# Add to shell config
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init --path)"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Install Python 3.11
pyenv install 3.11.7

# Set as global default
pyenv global 3.11.7

# Verify
python3 --version  # Should show 3.11.7
```

### Option 3: Official Python Installer

1. Download Python 3.11 from https://www.python.org/downloads/
2. Run the installer
3. Add to PATH in your shell config

## After Upgrading

### 1. Reinstall Dependencies

```bash
# Remove old virtual environments
rm -rf venv .venv

# Create new virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Verify Python version in venv
python --version  # Should show 3.11.x

# Reinstall dependencies
pip install -r ingestion/requirements.txt
pip install -r requirements-dev.txt
```

### 2. Update Your IDE

**VSCode:**
1. Open Command Palette (Cmd+Shift+P)
2. Search "Python: Select Interpreter"
3. Choose Python 3.11

**PyCharm:**
1. Preferences → Project → Python Interpreter
2. Click gear icon → Add
3. Select Python 3.11

### 3. Verify Everything Works

```bash
# Run a simple test
python3 --version
python3 -c "import boto3; print(boto3.__version__)"

# Run the tests
make test

# Try local pipeline
make local-run
```

## Windows

### Using Python.org Installer

1. Download Python 3.11 from https://www.python.org/downloads/windows/
2. Run installer
3. ✅ Check "Add Python 3.11 to PATH"
4. Click "Install Now"
5. Verify: `python --version`

### Using Microsoft Store

```powershell
# Search for "Python 3.11" in Microsoft Store
# Click Install
```

## Linux

### Ubuntu/Debian

```bash
# Add deadsnakes PPA (for latest Python versions)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Make it the default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Verify
python3 --version
```

### Fedora/RHEL

```bash
sudo dnf install python3.11

# Verify
python3.11 --version
```

### Arch Linux

```bash
sudo pacman -S python

# Verify
python --version
```

## Troubleshooting

### "python3.11: command not found"

Your shell can't find Python 3.11. Check your PATH:

```bash
# Find where Python 3.11 is installed
which python3.11

# If found, add to PATH in ~/.zshrc or ~/.bashrc
export PATH="/path/to/python3.11/bin:$PATH"
```

### boto3 Still Shows Warning

You're still using the old Python 3.9 installation. Verify:

```bash
python3 --version
which python3

# If it shows 3.9, update your PATH or create an alias
alias python3=/opt/homebrew/bin/python3.11
```

### Virtual Environment Using Wrong Python

```bash
# Delete old venv
rm -rf venv

# Create new venv with specific Python version
python3.11 -m venv venv
source venv/bin/activate

# Verify
python --version  # Should be 3.11.x
```

### Package Installation Errors

Some packages may need recompilation for Python 3.11:

```bash
# Install build tools (macOS)
xcode-select --install

# Install build tools (Ubuntu)
sudo apt install build-essential python3.11-dev

# Reinstall packages
pip install --force-reinstall -r requirements.txt
```

## Updating CI/CD

If you have GitHub Actions or other CI/CD:

```yaml
# .github/workflows/ci.yml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'  # Update from 3.9 to 3.11
```

## Compatibility Notes

### Breaking Changes from 3.9 → 3.11

Most code should work without changes. Potential issues:

1. **Removed modules**: `distutils` (use `setuptools` instead)
2. **Deprecated warnings**: Some old syntax may warn
3. **Type hints**: Stricter type checking in some cases

### Testing Your Code

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linting
make lint

# Run type checking
make type-check
```

## Resources

- [Python 3.11 Release Notes](https://docs.python.org/3.11/whatsnew/3.11.html)
- [boto3 Python Support Policy](https://aws.amazon.com/blogs/developer/python-support-policy-updates-for-aws-sdks-and-tools/)
- [Python Download Page](https://www.python.org/downloads/)

## Summary

✅ **Recommended Setup:**
- Use Python 3.11.7+ (latest stable)
- Use virtual environments (`venv` or `pyenv-virtualenv`)
- Update your IDE to use Python 3.11
- Run `make test` to verify everything works

After upgrading, the boto3 deprecation warning will disappear!
