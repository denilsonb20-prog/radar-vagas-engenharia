# -*- coding: utf-8 -*-
"""
Script de Varredura + Disparo Direto para o Telegram (Ideal para Nuvem / GitHub Actions ou Agendador)
Executa o scanner_vagas.py e envia o resumo + top vagas inéditas para o Telegram do Denilson.
"""

import os
import sys
import json
import requests
import scanner_vagas
import bot_telegram_radar

sys.stdout.reconfigure(encoding="utf-8")


def executar_e_enviar():
    cfg = bot_telegram_radar.load_config()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("bot_token", "")
    chat_id_env = os.environ.get("TELEGRAM_CHAT_ID", "")
    chat_ids = [chat_id_env] if chat_id_env else cfg.get("chat_ids", [])

    vagas = scanner_vagas.executar_varredura_completa()
    if not token or not chat_ids:
        print("Varredura concluída. Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID para envio no Telegram.")
        return

    g = sum(1 for v in vagas if v.get("plataforma") == "Gupy")
    i = sum(1 for v in vagas if v.get("plataforma") == "Indeed")
    l = sum(1 for v in vagas if v.get("plataforma") == "LinkedIn Vagas")
    p = sum(1 for v in vagas if "Publicação" in v.get("plataforma", ""))

    resumo = (
        f"🚀 <b>Relatório Automático de Vagas — Engenharia Civil</b>\n\n"
        f"Total qualificado: <b>{len(vagas)} vagas</b>\n"
        f"• 🟦 Gupy: <b>{g}</b> | 🟪 Indeed: <b>{i}</b> | 🔵 LinkedIn: <b>{l}</b> | 🔥 Posts: <b>{p}</b>\n\n"
        f"<b>Top 8 Vagas Mais Recentes / Maior Afinidade:</b>"
    )

    for cid in chat_ids:
        bot_telegram_radar.send_msg(token, cid, resumo)
        for idx, v in enumerate(vagas[:8]):
            plat = v.get("plataforma", "Vaga")
            titulo = v.get("titulo", "Engenheiro Civil")
            empresa = v.get("empresa", "Empresa")
            local = v.get("local", "")
            rec = v.get("data_publicacao", "Recente")
            pdf = v.get("curriculo_recomendado", "")
            url = v.get("url", "")
            msg = (
                f"<b>{idx+1}. [{plat} • {rec}] {titulo}</b>\n"
                f"🏢 {empresa} ({local})\n"
                f"📎 PDF: <code>{pdf}</code>\n"
                f"🔗 <a href=\"{url}\">Abrir Vaga Direto</a>"
            )
            bot_telegram_radar.send_msg(token, cid, msg)


if __name__ == "__main__":
    executar_e_enviar()
