import subprocess
from pathlib import Path



def test_package_versions_in_isolated_env():
    """
    Test package version detection in an isolated environment with known package versions.
    Creates a temporary venv in the test directory and cleans it up after.
    """
    test_dir = Path(__file__).parent
    plugin_dir = test_dir.parent  # Get the plugin root directory
    flytekit_dir = plugin_dir.parent.parent  # Get the flytekit root directory
    reqs_file = test_dir / "requirements-test.txt"

    venv_path = test_dir / ".venv"
    subprocess.run(["python", "-m", "venv", str(venv_path)], check=True)

    try:
        pip = str(venv_path / "bin" / "pip")
        # First install flytekit in editable mode
        subprocess.run([pip, "install", "-e", str(flytekit_dir)], check=True)
        # Then install the local plugin in editable mode
        subprocess.run([pip, "install", "-e", str(plugin_dir)], check=True)
        # Finally install the test requirements
        subprocess.run([pip, "install", "-r", str(reqs_file)], check=True)

        python = str(venv_path / "bin" / "python")

        # Run a test to verify that CacheExternalDependencies can identify the version of various popular packages
        verify_version_script = test_dir / "verify_versions.py"
        result_version = subprocess.run(
            [python, str(verify_version_script)],
            capture_output=True,
            text=True,
            check=True
        )

        assert result_version.returncode == 0, f"Version verification failed: {result_version.stderr}"

        # Run a test to verify that CacheExternalDependencies cen identify packages used in a complex repo
        verify_packages_script = test_dir / "verify_identified_packages.py"
        result_package = subprocess.run(
            [python, str(verify_packages_script)],
            capture_output=True,
            text=True,
            check=True
        )

        assert result_package.returncode == 0, f"Package verification failed: {result_package.stderr}"

    finally:
        import shutil
        shutil.rmtree(venv_path)

if __name__ == "__main__":
    test_package_versions_in_isolated_env()
