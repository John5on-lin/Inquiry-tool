import sys
import pkg_resources

def print_env_info():
    print("=== Python & Package Diagnostics ===")
    print("Python:", sys.version)
    for pkg in ["gradio", "gradio_client", "fastapi","pandas", "openpyxl", "gspread", "google-auth", "pydantic"]:
        try:
            version = pkg_resources.get_distribution(pkg).version
            print(f"{pkg}: {version}")
        except pkg_resources.DistributionNotFound:
            print(f"{pkg}: not installed")
    print("====================================")