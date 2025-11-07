import time
import logging
import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COOKIE_URL = "https://orteil.dashnet.org/cookieclicker/"

CLICKS_PER_FRAME = 100
STATE_READ_INTERVAL = 5.0
PURCHASE_INTERVAL = 11.0
RECORD_CHECK_INTERVAL = 60.0   # só checa recordes a cada 60s
RUN_DURATION = None

RECORD_FILE = "cookie_records.json"


# ---------------- DATACLASSES ----------------
@dataclass
class Upgrade:
    id: int
    name: str
    price: float
    can_buy: bool

@dataclass
class Building:
    id: int
    name: str
    price: float
    amount: int

@dataclass
class GameState:
    ready: bool
    cookies: float
    cps: float
    upgrades: List[Upgrade]
    buildings: List[Building]

@dataclass
class Purchase:
    type: str   # "upgrade" ou "building"
    id: int
    name: str
    price: float
# ---------------------------------------------


# ---------------- RECORDES ----------------
def load_record():
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"max_cookies": 0, "max_cps": 0, "history": []}

def save_record(record):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=4, ensure_ascii=False)
# ------------------------------------------


def read_game_state(page) -> GameState:
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
    raw = page.evaluate(script)

    if not raw.get("ready"):
        return GameState(False, 0, 0, [], [])

    upgrades = [Upgrade(id=u["id"], name=u["name"], price=u["price"], can_buy=u["canBuy"]) for u in raw["upgrades"]]
    buildings = [Building(id=b["id"], name=b["name"], price=b["price"], amount=b["amount"]) for b in raw["buildings"]]

    return GameState(
        ready=True,
        cookies=raw["cookies"],
        cps=raw["cps"],
        upgrades=upgrades,
        buildings=buildings
    )


def choose_best_purchase(state: GameState, force_building=False) -> Optional[Purchase]:
    if not force_building:
        for u in state.upgrades:
            if u.can_buy and state.cookies >= u.price:
                return Purchase("upgrade", u.id, u.name, u.price)

    best: Optional[Purchase] = None
    best_eff = 0
    for b in state.buildings:
        if state.cookies < b.price:
            continue
        eff = 1.0 / (b.price * (1 + b.amount))
        if eff > best_eff:
            best_eff = eff
            best = Purchase("building", b.id, b.name, b.price)
    return best


def attempt_purchase(page, purchase: Optional[Purchase]) -> bool:
    if purchase is None:
        return False
    if purchase.type == "upgrade":
        js = f"""
            (function() {{
                let upg = Game.UpgradesInStore.find(u => u.id === {purchase.id});
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
                let obj = Game.ObjectsById[{purchase.id}];
                if (obj && Game.cookies >= obj.getPrice()) {{
                    obj.buy(1);
                    return true;
                }}
                return false;
            }})();
        """
    return page.evaluate(js)


def run_bot():
    record = load_record()

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

        # 🔧 Adaptação: esperar tela de idioma
        page.wait_for_selector("div.langSelectButton", timeout=60000)
        logging.info("Selecionando idioma EN...")
        page.click("div.langSelectButton#langSelect-EN")

        # Se abrir uma nova aba (Cloudflare), fecha e volta para a principal
        if len(context.pages) > 1:
            for extra_page in context.pages[1:]:
                extra_page.close()
            page = context.pages[0]

        # Agora espera o cookie principal
        page.wait_for_selector("#bigCookie", timeout=60000)

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
        next_record_check = time.time()
        start_time = time.time()
        state: GameState = GameState(False, 0, 0, [], [])
        last_purchase_type = None

        try:
            while True:
                now = time.time()

                # leitura do estado
                if now >= next_state:
                    state = read_game_state(page)
                    if state.ready:
                        cookies = int(state.cookies)
                        cps = float(state.cps)
                        logging.info("Cookies: %s | CPS: %.2f", cookies, cps)
                    next_state = now + STATE_READ_INTERVAL

                # verificação de recordes (intervalo maior)
                if now >= next_record_check and state.ready:
                    updated = False
                    cookies = int(state.cookies)
                    cps = float(state.cps)

                    if cookies > record["max_cookies"] * 1.01:  # só salva se for 1% maior
                        record["max_cookies"] = cookies
                        record["history"].append({
                            "type": "cookies",
                            "value": cookies,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        updated = True

                    if cps > record["max_cps"] * 1.01:
                        record["max_cps"] = cps
                        record["history"].append({
                            "type": "cps",
                            "value": cps,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        updated = True

                    if updated:
                        save_record(record)
                        logging.info("🎉 Novo recorde salvo!")

                    next_record_check = now + RECORD_CHECK_INTERVAL

                # compras
                if now >= next_purchase:
                    force_building = (last_purchase_type == "upgrade")
                    purchase = choose_best_purchase(state, force_building=force_building)
                    if purchase:
                        logging.info("Tentando compra: %s (price %s)", purchase.name, purchase.price)
                        ok = attempt_purchase(page, purchase)
                        logging.info("Compra %s", "efetuada" if ok else "falhou")
                        if ok:
                            last_purchase_type = purchase.type
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