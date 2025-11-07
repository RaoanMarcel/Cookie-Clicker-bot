import tkinter as tk
import threading
import logging
import json
from bot import run_bot

logging.basicConfig(level=logging.INFO)
RECORD_FILE = "cookie_records.json"

def load_record():
    try:
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"max_cookies": 0, "max_cps": 0}

class CookieBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CookieBot 🍪")
        self.root.geometry("650x450")
        self.root.configure(bg="#fdf5e6")  # fundo creme aconchegante

        self.running = False
        self.thread = None

        # Título elegante
        tk.Label(root, text="CookieBot",
                 font=("Segoe UI", 26, "bold"),
                 bg="#fdf5e6", fg="#8b4513").pack(pady=20)

        # Card de recordes
        self.records_frame = tk.Frame(root, bg="#fffaf0", bd=2, relief="groove")
        self.records_frame.pack(pady=20, fill="x", padx=50)

        self.cookies_label = tk.Label(self.records_frame,
                                      text="🏆 Você já conquistou 0 cookies",
                                      font=("Segoe UI", 16),
                                      bg="#fffaf0", fg="#5c4033")
        self.cookies_label.pack(pady=10)

        self.cps_label = tk.Label(self.records_frame,
                                  text="⚡ Sua melhor velocidade foi 0 por segundo",
                                  font=("Segoe UI", 16),
                                  bg="#fffaf0", fg="#5c4033")
        self.cps_label.pack(pady=10)

        # Botões estilizados
        self.start_btn = tk.Button(root, text="▶ Iniciar",
                                   font=("Segoe UI", 14, "bold"),
                                   bg="#c3b091", fg="black",
                                   width=18, command=self.start_bot)
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(root, text="■ Parar",
                                  font=("Segoe UI", 14, "bold"),
                                  bg="#a0522d", fg="white",
                                  width=18, state=tk.DISABLED,
                                  command=self.stop_bot)
        self.stop_btn.pack(pady=5)

        # Status
        self.status = tk.Label(root, text="Bot parado ❌",
                               font=("Segoe UI", 12, "italic"),
                               fg="red", bg="#fdf5e6")
        self.status.pack(pady=15)

        # Atualizar recordes
        self.update_records()

    def update_records(self):
        record = load_record()
        self.cookies_label.config(text=f"🏆 Você já conquistou {record['max_cookies']} cookies")
        self.cps_label.config(text=f"⚡ Sua melhor velocidade foi {record['max_cps']} por segundo")

    def start_bot(self):
        if not self.running:
            self.running = True
            self.status.config(text="Bot rodando... 🍪", fg="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.thread = threading.Thread(target=run_bot, daemon=True)
            self.thread.start()

    def stop_bot(self):
        if self.running:
            self.running = False
            self.status.config(text="Bot parado ❌", fg="red")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = CookieBotApp(root)
    root.mainloop()