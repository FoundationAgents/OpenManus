# OpenManus Desktop App Packaging

This directory contains scripts and configurations for building standalone desktop applications.

## Requirements

### Windows

1. **Python 3.11-3.13**
2. **PyInstaller**: `pip install pyinstaller`
3. **Inno Setup** (for installer): https://jrsoftware.org/isdl.php

## Building

### Windows Executable

```bash
# Build standalone executable
python setup/desktop_app/build.py

# Build without cleaning
python setup/desktop_app/build.py --no-clean

# Build without creating installer
python setup/desktop_app/build.py --no-installer
```

Output:
- `dist/OpenManus.exe` - Standalone executable
- `dist/installer/OpenManus-1.0.0-setup.exe` - Installer

### Manual PyInstaller Build

```bash
pyinstaller --name=OpenManus \
    --windowed \
    --onefile \
    --add-data=config:config \
    --add-data=app:app \
    --hidden-import=PyQt6 \
    --collect-all=PyQt6 \
    main_gui.py
```

## Installer Features

The Windows installer provides:

- ✅ One-click installation
- ✅ Desktop shortcut (optional)
- ✅ Start menu integration
- ✅ Add to PATH (optional)
- ✅ Auto-start with Windows (optional)
- ✅ Uninstaller
- ✅ Version management

## Installation Options

When running the installer, users can choose:

1. **Desktop Icon**: Create shortcut on desktop
2. **Add to PATH**: Add OpenManus to system PATH for CLI access
3. **Auto-start**: Launch OpenManus when Windows starts

## Distribution

### File Structure

```
dist/
├── OpenManus.exe                    # Standalone executable (~100MB)
└── installer/
    └── OpenManus-1.0.0-setup.exe    # Installer (~80MB)
```

### Distribution Methods

1. **Direct Download**: Host the installer on your website
2. **GitHub Releases**: Attach to GitHub releases
3. **Package Managers**: Future support for Chocolatey, Scoop
4. **Microsoft Store**: Future support

## Testing

Before distribution, test:

1. **Clean Installation**: Test on fresh Windows VM
2. **Upgrade**: Test upgrade from previous version
3. **Uninstall**: Ensure clean uninstallation
4. **Auto-start**: Verify auto-start functionality
5. **PATH**: Test CLI access if PATH enabled

## Troubleshooting

### Build Fails

**Error**: `ModuleNotFoundError: No module named 'PyQt6'`

**Solution**: Install PyQt6: `pip install PyQt6`

**Error**: `FileNotFoundError: icon.ico`

**Solution**: Create or remove icon reference in build.py

### Installer Fails

**Error**: Inno Setup not found

**Solution**: Install from https://jrsoftware.org/isdl.php

### Large File Size

The standalone executable is large (~100MB) because it includes:
- Python interpreter
- PyQt6 libraries
- All dependencies

**Optimization**:
- Use `--exclude-module` to remove unused modules
- Use UPX compression: `--upx-dir=C:\path\to\upx`

### Application Won't Start

**Issue**: Double-click does nothing

**Solutions**:
1. Run from command line to see errors
2. Check if antivirus is blocking
3. Ensure Windows Defender allows the app
4. Check Event Viewer for crash logs

## Auto-Update

Future feature: Implement auto-update using:
- GitHub Releases API
- Delta updates
- Background download
- User-approved installation

## Code Signing

For production distribution, sign the executable:

```powershell
# Using SignTool (Windows SDK)
signtool sign /f certificate.pfx /p password /t http://timestamp.server OpenManus.exe
```

Benefits:
- Removes "Unknown Publisher" warning
- Increases user trust
- Required for Microsoft Store

## Platform Support

### Current

- ✅ Windows 10/11 (x64)

### Planned

- ⏳ macOS (DMG/PKG)
- ⏳ Linux (AppImage/DEB/RPM)

## macOS Build (Future)

```bash
# Using py2app
python setup.py py2app

# Create DMG
hdiutil create -volname "OpenManus" -srcfolder dist/OpenManus.app -ov OpenManus.dmg
```

## Linux Build (Future)

```bash
# Using AppImage
python -m PyInstaller --onefile main_gui.py
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build Desktop App

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: python setup/desktop_app/build.py
      - uses: actions/upload-artifact@v2
        with:
          name: windows-installer
          path: dist/installer/*.exe
```

## Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Inno Setup Documentation](https://jrsoftware.org/ishelp/)
- [Windows Code Signing Guide](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)
- [Microsoft Store Submission](https://docs.microsoft.com/en-us/windows/uwp/publish/)

## License

Same as main project (see LICENSE file).
