"""
[Database 초기화 시나리오]
기본 compose.yml은 이미 실행 중인 공용 PostgreSQL을 사용하므로 PostgreSQL Container의
`docker-entrypoint-initdb.d`가 실행되지 않습니다. 그 결과 Backend가 사용하는 Table이
없을 수 있습니다. 이 프로그램은 `database/init.sql`을 공용 PostgreSQL에 직접 실행하여
`simple_multi_llm` 전용 Schema와 Table을 준비합니다.

기존 Schema나 데이터를 삭제하지 않으며 `CREATE ... IF NOT EXISTS`만 실행합니다.
연결·인증·SQL 오류는 성공으로 숨기지 않습니다. `.env`에 HOST_DATABASE_URL이 없으면
Container용 DATABASE_URL의 `host.docker.internal`을 Host용 `127.0.0.1`로 바꿉니다.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
SQL_PATH = ROOT / "database" / "init.sql"
DEFAULT_HOST_DATABASE_URL = (
    "postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db"
)


def host_database_url() -> str:
    load_dotenv(ENV_PATH)
    explicit_host_url = os.getenv("HOST_DATABASE_URL", "").strip()
    if explicit_host_url:
        return explicit_host_url

    container_url = os.getenv("DATABASE_URL", "").strip()
    if container_url:
        return container_url.replace("host.docker.internal", "127.0.0.1")
    return DEFAULT_HOST_DATABASE_URL


def initialize_database() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    print(f"실행할 SQL: {SQL_PATH}")
    print("공용 PostgreSQL에 simple_multi_llm Schema를 준비합니다.")

    with psycopg.connect(host_database_url()) as connection:
        connection.execute(sql)
        tables = connection.execute(
            """SELECT table_name
               FROM information_schema.tables
               WHERE table_schema = 'simple_multi_llm'
               ORDER BY table_name"""
        ).fetchall()

    print("Database 초기화가 완료되었습니다.")
    for table in tables:
        print(f"- simple_multi_llm.{table[0]}")


if __name__ == "__main__":
    initialize_database()
