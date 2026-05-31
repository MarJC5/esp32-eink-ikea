#!/usr/bin/env python3
"""
epd_gui.py — petite app de bureau (Tkinter) pour pousser une image ou du texte
sur l'écran e-ink via le push série, avec aperçu. Aucune ligne de commande.

Lancement : python tools/epd_gui.py   (ou : make gui)
Dépendances : pillow, pyserial, tkinter (stdlib ; macOS : brew install python-tk).
"""
import os
import queue
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import ImageTk
import epd_push as ep

PREVIEW_SCALE = 2   # 384x168 -> 768x336


class App:
    def __init__(self, root):
        self.root = root
        root.title("e-ink — envoyer du contenu")
        self.q = queue.Queue()
        self.image_path = None
        self._preview_job = None
        self._tkimg = None

        main = ttk.Frame(root, padding=10)
        main.pack(fill="both", expand=True)

        # --- Port série ---
        top = ttk.Frame(main); top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Port :").pack(side="left")
        self.port = tk.StringVar(value=ep.default_port())
        self.port_menu = ttk.Combobox(top, textvariable=self.port, width=34,
                                      values=ep.list_ports_pref())
        self.port_menu.pack(side="left", padx=4)
        ttk.Button(top, text="⟳", width=3, command=self.refresh_ports).pack(side="left")

        # --- Source : image / texte ---
        self.source = tk.StringVar(value="image")
        src = ttk.LabelFrame(main, text="Contenu", padding=8); src.pack(fill="x")
        row = ttk.Frame(src); row.pack(fill="x")
        ttk.Radiobutton(row, text="Image", variable=self.source, value="image",
                        command=self.on_change).pack(side="left")
        ttk.Radiobutton(row, text="Texte", variable=self.source, value="text",
                        command=self.on_change).pack(side="left", padx=(10, 0))

        irow = ttk.Frame(src); irow.pack(fill="x", pady=(6, 0))
        ttk.Button(irow, text="Parcourir…", command=self.pick_image).pack(side="left")
        self.file_lbl = ttk.Label(irow, text="(aucune image)"); self.file_lbl.pack(side="left", padx=6)

        trow = ttk.Frame(src); trow.pack(fill="x", pady=(6, 0))
        self.text = tk.Text(trow, height=3, width=40); self.text.pack(side="left", fill="x", expand=True)
        self.text.bind("<KeyRelease>", lambda e: self.on_change())
        self.tcolor = tk.StringVar(value="black")
        cf = ttk.Frame(trow); cf.pack(side="left", padx=6)
        ttk.Radiobutton(cf, text="noir", variable=self.tcolor, value="black", command=self.on_change).pack(anchor="w")
        ttk.Radiobutton(cf, text="rouge", variable=self.tcolor, value="red", command=self.on_change).pack(anchor="w")

        # --- Options ---
        opt = ttk.LabelFrame(main, text="Options", padding=8); opt.pack(fill="x", pady=8)
        self.dither = tk.StringVar(value="auto")
        self.mode = tk.StringVar(value="cover")
        self.brightness = tk.DoubleVar(value=1.0)
        self.red_level = tk.IntVar(value=110)
        self.invert = tk.BooleanVar(value=False)
        r1 = ttk.Frame(opt); r1.pack(fill="x")
        ttk.Label(r1, text="Tramage").pack(side="left")
        ttk.OptionMenu(r1, self.dither, "auto", "auto", "floyd3", "floyd", "ordered", "none",
                       command=lambda *_: self.on_change()).pack(side="left", padx=4)
        ttk.Label(r1, text="Cadrage").pack(side="left", padx=(10, 0))
        ttk.OptionMenu(r1, self.mode, "cover", "cover", "fit", "stretch",
                       command=lambda *_: self.on_change()).pack(side="left", padx=4)
        ttk.Checkbutton(r1, text="inverser", variable=self.invert, command=self.on_change).pack(side="left", padx=10)
        r2 = ttk.Frame(opt); r2.pack(fill="x", pady=(6, 0))
        ttk.Label(r2, text="Luminosité").pack(side="left")
        ttk.Scale(r2, from_=0.4, to=1.8, variable=self.brightness, command=lambda *_: self.schedule_preview()).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Label(r2, text="Rouge").pack(side="left")
        ttk.Scale(r2, from_=40, to=200, variable=self.red_level, command=lambda *_: self.schedule_preview()).pack(side="left", fill="x", expand=True, padx=4)

        # --- Position image (zoom + décalage) ---
        pos = ttk.LabelFrame(main, text="Position image", padding=8); pos.pack(fill="x")
        self.zoom = tk.DoubleVar(value=1.0)
        self.offx = tk.DoubleVar(value=0.0)
        self.offy = tk.DoubleVar(value=0.0)
        pr1 = ttk.Frame(pos); pr1.pack(fill="x")
        ttk.Label(pr1, text="Zoom").pack(side="left")
        ttk.Scale(pr1, from_=0.3, to=3.0, variable=self.zoom, command=lambda *_: self.schedule_preview()).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(pr1, text="Recentrer", command=self.recenter).pack(side="left")
        pr2 = ttk.Frame(pos); pr2.pack(fill="x", pady=(6, 0))
        ttk.Label(pr2, text="← X →").pack(side="left")
        ttk.Scale(pr2, from_=-1.0, to=1.0, variable=self.offx, command=lambda *_: self.schedule_preview()).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Label(pr2, text="↑ Y ↓").pack(side="left")
        ttk.Scale(pr2, from_=-1.0, to=1.0, variable=self.offy, command=lambda *_: self.schedule_preview()).pack(side="left", fill="x", expand=True, padx=4)

        # --- Aperçu ---
        self.preview = ttk.Label(main, relief="solid", borderwidth=1)
        self.preview.pack(pady=8)

        # --- Envoyer + log ---
        bottom = ttk.Frame(main); bottom.pack(fill="x")
        self.send_btn = ttk.Button(bottom, text="Envoyer à l'écran", command=self.send)
        self.send_btn.pack(side="left")
        self.status = ttk.Label(bottom, text="prêt"); self.status.pack(side="left", padx=10)
        self.log = tk.Text(main, height=5, width=50, state="disabled"); self.log.pack(fill="x", pady=(8, 0))

        self.on_change()
        self.root.after(100, self.poll)

    # ---------- helpers ----------
    def refresh_ports(self):
        self.port_menu["values"] = ep.list_ports_pref()

    def recenter(self):
        self.zoom.set(1.0); self.offx.set(0.0); self.offy.set(0.0)
        self.schedule_preview()

    def pick_image(self):
        p = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("Tous", "*.*")])
        if p:
            self.image_path = p
            self.file_lbl.config(text=os.path.basename(p))
            self.source.set("image")
            self.on_change()

    def resolved_dither(self):
        d = self.dither.get()
        if d != "auto":
            return d
        return "none" if self.source.get() == "text" else "floyd3"

    def build_image(self):
        if self.source.get() == "text":
            txt = self.text.get("1.0", "end").strip() or " "
            return ep.render_content(text=txt, color=self.tcolor.get())
        if not self.image_path:
            return None
        return ep.render_content(image_path=self.image_path, mode=self.mode.get(),
                                 zoom=self.zoom.get(), off_x=self.offx.get(), off_y=self.offy.get())

    def schedule_preview(self):
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(250, self.update_preview)

    def on_change(self):
        self.schedule_preview()

    def update_preview(self):
        self._preview_job = None
        try:
            img = self.build_image()
        except Exception as e:
            self.set_status(f"erreur image : {e}")
            return
        if img is None:
            self.preview.config(image="", text="(choisis une image)")
            return
        rgb = ep.preview_rgb(img, dither=self.resolved_dither(),
                             red_level=self.red_level.get(),
                             brightness=self.brightness.get(), invert=self.invert.get())
        rgb = rgb.resize((ep.SCREEN_W * PREVIEW_SCALE, ep.SCREEN_H * PREVIEW_SCALE))
        self._tkimg = ImageTk.PhotoImage(rgb)
        self.preview.config(image=self._tkimg, text="")

    def set_status(self, msg):
        self.status.config(text=msg)

    def log_line(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ---------- envoi (thread) ----------
    def send(self):
        try:
            img = self.build_image()
        except Exception as e:
            self.set_status(f"erreur : {e}"); return
        if img is None:
            self.set_status("choisis une image d'abord"); return
        bdata, rdata, w, h = ep.make_frame(img, dither=self.resolved_dither(),
                                           red_level=self.red_level.get(),
                                           brightness=self.brightness.get(),
                                           invert=self.invert.get())
        port = self.port.get()
        self.send_btn.config(state="disabled")
        self.set_status("envoi…")
        self.log_line(f"--- {port} : {len(bdata)} o/plan ---")

        def worker():
            try:
                ok = ep.push(port, bdata, rdata, w, h, log=lambda m: self.q.put(("log", m)))
                self.q.put(("done", ok))
            except Exception as e:
                self.q.put(("log", f"ERREUR : {e}"))
                self.q.put(("done", False))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.log_line(val)
                elif kind == "done":
                    self.send_btn.config(state="normal")
                    self.set_status("OK ✅" if val else "terminé (sans confirmation)")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
