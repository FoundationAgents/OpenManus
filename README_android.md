# Running OpenManus on Android

This guide explains how to install and run OpenManus on Android devices using **Termux** and a **PRoot Linux environment**. Since Android does not natively support Docker, OpenManus includes a built-in **Local Subprocess Sandbox** fallback and automatic Chromium configuration to ensure all tools (including bash, python, browser automation, and chart visualization) run flawlessly on Android.

---

## Prerequisite: Installing Termux

1. Download and install **Termux** on your Android device:
   - **Highly Recommended:** Download from [F-Droid](https://f-droid.org/en/packages/com.termux/) or [GitHub Releases](https://github.com/termux/termux-app/releases).
   - *Do not download Termux from the Google Play Store*, as that version is deprecated and outdated.

2. Open Termux and grant storage permissions:
   ```bash
   termux-setup-storage
   ```

---

## One-Line Automated Installation

Simply run the following command in your Termux terminal to automatically set up PRoot, install Ubuntu, set up all compiler stacks, Chromium, Node.js, and configure your Python environment:

```bash
git clone https://github.com/whoami22888/OpenManus.git
cd OpenManus
chmod +x setup_android.sh
./setup_android.sh
```

### What the installer does:
- **Outside PRoot (Termux):** Checks for and installs `proot-distro` and `ubuntu` if they are not already installed, then launches the installer inside the PRoot environment.
- **Inside PRoot (Ubuntu):**
  - Installs the C++ compiler stack (`build-essential`), `git`, and developer libraries.
  - Installs Rust and Cargo (`rustc`/`cargo`) to compile native arm64/aarch64 Python wheels.
  - Installs Node.js and NPM to support the React-based **Chart Visualization** feature.
  - Installs system-packaged **Chromium** for browser automation.
  - Sets up a Python virtual environment and installs all dependencies from `requirements.txt`.
  - Configures OpenManus to automatically run Chromium with sandbox-disabled flags (`--no-sandbox`, `--disable-setuid-sandbox`) required inside PRoot containerized environments.

---

## How to Run OpenManus on Android

After installation is complete, you can start OpenManus from your Termux terminal anytime using the following command:

```bash
proot-distro login ubuntu --shared-tmp -- bash -c "cd \"\$(pwd)\" && ./run_android.sh"
```

*(Ensure you run this command from the cloned `OpenManus` directory inside Termux so that `$(pwd)` resolves correctly).*

### Configuration
Make sure to add your LLM API keys in `config/config.toml` (copy from `config/config.example.toml` if it's your first time):
```bash
cp config/config.example.toml config/config.toml
nano config/config.toml
```

---

## Core Capabilities Supported on Android

- **Agent Sandbox (Local Subprocess Fallback):** When Docker is unavailable on Android, OpenManus seamlessly falls back to a highly isolated local directory sandbox (`workspace/sandbox`), allowing the agent to write files, run Python scripts, and run bash commands locally.
- **Browser Automation (`browser_use`):** Playwright uses the system-installed Chromium binary with no extra configuration needed.
- **Chart Visualization:** Supports full local node-based visual chart generation.
