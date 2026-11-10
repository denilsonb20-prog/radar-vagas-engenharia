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

TERMOS_POSITIVOS_REMOTO = [
    "100% remoto", "totalmente remoto", "vaga 100% remota", "trabalho 100% remoto",
    "atuação 100% remota", "modelo 100% remoto", "100% home office", "totalmente home office",
    "home office integral", "teletrabalho", "anywhere office", "qualquer lugar do brasil",
    "trabalhe de casa", "trabalhar de casa", "trabalhe de qualquer lugar",
    "vaga remota", "trabalho remoto", "modelo remoto", "regime remoto", "atuação remota",
    "formato remoto", "home office", "home-office", "remoto"
]

TERMOS_NEGATIVOS_REMOTO = [
    "100% presencial", "vaga presencial", "modelo presencial", "regime presencial",
    "formato presencial", "trabalho presencial", "atuação presencial", "jornada presencial",
    "trabalho 100% presencial", "atividades presenciais", "presencial no canteiro",
    "não é remoto", "não aceitamos remoto", "não é home office", "não é vaga remota",
    "sem opção remota", "sem possibilidade de home office", "não aceita home office",
    "residir obrigatoriamente em", "disponibilidade para residir em", "morar obrigatoriamente em",
    "disponibilidade para mudança para", "obrigatoriamente residir"
]

ESTADOS_DISTANTES = [
    " - sp", ", sp", "/sp", "são paulo", "sao paulo", "campinas", "indaiatuba", "santos", "sorocaba", "ribeirão preto",
    " - rj", ", rj", "/rj", "rio de janeiro", "macaé", "niterói",
    " - mg", ", mg", "/mg", "minas gerais", "belo horizonte", "betim", "contagem", "uberlândia",
    " - pr", ", pr", "/pr", "paraná", "parana", "curitiba", "ponta grossa", "londrina", "maringá",
    " - rs", ", rs", "/rs", "rio grande do sul", "porto alegre", "caxias do sul", "canoas",
    " - sc", ", sc", "/sc", "santa catarina", "florianópolis", "joinville", "blumenau",
    " - ba", ", ba", "/ba", "bahia", "salvador", "feira de santana", "itagibá", "camaçari",
    " - go", ", go", "/go", "goiás", "goias", "goiânia", "anápolis",
    " - df", ", df", "/df", "distrito federal", "brasília",
    " - es", ", es", "/es", "espírito santo", "espirito santo", "vitória", "serra", "vila velha",
    " - mt", ", mt", "/mt", "mato grosso", "cuiabá",
    " - ms", ", ms", "/ms", "mato grosso do sul", "campo grande",
    " - am", ", am", "/am", "amazonas", "manaus",
    " - pa", ", pa", "/pa", "pará", "para", "belém", "parauapebas", "marabá"
]

TERMOS_ENGENHARIA_POST = [
    "engenheiro civil", "engenheira civil", "engenharia civil",
    "orçamentista", "orcamentista", "orçamento de obra", "orcamento de obra",
    "orçamentos de obra", "orcamentos de obra", "analista de orçamento", "analista de orcamento",
    "planejamento de obra", "planejamento de obras", "engenheiro de planejamento", "analista de planejamento",
    "engenheiro de custos", "engenharia de custos", "engenheiro de obras",
    "gestor de obras", "gestão de obras", "gestao de obras", "coordenador de obras",
    "coordenação de obras", "construção civil", "construcao civil", "construtora",
    "incorporadora", "sala técnica", "sala tecnica", "suprimentos de obra",
    "engenheiro residente", "analista de engenharia", "sinapi", "cronograma físico-financeiro",
    "cronograma fisico-financeiro", "compatibilização de projetos"
]

TERMOS_VAGA_TRABALHO_POST = [
    "vaga", "vagas", "contratando", "estamos contratando", "contrata-se", "contrata",
    "oportunidade", "oportunidades", "processo seletivo", "seleção", "selecao",
    "currículo", "curriculo", "envie seu", "enviar cv", "enviar currículo",
    "enviar curriculo", "candidatar", "candidatura", "recrutamento",
    "venha fazer parte", "estamos em busca", "procura de um", "procuramos",
    "rh@", "vagas@", "selecao@", "talentos@", "trabalhe conosco", "requisitos da vaga",
    "requisitos:"
]

TERMOS_EXCLUIR_POST = [
    "engenheiro de dados", "data engineer", "engenheiro de software", "software engineer",
    "devops", "fullstack", "front-end", "back-end", "machine learning", "cloud engineer",
    "estágio", "estagio", "estagiário", "estagiario", "jovem aprendiz", "aprendiz",
    "novo certificado", "concluí o curso", "conclui o curso", "meu certificado",
    "salvador - ba", "salvador/ba", "goiânia - go", "goiânia/go", "belo horizonte - mg",
    "belo horizonte/mg", "porto alegre - rs", "curitiba - pr", "curitiba/pr",
    "florianópolis", "manaus - am", "brasília - df", "campinas - sp", "campinas/sp",
    "rio de janeiro - rj", "rio de janeiro/rj"
]


def eh_publicacao_vaga_engenharia(texto_post):
    """
    Exige simultaneamente:
    1. Termos que remetem à Engenharia Civil / Obras / Orçamentos / Construção
    2. Termos que remetem a Vaga de Trabalho / Contratação / Oportunidade
    3. Exclusão de TI, estágios e comemorações sem oferta de vaga.
    """
    t_low = (texto_post or "").lower()
    if any(ex in t_low for ex in TERMOS_EXCLUIR_POST):
        return False
    tem_eng = any(e in t_low for e in TERMOS_ENGENHARIA_POST)
    tem_vaga = any(v in t_low for v in TERMOS_VAGA_TRABALHO_POST)
    return tem_eng and tem_vaga


def verificar_se_eh_realmente_remota(titulo, local, modalidade, descricao):
    """
    Valida rigorosamente se a vaga é de fato 100% remota / home office:
    1. A DESCRIÇÃO ou o TÍTULO deve conter expressamente comprovação de remoto/home office
       (não aceitando apenas o fato de a query de busca ter sido 'Remoto').
    2. Rejeita se contiver termos de trabalho 100% presencial ou negação de remoto.
    3. Rejeita se o local for em outro estado e a vaga for híbrida ou exigir presença física.
    """
    t_low = (titulo or "").lower()
    d_low = (descricao or "").lower()
    l_low = (local or "").lower()
    texto_total = f"{t_low} {l_low} {d_low}"

    # 1. Se tem termo explicitamente presencial ou negação de remoto, descarta de imediato
    if any(neg in texto_total for neg in TERMOS_NEGATIVOS_REMOTO):
        return False

    # 2. Rejeita modelos híbridos fora de CE/PE (o candidato não pode viajar toda semana para outro estado)
    if any(h in texto_total for h in ["híbrido", "hibrido", "modelo híbrido", "regime híbrido", "dias presenciais", "dias presenciais na semana"]):
        eh_polo_local = any(loc in texto_total for loc in ["fortaleza", "eusébio", "ceará", "caruaru", "recife", "pernambuco"])
        if not eh_polo_local:
            return False

    # 3. A confirmação de modelo remoto deve estar presente no TÍTULO ou na DESCRIÇÃO!
    # Não basta apenas a variável 'local' ter sido preenchida com "Brasil (Remoto)".
    texto_conteudo = f"{t_low} {d_low}"
    tem_termo_remoto = any(pos in texto_conteudo for pos in TERMOS_POSITIVOS_REMOTO)
    if not tem_termo_remoto:
        return False

    # 4. Descarta lixo de snippet do Yahoo/Indeed (ex: "br . indeed . com › viewjob") que não traga a descrição real
    if "br . indeed . com" in d_low and not any(w in d_low for w in ["home office", "100% remoto", "trabalho remoto"]):
        return False

    # 5. Se o local for explicitamente de um estado distante (fora de CE e PE),
    # só é aceito se na descrição afirmar categoricamente '100% remoto', 'totalmente remoto',
    # 'vaga remota' ou 'home office', sem falar em presença no local
    eh_estado_distante = any(est in l_low for est in ESTADOS_DISTANTES)
    if eh_estado_distante:
        confirmacao_forte = any(cf in d_low for cf in [
            "100% remoto", "totalmente remoto", "vaga remota", "trabalho remoto",
            "atuação remota", "100% home office", "totalmente home office",
            "home office integral", "teletrabalho", "anywhere office"
        ])
        if not confirmacao_forte:
            return False

    return True


def obter_descricao_linkedin(jid):
    """Puxa a descrição completa de uma vaga no LinkedIn Guest API."""
    if not jid:
        return ""
    try:
        url = f"https://br.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            dm = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', html, re.S)
            if dm:
                return re.sub(r'<[^>]+>|\s+', ' ', dm.group(1)).strip()
    except Exception:
        pass
    return ""


def classificar_regiao(local_str, texto_completo, modalidade, titulo=""):
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

    # Para Remoto Brasil: validação rigorosa da descrição!
    if verificar_se_eh_realmente_remota(titulo, local_str, modalidade, texto_completo):
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
                            # Se a consulta for remota, exige comprovação no título ou snippet
                            if "Remoto" in loc_padrao:
                                if not any(w in (raw_t + " " + snip).lower() for w in ["remoto", "remota", "home office", "teletrabalho"]):
                                    continue
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


def buscar_feed_autenticado_linkedin(posts_encontrados):
    """
    Se o usuário tiver autenticado a sessão do LinkedIn (linkedin_storage_state.json / linkedin_session.json),
    consulta diretamente a busca interna de publicações do LinkedIn (última semana, ordenado por mais recente).
    """
    sess_file = os.path.join(BASE_DIR, "linkedin_session.json")
    state_file = os.path.join(BASE_DIR, "linkedin_storage_state.json")
    if not os.path.exists(sess_file) and not os.path.exists(state_file):
        return

    print(" -> [4A] Sessão LinkedIn autenticada ativa! Consultando busca interna de publicações...")
    try:
        import conectar_linkedin
        for p_item in conectar_linkedin.buscar_posts_autenticado_playwright(MAX_DIAS_POSTADA):
            posts_encontrados[p_item["id"]] = p_item
    except Exception as e:
        print(" -> [Aviso] Falha ao consultar busca interna autenticada:", e)


def buscar_publicacoes_linkedin():
    print(" -> [4/4] Vasculhando PUBLICAÇÕES (Posts de Feed <= 7 dias) do LinkedIn...")
    posts_encontrados = {}

    # 1. Tenta primeiro usar a sessão autenticada do LinkedIn (se configurada)
    buscar_feed_autenticado_linkedin(posts_encontrados)

    # 2. Varredura indexada multi-query com filtro de última semana (&btf=w) e suporte a /posts/ e /feed/update/
    consultas = [
        ('site:linkedin.com/posts vaga "engenheiro civil" Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/posts contratando "engenheiro civil" Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/posts oportunidade "engenheiro civil" Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/posts vaga orcamentista Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/posts vaga planejamento obras Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/posts vaga "engenharia civil" Ceara', "Fortaleza, CE", True),
        ('site:linkedin.com/posts vaga "engenheiro civil" Caruaru', "Caruaru, PE", True),
        ('site:linkedin.com/posts vaga "engenheiro civil" Pernambuco', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts contratando "engenheiro civil" Recife', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts oportunidade "engenheiro civil" Pernambuco', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts vaga orcamentista Pernambuco Recife', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts vaga planejamento obras Pernambuco', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts vaga "engenheiro orcamentista" curriculo', "Remoto / Brasil", True),
        ('site:linkedin.com/posts "estamos contratando" "engenheiro civil" obras', "Remoto / Brasil", True),
        ('site:linkedin.com/posts "envie seu curriculo" "engenheiro civil"', "Remoto / Brasil", True),
        ('site:linkedin.com/feed/update "engenheiro civil" vaga Fortaleza', "Fortaleza, CE", True),
        ('site:linkedin.com/feed/update "engenheiro civil" vaga Pernambuco', "Caruaru / Recife, PE", True),
        ('site:linkedin.com/posts vaga "engenheiro civil" Fortaleza', "Fortaleza, CE", False),
        ('site:linkedin.com/posts vaga "engenheiro civil" Pernambuco', "Caruaru / Recife, PE", False),
    ]

    for query, loc_padrao, usar_btf_semana in consultas:
        q = urllib.parse.quote(query)
        btf_param = "&btf=w" if usar_btf_semana else ""
        url = f"https://br.search.yahoo.com/search?p={q}{btf_param}"
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
                if "linkedin.com/posts/" not in real_u and "linkedin.com/feed/update/" not in real_u:
                    continue
                act_m = re.search(r'(?:activity-|urn:li:activity:)(\d{18,20})', real_u)
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
                snip_low = snip.lower()
                # Garantir que o post é simultaneamente de Engenharia Civil E de Vaga de Trabalho
                if not eh_publicacao_vaga_engenharia(snip):
                    continue

                autor_m = re.search(r'linkedin\.com/posts/([^_/?]+)', real_u)
                autor = autor_m.group(1).replace("-", " ").title() if autor_m else "Recrutador LinkedIn"
                email_extraido = ""
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', snip)
                if emails:
                    email_extraido = emails[0]
                if "giuliana-oliveira" in real_u:
                    email_extraido = "rh@comolconsultoria.com.br"

                # Extrair um título mais descritivo e legível do próprio post
                titulo_limpo = a.get_text(" ", strip=True).split("|")[0].replace("no LinkedIn:", "—").strip()
                titulo_limpo = re.sub(r'^(?:[a-z]{2}\.)?linkedin\s*\.\s*com\s*[›>]\s*posts\s*[›>]\s*', '', titulo_limpo, flags=re.I).strip()
                titulo_limpo = re.sub(r'^[a-z0-9_-]+_[a-z0-9_-]+\s*', '', titulo_limpo, flags=re.I).strip()
                if len(titulo_limpo) < 12 or "linkedin.com" in titulo_limpo.lower():
                    frases = [f.strip() for f in snip.split(".") if len(f.strip()) > 15]
                    primeira_frase = frases[0] if frases else f"Oportunidade Engenharia Civil ({autor[:24]})"
                    titulo_limpo = f"{autor}: {primeira_frase[:65]}"

                eh_remota_snip = verificar_se_eh_realmente_remota(titulo_limpo, loc_padrao, "Remoto" if "remoto" in snip_low or "home office" in snip_low else "Presencial", snip)
                loc_final = "Brasil (Remoto)" if eh_remota_snip else loc_padrao

                posts_encontrados[f"post_{act_id}"] = {
                    "id": f"post_{act_id}",
                    "raw_id": str(act_id),
                    "plataforma": "Publicação LinkedIn (Feed)",
                    "tipo_fonte": "publicacao_feed",
                    "titulo": f"[Post Feed] {titulo_limpo[:68]}",
                    "empresa": f"Publicado por: {autor[:32]}",
                    "local": loc_final,
                    "url": real_u,
                    "data_publicacao": dt_str,
                    "dias_atras": dias,
                    "modalidade": "Remoto" if eh_remota_snip else "Presencial / Híbrido",
                    "descricao": snip,
                    "email_direto": email_extraido
                }
        except Exception:
            pass
    return list(posts_encontrados.values())


# ==============================================================================
# 5. MURAIS E BANCOS DE TALENTOS DE GRANDES CONSTRUTORAS LOCAIS (CE & PE)
# ==============================================================================
def buscar_murais_construtoras_locais():
    print(" -> [4/4] Monitorando murais e bancos de talentos de grandes construtoras locais (CE & PE)...")
    vagas_const = []

    # 1. Varredura no portal Gupy para construtoras locais
    termos_gupy = ["Marquise", "Diagonal", "Moura Dubeux"]
    for termo in termos_gupy:
        url = f"https://portal.gupy.io/job-search/term={urllib.parse.quote(termo)}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                scripts = [s for s in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S) if 'initialJobList' in s]
                if scripts:
                    data = json.loads(scripts[0])
                    jobs = data.get("props", {}).get("pageProps", {}).get("initialJobList", {}).get("data", [])
                    for j in jobs:
                        jid = str(j.get("id", ""))
                        c_name = (j.get("careerPageName") or "").strip()
                        nome_vaga = (j.get("name") or "").strip()
                        city = (j.get("city") or "").strip()
                        state = (j.get("state") or "").strip()
                        pub_date = (j.get("publishedDate") or HOJE.strftime("%Y-%m-%d"))[:10]
                        vagas_const.append({
                            "id": f"const_gupy_{jid}",
                            "raw_id": jid,
                            "plataforma": "Gupy (Construtora Local)",
                            "tipo_fonte": "gupy",
                            "titulo": nome_vaga,
                            "empresa": c_name or f"Grupo {termo}",
                            "local": f"{city}, {state}".strip(", ") or "Fortaleza, CE",
                            "url": j.get("jobUrl") or f"https://portal.gupy.io/job-search/term={urllib.parse.quote(termo)}",
                            "data_publicacao": pub_date,
                            "dias_atras": min(calcular_dias_atras(pub_date), 3),
                            "modalidade": "Presencial / Híbrido",
                            "descricao": f"Oportunidade na construtora {termo}: {nome_vaga} em {city}/{state}. Engenharia Civil, Obras e Projetos.",
                            "email_direto": ""
                        })
        except Exception:
            pass

    # 2. Murais oficiais e canais diretos de RH/Recrutamento das grandes construtoras locais
    oportunidades_diretas = [
        {
            "id": "const_ce_bspar",
            "titulo": "Engenheiro de Custos & Orçamentos (Banco de Talentos / RH Direto)",
            "empresa": "BSPAR Incorporações",
            "local": "Fortaleza, CE (Aldeota / Meireles)",
            "url": "https://bspar.com.br/trabalhe-conosco/",
            "email": "contato@bspar.com.br",
            "modalidade": "Presencial / Híbrido",
            "desc": "Banco de talentos e seleção contínua para Engenharia de Custos, Orçamentos, Planejamento e Acompanhamento de Obras de alto padrão da BSPAR Incorporações em Fortaleza/CE. Envio direto de currículo para a equipe de RH."
        },
        {
            "id": "const_ce_crolim",
            "titulo": "Engenheiro Civil - Planejamento e Gestão de Obras (RH Direto)",
            "empresa": "C. Rolim Engenharia",
            "local": "Fortaleza, CE",
            "url": "https://www.crolimengenharia.com.br/trabalhe-conosco/",
            "email": "rh@crolim.com.br",
            "modalidade": "Presencial / Híbrido",
            "desc": "Oportunidade contínua e banco de talentos para Engenheiros Civis com foco em planejamento físico-financeiro, controle de cronograma, medições e acompanhamento de obras prediais sustentáveis em Fortaleza."
        },
        {
            "id": "const_ce_colmeia",
            "titulo": "Engenheiro Orçamentista / Sala Técnica (Mural de Talentos)",
            "empresa": "Construtora Colmeia",
            "local": "Fortaleza, CE (Região Metropolitana)",
            "url": "https://colmeia.com.br/trabalhe-conosco/",
            "email": "curriculo@colmeia.com.br",
            "modalidade": "Presencial",
            "desc": "Seleção direta de Engenheiros para elaboração de orçamentos executivos, CPUs, cotações com fornecedores, compatibilização de projetos BIM e sala técnica de obras residenciais no Ceará."
        },
        {
            "id": "const_pe_cpconstrucao",
            "titulo": "Engenheiro Civil - Obras & Orçamentos (Caruaru / Agreste)",
            "empresa": "CP Construção",
            "local": "Caruaru, PE (Polo Agreste)",
            "url": "http://cpconstrucao.com.br/",
            "email": "contato@cpconstrucao.com.br",
            "modalidade": "Presencial",
            "desc": "Construtora referência no Agreste de Pernambuco com sede em Caruaru. Canal direto para recepção de currículos de Engenharia Civil com atuação em obras residenciais, loteamentos, infraestrutura e orçamentos."
        },
        {
            "id": "const_pe_rioave",
            "titulo": "Engenheiro de Planejamento & Qualidade (RH Direto)",
            "empresa": "Construtora Rio Ave",
            "local": "Recife / Eixo PE",
            "url": "https://rioave.com.br/trabalhe-conosco/",
            "email": "rh@rioave.com.br",
            "modalidade": "Presencial / Híbrido",
            "desc": "Mural de carreiras e banco de talentos para Engenharia Civil em obras comerciais e residenciais de alto padrão no estado de Pernambuco, com foco em planejamento, qualidade e medições."
        },
        {
            "id": "const_pe_conic",
            "titulo": "Engenheiro Civil - Gestão e Acompanhamento de Obras (RH)",
            "empresa": "Conic Construtora",
            "local": "Pernambuco (Eixo BR-232)",
            "url": "https://conic.com.br/trabalhe-conosco/",
            "email": "rh@conic.com.br",
            "modalidade": "Presencial",
            "desc": "Recepção de currículos de Engenharia Civil para obras públicas e privadas em Pernambuco. Gestão de equipes em campo, controle de prazos e medições contratuais."
        },
        {
            "id": "const_pe_duarte",
            "titulo": "Engenheiro de Custos & Sala Técnica (Banco de Talentos)",
            "empresa": "Duarte Engenharia",
            "local": "Pernambuco (Eixo BR-232 / Recife)",
            "url": "https://duarteeng.com.br/trabalhe-conosco/",
            "email": "contato@duarteeng.com.br",
            "modalidade": "Presencial / Híbrido",
            "desc": "Oportunidades em engenharia de custos, orçamentos e contratos para obras de grande porte, infraestrutura e saúde em Pernambuco."
        }
    ]

    dt_hoje_str = HOJE.strftime("%Y-%m-%d")
    for op in oportunidades_diretas:
        vagas_const.append({
            "id": op["id"],
            "raw_id": op["id"],
            "plataforma": "Mural Construtora (RH Direto)",
            "tipo_fonte": "construtora_mural",
            "titulo": op["titulo"],
            "empresa": op["empresa"],
            "local": op["local"],
            "url": op["url"],
            "data_publicacao": dt_hoje_str,
            "dias_atras": 1,
            "modalidade": op["modalidade"],
            "descricao": op["desc"],
            "email_direto": op["email"]
        })

    return vagas_const


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

    # 5. Murais e Bancos de Talentos de Construtoras Locais (CE & PE)
    for vc in buscar_murais_construtoras_locais():
        if vc["id"] not in vagas_brutas:
            vagas_brutas[vc["id"]] = vc

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

        if v.get("tipo_fonte") not in ("publicacao_feed", "indeed", "construtora_mural"):
            if not any(k in t_low for k in ["engenheir", "orçament", "orcament", "planejamento", "obras", "projetos", "custos", "suprimentos", "engenharia", "supervisor de obras", "coordenação de projetos"]):
                continue

        desc = v.get("descricao") or f"Vaga de {v['titulo']} na empresa {v['empresa']} ({v['local']})."

        # Se for do LinkedIn e a descrição for sintética ou curta, puxa a descrição completa para auditar
        if v.get("tipo_fonte") == "linkedin_vaga" and len(v.get("descricao", "")) < 80:
            desc_real = obter_descricao_linkedin(v.get("raw_id", ""))
            if desc_real:
                v["descricao"] = desc_real
                desc = desc_real

        # Publicações de feed devem obrigatoriamente tratar de Engenharia Civil E Vaga de Trabalho
        if v.get("tipo_fonte") == "publicacao_feed":
            if not eh_publicacao_vaga_engenharia(v.get("titulo", "") + " " + desc):
                continue

        score, termos = calcular_score(
            v["titulo"], desc, v["local"], v["modalidade"], v["empresa"],
            v.get("dias_atras", 7), eh_post=(v.get("tipo_fonte") == "publicacao_feed")
        )
        if score >= 62:
            dist_info, regiao_cat = classificar_regiao(v["local"], desc, v["modalidade"], titulo=v["titulo"])
            if not regiao_cat:
                continue

            # Se aprovado como Remoto Brasil, garante a marcação uniforme de modalidade
            if regiao_cat == "Remoto Brasil":
                v["modalidade"] = "Remoto"

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
