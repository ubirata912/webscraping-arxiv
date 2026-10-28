"""
Atividade: Web Scraping com Requests + BeautifulSoup
Alvo: arXiv - Computer Science / Artificial Intelligence (cs.AI) - envios recentes
URL base: https://arxiv.org/list/cs.AI/recent

O que o script faz:
1. Percorre várias páginas da listagem usando paginação via parâmetros GET
   (?skip=0&show=25, ?skip=25&show=25, ...).
2. Extrai de cada artigo: ID, título, autores, comentários, assuntos e links.
3. Trata irregularidades do HTML (campos ausentes, rótulos "Title:" misturados
   no texto, quantidade variável de autores/assuntos, classes com sufixos extras).
4. Salva o resultado em editais_extraidos.csv e editais_extraidos.json.

"""

import csv
import json
import time

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
URL_BASE = "https://arxiv.org/list/cs.AI/recent"
ITENS_POR_PAGINA = 25          # valor do parâmetro GET "show"
NUM_PAGINAS = 3                # 3 x 25 = 75 registros (mínimo exigido: 30)
INTERVALO_SEGUNDOS = 3         # pausa entre requisições (boa prática com o arXiv)

HEADERS = {
    # Identifica o script de forma honesta, em vez de fingir ser um navegador
    "User-Agent": "Mozilla/5.0 (atividade academica Unicruz - web scraping de metadados)"
}

ARQUIVO_CSV = "editais_extraidos.csv"
ARQUIVO_JSON = "editais_extraidos.json"


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def texto_limpo(tag, rotulo=None):
    """
    Retorna o texto de uma tag sem espaços/quebras extras.
    - Se a tag não existir (campo ausente no HTML), devolve string vazia
      em vez de quebrar o script com AttributeError.
    - Se 'rotulo' for informado (ex.: "Title:"), remove esse prefixo,
      porque o arXiv coloca o rótulo dentro da mesma div do conteúdo.
    """
    if tag is None:
        return ""
    # get_text com separador " " evita palavras grudadas quando há tags internas
    texto = " ".join(tag.get_text(" ", strip=True).split())
    if rotulo and texto.startswith(rotulo):
        texto = texto[len(rotulo):].strip()
    return texto


def baixar_pagina(skip):
    """Faz o GET de uma página da listagem usando a paginação por parâmetros."""
    params = {"skip": skip, "show": ITENS_POR_PAGINA}
    resposta = requests.get(URL_BASE, params=params, headers=HEADERS, timeout=30)
    resposta.raise_for_status()  # para o script se vier 4xx/5xx
    print(f"  GET {resposta.url} -> {resposta.status_code}")
    return resposta.text


def extrair_artigos(html, numero_pagina):
    """
    Lê o HTML de uma página e devolve uma lista de dicionários (um por artigo).

    Estrutura do arXiv: os artigos ficam numa lista de definição <dl>.
    Cada artigo é um PAR de tags irmãs:
        <dt>  -> número, ID e links (abs, pdf, html)
        <dd>  -> metadados (título, autores, comentários, assuntos)
    Por isso percorremos os <dt> e pegamos o <dd> irmão seguinte.
    """
    soup = BeautifulSoup(html, "html.parser")
    registros = []

    # Os blocos de listagem podem ter id="articles" ou não, dependendo da versão
    # do layout; por isso buscamos todos os <dl> e usamos o que tem <dt>.
    listas = soup.select("dl#articles") or soup.find_all("dl")

    for lista in listas:
        for dt in lista.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd is None:          # par incompleto: ignora com segurança
                continue

            # Data da listagem: o <h3> fica DENTRO do <dl>, intercalado com os
            # pares <dt>/<dd>, e um mesmo bloco pode ter vários dias. Por isso
            # buscamos o <h3> mais próximo ANTES de cada <dt>.
            # Ex.: "Tue, 27 Oct 2026 (continued, showing 25 of 433 entries )"
            cabecalho = dt.find_previous("h3")
            data_listagem = texto_limpo(cabecalho).split("(")[0].strip()

            # --- ID e links (no <dt>) ------------------------------------
            # Seleciona pelo atributo href (mais estável que a classe do link)
            link_abs = dt.select_one('a[href^="/abs/"]')
            if link_abs is None:    # sem ID não dá para identificar o artigo
                continue
            arxiv_id = link_abs["href"].replace("/abs/", "").strip()

            link_pdf = dt.select_one('a[href^="/pdf/"]')
            url_pdf = "https://arxiv.org" + link_pdf["href"] if link_pdf else ""

            # --- Metadados (no <dd>) -------------------------------------
            # Seletores por "classe contém" ([class*=...]) porque as divs têm
            # classes compostas e variáveis, ex.: "list-title mathjax".
            titulo = texto_limpo(dd.select_one("div[class*='list-title']"), "Title:")

            # Autores: quantidade variável de <a>; juntamos todos em uma string.
            div_autores = dd.select_one("div[class*='list-authors']")
            autores = [a.get_text(strip=True) for a in div_autores.find_all("a")] if div_autores else []

            # Comentários: campo OPCIONAL (muitos artigos não têm).
            comentarios = texto_limpo(dd.select_one("div[class*='list-comments']"), "Comments:")

            # Assuntos: o principal fica num <span class="primary-subject">,
            # os demais vêm como texto separado por ";".
            div_assuntos = dd.select_one("div[class*='list-subjects']")
            assuntos = texto_limpo(div_assuntos, "Subjects:")
            primario = div_assuntos.select_one("span.primary-subject") if div_assuntos else None
            assunto_primario = texto_limpo(primario) or (assuntos.split(";")[0].strip() if assuntos else "")

            # Referência a periódico: também opcional
            periodico = texto_limpo(dd.select_one("div[class*='list-journal-ref']"), "Journal-ref:")

            registros.append({
                "arxiv_id": arxiv_id,
                "titulo": titulo,
                "autores": "; ".join(autores),
                "qtd_autores": len(autores),
                "assunto_primario": assunto_primario,
                "assuntos": assuntos,
                "comentarios": comentarios,
                "periodico": periodico,
                "data_listagem": data_listagem,
                "url_resumo": f"https://arxiv.org/abs/{arxiv_id}",
                "url_pdf": url_pdf,
                "pagina_coleta": numero_pagina,
            })

    return registros


def salvar_csv(registros, caminho):
    """Salva em CSV com UTF-8 + BOM (abre certinho no Excel com acentos)."""
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=registros[0].keys())
        writer.writeheader()
        writer.writerows(registros)


def salvar_json(registros, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------
def main():
    todos = []
    ids_vistos = set()  # evita duplicados caso a listagem mude durante a coleta

    for pagina in range(NUM_PAGINAS):
        skip = pagina * ITENS_POR_PAGINA
        print(f"Página {pagina + 1}/{NUM_PAGINAS} (skip={skip})")

        try:
            html = baixar_pagina(skip)
        except requests.RequestException as erro:
            print(f"  Falha na requisição: {erro}. Pulando esta página.")
            continue

        novos = 0
        for registro in extrair_artigos(html, pagina + 1):
            if registro["arxiv_id"] not in ids_vistos:
                ids_vistos.add(registro["arxiv_id"])
                todos.append(registro)
                novos += 1
        print(f"  {novos} artigos extraídos")

        if novos == 0:      # chegou ao fim da listagem
            break
        time.sleep(INTERVALO_SEGUNDOS)

    if not todos:
        print("Nenhum registro coletado.")
        return

    salvar_csv(todos, ARQUIVO_CSV)
    salvar_json(todos, ARQUIVO_JSON)
    print(f"\nTotal: {len(todos)} registros salvos em {ARQUIVO_CSV} e {ARQUIVO_JSON}")


if __name__ == "__main__":
    main()
