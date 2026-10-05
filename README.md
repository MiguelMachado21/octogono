# Octógono em Números

Estatísticas do UFC: perfis de lutadores, lutas, eventos, divisões com gráficos, comparação e agenda dos próximos eventos. Funciona no celular e no notebook.

**Site:** https://miguelmachado21.github.io/octogono/

## Como funciona

- `site/` é o site em si: `index.html` (o app) e os dados que ele lê (`data.json` e `photos.json`).
- `scripts/` baixa e organiza os dados:
  - `build_data.py` puxa as lutas do UFC Stats (pelos arquivos do projeto aberto [scrape_ufc_stats](https://github.com/Greco1899/scrape_ufc_stats)) e os próximos eventos do ufcstats.com, e gera `site/data.json`.
  - `fetch_html.js` abre páginas do ufcstats.com num navegador sem tela, porque o site pede verificação de navegador.
  - `fotos/crawl.js` e `fotos/proc.py` buscam no ufc.com a foto dos lutadores novos e recortam o rosto.
  - `atualizar.sh` roda tudo isso em ordem.
- `.github/workflows/atualizar.yml` roda `atualizar.sh` todo dia às 15:47 (Brasília), salva os dados novos e publica o site no GitHub Pages. Também dá para rodar na hora em **Actions → Atualizar e publicar → Run workflow**.

## Rodar no seu computador

```sh
pip install pillow
npm install -g playwright && npx playwright install chromium
sh scripts/atualizar.sh
cd site && python3 -m http.server 8000   # abra http://localhost:8000
```

Dados: ufcstats.com. Fotos: ufc.com. Projeto pessoal, sem fins comerciais.
