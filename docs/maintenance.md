# Manutenção e atualizações

## Fluxo para atualizar código
1. Entre na pasta do projeto e ative o venv:
   ```bash
   cd /root/workana-radar
   . .venv/bin/activate
   ```
2. Atualize o código:
   ```bash
   git pull
   pip install -r requirements.txt
   ```
3. Ajuste variáveis em `.env` se houver novas chaves.
4. Reinicie os serviços (ex.: `systemctl restart workana.service`).

## Evoluir o schema
- As mudanças de schema usam `init_db` idempotente. Rode:
  ```bash
  python - <<'PY'
  from workana.db import init_db
  init_db()
  print('Schema OK')
  PY
  ```
- Para verificar colunas: `sqlite3 data/workana.sqlite '.schema projects'`.

## Rotina de higiene
- **Backups**: copie `data/workana.sqlite` antes de atualizações maiores.
- **Logs**: no modo systemd, veja `journalctl -u workana.service -f`.
- **Tokens**: monitore consumo pela coluna `analysis_tokens` e dashboards da OpenAI.

## Rodar manualmente
- Coleta: `python -m workana.scraper`
- Análise: `python -m workana.analyzer`
- Dashboard: `flask --app workana.app:APP run --port 8000`

## Dicas
- Ajuste `WORKANA_MAX_PAGES` para diminuir/expandir carga.
- Se a IA falhar, os itens ficam com `analysis_status=error`; basta corrigir o ambiente e rodar `make analyze` novamente.
- `analysis_raw` guarda a resposta completa para auditoria ou debug.
