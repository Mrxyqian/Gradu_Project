from __future__ import annotations

import io
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SPRING_APPLICATION_YML = (
    BASE_DIR.parent / "springboot" / "src" / "main" / "resources" / "application.yml"
)


@dataclass(frozen=True)
class MySqlConfig:
    host: str = "localhost"
    port: int = 3306
    database: str = "gra_data"
    username: str = "root"
    password: str = "123"


def _extract_yaml_value(text: str, key: str) -> Optional[str]:
    pattern = rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    return value.strip("'\"")


def load_mysql_config() -> MySqlConfig:
    default_config = MySqlConfig()
    if not SPRING_APPLICATION_YML.exists():
        return default_config

    try:
        content = SPRING_APPLICATION_YML.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return default_config

    username = _extract_yaml_value(content, "username") or default_config.username
    password = _extract_yaml_value(content, "password") or default_config.password
    jdbc_url = _extract_yaml_value(content, "url")
    if not jdbc_url:
        return MySqlConfig(username=username, password=password)

    normalized_url = jdbc_url.replace("jdbc:", "", 1)
    parsed = urlparse(normalized_url)
    database = parsed.path.lstrip("/") or default_config.database
    host = parsed.hostname or default_config.host
    port = int(parsed.port or default_config.port)
    return MySqlConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
    )


def run_mysql_query(query: str, config: Optional[MySqlConfig] = None) -> str:
    resolved_config = config or load_mysql_config()
    command = [
        "mysql",
        "--batch",
        "--raw",
        "--default-character-set=utf8mb4",
        "-h",
        resolved_config.host,
        "-P",
        str(resolved_config.port),
        "-u",
        resolved_config.username,
        "-D",
        resolved_config.database,
        "-e",
        query,
    ]
    env = os.environ.copy()
    env["MYSQL_PWD"] = resolved_config.password
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("mysql command not found in PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = stderr or stdout or str(exc)
        raise RuntimeError(f"MySQL query failed: {details}") from exc
    return completed.stdout


def read_mysql_dataframe(query: str, config: Optional[MySqlConfig] = None) -> pd.DataFrame:
    output = run_mysql_query(query, config=config)
    if not output.strip():
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(output), sep="\t")


def load_csv_dataframe(csv_path: str | Path) -> pd.DataFrame:
    dataset_path = Path(csv_path).expanduser()
    if not dataset_path.is_absolute():
        dataset_path = (BASE_DIR / dataset_path).resolve()
    if not dataset_path.exists():
        raise RuntimeError(f"Training csv '{dataset_path}' does not exist")
    df = pd.read_csv(dataset_path)
    if df.empty:
        raise RuntimeError(f"Training csv '{dataset_path}' is empty")
    return df


def load_training_dataframe(table_name: str = "train_data") -> pd.DataFrame:
    dataset_path = Path(table_name).expanduser()
    if dataset_path.suffix.lower() == ".csv" or dataset_path.exists():
        return load_csv_dataframe(dataset_path)
    df = read_mysql_dataframe(f"SELECT * FROM `{table_name}`")
    if df.empty:
        raise RuntimeError(f"Training table '{table_name}' is empty")
    return df


__all__ = [
    "MySqlConfig",
    "load_csv_dataframe",
    "load_mysql_config",
    "load_training_dataframe",
    "read_mysql_dataframe",
    "run_mysql_query",
]
