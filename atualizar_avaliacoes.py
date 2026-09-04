#!/usr/bin/env python3
"""
Atualiza o widget de avaliações (avaliacoes-lucas-hopner.html) com os dados
mais recentes do perfil público na Psitto.

Como funciona:
1. Baixa o HTML da página do perfil na Psitto.
2. Localiza o bloco de avaliações verificadas e extrai nome, data e comentário
   de cada uma (o site sempre repete o padrão "Atenção / Pontualidade /
   Ambiente / comentário / nome / data").
3. Substitui o array REVIEWS e o cabeçalho (nota média + total) dentro do
   arquivo HTML do widget, entre os marcadores ===REVIEWS_START=== / ===REVIEWS_END===.

Uso:
    pip install requests beautifulsoup4
    python atualizar_avaliacoes.py

Requisitos de arquivo:
    Este script espera encontrar "avaliacoes-lucas-hopner.html" na mesma pasta.
"""

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PERFIL_URL = "https://www.psitto.com.br/psicologo/lucas-hopner/"
WIDGET_PATH = Path(__file__).parent / "avaliacoes-lucas-hopner.html"
MAX_REVIEWS = 13  # quantas avaliações mais recentes manter no widget

MESES = {
    "janeiro": "jan", "fevereiro": "fev", "março": "mar", "abril": "abr",
    "maio": "mai", "junho": "jun", "julho": "jul", "agosto": "ago",
    "setembro": "set", "outubro": "out", "novembro": "nov", "dezembro": "dez",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AvaliacoesWidgetBot/1.0; "
                  "+contato@seu-dominio.com.br)"
}


def formatar_data(data_extenso: str) -> str:
    """Converte '31/agosto/2026' em '31/ago/2026'."""
    dia, mes, ano = data_extenso.split("/")
    mes_abrev = MESES.get(mes.lower(), mes[:3])
    return f"{dia}/{mes_abrev}/{ano}"


def extrair_avaliacoes(texto: str):
    """
    Percorre o texto visível da página e extrai cada avaliação, que sempre
    segue o padrão:
        Atenção: 5
        Pontualidade: 5
        Ambiente: 5
        <comentário>
        <nome>
        <dd/mês por extenso/aaaa>
    """
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]

    padrao_data = re.compile(r"^\d{1,2}/[a-zçã]+/\d{4}$", re.IGNORECASE)
    avaliacoes = []

    i = 0
    while i < len(linhas):
        if linhas[i].startswith("Atenção:"):
            # pula as 3 linhas de notas (Atenção / Pontualidade / Ambiente)
            j = i + 3
            if j < len(linhas):
                comentario = linhas[j]
                nome = linhas[j + 1] if j + 1 < len(linhas) else ""
                data = linhas[j + 2] if j + 2 < len(linhas) else ""
                if padrao_data.match(data):
                    if "não escreveu comentário" not in comentario.lower():
                        avaliacoes.append({
                            "name": nome,
                            "date": formatar_data(data),
                            "text": comentario,
                        })
                    i = j + 3
                    continue
        i += 1

    return avaliacoes


def extrair_resumo(texto: str):
    """Extrai o total de avaliações verificadas (ex.: 22)."""
    m = re.search(r"Baseado em\D*(\d+)\D*avaliaç(ão|ões) verificad", texto, re.IGNORECASE)
    total = m.group(1) if m else "?"
    return total


def montar_bloco_js(avaliacoes):
    linhas = ["  // ===REVIEWS_START=== (não edite estas duas linhas de marcador — o script de atualização procura por elas)",
              "  const REVIEWS = ["]
    for r in avaliacoes:
        nome = r["name"].replace('"', '\\"')
        texto = r["text"].replace('"', '\\"')
        linhas.append(f'    {{ name:"{nome}", date:"{r["date"]}", text:"{texto}" }},')
    linhas.append("  ];")
    linhas.append("  // ===REVIEWS_END===")
    return "\n".join(linhas)


def atualizar_widget(avaliacoes, total: str):
    html = WIDGET_PATH.read_text(encoding="utf-8")

    novo_bloco = montar_bloco_js(avaliacoes)
    html = re.sub(
        r"  // ===REVIEWS_START===.*?// ===REVIEWS_END===",
        novo_bloco,
        html,
        flags=re.DOTALL,
    )

    html = re.sub(
        r'(<div class="rating-number" id="ratingNumber">).*?(</div>)',
        r"\g<1>5,0\g<2>",
        html,
    )
    html = re.sub(
        r'(<div class="header-sub" id="reviewCount">).*?(</div>)',
        rf"\g<1>Baseado em {total} avaliações verificadas\g<2>",
        html,
    )

    WIDGET_PATH.write_text(html, encoding="utf-8")


def main():
    if not WIDGET_PATH.exists():
        sys.exit(f"Arquivo não encontrado: {WIDGET_PATH}")

    resp = requests.get(PERFIL_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    texto = soup.get_text("\n")

    avaliacoes = extrair_avaliacoes(texto)
    total = extrair_resumo(texto)

    if not avaliacoes:
        sys.exit(
            "Nenhuma avaliação encontrada. O layout da página pode ter mudado — "
            "verifique manualmente e ajuste o padrão de extração no script."
        )

    avaliacoes = avaliacoes[:MAX_REVIEWS]
    atualizar_widget(avaliacoes, total)

    print(f"Widget atualizado com {len(avaliacoes)} avaliações (total no perfil: {total}).")


if __name__ == "__main__":
    main()
