#!/usr/bin/env python3
"""
Desktop App Builder for OpenManus IDE.

Builds standalone executables for Windows using PyInstaller.
"""

import sys
import subprocess
import shutil
from pathlib import Path
import platform


class DesktopAppBuilder:
    """Builds desktop application packages."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = Path(__file__).parent / "openmanus.spec"
        
    def check_requirements(self) -> bool:
        """Check if build requirements are met."""
        try:
            import PyInstaller
            print(f"✓ PyInstaller installed: {PyInstaller.__version__}")
            return True
        except ImportError:
            print("✗ PyInstaller not installed")
            print("Install with: pip install pyinstaller")
            return False
    
    def clean_build_artifacts(self):
        """Clean previous build artifacts."""
        print("Cleaning build artifacts...")
        
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
            print(f"  Removed {self.dist_dir}")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"  Removed {self.build_dir}")
    
    def build_windows_exe(self):
        """Build Windows executable."""
        print("Building Windows executable...")
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--name=OpenManus",
            "--windowed",  # No console
            "--onefile",   # Single executable
            f"--icon={self.project_root}/assets/icon.ico" if (self.project_root / "assets/icon.ico").exists() else "",
            "--add-data=config:config",
            "--add-data=app:app",
            "--hidden-import=PyQt6",
            "--hidden-import=app.ui",
            "--hidden-import=app.tool",
            "--hidden-import=app.agent",
            "--collect-all=PyQt6",
            str(self.project_root / "main_gui.py")
        ]
        
        # Remove empty args
        cmd = [arg for arg in cmd if arg]
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=self.project_root)
        
        if result.returncode == 0:
            print("✓ Build successful")
            print(f"  Executable: {self.dist_dir / 'OpenManus.exe'}")
            return True
        else:
            print("✗ Build failed")
            return False
    
    def create_installer(self):
        """Create Windows installer using Inno Setup."""
        print("Creating Windows installer...")
        
        # Check if Inno Setup is available
        inno_setup = Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")
        
        if not inno_setup.exists():
            print("✗ Inno Setup not found")
            print("  Download from: https://jrsoftware.org/isdl.php")
            return False
        
        # Create Inno Setup script
        script_path = Path(__file__).parent / "installer.iss"
        
        if not script_path.exists():
            print(f"✗ Installer script not found: {script_path}")
            return False
        
        # Run Inno Setup
        cmd = [str(inno_setup), str(script_path)]
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("✓ Installer created")
            return True
        else:
            print("✗ Installer creation failed")
            return False
    
    def build(self, clean: bool = True, create_installer: bool = True):
        """
        Build the desktop application.
        
        Args:
            clean: Clean build artifacts before building
            create_installer: Create installer after building
        """
        print("=" * 60)
        print("OpenManus Desktop App Builder")
        print("=" * 60)
        
        # Check requirements
        if not self.check_requirements():
            return False
        
        # Clean
        if clean:
            self.clean_build_artifacts()
        
        # Build based on platform
        if platform.system() == "Windows":
            success = self.build_windows_exe()
            
            if success and create_installer:
                self.create_installer()
        else:
            print(f"Platform {platform.system()} not yet supported")
            print("Windows support only at this time")
            return False
        
        print("\n" + "=" * 60)
        print("Build complete!")
        print("=" * 60)
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build OpenManus desktop app")
    parser.add_argument("--no-clean", action="store_true", help="Don't clean build artifacts")
    parser.add_argument("--no-installer", action="store_true", help="Don't create installer")
    
    args = parser.parse_args()
    
    builder = DesktopAppBuilder()
    success = builder.build(
        clean=not args.no_clean,
        create_installer=not args.no_installer
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
