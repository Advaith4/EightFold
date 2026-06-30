import subprocess


def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True)


run_cmd("python -m ruff check --fix .")
run_cmd("python -m mypy .")
run_cmd("python -m black .")
