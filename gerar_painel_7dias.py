# -*- coding: utf-8 -*-
"""
Gera o painel_vagas_caruaru.html (e index.html para o GitHub Pages) com:
1. Apenas vagas de no máximo 7 dias (1 semana postada).
2. Ocultação automática e sincronização bidirecional de vagas já clicadas (localStorage + API + GitHub Pages).
3. Botão de "Candidatura Rápida por E-mail (1 Toque)" com carta personalizada e link público do PDF correspondente.
4. Monitoramento direto dos murais e bancos de talentos de grandes construtoras locais (CE & PE).
5. Compatibilidade total com Antigravity, Servidor Local e GitHub Pages (PWA instalável).
"""

import json
import os
import shutil

BASE_DIR = r"c:\Users\Denil\Desktop\projeto\radar_vagas_caruaru"
ARTIFACT_DIR = r"C:\Users\Denil\.gemini\antigravity\brain\3e1c3540-4602-4d7d-b522-77c8dae96475"
VAGAS_JSON = os.path.join(BASE_DIR, "vagas_mapeadas.json")

if not os.path.exists(VAGAS_JSON):
    dados = {"vagas": []}
else:
    with open(VAGAS_JSON, "r", encoding="utf-8") as f:
        dados = json.load(f)

vagas_raw = dados.get("vagas", [])
vagas_js = []

for idx, v in enumerate(vagas_raw, 1):
    dias = int(v.get("dias_atras", 3))
    if dias > 7:
        continue
    plat_raw = v.get("plataforma", "LinkedIn Vagas")
    if "Mural Construtora" in plat_raw:
        plat = "Mural Construtora (RH)"
    elif "Gupy" in plat_raw:
        plat = "Gupy"
    elif "Indeed" in plat_raw:
        plat = "Indeed"
    elif "Publicação" in plat_raw:
        plat = "Publicação LinkedIn"
    else:
        plat = "LinkedIn Vagas"

    cat_geo = v.get("categoria_geografica", "Remoto Brasil")
    if "Fortaleza" in cat_geo:
        reg = "fortaleza"
    elif "Caruaru" in cat_geo or "PE" in cat_geo:
        reg = "caruaru"
    else:
        reg = "remoto"

    dt_pub = v.get("data_publicacao", "2026-11-05")
    try:
        partes = dt_pub[:10].split("-")
        dt_br = f"{partes[2]}/{partes[1]}/{partes[0]}"
    except Exception:
        dt_br = dt_pub

    rec_str = "Hoje" if dias == 0 else (f"Há 1 dia ({dt_br})" if dias == 1 else f"Há {dias} dias ({dt_br})")

    vagas_js.append({
        "id": v.get("id", f"v_{idx}"),
        "plat": plat,
        "reg": reg,
        "regLabel": cat_geo,
        "dias": dias,
        "recencia": rec_str,
        "score": v.get("score_afinidade", 90),
        "titulo": v.get("titulo", "Engenheiro Civil"),
        "empresa": v.get("empresa", "Construtora"),
        "local": v.get("local", cat_geo),
        "pdf": v.get("curriculo_recomendado", "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf"),
        "email": v.get("email_direto", ""),
        "url": v.get("url", ""),
        "resumo": (v.get("descricao") or "")[:260],
        "motivo": f"Publicada há {dias} dia(s) • Afinidade com {', '.join(v.get('termos_afinidade', ['Engenharia Civil'])[:3])}."
    })

vagas_json_inline = json.dumps(vagas_js, ensure_ascii=False, indent=2)

HTML_CONTENT = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <meta name="theme-color" content="#0f172a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Radar Vagas">
  <link rel="manifest" href="./manifest.json">
  <link rel="apple-touch-icon" href="./icon-192.png">
  <link rel="icon" type="image/png" href="./icon-192.png">
  <title>Radar de Vagas de Engenharia: Fortaleza, Caruaru & Remoto (≤ 7 Dias)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --background: #0f172a;
      --foreground: #f8fafc;
      --card: #1e293b;
      --border: #334155;
      --muted-foreground: #94a3b8;
    }}
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-3 md:p-6">
  <div class="max-w-5xl mx-auto space-y-5">
    <!-- Cabeçalho + Botões de Ação Ao Vivo -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div class="flex flex-wrap items-center gap-2 mb-2">
            <span class="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              ⚡ Vagas Recentes: Máximo 7 Dias
            </span>
            <span class="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
              👁️ Vagas Clicadas Ocultas
            </span>
            <span id="api-badge" class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-300 border border-blue-500/30">
              Sincronizado
            </span>
            <button onclick="carregarDadosServidor()" title="Sincronizar descartes entre PC e Celular" class="px-2 py-0.5 rounded text-xs bg-slate-800 border border-slate-700 text-slate-300 hover:text-white cursor-pointer">
              🔄 Sincronizar
            </button>
          </div>
          <h1 class="text-xl md:text-2xl font-bold text-[var(--foreground)]">Radar de Vagas de Engenharia Civil</h1>
          <p class="text-xs md:text-sm text-[var(--muted-foreground)] mt-1">
            Polos: <strong>Fortaleza + 60 km (CE)</strong> • <strong>Caruaru + 80 km (PE)</strong> • <strong>Remoto Brasil</strong>
          </p>
        </div>

        <!-- Botões de Ação -->
        <div class="flex flex-col items-stretch md:items-end gap-2">
          <div class="flex flex-col sm:flex-row gap-2">
            <button id="btn-install-pwa" onclick="instalarAppCelular()" class="px-4 py-3 rounded-xl font-bold text-xs md:text-sm bg-sky-600 hover:bg-sky-500 text-white shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer">
              <span>📲</span>
              <span id="txt-install-pwa">Adicionar à Tela Inicial</span>
            </button>
            <button id="btn-live-scan" onclick="dispararScanPainel()" class="px-5 py-3 rounded-xl font-bold text-xs md:text-sm bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer">
              <span id="icon-live-scan">🔄</span>
              <span id="txt-live-scan">Varredura Ao Vivo (≤ 7 Dias)</span>
            </button>
          </div>
          <span id="sub-live-scan" class="text-[11px] text-[var(--muted-foreground)] text-center md:text-right">
            Busca novas vagas em murais de construtoras, Indeed, Gupy e LinkedIn
          </span>
        </div>
      </div>

      <!-- Caixa Guia Visual de Instalação no Celular -->
      <div id="pwa-help-box" class="hidden mt-4 pt-3 border-t border-sky-500/40 bg-sky-950/40 rounded-xl p-4 text-xs space-y-2">
        <div class="flex items-center justify-between">
          <strong class="text-sky-300 text-sm">📲 Como fixar o aplicativo na tela inicial do celular:</strong>
          <button onclick="document.getElementById('pwa-help-box').classList.add('hidden')" class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">Fechar ✕</button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div class="bg-slate-900/90 border border-slate-700 rounded-lg p-3">
            <div class="font-bold text-emerald-400 mb-1">🤖 No Android (Chrome / Samsung Internet):</div>
            <p class="text-slate-200">1. Toque nos <strong>3 pontinhos (⋮)</strong> no canto superior direito.</p>
            <p class="text-slate-200 mt-1">2. Toque em <strong>"Adicionar à tela inicial"</strong> (ou "Instalar aplicativo") e confirme.</p>
          </div>
          <div class="bg-slate-900/90 border border-slate-700 rounded-lg p-3">
            <div class="font-bold text-sky-400 mb-1">🍎 No iPhone / iOS (Safari):</div>
            <p class="text-slate-200">1. Toque no ícone de <strong>Compartilhar (quadrado com seta ⬆️)</strong>.</p>
            <p class="text-slate-200 mt-1">2. Role para baixo e selecione <strong>"Adicionar à Tela de Início"</strong>.</p>
          </div>
        </div>
      </div>

      <!-- Barra de Progresso da Varredura -->
      <div id="scan-progress-wrap" class="hidden mt-4 pt-3 border-t border-[var(--border)]">
        <div class="flex justify-between text-xs font-semibold text-emerald-400 mb-1">
          <span id="scan-progress-msg">Iniciando varredura (≤ 7 dias)...</span>
          <span id="scan-progress-pct">15%</span>
        </div>
        <div class="w-full h-2 bg-[var(--background)] rounded-full overflow-hidden">
          <div id="scan-progress-bar" class="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-300" style="width: 15%"></div>
        </div>
      </div>

      <!-- Placar Rápido com 5 Plataformas -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 text-center mt-4 pt-4 border-t border-[var(--border)]">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-xs font-bold text-emerald-400">Construtoras (RH)</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5" id="count-const">0 Murais</div>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-xs font-bold text-indigo-400">Indeed Brasil</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5" id="count-indeed">0 Vagas</div>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-xs font-bold text-blue-400">LinkedIn Vagas</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5" id="count-linkedin">0 Vagas</div>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-xs font-bold text-cyan-400">Gupy</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5" id="count-gupy">0 Vagas</div>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-xs font-bold text-purple-400">Posts Feed</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5" id="count-posts">0 Posts</div>
        </div>
      </div>
    </div>

    <!-- Os 4 Currículos Salvos (Download Direto no Celular e PC) -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
      <h3 class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
        📄 4 Currículos PDF Estratégicos (Toque para baixar ou enviar):
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
          <div class="font-bold text-emerald-400">📍 Fortaleza + 60km e Remoto (Cabeçalho: Eusébio, CE)</div>
          <a id="dl-for-orc" href="./pdf/Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf" target="_blank" class="block font-mono truncate text-blue-400 hover:underline">⬇ Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf</a>
          <a id="dl-for-obr" href="./pdf/Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Fortaleza_CE.pdf" target="_blank" class="block font-mono truncate text-blue-400 hover:underline">⬇ Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Fortaleza_CE.pdf</a>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-1.5">
          <div class="font-bold text-amber-400">📍 Caruaru + 80km e PE (Cabeçalho: Caruaru, PE)</div>
          <a id="dl-car-orc" href="./pdf/Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Caruaru_PE.pdf" target="_blank" class="block font-mono truncate text-blue-400 hover:underline">⬇ Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Caruaru_PE.pdf</a>
          <a id="dl-car-obr" href="./pdf/Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Caruaru_PE.pdf" target="_blank" class="block font-mono truncate text-blue-400 hover:underline">⬇ Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Caruaru_PE.pdf</a>
        </div>
      </div>
    </div>

    <!-- Filtros Duplos + Vagas Ocultas -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
      <div class="flex flex-col gap-3 mb-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">1. Filtrar por Plataforma:</span>
          <div class="flex flex-wrap gap-1.5">
            <button onclick="setPlat('todas')" id="plat-todas" class="px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white cursor-pointer">Todas</button>
            <button onclick="setPlat('Mural Construtora (RH)')" id="plat-Mural Construtora (RH)" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Murais Construtoras (RH)</button>
            <button onclick="setPlat('Indeed')" id="plat-Indeed" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Indeed Brasil</button>
            <button onclick="setPlat('LinkedIn Vagas')" id="plat-LinkedIn Vagas" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">LinkedIn Vagas</button>
            <button onclick="setPlat('Gupy')" id="plat-Gupy" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Gupy</button>
            <button onclick="setPlat('Publicação LinkedIn')" id="plat-Publicação LinkedIn" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Posts Feed</button>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-3">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">2. Filtrar por Região:</span>
          <div class="flex flex-wrap gap-1.5">
            <button onclick="setReg('todas')" id="reg-todas" class="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white cursor-pointer">Todas as Regiões</button>
            <button onclick="setReg('fortaleza')" id="reg-fortaleza" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Fortaleza + 60km (CE)</button>
            <button onclick="setReg('caruaru')" id="reg-caruaru" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Caruaru + 80km & PE</button>
            <button onclick="setReg('remoto')" id="reg-remoto" class="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer">Remoto Brasil</button>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-3 text-xs text-[var(--muted-foreground)]">
          <span>💡 Toque em <strong>"✉️ Candidatura Rápida (1 Toque)"</strong> para abrir seu e-mail já preenchido com seu currículo em anexo e texto profissional.</span>
          <div class="flex items-center gap-2">
            <span id="clicadas-info" class="font-semibold text-amber-400">0 vagas já clicadas ocultadas</span>
            <button onclick="restaurarVagasClicadas()" class="px-2 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] hover:text-white cursor-pointer">Restaurar</button>
          </div>
        </div>
      </div>

      <div id="jobs-container" class="space-y-3"></div>
    </div>

    <!-- Área de Carta de Apresentação -->
    <div id="carta-box" class="hidden bg-[var(--card)] border-2 border-blue-500/40 rounded-xl p-5 shadow-md">
      <div class="flex items-center justify-between mb-2">
        <h3 class="font-bold text-base" id="carta-titulo">Carta de Apresentação / Mensagem ao Recrutador</h3>
        <button onclick="copiarCarta()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 cursor-pointer">
          Copiar Texto
        </button>
      </div>
      <p class="text-xs text-[var(--muted-foreground)] mb-2" id="carta-pdf-indicado"></p>
      <textarea id="carta-texto" rows="11" class="w-full bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] rounded-lg p-3 text-xs font-mono"></textarea>
    </div>
  </div>

  <script>
    const IS_GITHUB_PAGES = window.location.hostname.includes("github.io");
    const API_BASE = window.location.origin.includes("3456") ? window.location.origin : "http://" + window.location.hostname + ":3456";
    const GITHUB_PAGES_BASE = "https://denilsonb20-prog.github.io/radar-vagas-engenharia";

    const STORAGE_KEY_CLICADAS = "radar_vagas_clicadas_ids";
    let clicadasSet = new Set();
    try {{
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY_CLICADAS) || "[]");
      saved.forEach(x => clicadasSet.add(String(x)));
    }} catch (e) {{}}

    let filtroPlat = "todas";
    let filtroReg = "todas";

    let VAGAS = {vagas_json_inline};

    function foiClicada(v) {{
      return clicadasSet.has(String(v.id)) || (v.url && clicadasSet.has(String(v.url).trim()));
    }}

    function salvarClicadasLocal() {{
      try {{
        localStorage.setItem(STORAGE_KEY_CLICADAS, JSON.stringify(Array.from(clicadasSet)));
      }} catch (e) {{}}
    }}

    function registrarCliqueVaga(id, url) {{
      if (id) clicadasSet.add(String(id));
      if (url) clicadasSet.add(String(url).trim());
      salvarClicadasLocal();

      if (!IS_GITHUB_PAGES) {{
        fetch(`${{API_BASE}}/api/marcar_clicada`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ id: String(id), url: String(url || "").trim() }})
        }}).catch(() => {{}});
      }}

      setTimeout(() => {{
        atualizarPlacar();
        renderVagas();
      }}, 250);
    }}

    function restaurarVagasClicadas() {{
      clicadasSet.clear();
      salvarClicadasLocal();
      if (!IS_GITHUB_PAGES) {{
        fetch(`${{API_BASE}}/api/limpar_clicadas`, {{ method: "POST" }}).catch(() => {{}});
      }}
      atualizarPlacar();
      renderVagas();
    }}

    function atualizarPlacar() {{
      const visiveis = VAGAS.filter(v => !foiClicada(v) && (v.dias === undefined || v.dias <= 7));
      const cConst = visiveis.filter(v => v.plat === "Mural Construtora (RH)").length;
      const cInd = visiveis.filter(v => v.plat === "Indeed").length;
      const cLin = visiveis.filter(v => v.plat === "LinkedIn Vagas").length;
      const cGupy = visiveis.filter(v => v.plat === "Gupy").length;
      const cPos = visiveis.filter(v => v.plat === "Publicação LinkedIn").length;

      document.getElementById("count-const").textContent = `${{cConst}} Murais`;
      document.getElementById("count-indeed").textContent = `${{cInd}} Vagas`;
      document.getElementById("count-linkedin").textContent = `${{cLin}} Vagas`;
      document.getElementById("count-gupy").textContent = `${{cGupy}} Vagas`;
      document.getElementById("count-posts").textContent = `${{cPos}} Posts`;

      const ocultadas = VAGAS.filter(v => foiClicada(v)).length;
      const elInfo = document.getElementById("clicadas-info");
      if (elInfo) {{
        elInfo.textContent = `${{ocultadas}} vaga(s) já clicada(s) ocultada(s)`;
      }}
    }}

    function setPlat(p) {{
      filtroPlat = p;
      ["todas", "Mural Construtora (RH)", "Indeed", "LinkedIn Vagas", "Gupy", "Publicação LinkedIn"].forEach(k => {{
        const b = document.getElementById("plat-" + k);
        if (b) {{
          b.className = (k === p)
            ? "px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white cursor-pointer"
            : "px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer";
        }}
      }});
      renderVagas();
    }}

    function setReg(r) {{
      filtroReg = r;
      ["todas", "fortaleza", "caruaru", "remoto"].forEach(k => {{
        const b = document.getElementById("reg-" + k);
        if (b) {{
          b.className = (k === r)
            ? "px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white cursor-pointer"
            : "px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--background)] border border-[var(--border)] cursor-pointer";
        }}
      }});
      renderVagas();
    }}

    function obterMailtoLink(v) {{
      const tituloVaga = v.titulo.replace(/\\[.*?\\]/g, "").trim();
      const assunto = encodeURIComponent(`Candidatura: ${{tituloVaga}} - Denilson Barbosa (Engenheiro Civil)`);
      
      let locMsg = "";
      if (v.reg === "fortaleza") {{
        locMsg = "Resido atualmente em Eusébio/CE, com total disponibilidade para atuação presencial imediata em Fortaleza, Região Metropolitana e Pecém.";
      }} else if (v.reg === "caruaru") {{
        const cid = (v.local || "Caruaru").split("(")[0].trim();
        locMsg = `Estou em processo de mudança planejada para Caruaru/PE, com disponibilidade para atuação presencial imediata em ${{cid}} e em todo o Agreste e eixo da BR-232.`;
      }} else {{
        locMsg = "Conto com estrutura completa para atuação 100% remota imediata e disponibilidade para viagens técnicas sempre que necessário.";
      }}

      const pdfUrl = `${{GITHUB_PAGES_BASE}}/pdf/${{encodeURIComponent(v.pdf)}}`;

      const corpo = encodeURIComponent(
        `Prezada equipe de seleção e RH da ${{v.empresa}},\\n\\n` +
        `Apresento meu currículo para avaliação na oportunidade de ${{tituloVaga}}.\\n\\n` +
        `Sou Engenheiro Civil graduado pela UFERSA, com pós-graduação em Construção Civil e MBA em Projetos de Instalações Prediais pelo IPOG. Nos últimos 5 anos, atuei diretamente com engenharia de custos, orçamentos executivos (CPUs, SINAPI/SICRO), planejamento físico-financeiro e gestão de obras públicas e privadas.\\n\\n` +
        `Na SS&B Construtora, estruturei um banco próprio com mais de 250 composições de custos unitários e conduzi a revisão técnica e tributária do orçamento de um contrato de R$ 60 milhões, viabilizando uma redução real de R$ 1,2 milhão no fechamento. Antes disso, exerci o cargo de Diretor de Engenharia na Prefeitura de Mossoró, coordenando equipes multidisciplinares e fiscalização de obras hospitalares e educacionais, onde liderei uma revisão técnica que evitou perdas estimadas em 10% do custo da obra.\\n\\n` +
        `${{locMsg}}\\n\\n` +
        `📄 Link direto para o meu currículo completo em PDF:\\n${{pdfUrl}}\\n\\n` +
        `O currículo detalha minha experiência com AutoCAD, Revit (BIM), MS Project, Eberick e bases referenciais de preços. Fico à disposição para uma entrevista.\\n\\n` +
        `Atenciosamente,\\n` +
        `Marcos Denílson Barbosa dos Santos (Denilson Barbosa)\\n` +
        `Engenheiro Civil | CREA Ativo\\n` +
        `Telefone/WhatsApp: (88) 9627-1246\\n` +
        `E-mail: denilsonb20@gmail.com\\n` +
        `LinkedIn: https://linkedin.com/in/denilsonbarbosasantos`
      );

      return `mailto:${{v.email}}?subject=${{assunto}}&body=${{corpo}}`;
    }}

    function renderVagas() {{
      const container = document.getElementById("jobs-container");
      container.innerHTML = "";
      const lista = VAGAS.filter(v => {{
        if (foiClicada(v)) return false;
        if (v.dias !== undefined && v.dias > 7) return false;
        const okPlat = (filtroPlat === "todas") || (v.plat === filtroPlat);
        const okReg = (filtroReg === "todas") || (v.reg === filtroReg);
        return okPlat && okReg;
      }});

      if (lista.length === 0) {{
        container.innerHTML = `<div class="p-6 text-center text-sm text-[var(--muted-foreground)] bg-[var(--background)] border border-[var(--border)] rounded-xl">Nenhuma vaga não lida (≤ 7 dias) neste filtro. Clique em <strong>Varredura Ao Vivo</strong> ou altere os filtros acima.</div>`;
        return;
      }}

      lista.forEach(v => {{
        let platColor = "bg-blue-500/15 text-blue-300 border-blue-500/30";
        if (v.plat === "Mural Construtora (RH)") {{
          platColor = "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
        }} else if (v.plat === "Indeed") {{
          platColor = "bg-indigo-500/15 text-indigo-300 border-indigo-500/30";
        }} else if (v.plat === "Gupy") {{
          platColor = "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
        }} else if (v.plat === "Publicação LinkedIn") {{
          platColor = "bg-purple-500/15 text-purple-300 border-purple-500/30";
        }}

        const safeId = String(v.id).replace(/'/g, "");
        const safeUrl = String(v.url || "").replace(/'/g, "");

        const emailBtn = v.email
          ? `<a href="${{obterMailtoLink(v)}}" onclick="registrarCliqueVaga('${{safeId}}', '${{safeUrl}}')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md flex items-center gap-1.5 transition-all"><span>✉️</span> Candidatura Rápida (1 Toque)</a>`
          : "";

        const card = document.createElement("div");
        card.className = "bg-[var(--background)] border border-[var(--border)] rounded-xl p-4 hover:border-blue-500/40 transition-all";
        card.innerHTML = `
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <span class="px-2 py-0.5 rounded text-xs font-bold border ${{platColor}}">${{v.plat}}</span>
                <span class="px-2 py-0.5 rounded text-xs font-semibold bg-[var(--card)] border border-[var(--border)]">${{v.regLabel}}</span>
                <span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300">🕒 ${{v.recencia}}</span>
                <span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-500/20 text-blue-300">Afinidade: ${{v.score}}%</span>
              </div>
              <h4 class="font-bold text-base text-[var(--foreground)]">${{v.titulo}} <span class="text-blue-400 font-semibold">@ ${{v.empresa}}</span></h4>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">📍 ${{v.local}} &nbsp;|&nbsp; 📄 Anexar: <strong>${{v.pdf}}</strong></p>
            </div>
            <div class="flex flex-wrap items-center gap-2 shrink-0 mt-2 md:mt-0">
              ${{emailBtn}}
              <button onclick="verCarta('${{safeId}}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] border border-[var(--border)] hover:bg-blue-600 hover:text-white transition-colors cursor-pointer">
                Ver Carta
              </button>
              <a href="${{v.url}}" target="_blank" onclick="registrarCliqueVaga('${{safeId}}', '${{safeUrl}}')" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 transition-colors">
                Abrir Portal ↗
              </a>
              <button onclick="registrarCliqueVaga('${{safeId}}', '${{safeUrl}}')" title="Marcar como já vista e ocultar" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] border border-[var(--border)] text-[var(--muted-foreground)] hover:text-rose-400 cursor-pointer">
                ✕ Já vi
              </button>
            </div>
          </div>
          <p class="text-xs text-[var(--muted-foreground)] mt-2">${{v.resumo}}</p>
          <p class="text-xs text-emerald-400/90 mt-1"><strong>Por que se candidatar:</strong> ${{v.motivo}}</p>
        `;
        container.appendChild(card);
      }});
    }}

    function verCarta(id) {{
      const v = VAGAS.find(x => String(x.id) === String(id));
      if (!v) return;
      const box = document.getElementById("carta-box");
      box.classList.remove("hidden");
      document.getElementById("carta-titulo").textContent = `Carta de Apresentação: ${{v.titulo}} (${{v.empresa}})`;
      document.getElementById("carta-pdf-indicado").textContent = `Anexar o currículo: ${{v.pdf}}`;

      let locMsg = "";
      if (v.reg === "fortaleza") {{
        locMsg = "Resido atualmente em Eusébio/CE, com disponibilidade imediata para atuação presencial em Fortaleza, Região Metropolitana e eixo do Pecém.";
      }} else if (v.reg === "caruaru") {{
        locMsg = `Estou em processo de mudança planejada para Caruaru/PE, com disponibilidade imediata para atuação presencial em ${{v.local.split('(')[0].trim()}} e em todo o Agreste e eixo da BR-232.`;
      }} else {{
        locMsg = "Conto com estrutura completa para atuação remota imediata e disponibilidade para viagens técnicas sempre que necessário.";
      }}

      const pdfUrl = `${{GITHUB_PAGES_BASE}}/pdf/${{encodeURIComponent(v.pdf)}}`;
      const texto = `Assunto: Candidatura: ${{v.titulo}} - Denilson Barbosa (Engenheiro Civil)\\n\\nPrezada equipe de seleção da ${{v.empresa}},\\n\\nEnvio meu currículo para avaliação na oportunidade de ${{v.titulo}}.\\n\\nSou Engenheiro Civil graduado pela UFERSA, com pós-graduação em Construção Civil e MBA em Projetos de Instalações Prediais pelo IPOG. Nos últimos cinco anos, atuei diretamente com engenharia de custos, planejamento físico-financeiro e gestão de obras públicas e privadas.\\n\\nAtualmente, como Engenheiro Orçamentista na SS&B Construtora, estruturei um banco próprio com mais de 250 composições de custos unitários (CPUs) e conduzi a revisão técnica e tributária de um orçamento de R$ 60 milhões, gerando uma redução real de R$ 1,2 milhão que viabilizou o fechamento do contrato. Antes disso, exerci o cargo de Diretor de Engenharia na Prefeitura de Mossoró, coordenando equipes multidisciplinares, medições e compatibilização de projetos em obras hospitalares e educacionais, onde liderei uma revisão estrutural de emergência que evitou perdas estimadas em 10% do custo da obra.\\n\\n${{locMsg}}\\n\\n📄 Link direto para download do currículo completo em PDF:\\n${{pdfUrl}}\\n\\nO currículo detalha minha experiência com AutoCAD, Revit (BIM), MS Project, Eberick e bases referenciais de preços (SINAPI, SICRO e composições próprias). Fico à disposição para uma entrevista.\\n\\nAtenciosamente,\\n\\nMarcos Denílson Barbosa dos Santos (Denilson Barbosa)\\nEngenheiro Civil | CREA Ativo\\n(88) 9627-1246 | denilsonb20@gmail.com\\nlinkedin.com/in/denilsonbarbosasantos`;

      document.getElementById("carta-texto").value = texto;
      box.scrollIntoView({{ behavior: "smooth" }});
    }}

    function copiarCarta() {{
      const ta = document.getElementById("carta-texto");
      ta.select();
      document.execCommand("copy");
    }}

    function sincronizarLinksPdf() {{
      const mapIds = {{
        "dl-for-orc": "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf",
        "dl-for-obr": "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Fortaleza_CE.pdf",
        "dl-car-orc": "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Caruaru_PE.pdf",
        "dl-car-obr": "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Caruaru_PE.pdf"
      }};
      Object.entries(mapIds).forEach(([id, fname]) => {{
        const el = document.getElementById(id);
        if (el) el.href = IS_GITHUB_PAGES ? `./pdf/${{fname}}` : `${{API_BASE}}/pdf/${{fname}}`;
      }});
    }}

    function mesclarVagasApi(listaApi) {{
      if (!Array.isArray(listaApi) || !listaApi.length) return;
      const urlsExistentes = new Set(VAGAS.map(v => v.url));

      listaApi.forEach((item, i) => {{
        const dias = item.dias_atras !== undefined ? Number(item.dias_atras) : 3;
        if (dias > 7) return;
        if (!item.url || urlsExistentes.has(item.url)) return;
        urlsExistentes.add(item.url);

        const platRaw = item.plataforma || "LinkedIn Vagas";
        let plat = "LinkedIn Vagas";
        if (platRaw.includes("Mural Construtora")) plat = "Mural Construtora (RH)";
        else if (platRaw.includes("Gupy")) plat = "Gupy";
        else if (platRaw.includes("Indeed")) plat = "Indeed";
        else if (platRaw.includes("Publicação")) plat = "Publicação LinkedIn";

        const regRaw = (item.categoria_geografica || item.regiao_alvo || "").toLowerCase();
        let reg = "remoto";
        let regLabel = item.categoria_geografica || "Remoto Brasil";
        if (regRaw.includes("fortaleza") || (item.local || "").toLowerCase().includes("ce")) {{
          reg = "fortaleza";
        }} else if (regRaw.includes("caruaru") || regRaw.includes("pe") || (item.local || "").toLowerCase().includes("pe")) {{
          reg = "caruaru";
        }}

        VAGAS.push({{
          id: item.id || `api_${{i}}`,
          plat: plat,
          reg: reg,
          regLabel: regLabel,
          dias: dias,
          recencia: `Há ${{dias}} dia(s) (${{item.data_publicacao || 'Recente'}})`,
          score: item.score_afinidade || item.afinidade_estimada || 88,
          titulo: item.titulo || "Vaga Engenharia Civil",
          empresa: item.empresa || "Empresa / Construtora",
          local: item.local || regLabel,
          pdf: item.curriculo_recomendado || "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf",
          email: item.email_direto || "",
          url: item.url,
          resumo: (item.descricao || item.trecho || `Oportunidade mapeada em ${{plat}} para ${{item.local || regLabel}}.`).slice(0, 260),
          motivo: `Publicada há ${{dias}} dia(s) • Capturada na varredura ao vivo.`
        }});
      }});

      atualizarPlacar();
      renderVagas();
    }}

    async function carregarDadosServidor() {{
      try {{
        // Sincronização bidirecional de vagas descartadas:
        // No celular (GitHub Pages), busca ./vagas_clicadas.json; no PC, busca /api/clicadas
        const clicadasUrl = IS_GITHUB_PAGES ? `./vagas_clicadas.json?t=${{Date.now()}}` : `${{API_BASE}}/api/clicadas`;
        try {{
          const rClic = await fetch(clicadasUrl);
          if (rClic.ok) {{
            const dClic = await rClic.json();
            (dClic.ids || []).forEach(x => clicadasSet.add(String(x)));
            (dClic.urls || []).forEach(x => clicadasSet.add(String(x)));
            salvarClicadasLocal();
          }}
        }} catch (e) {{}}

        const endpoint = IS_GITHUB_PAGES ? `./vagas_mapeadas.json?t=${{Date.now()}}` : `${{API_BASE}}/api/vagas`;
        const res = await fetch(endpoint);
        if (!res.ok) return;
        const data = await res.json();
        if (data.vagas) mesclarVagasApi(data.vagas);
        const badge = document.getElementById("api-badge");
        if (badge) {{
          const vis = VAGAS.filter(v => !foiClicada(v) && (v.dias === undefined || v.dias <= 7)).length;
          badge.textContent = `Ativo (${{vis}} vagas não lidas ≤ 7d)`;
          badge.className = "inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30";
        }}
      }} catch (e) {{}}
    }}

    async function dispararScanPainel() {{
      const btn = document.getElementById("btn-live-scan");
      const txt = document.getElementById("txt-live-scan");
      const wrap = document.getElementById("scan-progress-wrap");
      const bar = document.getElementById("scan-progress-bar");
      const msg = document.getElementById("scan-progress-msg");
      const pct = document.getElementById("scan-progress-pct");
      const badge = document.getElementById("api-badge");

      btn.disabled = true;
      btn.classList.add("opacity-75");
      txt.textContent = "Varrendo vagas de até 7 dias...";
      wrap.classList.remove("hidden");

      if (IS_GITHUB_PAGES) {{
        bar.style.width = "60%";
        pct.textContent = "60%";
        msg.textContent = "Recarregando vagas atualizadas pelo GitHub Actions (≤ 7 dias)...";
        await carregarDadosServidor();
        bar.style.width = "100%";
        pct.textContent = "100%";
        const vis = VAGAS.filter(v => !foiClicada(v)).length;
        msg.textContent = `Lista sincronizada! ${{vis}} vagas não lidas (≤ 7 dias) em exibição.`;
        btn.disabled = false;
        btn.classList.remove("opacity-75");
        txt.textContent = "Varredura Ao Vivo (≤ 7 Dias)";
        return;
      }}

      let p = 15;
      const etapas = [
        "Consultando murais de construtoras locais (BSPAR, Colmeia, C. Rolim, CP Construção)...",
        "Buscando vagas recentes no Indeed Brasil (Fortaleza, Caruaru e Remoto)...",
        "Varrendo LinkedIn Vagas e Publicações recentes (últimos 7 dias)...",
        "Ocultando vagas já clicadas e sincronizando...",
        "Calculando score de afinidade e currículo ideal..."
      ];
      let idx = 0;
      const timer = setInterval(() => {{
        if (p < 92) p += 8;
        bar.style.width = p + "%";
        pct.textContent = p + "%";
        msg.textContent = etapas[idx % etapas.length];
        idx++;
      }}, 2000);

      try {{
        await fetch(`${{API_BASE}}/api/scan`);
        let checks = 0;
        while (checks < 35) {{
          await new Promise(r => setTimeout(r, 2000));
          checks++;
          const rStatus = await fetch(`${{API_BASE}}/api/vagas`);
          if (!rStatus.ok) continue;
          const dStatus = await rStatus.json();
          const st = dStatus.scan_state || {{}};
          if (st.progress_msg) msg.textContent = st.progress_msg;
          if (!st.scanning) {{
            clearInterval(timer);
            bar.style.width = "100%";
            pct.textContent = "100%";
            if (dStatus.vagas) mesclarVagasApi(dStatus.vagas);
            const dt = dStatus.atualizado_em || st.last_scan || "agora";
            const vis = VAGAS.filter(v => !foiClicada(v)).length;
            msg.textContent = `Varredura concluída (${{dt}})! ${{vis}} vagas inéditas (≤ 7 dias) prontas.`;
            if (badge) badge.textContent = `Atualizado (${{dt}})`;
            break;
          }}
        }}
      }} catch (e) {{
        clearInterval(timer);
        msg.textContent = "Servidor local offline. Recarregando dados armazenados.";
      }} finally {{
        btn.disabled = false;
        btn.classList.remove("opacity-75");
        txt.textContent = "Varredura Ao Vivo (≤ 7 Dias)";
      }}
    }}

    let deferredPrompt = null;
    window.addEventListener("beforeinstallprompt", (e) => {{
      e.preventDefault();
      deferredPrompt = e;
    }});

    async function instalarAppCelular() {{
      if (deferredPrompt) {{
        deferredPrompt.prompt();
        const choice = await deferredPrompt.userChoice;
        if (choice.outcome === "accepted") {{
          deferredPrompt = null;
          return;
        }}
      }}
      const box = document.getElementById("pwa-help-box");
      if (box) {{
        box.classList.remove("hidden");
        box.scrollIntoView({{ behavior: "smooth" }});
      }}
    }}

    if ("serviceWorker" in navigator) {{
      navigator.serviceWorker.register("./sw.js").catch(() => {{}});
    }}

    sincronizarLinksPdf();
    atualizarPlacar();
    renderVagas();
    carregarDadosServidor();
  </script>
</body>
</html>
"""

p1 = os.path.join(BASE_DIR, "painel_vagas_caruaru.html")
p2 = os.path.join(BASE_DIR, "index.html")
p3 = os.path.join(ARTIFACT_DIR, "painel_vagas_caruaru.html")

for p in (p1, p2, p3):
    with open(p, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)

print(f"Painel gerado com sucesso com {len(vagas_js)} vagas de no máximo 7 dias!")
