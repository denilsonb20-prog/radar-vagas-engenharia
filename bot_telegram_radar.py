# -*- coding: utf-8 -*-
"""
Bot Oficial do Telegram — Radar de Vagas de Engenharia Civil (Denilson Barbosa)
Controla a varredura ao vivo (Gupy, Indeed, LinkedIn Vagas e Posts do Feed),
filtra vagas por região/plataforma, gera cartas de apresentação e envia os 4 PDFs
diretamente no celular via Telegram (funciona no Wi-Fi e no 4G/5G).
"""

import json
import os
import subprocess
import sys
import time
import threading
import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = r"C:\Users\Denil\Desktop"
CONFIG_FILE = os.path.join(BASE_DIR, "telegram_config.json")
VAGAS_FILE = os.path.join(BASE_DIR, "vagas_mapeadas.json")
SCANNER_SCRIPT = os.path.join(BASE_DIR, "scanner_vagas.py")

PDF_FILES = [
    (
        "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf",
        "📍 Fortaleza + 60km / Remoto — Foco: Orçamentos, Planejamento & Custos (Eusébio/CE)"
    ),
    (
        "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Fortaleza_CE.pdf",
        "📍 Fortaleza + 60km / Remoto — Foco: Gestão de Obras & Projetos BIM (Eusébio/CE)"
    ),
    (
        "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Caruaru_PE.pdf",
        "📍 Caruaru + 80km & PE — Foco: Orçamentos, Planejamento & Custos (Caruaru/PE)"
    ),
    (
        "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Caruaru_PE.pdf",
        "📍 Caruaru + 80km & PE — Foco: Gestão de Obras & Projetos BIM (Caruaru/PE)"
    ),
]


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""), "chat_ids": []}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_vagas_data():
    if not os.path.exists(VAGAS_FILE):
        return {"atualizado_em": "N/A", "vagas": []}
    try:
        with open(VAGAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"atualizado_em": "N/A", "vagas": []}


def get_reply_keyboard():
    return {
        "keyboard": [
            [{"text": "🔄 Varrer Vagas Agora"}],
            [{"text": "🏢 Construtoras Locais (RH)"}, {"text": "🔥 Posts com E-mail"}],
            [{"text": "📍 Fortaleza + 60km"}, {"text": "📍 Caruaru + 80km"}],
            [{"text": "🏠 Remoto Brasil"}, {"text": "🟪 Só Indeed"}],
            [{"text": "🟦 Só Gupy"}, {"text": "🔵 Só LinkedIn"}],
            [{"text": "📄 Baixar Meus 4 Currículos PDF"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def tg_request(token, method, payload=None, files=None, timeout=35):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if files:
            r = requests.post(url, data=payload, files=files, timeout=timeout)
        else:
            r = requests.post(url, json=payload, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_msg(token, chat_id, text, inline_kb=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": inline_kb if inline_kb else get_reply_keyboard(),
    }
    return tg_request(token, "sendMessage", payload)


def gerar_carta_vaga(v):
    titulo = v.get("titulo", "Engenheiro Civil")
    empresa = v.get("empresa", "Empresa Contratante")
    local = v.get("local", "")
    reg = (v.get("regiao_alvo", "") + " " + local).lower()
    pdf = v.get("curriculo_recomendado", "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf")

    if "fortaleza" in reg or "ce" in reg or "eusébio" in reg:
        loc_msg = "Resido atualmente em Eusébio/CE, com disponibilidade imediata para atuação presencial em Fortaleza, Região Metropolitana e eixo do Pecém."
    elif "caruaru" in reg or "pe" in reg or "belo jardim" in reg:
        loc_msg = f"Estou em processo de mudança planejada para Caruaru/PE, com disponibilidade imediata para atuação presencial em {local or 'Caruaru e região'} e em todo o eixo da BR-232."
    else:
        loc_msg = "Conto com estrutura completa para atuação remota imediata e disponibilidade para viagens técnicas sempre que necessário."

    carta = (
        f"<b>📄 PDF Recomendado para anexar:</b>\n<code>{pdf}</code>\n\n"
        f"<b>✉️ Texto pronto (toque para copiar):</b>\n\n"
        f"<code>Assunto: Candidatura: {titulo} - Denilson Barbosa (Engenheiro Civil)\n\n"
        f"Prezada equipe de seleção da {empresa},\n\n"
        f"Envio meu currículo para avaliação na oportunidade de {titulo}.\n\n"
        f"Sou Engenheiro Civil graduado pela UFERSA, com pós-graduação em Construção Civil e MBA em Projetos de Instalações Prediais pelo IPOG. Nos últimos cinco anos, atuei diretamente com engenharia de custos, planejamento físico-financeiro e gestão de obras públicas e privadas.\n\n"
        f"Atualmente, como Engenheiro Orçamentista na SS&B Construtora, estruturei um banco próprio com mais de 250 composições de custos unitários (CPUs) e conduzi a revisão técnica e tributária de um orçamento de R$ 60 milhões, gerando uma redução real de R$ 1,2 milhão que viabilizou o fechamento do contrato. Antes disso, exerci o cargo de Diretor de Engenharia na Prefeitura de Mossoró, coordenando equipes multidisciplinares, medições e compatibilização de projetos em obras hospitalares e educacionais, onde liderei uma revisão estrutural de emergência que evitou perdas estimadas em 10% do custo da obra.\n\n"
        f"{loc_msg}\n\n"
        f"O currículo em anexo detalha minha experiência com AutoCAD, Revit (BIM), MS Project, Eberick e bases referenciais de preços (SINAPI, SICRO e composições próprias). Fico à disposição para uma entrevista.\n\n"
        f"Atenciosamente,\n"
        f"Denilson Barbosa\n"
        f"Engenheiro Civil | (88) 9627-1246 | denilsonb20@gmail.com\n"
        f"linkedin.com/in/denilsonbarbosasantos</code>"
    )
    return carta


def enviar_lista_vagas(token, chat_id, filtro_fn, titulo_secao, limite=10):
    import scanner_vagas
    ids_clic, urls_clic = scanner_vagas.carregar_vagas_clicadas()
    data = load_vagas_data()
    vagas = data.get("vagas", [])
    filtradas = [
        (idx, v) for idx, v in enumerate(vagas)
        if filtro_fn(v)
        and v.get("dias_atras", 0) <= 7
        and str(v.get("id", "")) not in ids_clic
        and str(v.get("url", "")).strip() not in urls_clic
    ]

    if not filtradas:
        send_msg(token, chat_id, f"Nenhuma vaga não lida (≤ 7 dias) no filtro <b>{titulo_secao}</b>. Toque em <b>🔄 Varrer Vagas Agora</b> para atualizar.")
        return

    cabecalho = (
        f"🎯 <b>{titulo_secao} (Máx. 7 dias • Não clicadas)</b>\n"
        f"Total inédito neste filtro: <b>{len(filtradas)} vagas</b> (Exibindo {min(limite, len(filtradas))})\n"
        f"🕒 Última atualização: <i>{data.get('atualizado_em', 'Recente')}</i>"
    )
    send_msg(token, chat_id, cabecalho)

    for idx, v in filtradas[:limite]:
        plat = v.get("plataforma", "Vaga")
        titulo = v.get("titulo", "Engenheiro Civil")
        empresa = v.get("empresa", "Empresa")
        local = v.get("local", "")
        dias = v.get("dias_atras", 2)
        recencia = f"Há {dias}d ({v.get('data_publicacao', '')})"
        score = v.get("score_afinidade", v.get("afinidade_estimada", 90))
        pdf = v.get("curriculo_recomendado", "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf")
        email = v.get("email_direto", "")
        url = v.get("url", "https://www.linkedin.com/jobs")

        email_line = f"\n📧 <b>E-mail Direto RH:</b> <code>{email}</code>" if email else ""
        texto = (
            f"🏷 <b>[{plat}]</b> • 🕒 <b>{recencia}</b> • 🎯 <b>{score}%</b>\n"
            f"👷 <b>{titulo}</b>\n"
            f"🏢 {empresa} — 📍 {local}{email_line}\n"
            f"📎 <i>PDF ideal: {pdf}</i>"
        )

        botoes = [
            [
                {"text": f"🔗 Abrir no {plat.split()[0]}", "url": url},
                {"text": "📝 Carta + PDF", "callback_data": f"carta_{idx}"},
                {"text": "✕ Já vi", "callback_data": f"ocultar_{idx}"},
            ]
        ]
        send_msg(token, chat_id, texto, inline_kb={"inline_keyboard": botoes})


def enviar_curriculos_pdf(token, chat_id):
    send_msg(
        token,
        chat_id,
        "📄 <b>Enviando os seus 4 Currículos PDF otimizados (ATS)...</b>\n"
        "Você pode salvá-los no celular ou encaminhá-los diretamente daqui quando for se candidatar pelo aplicativo da Gupy, Indeed, LinkedIn ou E-mail:"
    )
    for fname, legenda in PDF_FILES:
        fpath = os.path.join(DESKTOP_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as doc:
                tg_request(
                    token,
                    "sendDocument",
                    payload={"chat_id": chat_id, "caption": legenda},
                    files={"document": (fname, doc, "application/pdf")},
                    timeout=60,
                )
        else:
            send_msg(token, chat_id, f"⚠️ Arquivo não encontrado em {fpath}")


def executar_varredura_telegram(token, chat_id):
    send_msg(
        token,
        chat_id,
        "🔄 <b>Varredura Ao Vivo Iniciada!</b>\n"
        "Vasculhando agora:\n"
        "• 🟦 <b>Gupy</b> (Portais das construtoras em Fortaleza, Caruaru/PE e Remoto)\n"
        "• 🟪 <b>Indeed Brasil</b> (Vagas recentes CE, PE e Home Office)\n"
        "• 🔵 <b>LinkedIn Vagas</b> (Últimos dias)\n"
        "• 🔥 <b>Publicações do Feed do LinkedIn</b> (Com e-mail direto)\n\n"
        "<i>Aguarde cerca de 25 a 40 segundos, vou te avisar assim que terminar...</i>"
    )
    try:
        subprocess.run(
            [sys.executable, SCANNER_SCRIPT],
            cwd=BASE_DIR,
            timeout=180,
            check=False,
        )
        data = load_vagas_data()
        vagas = data.get("vagas", [])
        g = sum(1 for v in vagas if v.get("plataforma") == "Gupy")
        i = sum(1 for v in vagas if v.get("plataforma") == "Indeed")
        l = sum(1 for v in vagas if v.get("plataforma") == "LinkedIn Vagas")
        p = sum(1 for v in vagas if "Publicação" in v.get("plataforma", ""))

        resumo = (
            f"✅ <b>Varredura Concluída com Sucesso!</b>\n"
            f"🕒 Atualizado em: <b>{data.get('atualizado_em', 'Agora')}</b>\n\n"
            f"📊 <b>Total Qualificado: {len(vagas)} vagas</b>\n"
            f"• 🟦 Gupy: <b>{g} vagas</b>\n"
            f"• 🟪 Indeed Brasil: <b>{i} vagas</b>\n"
            f"• 🔵 LinkedIn Vagas: <b>{l} vagas</b>\n"
            f"• 🔥 Posts do Feed: <b>{p} publicações</b>\n\n"
            f"👇 Use os botões abaixo para filtrar por região ou plataforma:"
        )
        send_msg(token, chat_id, resumo)
    except Exception as e:
        send_msg(token, chat_id, f"⚠️ Erro durante a varredura: {e}")


def processar_mensagem(token, msg):
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return

    cfg = load_config()
    if chat_id not in cfg.get("chat_ids", []):
        cfg.setdefault("chat_ids", []).append(chat_id)
        save_config(cfg)

    texto = (msg.get("text") or "").strip()

    if texto in ["/start", "/menu", "menu", "oi", "olá", "ola"]:
        data = load_vagas_data()
        total = len(data.get("vagas", []))
        boas_vindas = (
            "👷‍♂️ <b>Radar de Engenharia Civil — Denilson Barbosa</b>\n\n"
            f"Atualmente há <b>{total} vagas qualificadas</b> mapeadas (Gupy, Indeed Brasil, LinkedIn Vagas e Publicações do Feed).\n\n"
            "Toque em qualquer botão do menu abaixo para varrer em tempo real, filtrar vagas por polo (Fortaleza 60km, Caruaru 80km ou Remoto) ou baixar seus 4 currículos PDF direto no celular:"
        )
        send_msg(token, chat_id, boas_vindas)

    elif "Varrer Vagas Agora" in texto or texto == "/varrer":
        threading.Thread(target=executar_varredura_telegram, args=(token, chat_id), daemon=True).start()

    elif "Fortaleza" in texto or texto == "/fortaleza":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "fortaleza" in (v.get("regiao_alvo", "") + " " + v.get("local", "")).lower()
                      or "ceará" in (v.get("regiao_alvo", "") + " " + v.get("local", "")).lower()
                      or ", ce" in v.get("local", "").lower()
                      or "eusébio" in v.get("local", "").lower(),
            "Polo Fortaleza + 60km (CE)",
        )

    elif "Caruaru" in texto or texto == "/caruaru":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "caruaru" in (v.get("regiao_alvo", "") + " " + v.get("local", "")).lower()
                      or "pernambuco" in (v.get("regiao_alvo", "") + " " + v.get("local", "")).lower()
                      or ", pe" in v.get("local", "").lower()
                      or "recife" in v.get("local", "").lower(),
            "Polo Caruaru + 80km & Pernambuco",
        )

    elif "Remoto" in texto or texto == "/remoto":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "remoto" in (v.get("regiao_alvo", "") + " " + v.get("local", "") + " " + v.get("titulo", "")).lower()
                      or "home office" in (v.get("local", "") + " " + v.get("titulo", "")).lower(),
            "Vagas Remotas / Home Office (Brasil)",
        )

    elif "Construtoras Locais" in texto or texto == "/construtoras":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "Construtora" in v.get("plataforma", "") or "Mural" in v.get("plataforma", ""),
            "Murais & RH de Construtoras Locais (CE & PE)",
        )

    elif "Posts com E-mail" in texto or texto == "/posts":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "Publicação" in v.get("plataforma", "") or bool(v.get("email_direto")),
            "Publicações de Feed & Vagas com E-mail Direto",
        )

    elif "Só Gupy" in texto or texto == "/gupy":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: v.get("plataforma") == "Gupy",
            "Vagas na Plataforma Gupy",
        )

    elif "Só Indeed" in texto or texto == "/indeed":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: v.get("plataforma") == "Indeed",
            "Vagas no Indeed Brasil",
        )

    elif "Só LinkedIn" in texto or texto == "/linkedin":
        enviar_lista_vagas(
            token,
            chat_id,
            lambda v: "LinkedIn" in v.get("plataforma", ""),
            "Vagas no LinkedIn",
        )

    elif "Currículos PDF" in texto or texto == "/pdfs":
        enviar_curriculos_pdf(token, chat_id)

    else:
        send_msg(
            token,
            chat_id,
            "Use os botões na parte inferior da tela para filtrar as vagas, baixar seus 4 currículos PDF ou disparar uma nova varredura ao vivo.",
        )


def processar_callback(token, cb):
    import scanner_vagas
    cb_id = cb.get("id")
    data_str = cb.get("data", "")
    msg_obj = cb.get("message", {})
    chat_id = msg_obj.get("chat", {}).get("id")
    msg_id = msg_obj.get("message_id")

    if data_str.startswith("ocultar_") and chat_id:
        try:
            idx = int(data_str.split("_")[1])
            vagas = load_vagas_data().get("vagas", [])
            if 0 <= idx < len(vagas):
                v = vagas[idx]
                scanner_vagas.registrar_vaga_clicada(v.get("id", ""), v.get("url", ""))
            tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "Vaga ocultada permanentemente!"})
            if msg_id:
                tg_request(token, "deleteMessage", {"chat_id": chat_id, "message_id": msg_id})
        except Exception:
            pass
        return

    tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "Gerando carta personalizada..."})

    if data_str.startswith("carta_") and chat_id:
        try:
            idx = int(data_str.split("_")[1])
            vagas = load_vagas_data().get("vagas", [])
            if 0 <= idx < len(vagas):
                carta_html = gerar_carta_vaga(vagas[idx])
                send_msg(token, chat_id, carta_html)
        except Exception as e:
            send_msg(token, chat_id, f"Erro ao gerar carta: {e}")


def iniciar_loop_bot():
    print("=================================================================")
    print("🤖 BOT TELEGRAM — RADAR DE VAGAS ENGENHARIA (DENILSON BARBOSA)")
    print("=================================================================")
    offset = 0
    ultimo_token_logado = None

    while True:
        cfg = load_config()
        token = (cfg.get("bot_token") or "").strip()

        if not token:
            if ultimo_token_logado != "VAZIO":
                print("⏳ Aguardando configuração do Token do Bot (@BotFather)...")
                ultimo_token_logado = "VAZIO"
            time.sleep(3)
            continue

        if token != ultimo_token_logado:
            me = tg_request(token, "getMe", timeout=10)
            if me.get("ok"):
                bot_user = me["result"].get("username", "")
                print(f"✅ Conectado com sucesso ao Telegram: @{bot_user}")
                ultimo_token_logado = token
            else:
                print(f"❌ Token inválido: {me}")
                time.sleep(5)
                continue

        resp = tg_request(token, "getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
        if not resp.get("ok"):
            time.sleep(3)
            continue

        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1
            if "message" in upd:
                processar_mensagem(token, upd["message"])
            elif "callback_query" in upd:
                processar_callback(token, upd["callback_query"])


if __name__ == "__main__":
    iniciar_loop_bot()
