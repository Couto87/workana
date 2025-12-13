"""Send projects to OpenAI to decide scope, worth, and proposal."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from openai import OpenAI, OpenAIError

from .db import DEFAULT_DB, connect, fetch_pending, init_db, save_analysis

MODEL = os.environ.get("WORKANA_MODEL", "gpt-4o-mini")
PROJECT_SCOPE = os.environ.get(
    "WORKANA_SCOPE",
    "Projetos de software web e dados com stack Python/JS, preferencialmente B2B.",
)


class Analyzer:
    def __init__(self, api_key: Optional[str], db_path: str = DEFAULT_DB):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.db_path = db_path
        init_db(db_path)

    def build_prompt(self, row) -> List[Dict[str, str]]:
        description = row["descricao"] or ""
        skills = row["skills"] or ""
        budget = row["budget"] or ""
        country = row["country"] or ""
        return [
            {
                "role": "system",
                "content": (
                    "Você é um consultor que avalia projetos do Workana. "
                    "Aplique senso crítico e responda em JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Avalie o projeto com base no escopo alvo e retorne JSON com campos: "
                    "scope_fit (yes/no/maybe), worthiness (0-5), worthiness_reason, proposal (3-5 linhas). "
                    f"Escopo alvo: {PROJECT_SCOPE}. "
                    f"Título: {row['titulo']} | País: {country} | Budget: {budget} | Skills: {skills}. "
                    f"Descrição: {description}"
                ),
            },
        ]

    def analyze_row(self, row) -> Dict:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY ausente; análise não executada.")

        messages = self.build_prompt(row)
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        tokens = getattr(response.usage, "total_tokens", None)
        return {
            "result": parsed,
            "raw": response.model_dump(),
            "tokens": tokens,
        }

    def mark_error(self, conn, row, message: str):
        save_analysis(
            conn,
            row["workana_id_hash"],
            analysis_status="error",
            model=MODEL,
            analysis_raw={"error": message},
        )

    def run(self, limit: int = 5) -> int:
        conn = connect(self.db_path)
        pending = fetch_pending(conn, limit=limit)
        total = 0

        for row in pending:
            total += 1
            try:
                result = self.analyze_row(row)
                parsed = result["result"] or {}
                save_analysis(
                    conn,
                    row["workana_id_hash"],
                    analysis_status="complete",
                    model=MODEL,
                    scope_fit=str(parsed.get("scope_fit") or ""),
                    worthiness=int(parsed.get("worthiness")) if parsed.get("worthiness") is not None else None,
                    worthiness_reason=str(parsed.get("worthiness_reason") or ""),
                    proposal=str(parsed.get("proposal") or ""),
                    tokens=result.get("tokens"),
                    analysis_raw=result.get("raw"),
                )
            except (OpenAIError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
                self.mark_error(conn, row, str(exc))

        conn.close()
        return total


def run(limit: int = 5, db_path: str = DEFAULT_DB) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    analyzer = Analyzer(api_key=api_key, db_path=db_path)
    return analyzer.run(limit=limit)


if __name__ == "__main__":
    processed = run()
    print(f"Itens analisados: {processed}")
