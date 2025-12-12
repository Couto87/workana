# Deploy na DigitalOcean

Guia rápido para subir o Workana Radar em uma Droplet Ubuntu.

## 1) Preparar a Droplet
1. Crie uma Droplet Ubuntu 22.04 com pelo menos 1 vCPU e 1GB RAM.
2. Acesse por SSH: `ssh root@seu_ip`.
3. Atualize pacotes e instale dependências básicas:
   ```bash
   apt update && apt upgrade -y
   apt install -y git python3 python3-venv python3-pip
   ```

## 2) Clonar o repositório e instalar
```bash
git clone https://github.com/seu-usuario/workana-radar.git
cd workana-radar
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # preencha OPENAI_API_KEY e outras variáveis
make init-db
```

## 3) Rodar serviços
### Opção simples (screen/tmux)
```bash
# Janela 1: scraper periódico
watch -n 900 "source .venv/bin/activate && python -m workana.scraper && python -m workana.analyzer"
# Janela 2: dashboard
source .venv/bin/activate
flask --app workana.app:APP run --host=0.0.0.0 --port=8000
```

### Opção produção com systemd + gunicorn
Crie `/etc/systemd/system/workana.service` com:
```ini
[Unit]
Description=Workana Radar
After=network.target

[Service]
User=root
WorkingDirectory=/root/workana-radar
Environment="PATH=/root/workana-radar/.venv/bin"
EnvironmentFile=/root/workana-radar/.env
ExecStart=/root/workana-radar/.venv/bin/gunicorn --bind 0.0.0.0:8000 workana.app:APP
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative e verifique:
```bash
systemctl daemon-reload
systemctl enable --now workana.service
systemctl status workana.service
```

### SSL e domínio
- Use um proxy como Nginx ou Caddy para HTTPS.
- Configure Nginx como reverse proxy para `127.0.0.1:8000`.

## 4) Backups e logs
- O banco SQLite está em `data/workana.sqlite`. Faça backup periódico (rsync ou snapshot da Droplet).
- Logs do systemd: `journalctl -u workana.service -f`.

## 5) Atualizações
```bash
cd /root/workana-radar
git pull
. .venv/bin/activate
pip install -r requirements.txt
python -m workana.db  # opcional: garante schema atualizado
sudo systemctl restart workana.service
```
