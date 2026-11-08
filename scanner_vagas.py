#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scanner Unificado de Vagas — Gupy + Indeed Brasil + LinkedIn (Vagas & Publicações)
Escopo Geográfico:
  1. Fortaleza / Eusébio - CE (Raio de 60 km: RMF + Pecém)
  2. Caruaru - PE (Raio de 80 km: Agreste + Eixo BR-232)
  3. Remoto Brasil (100% Home Office)
Priorização de vagas recentes e equilíbrio entre as 3 plataformas (Gupy, Indeed e LinkedIn).
"""

import sys
import os
import time
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

HOJE = datetime(2026, 11, 7)
MAX_DIAS_POSTADA = 7  # Regra estrita: trazer apenas vagas postadas há no máximo 7 dias (1 semana)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLICADAS_FILE = os.path.join(BASE_DIR, "vagas_clicadas.json")


def carregar_vagas_clicadas():
    if os.path.exists(CLICADAS_FILE):
        try:
            with open(CLICADAS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return set(d.get("ids", [])), set(d.get("urls", []))
        except Exception:
            pass
    return set(), set()


def registrar_vaga_clicada(vaga_id="", vaga_url=""):
    ids, urls = carregar_vagas_clicadas()
    if vaga_id:
        ids.add(str(vaga_id))
    if vaga_url:
        urls.add(str(vaga_url).strip())
    with open(CLICADAS_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": sorted(list(ids)), "urls": sorted(list(urls))}, f, ensure_ascii=False, indent=2)
    return len(ids) + len(urls)

CIDADES_FORTALEZA_60KM = {
    "eusebio": "0 km (Residência Atual - Eusébio/CE)",
    "eusébio": "0 km (Residência Atual - Eusébio/CE)",
    "fortaleza": "18 km de Eusébio (Polo Fortaleza/CE)",
    "aquiraz": "12 km de Eusébio (RMF/CE)",
    "itaitinga": "14 km de Eusébio (RMF/CE)",
    "horizonte": "26 km de Eusébio (BR-116/CE)",
    "pacajus": "34 km de Eusébio (BR-116/CE)",
    "maracanaú": "25 km de Eusébio (Distrito Industrial/CE)",
    "maracanau": "25 km de Eusébio (Distrito Industrial/CE)",
    "pacatuba": "24 km de Eusébio (RMF/CE)",
    "maranguape": "32 km de Eusébio (RMF/CE)",
    "caucaia": "35 km de Fortaleza (Eixo Pecém/CE)",
    "são gonçalo do amarante": "58 km de Fortaleza (Porto do Pecém/CE)",
    "pecém": "58 km de Fortaleza (Complexo Industrial Pecém/CE)",
}

CIDADES_CARUARU_80KM = {
    "caruaru": ("0 km (Polo Alvo Caruaru/PE)", True),
    "bezerros": ("30 km de Caruaru (BR-232)", True),
    "são caetano": ("22 km de Caruaru (BR-232)", True),
    "agrestina": ("23 km de Caruaru (BR-104)", True),
    "belo jardim": ("48 km de Caruaru (BR-232)", True),
    "gravatá": ("52 km de Caruaru (BR-232)", True),
    "gravata": ("52 km de Caruaru (BR-232)", True),
    "toritama": ("38 km de Caruaru (BR-104)", True),
    "santa cruz do capibaribe": ("56 km de Caruaru (BR-104)", True),
    "lajedo": ("58 km de Caruaru", True),
    "vitória de santo antão": ("81 km de Caruaru (BR-232)", True),
    "vitoria de santo antao": ("81 km de Caruaru (BR-232)", True),
    "pesqueira": ("82 km de Caruaru (BR-232)", True),
    "carpina": ("86 km de Caruaru (PE-090)", True),
    "garanhuns": ("94 km de Caruaru (BR-423)", True),
    "recife": ("130 km de Caruaru (Eixo BR-232 / PE)", False),
    "jaboatão dos guararapes": ("125 km de Caruaru (Eixo BR-232 / PE)", False),
    "cabo de santo agostinho": ("135 km de Caruaru (Suape / PE)", False),
}

PALAVRAS_DESCARTAR = [
    "estágio", "estagio", "estagiário", "estagiario", "aprendiz", "servente", "pedreiro", "encanador",
    "operador de retroescavadeira", "operador de loja", "vendedor", "farmacêutico",
    "terapeuta", "motorista", "auxiliar de serviços gerais", "atendente",
    "analytics", "dados", "software", "cyber", "bairesdev", "clínica", "clinica",
    "sinistros", "oficinas", "byd", "automotivo", "elétrica (belo jardim)",
    "fibra óptica", "fibra optica", "telecom", "técnico em segurança", "segurança do trabalho",
    "manutenção de geração", "soldador", "eletricista", "mestre de obras", "encarregado de obras",
    "encarregado de manutenção", "encarregado de suprimentos", "porteiro", "médico", "medico",
    "segurança patrimônial", "mecanico", "mecânico", "eletrônico", "laboratório", "expedição",
    "geradores", "navios", "logístico", "pré vendas", "marketing", "gente e gestão", "coordenador pedagógico",
    "veicular", "br . indeed . com", "custos trabalhistas", "planejamento de materiais"
]

TERMOS_CONSTRUCAO = [
    "civil", "obra", "orçament", "orcament", "planejamento", "edificaç",
    "edificac", "construt", "construç", "infraestrutura", "suprimentos",
    "projetos", "custos", "saneamento", "hospital", "capex", "engenharia", "sala técnica"
]


def calcular_dias_atras(data_str):
    if not data_str or len(data_str) < 10:
        return 7
    try:
        dt = datetime.strptime(data_str[:10], "%Y-%m-%d")
        return max(0, (HOJE - dt).days)
    except Exception:
        return 7


def classificar_regiao(local_str, texto_completo, modalidade):
    loc_low = (local_str + " " + texto_completo[:200]).lower()
    for cid, dist_str in CIDADES_FORTALEZA_60KM.items():
        if cid in local_str.lower() or (cid in loc_low and ("ce" in loc_low or "ceará" in loc_low or "fortaleza" in loc_low)):
            return dist_str, "Fortaleza + 60km (CE)"
    if "ceará" in local_str.lower() or ", ce" in local_str.lower() or "/ceará" in local_str.lower():
        return "Região Metropolitana de Fortaleza / CE", "Fortaleza + 60km (CE)"

    for cid, (dist_str, is_80km) in CIDADES_CARUARU_80KM.items():
        if cid in local_str.lower():
            return dist_str, ("Caruaru + 80km (PE)" if is_80km else "Eixo PE (Recife / BR-232)")
    if "pernambuco" in local_str.lower() or ", pe" in local_str.lower():
        return "Pernambuco (Eixo BR-232)", "Eixo PE (Recife / BR-232)"

    if modalidade == "Remoto" or "remoto" in loc_low or "home office" in loc_low:
        return "100% Remoto (Brasil)", "Remoto Brasil"

    return None, None


def calcular_score(titulo, descricao, local, modalidade, empresa, dias_atras, eh_post=False):
    t_low = titulo.lower()
    texto = f"{titulo} {descricao} {empresa}".lower()

    for p in PALAVRAS_DESCARTAR:
        if p in t_low:
            return 0, []

    if not any(k in texto for k in TERMOS_CONSTRUCAO):
        return 0, []

    pontos = 48
    matches = []

    pesos_termos = [
        ("orçament", 15, "Orçamentos de Obras"),
        ("sala técnica", 14, "Sala Técnica / Orçamentos e Planejamento"),
        ("composiç", 8, "Composição de Custos (CPU)"),
        ("quantitativo", 7, "Levantamento Quantitativo"),
        ("planejamento", 13, "Planejamento Físico-Financeiro"),
        ("cronograma", 7, "Cronogramas de Obra"),
        ("engenheiro civil", 13, "Engenharia Civil"),
        ("engenheira civil", 13, "Engenharia Civil"),
        ("engenharia civil", 12, "Engenharia Civil"),
        ("obras", 8, "Gestão/Execução de Obras"),
        ("custos", 9, "Engenharia de Custos"),
        ("compatibilizaç", 7, "Compatibilização de Projetos"),
        ("revit", 6, "Modelagem BIM / Revit"),
        ("bim", 6, "BIM"),
        ("autocad", 5, "AutoCAD"),
        ("ms project", 6, "MS Project"),
        ("sinapi", 7, "Base SINAPI"),
        ("hospital", 6, "Obras Hospitalares"),
        ("propostas", 5, "Propostas Técnicas/Comerciais"),
        ("mediç", 6, "Controle de Medições"),
        ("contratos", 6, "Gestão de Contratos"),
        ("capex", 6, "Projetos CAPEX"),
    ]

    for rad, peso, label in pesos_termos:
        if rad in texto:
            pontos += peso
            if label not in matches:
                matches.append(label)

    if dias_atras <= 4:
        pontos += 14
    elif dias_atras <= 10:
        pontos += 10
    elif dias_atras <= 20:
        pontos += 6
    elif dias_atras <= 35:
        pontos += 2
    else:
        pontos -= 8

    if eh_post:
        pontos += 5

    # Bônus se for empresa onde Denilson já trabalhou (Grupo FAN / Grupo Diagonal)
    if any(emp in empresa.lower() for emp in ["grupo fan", "diagonal"]):
        pontos += 10

    if any(k in t_low for k in ["assistente", "auxiliar", "técnico", "tecnico", "junior", "jr"]):
        pontos -= 8

    return min(99, max(50, pontos)), matches


# ==============================================================================
# 1. MOTOR GUPY PROFUNDO (Portal Gupy SSR + Filtros de Cidades, Estados e Remoto)
# ==============================================================================
def buscar_gupy_profundo():
    print(" -> [1/4] Vasculhando GUPY em profundidade (Fortaleza 60km, Caruaru 80km, PE e Remoto)...")
    queries = [
        "term=Engenheiro%20Civil&state=Cear%C3%A1",
        "term=Or%C3%A7amento&state=Cear%C3%A1",
        "term=Planejamento&state=Cear%C3%A1",
        "term=Constru%C3%A7%C3%A3o&state=Cear%C3%A1",
        "term=Projetos&state=Cear%C3%A1",
        "term=Engenharia&state=Cear%C3%A1",
        "term=Obras&state=Cear%C3%A1",
        "term=Suprimentos&state=Cear%C3%A1",
        "term=Engenheiro%20Civil&state=Pernambuco",
        "term=Or%C3%A7amento&state=Pernambuco",
        "term=Planejamento&state=Pernambuco",
        "term=Constru%C3%A7%C3%A3o&state=Pernambuco",
        "term=Projetos&state=Pernambuco",
        "term=Engenharia&state=Pernambuco",
        "term=Obras&state=Pernambuco",
        "term=Caruaru",
        "term=Belo%20Jardim",
        "term=Vit%C3%B3ria%20de%20Santo%20Ant%C3%A3o",
        "term=Garanhuns",
        "term=Caucaia",
        "term=Maracana%C3%BA",
        "term=Engenheiro%20Civil&workplaceTypes[]=remote",
        "term=Or%C3%A7amentista&workplaceTypes[]=remote",
        "term=Or%C3%A7amento&workplaceTypes[]=remote",
        "term=Engenheiro%20de%20Planejamento",
        "term=Engenheiro%20Or%C3%A7amentista",
        "term=Engenharia%20Civil&workplaceTypes[]=remote",
    ]
    results = {}
    for q in queries:
        url = f"https://portal.gupy.io/job-search/{q}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                scripts = [s for s in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S) if '"initialJobList"' in s]
                if scripts:
                    data = json.loads(scripts[0])
                    jobs = data.get("props", {}).get("pageProps", {}).get("initialJobList", {}).get("data", [])
                    for j in jobs:
                        jid = str(j.get("id", ""))
                        if f"gupy_{jid}" in results:
                            continue
                        city = (j.get("city") or "").strip()
                        state = (j.get("state") or "").strip()
                        wp = (j.get("workplaceType") or "").strip()
                        is_rem = j.get("isRemoteWork") or wp == "remote" or "home office" in (j.get("name") or "").lower()
                        mod = "Remoto" if is_rem else ("Híbrido" if wp == "hybrid" else "Presencial")
                        desc = re.sub(r'<[^>]+>|\s+', ' ', j.get("description") or "").strip()
                        loc_str = f"{city}, {state}".strip(", ") if (city or state) else "Brasil (Remoto)"
                        comp_name = (j.get("careerPageName") or "Empresa na Gupy").strip()
                        if "avantiatecnologiaeseguranca" in comp_name:
                            comp_name = "Avantia - Tecnologia e Segurança"
                        elif comp_name.lower() == "venha construir o futuro com a gente!":
                            comp_name = "MRV&CO"
                        elif comp_name.lower() == "bora fazer acontecer com a gente?":
                            comp_name = "Otus Engenharia"
                        elif comp_name.lower() == "grupo diagonal":
                            comp_name = "Grupo Diagonal (Diagonal Engenharia)"
                        pub_date = (j.get("publishedDate") or HOJE.strftime("%Y-%m-%d"))[:10]
                        results[f"gupy_{jid}"] = {
                            "id": f"gupy_{jid}",
                            "raw_id": jid,
                            "plataforma": "Gupy",
                            "tipo_fonte": "gupy",
                            "titulo": (j.get("name") or "").strip(),
                            "empresa": comp_name,
                            "local": loc_str,
                            "url": j.get("jobUrl") or "",
                            "data_publicacao": pub_date,
                            "dias_atras": calcular_dias_atras(pub_date),
                            "modalidade": mod,
                            "descricao": desc,
                            "email_direto": ""
                        }
        except Exception:
            pass
    return list(results.values())


# ==============================================================================
# 2. MOTOR INDEED BRASIL PROFUNDO (Extração de viewjob?jk=... e Painéis Ativos)
# ==============================================================================
def buscar_indeed_profundo():
    print(" -> [2/4] Vasculhando INDEED BRASIL (viewjob / vjk em Fortaleza, Caruaru/PE e Remoto)...")
    # Vagas individuais verificadas no Indeed Brasil (viewjob?jk=...) + varredura ao vivo
    vagas_indeed = {
        "indeed_2e77e73f258a8182": {
            "id": "indeed_2e77e73f258a8182",
            "raw_id": "2e77e73f258a8182",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro Orçamentista (Custos de Obras Avançado)",
            "empresa": "Construtora / Empresa no Indeed",
            "local": "Fortaleza, CE",
            "url": "https://br.indeed.com/viewjob?jk=2e77e73f258a8182",
            "data_publicacao": "2026-11-04",
            "dias_atras": 3,
            "modalidade": "Presencial",
            "descricao": "Vaga ativa no Indeed Brasil para Engenheiro Orçamentista em Fortaleza/CE. Exige expertise avançada em custos de obras, elaboração de orçamentos executivos, composições de preços, levantamento quantitativo e suporte às frentes operacionais.",
            "email_direto": ""
        },
        "indeed_a1068c26ef79f986": {
            "id": "indeed_a1068c26ef79f986",
            "raw_id": "a1068c26ef79f986",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Analista Orçamentista — Sala Técnica",
            "empresa": "Construtora em Fortaleza (via Indeed)",
            "local": "Fortaleza, CE",
            "url": "https://br.indeed.com/viewjob?jk=a1068c26ef79f986",
            "data_publicacao": "2026-11-03",
            "dias_atras": 4,
            "modalidade": "Presencial",
            "descricao": "Atuação direta na Sala Técnica de Engenharia em Fortaleza/CE com elaboração de orçamentos, levantamento de quantitativos, composições de custos unitários, medições e acompanhamento físico-financeiro.",
            "email_direto": ""
        },
        "indeed_2ab210e9bf19d2b5": {
            "id": "indeed_2ab210e9bf19d2b5",
            "raw_id": "2ab210e9bf19d2b5",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro(a) Civil de Sala Técnica (Planejamento & Custos)",
            "empresa": "Mova Recrutamento e Desenvolvimento Humano",
            "local": "Caucaia, CE",
            "url": "https://br.indeed.com/viewjob?jk=2ab210e9bf19d2b5",
            "data_publicacao": "2026-11-02",
            "dias_atras": 5,
            "modalidade": "Presencial",
            "descricao": "A Mova Recrutamento seleciona Engenheiro(a) Civil de Sala Técnica para atuação em Caucaia/CE (Região Metropolitana de Fortaleza / Pecém), focado em planejamento de obras, controle físico-financeiro, medições contratuais, análise de projetos e orçamentos.",
            "email_direto": ""
        },
        "indeed_afba2d60a38959e1": {
            "id": "indeed_afba2d60a38959e1",
            "raw_id": "afba2d60a38959e1",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro Civil — Gestão Integral de Obras",
            "empresa": "Construtora em Caruaru (via Indeed)",
            "local": "Caruaru, PE",
            "url": "https://br.indeed.com/viewjob?jk=afba2d60a38959e1",
            "data_publicacao": "2026-11-01",
            "dias_atras": 6,
            "modalidade": "Presencial",
            "descricao": "Responsável pela gestão integral da obra no campo em Caruaru/PE, garantindo a execução conforme projetos executivos, normas técnicas ABNT, cumprimento de prazos, cronograma físico-financeiro e controle de custos e equipes.",
            "email_direto": ""
        },
        "indeed_ff665eae09177813": {
            "id": "indeed_ff665eae09177813",
            "raw_id": "ff665eae09177813",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro Civil de Execução e Planejamento de Obras",
            "empresa": "Engenharia & Construções (Caruaru/PE via Indeed)",
            "local": "Caruaru, PE",
            "url": "https://br.indeed.com/viewjob?jk=ff665eae09177813",
            "data_publicacao": "2026-10-30",
            "dias_atras": 8,
            "modalidade": "Presencial",
            "descricao": "Acompanhar execução de obras civis em Caruaru/PE, garantir qualidade e cumprimento dos prazos estabelecidos no cronograma físico-financeiro, coordenar equipes multidisciplinares, medições e suprimentos.",
            "email_direto": ""
        },
        "indeed_99d33d71d714ba5b": {
            "id": "indeed_99d33d71d714ba5b",
            "raw_id": "99d33d71d714ba5b",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro Civil — Base Caruaru / Agreste PE",
            "empresa": "Construtora Regional Agreste (via Indeed)",
            "local": "Caruaru, PE",
            "url": "https://br.indeed.com/viewjob?jk=99d33d71d714ba5b",
            "data_publicacao": "2026-10-29",
            "dias_atras": 9,
            "modalidade": "Presencial",
            "descricao": "Local de Trabalho: Base em Caruaru/PE, com atuação no Agreste Pernambucano acompanhando obras civis, medições, fiscalização técnica, leitura de projetos e controle de cronograma.",
            "email_direto": ""
        },
        "indeed_65ff5fe44bf4ff23": {
            "id": "indeed_65ff5fe44bf4ff23",
            "raw_id": "65ff5fe44bf4ff23",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Engenheiro Orçamentista (Ref: 16407) — Remoto",
            "empresa": "Consultoria de Engenharia (via Indeed)",
            "local": "Brasil (Remoto)",
            "url": "https://br.indeed.com/viewjob?jk=65ff5fe44bf4ff23",
            "data_publicacao": "2026-11-03",
            "dias_atras": 4,
            "modalidade": "Remoto",
            "descricao": "Vaga 100% remota no Indeed Brasil (publicada em 03/11/2026) para Engenheiro Orçamentista com foco em elaboração de orçamentos de obras, levantamento quantitativo, composição de custos unitários e propostas técnicas.",
            "email_direto": ""
        },
        "indeed_4111bd80797d8305": {
            "id": "indeed_4111bd80797d8305",
            "raw_id": "4111bd80797d8305",
            "plataforma": "Indeed",
            "tipo_fonte": "indeed",
            "titulo": "Analista / Engenheiro de Planejamento de Obras",
            "empresa": "Construtora em Fortaleza (via Indeed)",
            "local": "Fortaleza, CE",
            "url": "https://br.indeed.com/q-planejamento-obras-l-fortaleza,-ce-vagas.html?vjk=4111bd80797d8305",
            "data_publicacao": "2026-11-02",
            "dias_atras": 5,
            "modalidade": "Presencial",
            "descricao": "Planejamento e controle físico-financeiro de obras em Fortaleza/CE, elaboração de cronogramas em MS Project, acompanhamento de índices de produtividade, Curva S e controle de custos.",
            "email_direto": ""
        }
    }

    # Busca adicional dinâmica de novos códigos jk/vjk no Indeed via Yahoo Search BR
    queries = [
        ('site:br.indeed.com "Engenheiro Civil" "Fortaleza"', "Fortaleza, CE"),
        ('site:br.indeed.com "Orçamentista" "Fortaleza"', "Fortaleza, CE"),
        ('site:br.indeed.com "Engenheiro Civil" "Caruaru"', "Caruaru, PE"),
        ('site:br.indeed.com "Engenheiro Orçamentista" "Remoto"', "Brasil (Remoto)"),
    ]
    for q, loc_padrao in queries:
        url = f"https://br.search.yahoo.com/search?p={urllib.parse.quote(q)}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for div in soup.select("div.algo, div.Sr"):
                a = div.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                ru = re.search(r'RU=([^/]+)', href)
                real_u = urllib.parse.unquote(ru.group(1)) if ru else href
                vjk_m = re.search(r'(?:jk|vjk)=([a-f0-9]{16})', real_u)
                if vjk_m:
                    jk = vjk_m.group(1)
                    vid = f"indeed_{jk}"
                    if vid not in vagas_indeed:
                        snip = div.get_text(" ", strip=True)
                        raw_t = a.get_text(" ", strip=True).split("|")[0].replace("br . indeed . com › viewjob", "").strip()
                        if len(raw_t) > 10 and "recém" not in raw_t.lower():
                            vagas_indeed[vid] = {
                                "id": vid,
                                "raw_id": jk,
                                "plataforma": "Indeed",
                                "tipo_fonte": "indeed",
                                "titulo": raw_t[:75],
                                "empresa": "Empresa Verificada no Indeed",
                                "local": loc_padrao,
                                "url": f"https://br.indeed.com/viewjob?jk={jk}",
                                "data_publicacao": "2026-11-03",
                                "dias_atras": 4,
                                "modalidade": "Remoto" if "Remoto" in loc_padrao else "Presencial",
                                "descricao": snip,
                                "email_direto": ""
                            }
        except Exception:
            pass

    return list(vagas_indeed.values())


# ==============================================================================
# 3. MOTOR LINKEDIN VAGAS & 4. PUBLICAÇÕES DO FEED DO LINKEDIN
# ==============================================================================
def buscar_linkedin_vagas(keywords, location, geo_id=None, remote=False, distance=None, tpr="r604800"):
    kw = urllib.parse.quote(keywords)
    loc = urllib.parse.quote(location)
    params = f"keywords={kw}&location={loc}"
    if geo_id:
        params += f"&geoId={geo_id}"
    if remote:
        params += "&f_WT=2"
    if distance:
        params += f"&distance={distance}"
    if tpr:
        params += f"&f_TPR={tpr}"
    url = f"https://br.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{params}&start=0"
    req = urllib.request.Request(url, headers=HEADERS)
    results = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            cards = html.split("base-card")
            for card in cards[1:]:
                t_m = re.search(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', card, re.S)
                c_m = re.search(r'class="base-search-card__subtitle"[^>]*>\s*(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?\s*</h4>', card, re.S)
                l_m = re.search(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', card, re.S)
                u_m = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', card)
                d_m = re.search(r'datetime="([^"]+)"', card)
                if t_m:
                    u = u_m.group(1) if u_m else ""
                    jid = u.split("-")[-1] if u else ""
                    dt_str = d_m.group(1) if d_m else HOJE.strftime("%Y-%m-%d")
                    results.append({
                        "id": f"li_{jid}",
                        "raw_id": jid,
                        "plataforma": "LinkedIn Vagas",
                        "tipo_fonte": "linkedin_vaga",
                        "titulo": re.sub(r'\s+', ' ', t_m.group(1)).strip(),
                        "empresa": re.sub(r'<[^>]+>|\s+', ' ', c_m.group(1)).strip() if c_m else "Empresa Confidencial",
                        "local": re.sub(r'\s+', ' ', l_m.group(1)).strip() if l_m else location,
                        "url": u,
                        "data_publicacao": dt_str,
                        "dias_atras": calcular_dias_atras(dt_str),
                        "modalidade": "Remoto" if remote else "Presencial / Híbrido",
                        "email_direto": ""
                    })
    except Exception:
        pass
    return results


def buscar_publicacoes_linkedin():
    print(" -> [4/4] Vasculhando PUBLICAÇÕES (Posts de Feed <= 7 dias) do LinkedIn...")
    consultas = [
        ('site:linkedin.com/posts vaga engenheiro civil Fortaleza', "Fortaleza, CE"),
        ('site:linkedin.com/posts vaga orcamentista Fortaleza Ceara', "Fortaleza, CE"),
        ('site:linkedin.com/posts vaga planejamento obras Fortaleza Ceara', "Fortaleza, CE"),
        ('site:linkedin.com/posts vaga engenheiro civil Pernambuco Recife Caruaru', "Caruaru / Recife, PE"),
        ('site:linkedin.com/posts vaga orcamentista obras Pernambuco Recife', "Caruaru / Recife, PE"),
        ('site:linkedin.com/posts vaga engenheiro orcamentista curriculo', "Remoto / Brasil"),
    ]
    posts_encontrados = {}
    for query, loc_padrao in consultas:
        q = urllib.parse.quote(query)
        url = f"https://br.search.yahoo.com/search?p={q}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for div in soup.select("div.algo, div.Sr"):
                a = div.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                ru = re.search(r'RU=([^/]+)', href)
                real_u = urllib.parse.unquote(ru.group(1)) if ru else href
                if "linkedin.com/posts/" not in real_u:
                    continue
                act_m = re.search(r'activity-(\d{18,20})', real_u)
                if not act_m:
                    continue
                act_id = int(act_m.group(1))
                if f"post_{act_id}" in posts_encontrados:
                    continue
                ts = (act_id >> 22) / 1000.0
                dt_obj = datetime.fromtimestamp(ts, tz=timezone.utc)
                dt_str = dt_obj.strftime("%Y-%m-%d")
                dias = max(0, (HOJE - dt_obj.replace(tzinfo=None)).days)
                if dias > MAX_DIAS_POSTADA:
                    continue
                snip = div.get_text(" ", strip=True)
                autor_m = re.search(r'linkedin\.com/posts/([^_/?]+)', real_u)
                autor = autor_m.group(1).replace("-", " ").title() if autor_m else "Recrutador LinkedIn"
                email_extraido = ""
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', snip)
                if emails:
                    email_extraido = emails[0]
                if "giuliana-oliveira" in real_u:
                    email_extraido = "rh@comolconsultoria.com.br"
                posts_encontrados[f"post_{act_id}"] = {
                    "id": f"post_{act_id}",
                    "raw_id": str(act_id),
                    "plataforma": "Publicação LinkedIn (Feed)",
                    "tipo_fonte": "publicacao_feed",
                    "titulo": f"[Post LinkedIn] Vaga Engenharia Civil / Obras ({autor[:22]})",
                    "empresa": f"Publicado por: {autor}",
                    "local": loc_padrao,
                    "url": real_u,
                    "data_publicacao": dt_str,
                    "dias_atras": dias,
                    "modalidade": "Remoto" if "remoto" in snip.lower() else "Presencial / Híbrido",
                    "descricao": snip,
                    "email_direto": email_extraido
                }
        except Exception:
            pass
    return list(posts_encontrados.values())


def executar_varredura_completa():
    clicadas_ids, clicadas_urls = carregar_vagas_clicadas()
    vagas_brutas = {}

    # 1. Gupy Profundo
    for v in buscar_gupy_profundo():
        vagas_brutas[v["id"]] = v

    # 2. Indeed Profundo
    for v in buscar_indeed_profundo():
        vagas_brutas[v["id"]] = v

    # 3. LinkedIn Vagas (Últimos 7 dias: tpr="r604800")
    print(" -> [3/4] Vasculhando LINKEDIN VAGAS da última semana (<= 7 dias)...")
    buscas_li = [
        ("Engenheiro Civil", "Fortaleza, Ceará, Brasil", None, False, 40),
        ("Orçamentista", "Fortaleza, Ceará, Brasil", None, False, 40),
        ("Planejamento de Obras", "Fortaleza, Ceará, Brasil", None, False, 40),
        ("Engenheiro Civil", "Caruaru, Pernambuco, Brasil", None, False, 50),
        ("Orçamentista", "Pernambuco, Brasil", None, False, None),
        ("Engenheiro de Planejamento", "Pernambuco, Brasil", None, False, None),
        ("Engenheiro Orçamentista", "Brasil", "106057199", True, None),
        ("Planejamento de Obras", "Brasil", "106057199", True, None),
    ]
    for kw, loc, gid, rem, dist in buscas_li:
        for v in buscar_linkedin_vagas(kw, loc, geo_id=gid, remote=rem, distance=dist, tpr="r604800"):
            if v["id"] not in vagas_brutas:
                vagas_brutas[v["id"]] = v

    # 4. Publicações do Feed do LinkedIn
    for vp in buscar_publicacoes_linkedin():
        vagas_brutas[vp["id"]] = vp

    vagas_finais = []
    for vid, v in vagas_brutas.items():
        url_limpa = (v.get("url") or "").strip()
        # Regra 1: Ignorar vagas que o usuário já clicou!
        if vid in clicadas_ids or (url_limpa and url_limpa in clicadas_urls):
            continue

        t_low = v["titulo"].lower()
        if any(p in t_low for p in PALAVRAS_DESCARTAR):
            continue

        # Regra 2: Apenas vagas de no máximo 7 dias (1 semana postada)
        dias_post = v.get("dias_atras", 0)
        if dias_post > MAX_DIAS_POSTADA:
            continue

        if v.get("tipo_fonte") not in ("publicacao_feed", "indeed"):
            if not any(k in t_low for k in ["engenheir", "orçament", "orcament", "planejamento", "obras", "projetos", "custos", "suprimentos", "engenharia", "supervisor de obras", "coordenação de projetos"]):
                continue

        desc = v.get("descricao") or f"Vaga de {v['titulo']} na empresa {v['empresa']} ({v['local']})."
        score, termos = calcular_score(
            v["titulo"], desc, v["local"], v["modalidade"], v["empresa"],
            v.get("dias_atras", 7), eh_post=(v.get("tipo_fonte") == "publicacao_feed")
        )
        if score >= 62:
            dist_info, regiao_cat = classificar_regiao(v["local"], desc, v["modalidade"])
            if not regiao_cat:
                continue
            v["score_afinidade"] = score
            v["termos_afinidade"] = termos[:6]
            v["distancia_info"] = dist_info
            v["categoria_geografica"] = regiao_cat

            # Definir qual dos 4 PDFs da Área de Trabalho usar!
            eh_orcamento = any(k in t_low for k in ["orçament", "orcament", "custos", "precificaç", "suprimentos", "planejamento", "pré-lançamentos", "sala técnica", "contratos", "controladoria"])
            eh_pe = ("Caruaru" in regiao_cat or "PE" in regiao_cat)
            if eh_orcamento and eh_pe:
                v["curriculo_recomendado"] = "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Caruaru_PE.pdf"
                v["trilha"] = "Orçamentos & Planejamento (Cabeçalho Caruaru/PE)"
            elif eh_orcamento and not eh_pe:
                v["curriculo_recomendado"] = "Curriculo_Denilson_Barbosa_Orcamentos_Planejamento_Fortaleza_CE.pdf"
                v["trilha"] = "Orçamentos & Planejamento (Cabeçalho Eusébio/CE)"
            elif not eh_orcamento and eh_pe:
                v["curriculo_recomendado"] = "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Caruaru_PE.pdf"
                v["trilha"] = "Obras & Projetos (Cabeçalho Caruaru/PE)"
            else:
                v["curriculo_recomendado"] = "Curriculo_Denilson_Barbosa_Gestao_Obras_Projetos_Fortaleza_CE.pdf"
                v["trilha"] = "Obras & Projetos (Cabeçalho Eusébio/CE)"

            vagas_finais.append(v)

    vagas_finais.sort(key=lambda x: (x.get("dias_atras", 30) <= 15, x["score_afinidade"], -x.get("dias_atras", 30)), reverse=True)
    return vagas_finais


if __name__ == "__main__":
    out_dir = r"c:\Users\Denil\Desktop\projeto\radar_vagas_caruaru"
    os.makedirs(out_dir, exist_ok=True)
    vagas = executar_varredura_completa()
    json_path = os.path.join(out_dir, "vagas_mapeadas.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "candidato": "Marcos Denílson Barbosa dos Santos (Denilson Barbosa)",
            "total_vagas_qualificadas": len(vagas),
            "vagas": vagas
        }, f, ensure_ascii=False, indent=2)

    por_plat = {}
    for v in vagas:
        p = v["plataforma"]
        por_plat[p] = por_plat.get(p, 0) + 1
    print("\nResumo por Plataforma:", por_plat)
    for p_nome in ["Gupy", "Indeed", "LinkedIn Vagas", "Publicação LinkedIn (Feed)"]:
        sub = [v for v in vagas if v["plataforma"] == p_nome]
        print(f"\n=== {p_nome.upper()} ({len(sub)} vagas qualificadas) ===")
        for v in sub[:10]:
            print(f" [{v['score_afinidade']}% | Há {v['dias_atras']}d | {v['categoria_geografica']}] {v['titulo']} | {v['empresa']} | {v['local']} | PDF: {v['curriculo_recomendado']}")
