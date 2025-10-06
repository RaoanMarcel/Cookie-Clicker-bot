import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COOKIE_URL = "https://orteil.dashnet.org/cookieclicker/"

CLICKS_PER_FRAME = 100       # número de cliques por frame (~60 fps)
STATE_READ_INTERVAL = 5.0    # lê o estado a cada 5s
PURCHASE_INTERVAL = 28.0     # tenta comprar a cada 28s
RUN_DURATION = None


def read_game_state(page):
    script = """
        (function() {
            if (typeof Game === 'undefined') return {ready:false};
            try {
                return {
                    ready: true,
                    cookies: Game.cookies,
                    cps: Game.cookiesPs,
                    upgrades: Game.UpgradesInStore.map(u => ({
                        id: u.id, name: u.name, price: u.getPrice(), canBuy: u.canBuy && !u.bought
                    })),
                    buildings: Game.ObjectsById.map(o => ({
                        id: o.id, name: o.name, price: o.getPrice(), amount: o.amount
                    }))
                };
            } catch(e) {
                return {ready:false, error:String(e)};
            }
        })();
    """
    return page.evaluate(script)


def choose_best_purchase(state, force_building=False):
    if not force_building:
        for u in state.get("upgrades", []):
            if u.get("canBuy") and state["cookies"] >= u["price"]:
                return {"type": "upgrade", "id": u["id"], "name": u["name"], "price": u["price"]}

    best = None
    best_eff = 0
    for b in state.get("buildings", []):
        if state["cookies"] < b["price"]:
            continue
        eff = 1.0 / (b["price"] * (1 + b["amount"]))
        if eff > best_eff:
            best_eff = eff
            best = {"type": "building", "id": b["id"], "name": b["name"], "price": b["price"]}
    return best


def attempt_purchase(page, purchase):
    if purchase is None:
        return False
    if purchase["type"] == "upgrade":
        js = f"""
            (function() {{
                let upg = Game.UpgradesInStore.find(u => u.id === {purchase['id']});
                if (upg && upg.canBuy && !upg.bought) {{
                    upg.buy();
                    return true;
                }}
                return false;
            }})();
        """
    else:
        js = f"""
            (function() {{
                let obj = Game.ObjectsById[{purchase['id']}];
                if (obj && Game.cookies >= obj.getPrice()) {{
                    obj.buy(1);
                    return true;
                }}
                return false;
            }})();
        """
    return page.evaluate(js)


def run_bot():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-infobars"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        logging.info("Abrindo Cookie Clicker...")
        page.goto(COOKIE_URL, timeout=60000)

        page.wait_for_load_state("networkidle")

        for _ in range(60):
            ready = page.evaluate("typeof Game !== 'undefined' && Game.ready;")
            if ready:
                break
            time.sleep(1)

        logging.info("Game pronto. Iniciando auto-click e loop de compras.")

        page.evaluate(f"""
            (function() {{
                function autoClick() {{
                    const cookie = document.querySelector("#bigCookie");
                    if (cookie) {{
                        for (let i = 0; i < {CLICKS_PER_FRAME}; i++) cookie.click();
                    }}
                    requestAnimationFrame(autoClick);
                }}
                autoClick();
            }})();
        """)

        next_state = time.time()
        next_purchase = time.time()
        start_time = time.time()
        state = {}
        last_purchase_type = None

        try:
            while True:
                now = time.time()

                if now >= next_state:
                    state = read_game_state(page)
                    if state.get("ready"):
                        logging.info("Cookies: %s | CPS: %.2f", int(state["cookies"]), float(state["cps"]))
                    next_state = now + STATE_READ_INTERVAL

                if now >= next_purchase:
                    force_building = (last_purchase_type == "upgrade")
                    purchase = choose_best_purchase(state, force_building=force_building)
                    if purchase:
                        logging.info("Tentando compra: %s (price %s)", purchase["name"], purchase["price"])
                        ok = attempt_purchase(page, purchase)
                        logging.info("Compra %s", "efetuada" if ok else "falhou")
                        if ok:
                            last_purchase_type = purchase["type"]
                    next_purchase = now + PURCHASE_INTERVAL

                if RUN_DURATION and (time.time() - start_time) > RUN_DURATION:
                    break

                time.sleep(0.05)

        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
        finally:
            browser.close()
            logging.info("Bot finalizado.")


if __name__ == "__main__":
    run_bot()