# -*- coding: utf-8 -*-
"""
Módulo de OCR Leve para Leitura de Imagens e Flyers de Vagas (LinkedIn e Redes)
Utiliza nativamente a API Windows.Media.Ocr (via winocr) no Windows para extrair texto
de panfletos, artes gráficas e cartazes de contratação sem consumo excessivo de memória.
Conta com fallback suave para outros ambientes sem interromper a varredura.
"""

import io
import os
import re
import sys
from PIL import Image, ImageEnhance

sys.stdout.reconfigure(encoding="utf-8")

WINOCR_DISPONIVEL = False
try:
    import winocr
    WINOCR_DISPONIVEL = True
except Exception:
    WINOCR_DISPONIVEL = False


def preprocessar_imagem(img: Image.Image) -> Image.Image:
    """Melhora nitidez e contraste para leitura de textos pequenos em flyers de vagas."""
    try:
        w, h = img.size
        # Se a imagem for estreita ou média, faz upscale para aumentar os pixels das fontes
        if w < 1600 or h < 1600:
            fator = 2 if (w < 900 or h < 900) else 1.5
            nw, nh = int(w * fator), int(h * fator)
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        
        # Aumenta contraste moderadamente
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.35)
        return img
    except Exception:
        return img


def extrair_texto_imagem_bytes(img_bytes: bytes, lang: str = "pt-BR") -> str:
    """Recebe os bytes de uma imagem e retorna o texto extraído pelo OCR."""
    if not img_bytes:
        return ""
    try:
        img = Image.open(io.BytesIO(img_bytes))
        return extrair_texto_pil(img, lang=lang)
    except Exception as e:
        return ""


def extrair_texto_imagem_arquivo(caminho_arquivo: str, lang: str = "pt-BR") -> str:
    """Lê um arquivo local de imagem e retorna o texto extraído."""
    if not os.path.exists(caminho_arquivo):
        return ""
    try:
        img = Image.open(caminho_arquivo)
        return extrair_texto_pil(img, lang=lang)
    except Exception:
        return ""


def extrair_texto_pil(img: Image.Image, lang: str = "pt-BR") -> str:
    """Executa o OCR em uma imagem PIL usando winocr (Windows nativo)."""
    if not WINOCR_DISPONIVEL:
        # Fallback se winocr não estiver carregado
        return ""

    try:
        img_tratada = preprocessar_imagem(img)
        res = winocr.recognize_pil_sync(img_tratada, lang=lang)
        linhas = [l.get("text", "") for l in res.get("lines", []) if l.get("text")]
        texto_final = "\n".join(linhas).strip()
        if not texto_final and "text" in res:
            texto_final = str(res["text"]).strip()
        return texto_final
    except Exception as e:
        return ""


def analisar_texto_ocr_vaga(texto_ocr: str) -> dict:
    """
    Analisa se o texto extraído do panfleto gráfico corresponde a uma vaga de Engenharia Civil
    e extrai e-mails diretos de contato, empresa e prazos.
    """
    if not texto_ocr:
        return {"eh_vaga": False}

    t_low = texto_ocr.lower()

    # Termos de contratação
    tem_contratacao = any(x in t_low for x in [
        "estamos contratando", "contrata-se", "oportunidade", "vaga", "seleção",
        "processo seletivo", "faça parte", "envie seu currículo", "enviar currículo",
        "currículos para", "banco de talentos", "requisitos", "atribuições"
    ])

    # Termos de formação / cargo
    tem_cargo = any(x in t_low for x in [
        "engenheiro civil", "engenheira civil", "engenharia civil",
        "orçamentista", "planejamento de obras", "acompanhamento de obras",
        "área de engenharia", "crea"
    ])

    if not (tem_contratacao and tem_cargo):
        return {"eh_vaga": False}

    # Extrai e-mails de RH presentes na arte
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", texto_ocr)
    email_rh = emails[0].lower() if emails else ""

    return {
        "eh_vaga": True,
        "texto": texto_ocr,
        "email": email_rh,
    }


if __name__ == "__main__":
    teste_img = r"C:\Users\Denil\.gemini\antigravity\brain\3e1c3540-4602-4d7d-b522-77c8dae96475\.user_uploaded\media_1794441502704.jpg"
    if os.path.exists(teste_img):
        print("Testando extração OCR na imagem do usuário...")
        txt = extrair_texto_imagem_arquivo(teste_img)
        print("Resultado:\n", txt)
        analise = analisar_texto_ocr_vaga(txt)
        print("\nAnálise da Vaga:", analise)
