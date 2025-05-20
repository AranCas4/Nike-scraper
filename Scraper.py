import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import re
from datetime import datetime
from urllib.parse import urljoin
import webbrowser
import os
from PIL import Image, ImageTk  

# --- Configuración scraper Nike ---
NIKE_CONFIG = {
    "name": "nike",
    "base_url": "https://www.nike.com/es",
    "search_url": "https://www.nike.com/es/w",
    "search_method": "GET",
    "query_param": "q",
    "page_param": "page",
    "min_price_param": None,
    "max_price_param": "to",
    "size_param": "size",
    "product_selector": ".product-card",
    "title_selector": ".product-card__title",
    "price_selector": ".product-price",
    "img_selector": ".product-card__hero-image",
    "link_selector": ".product-card__link-overlay",
    "size_selector": ".product-card__available-sizes .size",
    "next_page_selector": ".pagination__next"
}

# Colores
COLORS = {
    "primary": "#f25c05",       # Naranja Nike
    "primary_hover": "#d95204", # Naranja oscuro
    "secondary": "#212121",     # Negro Nike
    "light_bg": "#f7f7f7",      # Fondo claro
    "white": "#ffffff",         # Blanco
    "text": "#212121",          # Texto principal
    "text_light": "#757575",    # Texto secundario
    "success": "#43a047",       # Verde éxito
    "error": "#e53935",         # Rojo error
    "input_bg": "#ffffff",      # Fondo de inputs
    "border": "#e0e0e0"         # Bordes
}


class ZapatillasScraper:
    def __init__(self, config):
        self.results = []
        self.config = config
        self.default_headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "es-ES,es;q=0.9"
        }

    def parse_price(self, price_str):
        if not price_str:
            return None
        price_text = re.sub(r'[^\d,.]', '', price_str).replace(',', '.')
        if price_text.count('.') > 1:
            parts = price_text.split('.')
            price_text = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return float(price_text)
        except ValueError:
            return None

    def search(self, query, max_pages=1, max_price=None, sizes=None, status_callback=None):
        cfg = self.config
        base_url = cfg['base_url']
        self.results = []

        for page in range(1, max_pages + 1):
            params = {
                cfg['query_param']: query,
                cfg['page_param']: page
            }

            if cfg.get('max_price_param') and max_price is not None:
                params[cfg['max_price_param']] = max_price
            if cfg.get('size_param') and sizes:
                params[cfg['size_param']] = ','.join(sizes)

            if status_callback:
                status_callback(f"🔍 Buscando en página {page}...")

            response = requests.get(cfg['search_url'], headers=self.default_headers, params=params)
            if response.status_code != 200:
                if status_callback:
                    status_callback(f"⚠️ Error {response.status_code} en página {page}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            products = soup.select(cfg['product_selector'])

            if not products:
                break

            for product in products:
                try:
                    title = product.select_one(cfg['title_selector']).get_text(strip=True)
                    price_text = product.select_one(cfg['price_selector']).get_text(strip=True)
                    price = self.parse_price(price_text)
                    if max_price and price and price > max_price:
                        continue

                    sizes_available = []
                    if cfg.get('size_selector'):
                        sizes_available = [s.get_text(strip=True) for s in product.select(cfg['size_selector'])]

                    if sizes and not cfg.get('size_param'):
                        if not any(s.lower() in [sa.lower() for sa in sizes_available] for s in sizes):
                            continue

                    image_elem = product.select_one(cfg['img_selector'])
                    img_url = image_elem.get("src") if image_elem else ""
                    if img_url and not img_url.startswith("http"):
                        img_url = urljoin(base_url, img_url)

                    link_elem = product.select_one(cfg['link_selector'])
                    product_url = urljoin(base_url, link_elem.get("href")) if link_elem else ""

                    self.results.append({
                        "title": title,
                        "price": price_text,
                        "image_url": img_url,
                        "product_url": product_url,
                        "store": cfg['name'],
                        "available_sizes": ', '.join(sizes_available) or "No especificado"
                    })
                except Exception:
                    continue

            time.sleep(random.uniform(1.0, 2.0))

        return self.results

    def export_to_csv(self, filename):
        if not self.results:
            return False

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "title", "price", "available_sizes", "product_url", "image_url", "store"
            ])
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        return True


# --- Custom widgets ---
class CustomEntry(ttk.Entry):
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = COLORS["text_light"]
        self.default_fg_color = COLORS["text"]
        
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        
        self.put_placeholder()
    
    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['foreground'] = self.placeholder_color
            
    def _focus_in(self, *args):
        if self.get() == self.placeholder:
            self.delete(0, 'end')
            self['foreground'] = self.default_fg_color
            
    def _focus_out(self, *args):
        if not self.get():
            self.put_placeholder()
            
    def get_value(self):
        if self.get() == self.placeholder:
            return ""
        return self.get()


class HoverButton(tk.Button):
    def __init__(self, master, background=COLORS["primary"], activebackground=COLORS["primary_hover"], **kwargs):
        tk.Button.__init__(self, master, background=background, activebackground=activebackground, **kwargs)
        self.default_bg = background
        self.hover_bg = activebackground
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.config(background=self.hover_bg)

    def _on_leave(self, e):
        self.config(background=self.default_bg)


class LoadingAnimation:
    def __init__(self, parent, text="Cargando"):
        self.parent = parent
        self.text = text
        self.count = 0
        self.running = False
        self.label = tk.Label(parent, text=text, font=("Segoe UI", 10), fg=COLORS["primary"], bg=COLORS["light_bg"])
        
    def start(self):
        self.running = True
        self.count = 0
        self.label.pack(pady=5)
        self.update()
        
    def update(self):
        if not self.running:
            return
        
        dots = "." * (self.count % 4)
        self.label.config(text=f"{self.text}{dots}")
        self.count += 1
        self.parent.after(300, self.update)
        
    def stop(self):
        self.running = False
        self.label.pack_forget()


class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.config(bg=COLORS["light_bg"], height=30)
        
        self.label = tk.Label(self, text="", font=("Segoe UI", 9), 
                              fg=COLORS["text_light"], bg=COLORS["light_bg"], anchor="w")
        self.label.pack(side=tk.LEFT, padx=10)
        
    def set_message(self, message, is_error=False):
        color = COLORS["error"] if is_error else COLORS["text_light"]
        self.label.config(text=message, fg=color)


class CustomTree(ttk.Treeview):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Configurar la barra de desplazamiento vertical
        self.vsb = ttk.Scrollbar(parent, orient="vertical", command=self.yview)
        self.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side='right', fill='y')
        
        # Configurar los colores alternos de las filas
        self.tag_configure('oddrow', background=COLORS["light_bg"])
        self.tag_configure('evenrow', background=COLORS["white"])


# --- App GUI ---
class App:
    def __init__(self, root):
        self.scraper = ZapatillasScraper(NIKE_CONFIG)
        self.root = root
        root.title("NIKE Scraper by Aran :)")
        root.geometry("950x700")
        root.configure(bg=COLORS["light_bg"])
        root.resizable(True, True)
        
        # Configura el estilo
        self.setup_styles()
        
        # Frame principal
        self.main_frame = tk.Frame(root, bg=COLORS["light_bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header con logo
        self.create_header()
        
        # Panel de búsqueda
        self.create_search_panel()
        
        # Resultados
        self.create_results_panel()
        
        # Panel de estado
        self.status_bar = StatusBar(root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Animación de carga
        self.loading = LoadingAnimation(self.main_frame)
        
        # Contador de resultados
        self.results_counter = tk.Label(
            self.results_frame, 
            text="0 resultados encontrados", 
            font=("Segoe UI", 10),
            fg=COLORS["text_light"],
            bg=COLORS["light_bg"]
        )
        self.results_counter.pack(pady=(0, 5), anchor="w", padx=10)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Estilo para etiquetas
        self.style.configure(
            "TLabel", 
            font=("Segoe UI", 10), 
            background=COLORS["light_bg"], 
            foreground=COLORS["text"]
        )
        
        # Estilo para entradas
        self.style.configure(
            "TEntry", 
            fieldbackground=COLORS["input_bg"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            borderwidth=1,
            font=("Segoe UI", 10)
        )
        self.style.map(
            "TEntry",
            bordercolor=[("focus", COLORS["primary"])]
        )
        
        # Estilo para botones
        self.style.configure(
            "TButton", 
            font=("Segoe UI", 10, "bold"),
            background=COLORS["primary"],
            foreground=COLORS["white"]
        )
        self.style.map(
            "TButton",
            background=[("active", COLORS["primary_hover"])]
        )
        
        # Estilo para el Treeview (tabla de resultados)
        self.style.configure(
            "Treeview", 
            background=COLORS["white"],
            fieldbackground=COLORS["white"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9),
            rowheight=30
        )
        self.style.configure(
            "Treeview.Heading", 
            font=("Segoe UI", 10, "bold"),
            background=COLORS["secondary"],
            foreground=COLORS["white"]
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", COLORS["primary"])]
        )
        
        # Estilo para el Combobox
        self.style.configure(
            "TCombobox", 
            fieldbackground=COLORS["input_bg"],
            background=COLORS["white"],
            bordercolor=COLORS["border"]
        )
        
        # Estilo para el Spinbox
        self.style.configure(
            "TSpinbox", 
            fieldbackground=COLORS["input_bg"],
            bordercolor=COLORS["border"],
            arrowcolor=COLORS["primary"]
        )

    def create_header(self):
        header_frame = tk.Frame(self.main_frame, bg=COLORS["secondary"], height=80)
        header_frame.pack(fill=tk.X)
        
        # Logo y título
        logo_text = tk.Label(
            header_frame, 
            text="NIKE", 
            font=("Arial Black", 24, "bold"), 
            fg=COLORS["white"],
            bg=COLORS["secondary"]
        )
        logo_text.pack(side=tk.LEFT, padx=20, pady=15)
        
        title = tk.Label(
            header_frame, 
            text="Scraper :)", 
            font=("Segoe UI", 18), 
            fg=COLORS["white"],
            bg=COLORS["secondary"]
        )
        title.pack(side=tk.LEFT, padx=0, pady=15)

    def create_search_panel(self):
        search_frame = tk.Frame(self.main_frame, bg=COLORS["light_bg"], padx=20, pady=15)
        search_frame.pack(fill=tk.X)
        
        # Título de la sección
        search_title = tk.Label(
            search_frame, 
            text="Uso propio con fines educativos", 
            font=("Segoe UI", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        )
        search_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Primera fila: Término de búsqueda
        tk.Label(
            search_frame, 
            text="¿Qué estás buscando?", 
            font=("Segoe UI", 10),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        ).grid(row=1, column=0, sticky="w", pady=(5, 2))
        
        self.query_entry = CustomEntry(
            search_frame, 
            placeholder="Ej: Nike Air Max, Air Jordan, Nocta...",
            width=50
        )
        self.query_entry.grid(row=2, column=0, sticky="ew", padx=(0, 20))
        
        # Segunda fila: Filtros
        filters_frame = tk.Frame(search_frame, bg=COLORS["light_bg"])
        filters_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        filters_frame.grid_columnconfigure(0, weight=1)
        filters_frame.grid_columnconfigure(1, weight=1)
        filters_frame.grid_columnconfigure(2, weight=1)
        
        # Precio máximo
        tk.Label(
            filters_frame, 
            text="Precio máximo (€)", 
            font=("Segoe UI", 10),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.max_price_entry = CustomEntry(filters_frame, placeholder="Ej: 120", width=15)
        self.max_price_entry.grid(row=1, column=0, sticky="w", padx=(0, 10))
        
        # Tallas
        tk.Label(
            filters_frame, 
            text="Tallas", 
            font=("Segoe UI", 10),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        ).grid(row=0, column=1, sticky="w", pady=(0, 2))
        
        self.size_entry = CustomEntry(filters_frame, placeholder="Ej: 42, 43, 44", width=15)
        self.size_entry.grid(row=1, column=1, sticky="w", padx=(0, 10))
        
        # Páginas a buscar
        tk.Label(
            filters_frame, 
            text="Páginas a buscar", 
            font=("Segoe UI", 10),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        ).grid(row=0, column=2, sticky="w", pady=(0, 2))
        
        self.page_spinbox = ttk.Spinbox(filters_frame, from_=1, to=10, width=5)
        self.page_spinbox.set(2)
        self.page_spinbox.grid(row=1, column=2, sticky="w")
        
        # Botón de búsqueda
        button_frame = tk.Frame(search_frame, bg=COLORS["light_bg"])
        button_frame.grid(row=4, column=0, sticky="w", pady=(20, 10))
        
        self.search_btn = HoverButton(
            button_frame,
            text="BUSCAR ZAPATILLAS",
            font=("Segoe UI", 11, "bold"),
            fg=COLORS["white"],
            bg=COLORS["primary"],
            activeforeground=COLORS["white"],
            activebackground=COLORS["primary_hover"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=15,
            pady=8,
            cursor="hand2",
            command=self.run_search
        )
        self.search_btn.pack(side=tk.LEFT)
        
        # Separador
        ttk.Separator(self.main_frame, orient='horizontal').pack(fill='x', padx=20)

    def create_results_panel(self):
        self.results_frame = tk.Frame(self.main_frame, bg=COLORS["light_bg"], padx=20, pady=15)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título de la sección
        results_title = tk.Label(
            self.results_frame, 
            text="Resultados", 
            font=("Segoe UI", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["light_bg"]
        )
        results_title.pack(anchor="w", pady=(0, 10))
        
        # Tabla de resultados
        tree_frame = tk.Frame(self.results_frame, bg=COLORS["light_bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = CustomTree(
            tree_frame,
            columns=("Título", "Precio", "Tallas", "Enlace"),
            show="headings",
            height=15
        )
        
        # Configurar anchos de columnas
        self.tree.column("Título", width=350, anchor="w")
        self.tree.column("Precio", width=100, anchor="center")
        self.tree.column("Tallas", width=150, anchor="center")
        self.tree.column("Enlace", width=300, anchor="w")
        
        # Configurar encabezados
        self.tree.heading("Título", text="Título")
        self.tree.heading("Precio", text="Precio")
        self.tree.heading("Tallas", text="Tallas Disponibles")
        self.tree.heading("Enlace", text="URL del producto")
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Eventos de la tabla
        self.tree.bind("<Double-1>", self.open_url)
        self.tree.bind("<Button-1>", self.check_click)
        
        # Panel inferior con botones de acciones
        actions_frame = tk.Frame(self.results_frame, bg=COLORS["light_bg"])
        actions_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.export_btn = HoverButton(
            actions_frame,
            text="GUARDAR EN CSV",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["white"],
            bg=COLORS["secondary"],
            activeforeground=COLORS["white"],
            activebackground=COLORS["primary"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.save_csv
        )
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_url_btn = HoverButton(
            actions_frame,
            text="ABRIR ENLACE SELECCIONADO",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["white"],
            bg=COLORS["secondary"],
            activeforeground=COLORS["white"],
            activebackground=COLORS["primary"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.open_selected_url
        )
        self.open_url_btn.pack(side=tk.LEFT)

    def check_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#4":  # Columna del enlace
                self.open_url(event)

    def update_status(self, msg, is_error=False):
        self.status_bar.set_message(msg, is_error)
        self.root.update_idletasks()

    def run_search(self):
        self.tree.delete(*self.tree.get_children())
        
        query = self.query_entry.get_value()
        max_price = self.max_price_entry.get_value()
        sizes = [s.strip() for s in self.size_entry.get_value().split(',') if s.strip()]
        pages = int(self.page_spinbox.get())

        if not query:
            messagebox.showwarning("Atención", "Introduce un término de búsqueda")
            return

        try:
            max_price = float(max_price) if max_price else None
        except ValueError:
            messagebox.showerror("Error", "Precio máximo inválido")
            self.update_status("Formato de precio inválido. Usa solo números.", True)
            return

        # Desactivar botón de búsqueda e iniciar animación
        self.search_btn.config(state=tk.DISABLED)
        self.loading.start()
        self.update_status("Iniciando búsqueda...")
        
        # Forzar actualizaciones de la interfaz
        self.root.update_idletasks()
        
        # Ejecutar búsqueda
        results = self.scraper.search(
            query, 
            max_pages=pages, 
            max_price=max_price,
            sizes=sizes, 
            status_callback=self.update_status
        )

        # Detener animación y reactivar botón
        self.loading.stop()
        self.search_btn.config(state=tk.NORMAL)
        
        if results:
            for i, product in enumerate(results):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.tree.insert(
                    '', 'end', 
                    values=(
                        product["title"], 
                        product["price"],
                        product["available_sizes"], 
                        product["product_url"]
                    ),
                    tags=(tag,)
                )
            self.update_status(f"Búsqueda completada. Se encontraron {len(results)} productos.")
            self.results_counter.config(text=f"{len(results)} productos encontrados")
        else:
            self.update_status("Búsqueda completada. No se encontraron productos.")
            self.results_counter.config(text="0 productos encontrados")
            messagebox.showinfo("Sin resultados", "No se encontraron productos para tu búsqueda.")

    def save_csv(self):
        if not self.scraper.results:
            messagebox.showwarning("Nada que guardar", "Realiza una búsqueda primero.")
            return

        filename = datetime.now().strftime("nike_zapatillas_%Y%m%d_%H%M%S.csv")
        file = filedialog.asksaveasfilename(
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Guardar resultados como..."
        )
        
        if file:
            if self.scraper.export_to_csv(file):
                self.update_status(f"Archivo guardado en: {file}")
                messagebox.showinfo("Éxito", f"Archivo guardado correctamente.")
            else:
                self.update_status("Error al guardar el archivo.", True)
                messagebox.showerror("Error", "No se pudo guardar el archivo.")

    def open_url(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#4":  # Columna del enlace
                row = self.tree.identify_row(event.y)
                if row:
                    item = self.tree.item(row)
                    url = item["values"][3]
                    webbrowser.open_new_tab(url)
                    self.update_status(f"Abriendo enlace: {url}")

    def open_selected_url(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            url = item["values"][3]
            webbrowser.open_new_tab(url)
            self.update_status(f"Abriendo enlace: {url}")
        else:
            messagebox.showinfo("Información", "Selecciona primero un producto de la lista.")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
