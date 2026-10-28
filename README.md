# Web Scraping do arXiv (cs.AI) com Requests + BeautifulSoup

O script `scraper_arxiv.py` coleta os envios recentes da categoria Inteligência Artificial do arXiv, na página `https://arxiv.org/list/cs.AI/recent`. A paginação é feita por parâmetros GET (`skip` e `show`): são lidas 3 páginas de 25 artigos (`?skip=0&show=25`, `?skip=25&show=25` e `?skip=50&show=25`), com pausa de 3 segundos entre as requisições, e cada artigo é deduplicado pelo seu ID do arXiv. Para lidar com as irregularidades do HTML, o script percorre os pares `<dt>`/`<dd>` da lista `<dl>` usando `find_next_sibling("dd")`. Também usa seletores por classe parcial como `[class*='list-title']`, porque as divs têm classes compostas do tipo `"list-title mathjax"`. Os campos opcionais (comments, journal-ref) usam `select_one` com fallback para string vazia quando não existem. Os rótulos `"Title:"`/`"Subjects:"`, que vêm dentro da mesma div do conteúdo, são removidos, e os links são capturados pelo atributo `a[href^="/abs/"]` (e `/pdf/`) em vez de pela classe. A data de cada artigo vem do `<h3>` mais próximo antes do `<dt>`, já que esse cabeçalho fica dentro do próprio `<dl>`.

## Como executar

```bash
pip install requests beautifulsoup4
python scraper_arxiv.py
```

Os arquivos `editais_extraidos.csv` (UTF-8 com BOM, abre direto no Excel) e `editais_extraidos.json` são gerados na mesma pasta.

## Colunas do CSV

| Coluna | Descrição |
|---|---|
| `arxiv_id` | Identificador do artigo no arXiv |
| `titulo` | Título (sem o rótulo "Title:") |
| `autores` | Autores separados por `; ` |
| `qtd_autores` | Quantidade de autores |
| `assunto_primario` | Assunto principal (ex.: Artificial Intelligence (cs.AI)) |
| `assuntos` | Todos os assuntos, separados por `;` |
| `comentarios` | Comentários do autor (opcional, pode vir vazio) |
| `periodico` | Referência a periódico/journal-ref (opcional, pode vir vazio) |
| `data_listagem` | Data da listagem no arXiv |
| `url_resumo` | Link para a página do resumo |
| `url_pdf` | Link para o PDF |
| `pagina_coleta` | Página da paginação (1 a 3) de onde o registro veio |

## Resultado

Na execução de 27/10/2026 foram coletados **75 registros** (3 páginas × 25), sem duplicados e com título e autores preenchidos em todos.
