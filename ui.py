#!/usr/bin/env python3
"""
GrowBot UI - Comparador de Outputs Claude vs OpenAI
"""

import csv
import io
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class GrowBotUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GrowBot - Comparador de Extrações")
        self.root.geometry("1600x900")

        # Dados
        self.input_text = ""
        self.claude_data = {"items": []}
        self.openai_data = {"items": []}
        self.filtered_claude = []
        self.filtered_openai = []

        # Carrega dados
        self.carregar_dados()

        # Cria interface
        self.criar_interface()

        # Aplica filtros iniciais
        self.aplicar_filtros()

    def carregar_dados(self):
        """Carrega arquivo de input e outputs."""
        # Input original
        exports_dir = Path("exports")
        for txt_file in exports_dir.glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                self.input_text = f.read()
            break

        # Outputs - pega os mais recentes
        output_dir = Path("output")

        claude_files = sorted(output_dir.glob("*claude*.json"), reverse=True)
        openai_files = sorted(output_dir.glob("*openai*.json"), reverse=True)

        # Se não tiver arquivos específicos, pega qualquer um
        if not claude_files and not openai_files:
            all_json = sorted(output_dir.glob("*.json"), reverse=True)
            if all_json:
                with open(all_json[0], 'r', encoding='utf-8') as f:
                    self.claude_data = json.load(f)
                if len(all_json) > 1:
                    with open(all_json[1], 'r', encoding='utf-8') as f:
                        self.openai_data = json.load(f)
        else:
            if claude_files:
                with open(claude_files[0], 'r', encoding='utf-8') as f:
                    self.claude_data = json.load(f)
            if openai_files:
                with open(openai_files[0], 'r', encoding='utf-8') as f:
                    self.openai_data = json.load(f)

    def criar_interface(self):
        """Cria a interface gráfica."""
        # Frame de filtros
        filtros_frame = ttk.Frame(self.root, padding=10)
        filtros_frame.pack(fill=tk.X)

        # Driver
        ttk.Label(filtros_frame, text="Driver:").pack(side=tk.LEFT, padx=5)
        self.driver_var = tk.StringVar(value="Todos")
        drivers = ["Todos", "RAFA", "FRANCIS", "RODRIGO", "KAROL", "ARTHUR"]
        self.driver_combo = ttk.Combobox(filtros_frame, textvariable=self.driver_var,
                                          values=drivers, width=12, state="readonly")
        self.driver_combo.pack(side=tk.LEFT, padx=5)
        self.driver_combo.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros())

        # Data
        ttk.Label(filtros_frame, text="Data:").pack(side=tk.LEFT, padx=5)
        self.data_var = tk.StringVar(value="")
        self.data_entry = ttk.Entry(filtros_frame, textvariable=self.data_var, width=12)
        self.data_entry.pack(side=tk.LEFT, padx=5)
        self.data_entry.bind("<KeyRelease>", lambda e: self.aplicar_filtros())

        # ID Entrega
        ttk.Label(filtros_frame, text="ID Entrega:").pack(side=tk.LEFT, padx=5)
        self.id_var = tk.StringVar(value="")
        self.id_entry = ttk.Entry(filtros_frame, textvariable=self.id_var, width=8)
        self.id_entry.pack(side=tk.LEFT, padx=5)
        self.id_entry.bind("<KeyRelease>", lambda e: self.aplicar_filtros())

        # Botão limpar
        ttk.Button(filtros_frame, text="Limpar Filtros",
                   command=self.limpar_filtros).pack(side=tk.LEFT, padx=20)

        # Botões de copiar
        ttk.Button(filtros_frame, text="📋 Copiar Claude CSV",
                   command=lambda: self.copiar_csv("claude")).pack(side=tk.RIGHT, padx=5)
        ttk.Button(filtros_frame, text="📋 Copiar OpenAI CSV",
                   command=lambda: self.copiar_csv("openai")).pack(side=tk.RIGHT, padx=5)
        ttk.Button(filtros_frame, text="📋 Copiar Ambos CSV",
                   command=lambda: self.copiar_csv("ambos")).pack(side=tk.RIGHT, padx=5)

        # Frame principal com 3 colunas
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configurar grid
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Painel Input Original
        input_frame = ttk.LabelFrame(main_frame, text="📄 Input Original", padding=5)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=5)

        self.input_text_widget = tk.Text(input_frame, wrap=tk.WORD, font=("Consolas", 10))
        input_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL,
                                      command=self.input_text_widget.yview)
        self.input_text_widget.configure(yscrollcommand=input_scroll.set)
        self.input_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_text_widget.insert("1.0", self.input_text)
        self.input_text_widget.config(state=tk.DISABLED)

        # Painel Claude
        claude_frame = ttk.LabelFrame(main_frame, text="🟣 Claude Output", padding=5)
        claude_frame.grid(row=0, column=1, sticky="nsew", padx=5)

        # Stats Claude
        self.claude_stats = ttk.Label(claude_frame, text="0 itens")
        self.claude_stats.pack(anchor=tk.W)

        # Treeview Claude
        claude_tree_frame = ttk.Frame(claude_frame)
        claude_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.claude_tree = ttk.Treeview(claude_tree_frame, columns=(
            "id", "produto", "qtd", "driver", "data", "endereco"
        ), show="headings", height=20)

        self.claude_tree.heading("id", text="ID")
        self.claude_tree.heading("produto", text="Produto")
        self.claude_tree.heading("qtd", text="Qtd")
        self.claude_tree.heading("driver", text="Driver")
        self.claude_tree.heading("data", text="Data")
        self.claude_tree.heading("endereco", text="Endereço")

        self.claude_tree.column("id", width=50)
        self.claude_tree.column("produto", width=100)
        self.claude_tree.column("qtd", width=40)
        self.claude_tree.column("driver", width=70)
        self.claude_tree.column("data", width=80)
        self.claude_tree.column("endereco", width=150)

        claude_scroll = ttk.Scrollbar(claude_tree_frame, orient=tk.VERTICAL,
                                       command=self.claude_tree.yview)
        self.claude_tree.configure(yscrollcommand=claude_scroll.set)
        self.claude_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        claude_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind para mostrar detalhes
        self.claude_tree.bind("<<TreeviewSelect>>",
                              lambda e: self.mostrar_detalhes("claude"))

        # Detalhes Claude
        self.claude_details = tk.Text(claude_frame, wrap=tk.WORD, height=8,
                                       font=("Consolas", 9))
        self.claude_details.pack(fill=tk.X, pady=(5, 0))

        # Painel OpenAI
        openai_frame = ttk.LabelFrame(main_frame, text="🟢 OpenAI Output", padding=5)
        openai_frame.grid(row=0, column=2, sticky="nsew", padx=5)

        # Stats OpenAI
        self.openai_stats = ttk.Label(openai_frame, text="0 itens")
        self.openai_stats.pack(anchor=tk.W)

        # Treeview OpenAI
        openai_tree_frame = ttk.Frame(openai_frame)
        openai_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.openai_tree = ttk.Treeview(openai_tree_frame, columns=(
            "id", "produto", "qtd", "driver", "data", "endereco"
        ), show="headings", height=20)

        self.openai_tree.heading("id", text="ID")
        self.openai_tree.heading("produto", text="Produto")
        self.openai_tree.heading("qtd", text="Qtd")
        self.openai_tree.heading("driver", text="Driver")
        self.openai_tree.heading("data", text="Data")
        self.openai_tree.heading("endereco", text="Endereço")

        self.openai_tree.column("id", width=50)
        self.openai_tree.column("produto", width=100)
        self.openai_tree.column("qtd", width=40)
        self.openai_tree.column("driver", width=70)
        self.openai_tree.column("data", width=80)
        self.openai_tree.column("endereco", width=150)

        openai_scroll = ttk.Scrollbar(openai_tree_frame, orient=tk.VERTICAL,
                                       command=self.openai_tree.yview)
        self.openai_tree.configure(yscrollcommand=openai_scroll.set)
        self.openai_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        openai_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind para mostrar detalhes
        self.openai_tree.bind("<<TreeviewSelect>>",
                              lambda e: self.mostrar_detalhes("openai"))

        # Detalhes OpenAI
        self.openai_details = tk.Text(openai_frame, wrap=tk.WORD, height=8,
                                       font=("Consolas", 9))
        self.openai_details.pack(fill=tk.X, pady=(5, 0))

        # Status bar
        self.status = ttk.Label(self.root, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def aplicar_filtros(self):
        """Aplica filtros aos dados."""
        driver = self.driver_var.get()
        data = self.data_var.get().strip()
        id_entrega = self.id_var.get().strip()

        def filtrar(items):
            resultado = []
            for item in items:
                # Filtro driver
                if driver != "Todos":
                    item_driver = (item.get("driver") or "").upper()
                    if item_driver != driver:
                        continue

                # Filtro data
                if data:
                    item_data = item.get("data_entrega") or ""
                    if data not in item_data:
                        continue

                # Filtro ID
                if id_entrega:
                    item_id = item.get("id_sale_delivery") or ""
                    if id_entrega not in item_id:
                        continue

                resultado.append(item)
            return resultado

        self.filtered_claude = filtrar(self.claude_data.get("items", []))
        self.filtered_openai = filtrar(self.openai_data.get("items", []))

        self.atualizar_treeviews()

    def atualizar_treeviews(self):
        """Atualiza as tabelas com dados filtrados."""
        # Limpa
        for item in self.claude_tree.get_children():
            self.claude_tree.delete(item)
        for item in self.openai_tree.get_children():
            self.openai_tree.delete(item)

        # Popula Claude
        for i, item in enumerate(self.filtered_claude):
            self.claude_tree.insert("", tk.END, iid=str(i), values=(
                item.get("id_sale_delivery", ""),
                item.get("produto", ""),
                item.get("quantidade", ""),
                item.get("driver", "") or "",
                item.get("data_entrega", "") or "",
                item.get("endereco_1", "") or ""
            ))

        # Popula OpenAI
        for i, item in enumerate(self.filtered_openai):
            self.openai_tree.insert("", tk.END, iid=str(i), values=(
                item.get("id_sale_delivery", ""),
                item.get("produto", ""),
                item.get("quantidade", ""),
                item.get("driver", "") or "",
                item.get("data_entrega", "") or "",
                item.get("endereco_1", "") or ""
            ))

        # Atualiza stats
        total_claude = len(self.claude_data.get("items", []))
        total_openai = len(self.openai_data.get("items", []))
        self.claude_stats.config(
            text=f"{len(self.filtered_claude)} itens (de {total_claude} total)")
        self.openai_stats.config(
            text=f"{len(self.filtered_openai)} itens (de {total_openai} total)")

        self.status.config(
            text=f"Claude: {len(self.filtered_claude)} | OpenAI: {len(self.filtered_openai)}")

    def mostrar_detalhes(self, provider):
        """Mostra detalhes do item selecionado."""
        if provider == "claude":
            tree = self.claude_tree
            details = self.claude_details
            data = self.filtered_claude
        else:
            tree = self.openai_tree
            details = self.openai_details
            data = self.filtered_openai

        selection = tree.selection()
        if not selection:
            return

        idx = int(selection[0])
        if idx >= len(data):
            return

        item = data[idx]

        details.config(state=tk.NORMAL)
        details.delete("1.0", tk.END)

        text = f"ID: {item.get('id_sale_delivery')}\n"
        text += f"Produto: {item.get('produto')} | Qtd: {item.get('quantidade')}\n"
        text += f"Driver: {item.get('driver')} | Data: {item.get('data_entrega')}\n"
        text += f"Endereço: {item.get('endereco_1', '')} {item.get('endereco_2', '')}\n"
        text += f"---\nParse:\n{item.get('parse_mensagem_dia', '')}\n"
        if item.get('observacoes'):
            text += f"---\nObs: {', '.join(item.get('observacoes', []))}"

        details.insert("1.0", text)
        details.config(state=tk.DISABLED)

    def limpar_filtros(self):
        """Limpa todos os filtros."""
        self.driver_var.set("Todos")
        self.data_var.set("")
        self.id_var.set("")
        self.aplicar_filtros()

    def copiar_csv(self, provider):
        """Copia dados para clipboard em formato CSV."""
        if provider == "claude":
            data = self.filtered_claude
        elif provider == "openai":
            data = self.filtered_openai
        else:  # ambos
            data = self.filtered_claude + self.filtered_openai

        if not data:
            messagebox.showwarning("Aviso", "Nenhum dado para copiar!")
            return

        # Gera CSV
        output = io.StringIO()
        campos = ["id_sale_delivery", "produto", "quantidade", "driver",
                  "data_entrega", "endereco_1", "endereco_2", "observacoes"]

        writer = csv.DictWriter(output, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()

        for item in data:
            row = item.copy()
            if row.get("observacoes"):
                row["observacoes"] = "; ".join(row["observacoes"])
            writer.writerow(row)

        csv_text = output.getvalue()

        # Copia para clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(csv_text)

        messagebox.showinfo("Sucesso",
            f"Copiado {len(data)} itens para o clipboard!\n\nCole no Excel/Google Sheets.")


def main():
    root = tk.Tk()
    app = GrowBotUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
