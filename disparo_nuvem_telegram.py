# -*- coding: utf-8 -*-
"""
Varredura Automática e Disparo para o Telegram com Deduplicação Estrita
Executa a cada 1 hora entre 07:00 e 20:00 (horário de Brasília).
Exibe apenas vagas inéditas. Se não houver novas vagas, notifica expressamente 0 vagas novas.
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
import requests
import scanner_vagas
import bot_telegram_radar

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENVIADAS = os.path.join(BASE_DIR, "vagas_enviadas_telegram.json")
ARQUIVO_VAGAS = os.path.join(BASE_DIR, "vagas_mapeadas.json")


def obter_hora_brasilia():
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br)


def carregar_vagas_enviadas():
    if os.path.exists(ARQUIVO_ENVIADAS):
        try:
            with open(ARQUIVO_ENVIADAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                ids = set(str(x).strip() for x in dados.get("ids", []) if x)
                urls = set(str(x).strip() for x in dados.get("urls", []) if x)
                return ids, urls, dados
        except Exception as e:
            print(f"Aviso: erro ao ler {ARQUIVO_ENVIADAS}: {e}")
    return set(), set(), {"ids": [], "urls": [], "total_enviadas": 0}


def salvar_vagas_enviadas(novos_ids, novas_urls, dados_existentes):
    ids_finais = set(str(x).strip() for x in dados_existentes.get("ids", []))
    urls_finais = set(str(x).strip() for x in dados_existentes.get("urls", []))

    ids_finais.update(str(x).strip() for x in novos_ids if x)
    urls_finais.update(str(x).strip() for x in novas_urls if x)

    agora_br = obter_hora_brasilia()
    dados_atualizados = {
        "ids": sorted(list(ids_finais)),
        "urls": sorted(list(urls_finais)),
        "total_enviadas": len(ids_finais),
        "ultima_atualizacao": agora_br.strftime("%d/%m/%Y %H:%M:%S")
    }

    with open(ARQUIVO_ENVIADAS, "w", encoding="utf-8") as f:
        json.dump(dados_atualizados, f, ensure_ascii=False, indent=2)


def executar_e_enviar(forcar=False):
    agora_br = obter_hora_brasilia()
    hora_atual = agora_br.hour

    if not forcar and not (7 <= hora_atual <= 20):
        print(f"⏰ Fora da janela de disparo (07h às 20h BRT). Hora atual em Brasília: {hora_atual}h. Envio suspenso.")
        return {"status": "fora_da_janela", "hora": hora_atual}

    cfg = bot_telegram_radar.load_config()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("bot_token", "")
    chat_id_env = os.environ.get("TELEGRAM_CHAT_ID", "")
    chat_ids = [chat_id_env] if chat_id_env else cfg.get("chat_ids", [])

    if not token or not chat_ids:
        print("Aviso: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return {"status": "sem_credenciais"}

    # Carrega ou executa a varredura
    if os.path.exists(ARQUIVO_VAGAS):
        try:
            with open(ARQUIVO_VAGAS, "r", encoding="utf-8") as f:
                d = json.load(f)
                vagas = d.get("vagas", [])
        except Exception:
            vagas = scanner_vagas.executar_varredura_completa()
    else:
        vagas = scanner_vagas.executar_varredura_completa()

    enviadas_ids, enviadas_urls, dados_enviadas = carregar_vagas_enviadas()

    # Filtra vagas inéditas (que não tiveram ID nem URL enviados antes)
    vagas_novas = []
    for v in vagas:
        vid = str(v.get("id", "")).strip()
        vurl = str(v.get("url", "")).strip()
        if vid and vid in enviadas_ids:
            continue
        if vurl and vurl in enviadas_urls:
            continue
        vagas_novas.append(v)

    data_hora_str = agora_br.strftime("%d/%m/%Y às %H:%M")

    # Cenário 1: 0 vagas novas
    if not vagas_novas:
        msg_zero = (
            f"🔍 <b>Radar de Vagas — Varredura Horária</b>\n"
            f"🕒 <i>{data_hora_str} (Horário de Brasília)</i>\n\n"
            f"✅ <b>0 vagas novas nesta rodada.</b>\n"
            f"Todas as <b>{len(vagas)}</b> oportunidades mapeadas no radar já foram enviadas para você anteriormente.\n\n"
            f"O monitoramento continua ativo a cada 1 hora (das 07h às 20h) e avisará imediatamente caso surja qualquer novidade."
        )
        for cid in chat_ids:
            bot_telegram_radar.send_msg(token, cid, msg_zero)
        print(f"Varredura concluída às {data_hora_str}: 0 vagas novas. Notificação enviada ao Telegram.")
        return {"status": "zero_novas", "total_vagas": len(vagas)}

    # Cenário 2: Há novas vagas
    msg_cabecalho = (
        f"🚨 <b>Radar de Vagas — {len(vagas_novas)} Nova(s) Vaga(s) Encontrada(s)!</b>\n"
        f"🕒 <i>{data_hora_str}</i>\n\n"
        f"Identificamos novas oportunidades qualificadas para Engenharia Civil:"
    )

    novos_ids = set()
    novas_urls = set()

    for cid in chat_ids:
        bot_telegram_radar.send_msg(token, cid, msg_cabecalho)
        for idx, v in enumerate(vagas_novas):
            plat = v.get("plataforma", "Vaga")
            titulo = v.get("titulo", "Engenheiro Civil")
            empresa = v.get("empresa", "Empresa")
            local = v.get("local", "")
            rec = v.get("data_publicacao", "Recente")
            pdf = v.get("curriculo_recomendado", "")
            url = v.get("url", "")
            email = v.get("email_direto", "")
            email_info = f"\n📧 <b>RH Direto:</b> <code>{email}</code>" if email else ""

            msg_card = (
                f"<b>{idx+1}. [{plat} • {rec}] {titulo}</b>\n"
                f"🏢 {empresa} ({local}){email_info}\n"
                f"📎 PDF: <code>{pdf}</code>\n"
                f"🔗 <a href=\"{url}\">Abrir Oportunidade</a>"
            )
            bot_telegram_radar.send_msg(token, cid, msg_card)

    for v in vagas_novas:
        if v.get("id"):
            novos_ids.add(str(v.get("id")).strip())
        if v.get("url"):
            novas_urls.add(str(v.get("url")).strip())

    salvar_vagas_enviadas(novos_ids, novas_urls, dados_enviadas)
    print(f"Varredura concluída: {len(vagas_novas)} novas vagas enviadas ao Telegram e registradas.")
    return {"status": "novas_enviadas", "qtd": len(vagas_novas)}


if __name__ == "__main__":
    forcar_arg = "--force" in sys.argv or os.environ.get("FORCAR_DISPARO") == "1"
    executar_e_enviar(forcar=forcar_arg)
