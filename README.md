 Cookie Clicker Bot
Um bot automatizado para o jogo [Cookie Clicker](https://orteil.dashnet.org/cookieclicker/), desenvolvido em Python com [Playwright](https://playwright.dev/).  
Ele cuida de clicar no cookie principal milhares de vezes por segundo e ainda compra automaticamente upgrades e construções para maximizar sua produção de cookies.

---

Funcionalidades

- **Auto‑click turbo**: dispara múltiplos cliques por frame usando `requestAnimationFrame`.
- **Compras automáticas**: avalia upgrades e construções disponíveis e compra de forma inteligente.
- **Configuração simples**: ajuste o número de cliques por frame (`CLICKS_PER_FRAME`) no topo do código.
- **Execução em tela cheia**: abre o Cookie Clicker em uma janela de navegador Chromium controlada pelo Playwright.
- **Logs em tempo real**: mostra no console a quantidade de cookies acumulados, CPS (cookies por segundo) e compras realizadas.

---

 Pré‑requisitos

- Python 3.9+  
- [Playwright para Python](https://playwright.dev/python/)  
  Instalação rápida:
  ```bash
  pip install playwright
  playwright install
