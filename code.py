"""
╔══════════════════════════════════════════════════════════╗
║         REMMY-STYLE SALES MANAGEMENT SYSTEM             ║
║         Built with Python | SQLite | Tkinter            ║
╚══════════════════════════════════════════════════════════╝

REQUIRED LIBRARIES:
    pip install reportlab pillow tk

BUILT-IN LIBRARIES USED:
    sqlite3, hashlib, datetime, os, sys, subprocess, platform
"""

# ─── IMPORTS ─────────────────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
import sqlite3
import hashlib
import datetime
import os
import sys
import platform
import subprocess

# ReportLab for Receipt/Invoice Printing
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠  ReportLab not found. Run: pip install reportlab")


# ─── CONSTANTS & THEME ───────────────────────────────────────────────────────
DB_PATH = "remmy_sales.db"

COLORS = {
    "primary":    "#F68B1E",   # remmy Orange
    "secondary":  "#3C3C3C",   # Dark Grey
    "success":    "#27AE60",
    "danger":     "#E74C3C",
    "warning":    "#F39C12",
    "light":      "#F5F5F5",
    "white":      "#FFFFFF",
    "dark":       "#1A1A1A",
    "card":       "#FAFAFA",
    "border":     "#E0E0E0",
    "text_dark":  "#2C2C2C",
    "text_light": "#777777",
}

APP_FONT        = ("Segoe UI", 10)
APP_FONT_BOLD   = ("Segoe UI", 10, "bold")
APP_FONT_LARGE  = ("Segoe UI", 14, "bold")
APP_FONT_TITLE  = ("Segoe UI", 20, "bold")
APP_FONT_SMALL  = ("Segoe UI", 9)


# ─── DATABASE LAYER ──────────────────────────────────────────────────────────
class Database:
    """Handles all SQLite database operations."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()

        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name   TEXT    NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                phone       TEXT,
                password    TEXT    NOT NULL,
                role        TEXT    DEFAULT 'salesman',
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Products table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                category    TEXT,
                price       REAL    NOT NULL,
                stock       INTEGER DEFAULT 0,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Carts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                customer    TEXT    NOT NULL,
                status      TEXT    DEFAULT 'open',
                created_at  TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Cart Items table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                product_name TEXT   NOT NULL,
                quantity    INTEGER NOT NULL,
                unit_price  REAL    NOT NULL,
                subtotal    REAL    NOT NULL,
                added_at    TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (cart_id)    REFERENCES carts(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Sales / Orders table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id      INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                customer     TEXT    NOT NULL,
                total_amount REAL    NOT NULL,
                payment_method TEXT  DEFAULT 'Cash',
                sold_at      TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (cart_id)  REFERENCES carts(id),
                FOREIGN KEY (user_id)  REFERENCES users(id)
            )
        """)

        self.conn.commit()
        self._seed_products()

    def _seed_products(self):
        """Add sample remmy-style products if table is empty."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            products = [
                ("Samsung Galaxy A54",   "Electronics",  450000, 20, "6.4\" Display, 128GB"),
                ("iPhone 15 Pro Max",    "Electronics", 3200000, 10, "256GB, Titanium"),
                ("HP Laptop 15",         "Computers",   1800000, 15, "Intel i5, 8GB RAM"),
                ("Nike Air Max",         "Footwear",      180000,  50, "Unisex, Sizes 37-45"),
                ("Samsung 43\" Smart TV","Electronics",   950000,  8,  "4K UHD, Smart"),
                ("Blender Sayona",       "Appliances",     85000, 30, "1.5L, 600W"),
                ("School Bag Jansport",  "Accessories",    75000, 40, "Large Capacity"),
                ("Wireless Earbuds",     "Electronics",    65000, 60, "Bluetooth 5.0"),
                ("Office Chair",         "Furniture",     350000, 12, "Ergonomic, Adjustable"),
                ("Canon Printer",        "Electronics",   480000,  7, "Color Inkjet, WiFi"),
            ]
            cur.executemany(
                "INSERT INTO products (name, category, price, stock, description) VALUES (?,?,?,?,?)",
                products
            )
            self.conn.commit()

    # ── AUTH ──
    def create_user(self, full_name, email, phone, password, role="salesman"):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.conn.execute(
                "INSERT INTO users (full_name,email,phone,password,role) VALUES (?,?,?,?,?)",
                (full_name, email, phone, hashed, role)
            )
            self.conn.commit()
            return True, "Account created successfully!"
        except sqlite3.IntegrityError:
            return False, "Email already registered."

    def login_user(self, email, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        row = self.conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?", (email, hashed)
        ).fetchone()
        return dict(row) if row else None

    # ── PRODUCTS ──
    def get_products(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM products ORDER BY category, name"
        ).fetchall()]

    def search_products(self, query):
        q = f"%{query}%"
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM products WHERE name LIKE ? OR category LIKE ?", (q, q)
        ).fetchall()]

    # ── CARTS ──
    def create_cart(self, user_id, customer):
        cur = self.conn.execute(
            "INSERT INTO carts (user_id, customer) VALUES (?,?)", (user_id, customer)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_carts(self, user_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM carts WHERE user_id=? AND status='open' ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()]

    def get_all_carts(self, user_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM carts WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()]

    def delete_cart(self, cart_id):
        self.conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))
        self.conn.execute("DELETE FROM carts WHERE id=?", (cart_id,))
        self.conn.commit()

    def close_cart(self, cart_id):
        self.conn.execute("UPDATE carts SET status='closed' WHERE id=?", (cart_id,))
        self.conn.commit()

    # ── CART ITEMS ──
    def add_item_to_cart(self, cart_id, product_id, product_name, quantity, unit_price):
        subtotal = quantity * unit_price
        # Check if product already in cart
        existing = self.conn.execute(
            "SELECT id, quantity FROM cart_items WHERE cart_id=? AND product_id=?",
            (cart_id, product_id)
        ).fetchone()
        if existing:
            new_qty = existing["quantity"] + quantity
            new_sub = new_qty * unit_price
            self.conn.execute(
                "UPDATE cart_items SET quantity=?, subtotal=? WHERE id=?",
                (new_qty, new_sub, existing["id"])
            )
        else:
            self.conn.execute(
                """INSERT INTO cart_items
                   (cart_id, product_id, product_name, quantity, unit_price, subtotal)
                   VALUES (?,?,?,?,?,?)""",
                (cart_id, product_id, product_name, quantity, unit_price, subtotal)
            )
        self.conn.commit()

    def get_cart_items(self, cart_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM cart_items WHERE cart_id=?", (cart_id,)
        ).fetchall()]

    def update_cart_item(self, item_id, quantity, unit_price):
        subtotal = quantity * unit_price
        self.conn.execute(
            "UPDATE cart_items SET quantity=?, unit_price=?, subtotal=? WHERE id=?",
            (quantity, unit_price, subtotal, item_id)
        )
        self.conn.commit()

    def delete_cart_item(self, item_id):
        self.conn.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
        self.conn.commit()

    def get_cart_total(self, cart_id):
        row = self.conn.execute(
            "SELECT SUM(subtotal) as total FROM cart_items WHERE cart_id=?", (cart_id,)
        ).fetchone()
        return row["total"] or 0.0

    # ── SALES ──
    def record_sale(self, cart_id, user_id, customer, total, payment):
        self.conn.execute(
            "INSERT INTO sales (cart_id,user_id,customer,total_amount,payment_method) VALUES (?,?,?,?,?)",
            (cart_id, user_id, customer, total, payment)
        )
        self.conn.commit()

    def get_sales(self, user_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM sales WHERE user_id=? ORDER BY sold_at DESC", (user_id,)
        ).fetchall()]


# ─── PRINT MANAGER ───────────────────────────────────────────────────────────
class PrintManager:
    """Generates PDF receipts using ReportLab."""

    @staticmethod
    def print_receipt(cart_data: dict, items: list, salesman: str, payment: str = "Cash"):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Print Error",
                "ReportLab not installed.\nRun: pip install reportlab")
            return

        filename = f"receipt_{cart_data['id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        story  = []

        # ── Header ──
        header_style = ParagraphStyle("header", fontSize=22, fontName="Helvetica-Bold",
                                       textColor=colors.HexColor("#F68B1E"),
                                       alignment=TA_CENTER, spaceAfter=4)
        sub_style    = ParagraphStyle("sub", fontSize=10, fontName="Helvetica",
                                       textColor=colors.HexColor("#555555"),
                                       alignment=TA_CENTER, spaceAfter=2)
        story.append(Paragraph("🛒 REMMY SALES SYSTEM", header_style))
        story.append(Paragraph("Your trusted marketplace partner", sub_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(HRFlowable(width="100%", thickness=2,
                                 color=colors.HexColor("#F68B1E")))
        story.append(Spacer(1, 0.3*cm))

        # ── Receipt Meta ──
        meta_style = ParagraphStyle("meta", fontSize=9, fontName="Helvetica",
                                     textColor=colors.HexColor("#333333"),
                                     spaceAfter=3)
        story.append(Paragraph(f"<b>Receipt No:</b> REC-{cart_data['id']:05d}", meta_style))
        story.append(Paragraph(f"<b>Customer:</b>   {cart_data['customer']}", meta_style))
        story.append(Paragraph(f"<b>Salesman:</b>   {salesman}", meta_style))
        story.append(Paragraph(f"<b>Date:</b>        {datetime.datetime.now().strftime('%d %b %Y  %H:%M')}", meta_style))
        story.append(Paragraph(f"<b>Payment:</b>    {payment}", meta_style))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1,
                                 color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 0.3*cm))

        # ── Items Table ──
        table_data = [["#", "Product", "Qty", "Unit Price (UGX)", "Subtotal (UGX)"]]
        total = 0
        for i, item in enumerate(items, 1):
            table_data.append([
                str(i),
                item["product_name"],
                str(item["quantity"]),
                f"{item['unit_price']:,.0f}",
                f"{item['subtotal']:,.0f}",
            ])
            total += item["subtotal"]

        # Totals rows
        table_data.append(["", "", "", "SUBTOTAL", f"{total:,.0f}"])
        table_data.append(["", "", "", "TAX (0%)", "0"])
        table_data.append(["", "", "", "TOTAL",    f"{total:,.0f}"])

        col_widths = [0.6*cm, 7*cm, 1.5*cm, 4*cm, 4*cm]
        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#F68B1E")),
            ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
            ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,0),  9),
            ("ALIGN",        (0,0), (-1,0),  "CENTER"),
            # Body rows
            ("FONTSIZE",     (0,1), (-1,-4), 9),
            ("ROWBACKGROUNDS",(0,1),(-1,-4), [colors.white, colors.HexColor("#FFF8F0")]),
            ("ALIGN",        (2,1), (-1,-1), "RIGHT"),
            # Total rows
            ("FONTNAME",     (3,-3),(-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",     (3,-3),(-1,-1), 10),
            ("BACKGROUND",   (3,-1),(-1,-1), colors.HexColor("#F68B1E")),
            ("TEXTCOLOR",    (3,-1),(-1,-1), colors.white),
            # Borders
            ("GRID",         (0,0), (-1,-4), 0.5, colors.HexColor("#DDDDDD")),
            ("LINEABOVE",    (0,-3),(5,-3),  1,   colors.HexColor("#AAAAAA")),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # ── Footer ──
        footer_style = ParagraphStyle("footer", fontSize=9, fontName="Helvetica",
                                       textColor=colors.HexColor("#888888"),
                                       alignment=TA_CENTER, spaceAfter=2)
        story.append(HRFlowable(width="100%", thickness=1,
                                 color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("Thank you for shopping with us! 🧡", footer_style))
        story.append(Paragraph("Powered by REMMY Sales System", footer_style))

        doc.build(story)

        # Open the PDF
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
            elif platform.system() == "Darwin":
                subprocess.call(["open", filename])
            else:
                subprocess.call(["xdg-open", filename])
        except Exception:
            pass

        messagebox.showinfo("Receipt Saved", f"Receipt saved as:\n{filename}")
        return filename


# ─── REUSABLE UI WIDGETS ─────────────────────────────────────────────────────
def styled_button(parent, text, command, bg=None, fg="white",
                  width=15, font=APP_FONT_BOLD, pady=8, padx=10, **kw):
    bg = bg or COLORS["primary"]
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, font=font,
                    activebackground=bg, activeforeground=fg,
                    relief="flat", cursor="hand2",
                    padx=padx, pady=pady, width=width, **kw)
    return btn


def labeled_entry(parent, label, row, show=None, width=30):
    tk.Label(parent, text=label, font=APP_FONT_BOLD,
             bg=COLORS["white"], fg=COLORS["text_dark"]).grid(
        row=row, column=0, sticky="w", pady=5, padx=5)
    var = tk.StringVar()
    e = tk.Entry(parent, textvariable=var, font=APP_FONT,
                 width=width, relief="solid", bd=1,
                 **( {"show": show} if show else {} ))
    e.grid(row=row, column=1, pady=5, padx=5, ipady=6)
    return var


# ─── AUTH WINDOW ─────────────────────────────────────────────────────────────
class AuthWindow:
    """Login and Signup screens."""

    def __init__(self, db: Database, on_login_success):
        self.db               = db
        self.on_login_success = on_login_success

        self.root = tk.Tk()
        self.root.title("Remmy Sales System — Login")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["white"])

        self._center(self.root, 480, 620)
        self._build_login()
        self.root.mainloop()

    def _center(self, win, w, h):
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── LOGIN UI ──
    def _build_login(self):
        self._clear()

        # Orange top banner
        banner = tk.Frame(self.root, bg=COLORS["primary"], height=120)
        banner.pack(fill="x")
        tk.Label(banner, text="🛒 REMMY", font=("Segoe UI", 28, "bold"),
                 bg=COLORS["primary"], fg=COLORS["white"]).pack(pady=20)
        tk.Label(banner, text="Sales Management System",
                 font=APP_FONT, bg=COLORS["primary"], fg="#FFE0B2").pack()

        card = tk.Frame(self.root, bg=COLORS["white"], padx=40, pady=30)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Welcome Back 👋", font=APP_FONT_LARGE,
                 bg=COLORS["white"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0,5))
        tk.Label(card, text="Sign in to your account", font=APP_FONT,
                 bg=COLORS["white"], fg=COLORS["text_light"]).pack(anchor="w", pady=(0,20))

        form = tk.Frame(card, bg=COLORS["white"])
        form.pack(fill="x")

        self._email_var = self._field(form, "📧  Email Address", 0)
        self._pass_var  = self._field(form, "🔒  Password",      1, show="*")

        tk.Button(card, text="SIGN IN", command=self._do_login,
                  bg=COLORS["primary"], fg="white", font=APP_FONT_BOLD,
                  relief="flat", cursor="hand2", pady=12,
                  activebackground="#e07b10").pack(fill="x", pady=(20,5))

        sep = tk.Frame(card, bg=COLORS["border"], height=1)
        sep.pack(fill="x", pady=15)

        tk.Label(card, text="Don't have an account?",
                 font=APP_FONT, bg=COLORS["white"],
                 fg=COLORS["text_light"]).pack()
        tk.Button(card, text="CREATE ACCOUNT", command=self._build_signup,
                  bg=COLORS["white"], fg=COLORS["primary"],
                  font=APP_FONT_BOLD, relief="solid", bd=1,
                  cursor="hand2", pady=10).pack(fill="x", pady=5)

    def _field(self, parent, label, row, show=None):
        tk.Label(parent, text=label, font=APP_FONT_BOLD,
                 bg=COLORS["white"], fg=COLORS["text_dark"]).grid(
            row=row*2, column=0, sticky="w", pady=(10,2))
        var = tk.StringVar()
        kw  = {"show": show} if show else {}
        e = tk.Entry(parent, textvariable=var, font=APP_FONT,
                     relief="solid", bd=1, **kw)
        e.grid(row=row*2+1, column=0, sticky="ew", ipady=8, pady=(0,5))
        parent.columnconfigure(0, weight=1)
        return var

    def _do_login(self):
        email = self._email_var.get().strip()
        pwd   = self._pass_var.get().strip()
        if not email or not pwd:
            messagebox.showwarning("Missing Fields", "Please fill in all fields.")
            return
        user = self.db.login_user(email, pwd)
        if user:
            self.root.destroy()
            self.on_login_success(user)
        else:
            messagebox.showerror("Login Failed", "Invalid email or password.")

    # ── SIGNUP UI ──
    def _build_signup(self):
        self._clear()

        banner = tk.Frame(self.root, bg=COLORS["primary"], height=100)
        banner.pack(fill="x")
        tk.Label(banner, text="🛒 REMMY", font=("Segoe UI", 22, "bold"),
                 bg=COLORS["primary"], fg=COLORS["white"]).pack(pady=10)
        tk.Label(banner, text="Create your account",
                 font=APP_FONT, bg=COLORS["primary"], fg="#FFE0B2").pack()

        card = tk.Frame(self.root, bg=COLORS["white"], padx=40, pady=20)
        card.pack(fill="both", expand=True)

        form = tk.Frame(card, bg=COLORS["white"])
        form.pack(fill="x")

        self._sn_name  = self._field(form, "👤  Full Name",  0)
        self._sn_email = self._field(form, "📧  Email",      1)
        self._sn_phone = self._field(form, "📱  Phone",      2)
        self._sn_pass  = self._field(form, "🔒  Password",   3, show="*")
        self._sn_pass2 = self._field(form, "🔒  Confirm Password", 4, show="*")

        tk.Button(card, text="CREATE ACCOUNT", command=self._do_signup,
                  bg=COLORS["primary"], fg="white", font=APP_FONT_BOLD,
                  relief="flat", cursor="hand2", pady=12,
                  activebackground="#e07b10").pack(fill="x", pady=(15,5))
        tk.Button(card, text="← Back to Login", command=self._build_login,
                  bg=COLORS["white"], fg=COLORS["text_light"],
                  font=APP_FONT, relief="flat", cursor="hand2").pack()

    def _do_signup(self):
        name  = self._sn_name.get().strip()
        email = self._sn_email.get().strip()
        phone = self._sn_phone.get().strip()
        pwd   = self._sn_pass.get().strip()
        pwd2  = self._sn_pass2.get().strip()

        if not all([name, email, phone, pwd, pwd2]):
            messagebox.showwarning("Missing Fields", "Please fill in all fields.")
            return
        if pwd != pwd2:
            messagebox.showerror("Password Mismatch", "Passwords do not match.")
            return
        if len(pwd) < 6:
            messagebox.showwarning("Weak Password", "Password must be at least 6 characters.")
            return

        ok, msg = self.db.create_user(name, email, phone, pwd)
        if ok:
            messagebox.showinfo("Success! 🎉", f"{msg}\nYou can now log in.")
            self._build_login()
        else:
            messagebox.showerror("Sign Up Failed", msg)

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()


# ─── MAIN APPLICATION ─────────────────────────────────────────────────────────
class SalesApp:
    """Main dashboard after login."""

    def __init__(self, db: Database, user: dict):
        self.db   = db
        self.user = user

        self.root = tk.Tk()
        self.root.title(f"Remmy Sales — {user['full_name']}")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg=COLORS["light"])

        self._center(self.root, 1200, 750)
        self._build_ui()
        self.root.mainloop()

    def _center(self, win, w, h):
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x  = max(0, (sw-w)//2)
        y  = max(0, (sh-h)//2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ── Top NavBar ──
        nav = tk.Frame(self.root, bg=COLORS["primary"], height=60)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Label(nav, text="🛒 REMMY Sales Manager",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["primary"], fg="white").pack(side="left", padx=20)

        user_info = f"👤 {self.user['full_name']}  |  {self.user['role'].upper()}"
        tk.Label(nav, text=user_info, font=APP_FONT,
                 bg=COLORS["primary"], fg="#FFE0B2").pack(side="right", padx=10)

        tk.Button(nav, text="Logout", command=self._logout,
                  bg="#c0580a", fg="white", font=APP_FONT_BOLD,
                  relief="flat", cursor="hand2", padx=15).pack(
            side="right", padx=5, pady=12)

        # ── Sidebar + Content ──
        main = tk.Frame(self.root, bg=COLORS["light"])
        main.pack(fill="both", expand=True)

        sidebar = tk.Frame(main, bg=COLORS["secondary"], width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.content = tk.Frame(main, bg=COLORS["light"])
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar(sidebar)
        self._show_dashboard()

    def _build_sidebar(self, sidebar):
        tk.Label(sidebar, text="MENU", font=("Segoe UI", 9, "bold"),
                 bg=COLORS["secondary"], fg="#AAAAAA").pack(pady=(20,5), padx=15, anchor="w")

        menus = [
            ("🏠  Dashboard",    self._show_dashboard),
            ("🛒  My Carts",     self._show_carts),
            ("➕  New Cart",     self._new_cart_dialog),
            ("📦  Products",     self._show_products),
            ("📊  Sales History",self._show_sales),
        ]

        self._sidebar_btns = []
        for label, cmd in menus:
            btn = tk.Button(sidebar, text=label, command=cmd,
                            bg=COLORS["secondary"], fg=COLORS["light"],
                            font=("Segoe UI", 10), relief="flat",
                            cursor="hand2", anchor="w", padx=20, pady=12,
                            activebackground=COLORS["primary"],
                            activeforeground="white")
            btn.pack(fill="x")
            self._sidebar_btns.append(btn)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _page_header(self, title, subtitle=""):
        hdr = tk.Frame(self.content, bg=COLORS["light"], pady=10)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text=title, font=APP_FONT_TITLE,
                 bg=COLORS["light"], fg=COLORS["text_dark"]).pack(anchor="w")
        if subtitle:
            tk.Label(hdr, text=subtitle, font=APP_FONT,
                     bg=COLORS["light"], fg=COLORS["text_light"]).pack(anchor="w")
        ttk.Separator(self.content, orient="horizontal").pack(fill="x", padx=20)

    # ── DASHBOARD ──
    def _show_dashboard(self):
        self._clear_content()
        self._page_header("Dashboard", f"Good day, {self.user['full_name']}! 👋")

        # Stat cards
        carts = self.db.get_all_carts(self.user["id"])
        sales = self.db.get_sales(self.user["id"])
        total_rev = sum(s["total_amount"] for s in sales)
        products  = self.db.get_products()

        stats = [
            ("🛒 Total Carts",   str(len(carts)),       COLORS["primary"]),
            ("💰 Revenue (UGX)", f"{total_rev:,.0f}",   COLORS["success"]),
            ("📦 Products",      str(len(products)),     COLORS["warning"]),
            ("🧾 Sales Made",    str(len(sales)),        "#8E44AD"),
        ]

        cards_frame = tk.Frame(self.content, bg=COLORS["light"])
        cards_frame.pack(fill="x", padx=20, pady=15)

        for i, (label, value, color) in enumerate(stats):
            card = tk.Frame(cards_frame, bg=COLORS["white"],
                            relief="flat", bd=0,
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
            card.grid(row=0, column=i, padx=8, pady=5, ipadx=15, ipady=15, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=value, font=("Segoe UI", 22, "bold"),
                     bg=COLORS["white"], fg=color).pack(pady=(10,2))
            tk.Label(card, text=label, font=APP_FONT,
                     bg=COLORS["white"], fg=COLORS["text_light"]).pack(pady=(0,10))

        # Recent carts
        tk.Label(self.content, text="📋 Recent Open Carts",
                 font=APP_FONT_LARGE, bg=COLORS["light"],
                 fg=COLORS["text_dark"]).pack(anchor="w", padx=20, pady=(15,5))

        open_carts = self.db.get_carts(self.user["id"])
        if open_carts:
            for cart in open_carts[:5]:
                self._mini_cart_card(cart)
        else:
            tk.Label(self.content, text="No open carts yet. Click 'New Cart' to start selling!",
                     font=APP_FONT, bg=COLORS["light"],
                     fg=COLORS["text_light"]).pack(padx=30, pady=10, anchor="w")

    def _mini_cart_card(self, cart):
        items = self.db.get_cart_items(cart["id"])
        total = self.db.get_cart_total(cart["id"])
        f = tk.Frame(self.content, bg=COLORS["white"],
                     highlightbackground=COLORS["border"],
                     highlightthickness=1)
        f.pack(fill="x", padx=20, pady=3, ipady=8)
        tk.Label(f, text=f"🛒 Cart #{cart['id']:03d}  |  Customer: {cart['customer']}",
                 font=APP_FONT_BOLD, bg=COLORS["white"],
                 fg=COLORS["text_dark"]).pack(side="left", padx=15)
        tk.Label(f, text=f"{len(items)} items  |  UGX {total:,.0f}",
                 font=APP_FONT, bg=COLORS["white"],
                 fg=COLORS["text_light"]).pack(side="left", padx=5)
        tk.Button(f, text="Open →", command=lambda c=cart: self._open_cart(c),
                  bg=COLORS["primary"], fg="white", font=APP_FONT_BOLD,
                  relief="flat", cursor="hand2", padx=10).pack(side="right", padx=15)

    # ── CARTS LIST ──
    def _show_carts(self):
        self._clear_content()
        self._page_header("My Carts", "Manage all your customer carts")

        toolbar = tk.Frame(self.content, bg=COLORS["light"])
        toolbar.pack(fill="x", padx=20, pady=10)
        styled_button(toolbar, "➕ New Cart", self._new_cart_dialog,
                      bg=COLORS["primary"]).pack(side="left")

        frame = tk.Frame(self.content, bg=COLORS["light"])
        frame.pack(fill="both", expand=True, padx=20, pady=5)

        cols = ("ID", "Customer", "Status", "Created", "Items", "Total (UGX)")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        tree.tag_configure("open",   background="#FFF8F0")
        tree.tag_configure("closed", background="#F0F0F0", foreground="#888")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="center")
        tree.column("Customer", width=200, anchor="w")

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        carts = self.db.get_all_carts(self.user["id"])
        for cart in carts:
            items = self.db.get_cart_items(cart["id"])
            total = self.db.get_cart_total(cart["id"])
            tag = "open" if cart["status"] == "open" else "closed"
            tree.insert("", "end",
                        values=(f"#{cart['id']:03d}", cart["customer"],
                                cart["status"].upper(), cart["created_at"][:16],
                                len(items), f"{total:,.0f}"),
                        iid=str(cart["id"]), tags=(tag,))

        # Action buttons
        btn_row = tk.Frame(self.content, bg=COLORS["light"])
        btn_row.pack(fill="x", padx=20, pady=8)

        def on_open():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a cart.")
                return
            cart = next(c for c in carts if str(c["id"]) == sel[0])
            self._open_cart(cart)

        def on_delete():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a cart.")
                return
            if messagebox.askyesno("Delete Cart", "Delete this cart and all its items?"):
                self.db.delete_cart(int(sel[0]))
                messagebox.showinfo("Deleted", "Cart deleted.")
                self._show_carts()

        styled_button(btn_row, "📂 Open Cart",   on_open,   bg=COLORS["primary"]).pack(side="left", padx=5)
        styled_button(btn_row, "🗑 Delete Cart", on_delete, bg=COLORS["danger"]).pack(side="left", padx=5)

    # ── NEW CART DIALOG ──
    def _new_cart_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("New Cart")
        win.geometry("400x220")
        win.configure(bg=COLORS["white"])
        win.grab_set()
        self._center(win, 400, 220)

        tk.Label(win, text="➕ Create New Cart", font=APP_FONT_LARGE,
                 bg=COLORS["white"], fg=COLORS["text_dark"]).pack(pady=(20,5))
        tk.Label(win, text="Enter customer name for this cart:",
                 font=APP_FONT, bg=COLORS["white"],
                 fg=COLORS["text_light"]).pack()

        var = tk.StringVar()
        e = tk.Entry(win, textvariable=var, font=APP_FONT,
                     relief="solid", bd=1, width=30)
        e.pack(pady=15, ipady=8)
        e.focus()

        def create():
            name = var.get().strip()
            if not name:
                messagebox.showwarning("Required", "Customer name is required.")
                return
            cart_id = self.db.create_cart(self.user["id"], name)
            win.destroy()
            cart = {"id": cart_id, "customer": name, "status": "open"}
            self._open_cart(cart)

        styled_button(win, "CREATE CART", create,
                      bg=COLORS["primary"], width=20).pack(pady=5)

    # ── OPEN CART (Cart Detail) ──
    def _open_cart(self, cart):
        self._clear_content()
        self._page_header(
            f"🛒 Cart #{cart['id']:03d} — {cart['customer']}",
            "Add, update, or remove items · Checkout to print receipt"
        )

        # Product search bar
        search_bar = tk.Frame(self.content, bg=COLORS["light"])
        search_bar.pack(fill="x", padx=20, pady=8)

        tk.Label(search_bar, text="Search Product:",
                 font=APP_FONT_BOLD, bg=COLORS["light"],
                 fg=COLORS["text_dark"]).pack(side="left")

        search_var = tk.StringVar()
        tk.Entry(search_bar, textvariable=search_var,
                 font=APP_FONT, relief="solid", bd=1,
                 width=30).pack(side="left", padx=8, ipady=6)

        qty_var = tk.StringVar(value="1")
        tk.Label(search_bar, text="Qty:", font=APP_FONT_BOLD,
                 bg=COLORS["light"], fg=COLORS["text_dark"]).pack(side="left")
        tk.Entry(search_bar, textvariable=qty_var,
                 font=APP_FONT, relief="solid", bd=1,
                 width=5).pack(side="left", padx=5, ipady=6)

        # Product list
        prod_frame = tk.Frame(self.content, bg=COLORS["light"])
        prod_frame.pack(fill="x", padx=20, pady=2)

        p_cols = ("ID", "Product Name", "Category", "Price (UGX)", "Stock")
        prod_tree = ttk.Treeview(prod_frame, columns=p_cols,
                                  show="headings", height=7)
        for col in p_cols:
            prod_tree.heading(col, text=col)
            prod_tree.column(col, width=130, anchor="center")
        prod_tree.column("Product Name", width=250, anchor="w")
        prod_tree.pack(fill="x")

        def refresh_products(query=""):
            prod_tree.delete(*prod_tree.get_children())
            products = self.db.search_products(query) if query else self.db.get_products()
            for p in products:
                prod_tree.insert("", "end",
                                  values=(p["id"], p["name"], p["category"],
                                          f"{p['price']:,.0f}", p["stock"]),
                                  iid=str(p["id"]))

        search_var.trace("w", lambda *_: refresh_products(search_var.get()))
        refresh_products()

        def add_to_cart():
            sel = prod_tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a product.")
                return
            try:
                qty = int(qty_var.get())
                if qty <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid", "Quantity must be a positive number.")
                return
            products = self.db.get_products()
            prod = next((p for p in products if str(p["id"]) == sel[0]), None)
            if prod:
                self.db.add_item_to_cart(
                    cart["id"], prod["id"], prod["name"], qty, prod["price"]
                )
                refresh_cart_items()

        styled_button(search_bar, "➕ Add to Cart", add_to_cart,
                      bg=COLORS["success"], width=14).pack(side="left", padx=10)

        # Cart Items
        tk.Label(self.content, text="Cart Items:", font=APP_FONT_BOLD,
                 bg=COLORS["light"], fg=COLORS["text_dark"]).pack(
            anchor="w", padx=20, pady=(10,2))

        cart_frame = tk.Frame(self.content, bg=COLORS["light"])
        cart_frame.pack(fill="both", expand=True, padx=20)

        c_cols = ("Item ID", "Product", "Qty", "Unit Price", "Subtotal (UGX)")
        cart_tree = ttk.Treeview(cart_frame, columns=c_cols,
                                  show="headings", height=8)
        for col in c_cols:
            cart_tree.heading(col, text=col)
            cart_tree.column(col, width=120, anchor="center")
        cart_tree.column("Product", width=250, anchor="w")
        cart_tree.pack(side="left", fill="both", expand=True)

        sb2 = ttk.Scrollbar(cart_frame, orient="vertical", command=cart_tree.yview)
        cart_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")

        total_var = tk.StringVar(value="UGX 0")

        def refresh_cart_items():
            cart_tree.delete(*cart_tree.get_children())
            items = self.db.get_cart_items(cart["id"])
            for item in items:
                cart_tree.insert("", "end",
                                  values=(item["id"], item["product_name"],
                                          item["quantity"],
                                          f"{item['unit_price']:,.0f}",
                                          f"{item['subtotal']:,.0f}"),
                                  iid=str(item["id"]))
            total = self.db.get_cart_total(cart["id"])
            total_var.set(f"TOTAL:  UGX {total:,.0f}")

        refresh_cart_items()

        # Totals & actions
        bottom = tk.Frame(self.content, bg=COLORS["white"],
                           highlightbackground=COLORS["border"],
                           highlightthickness=1)
        bottom.pack(fill="x", padx=20, pady=8, ipady=8)

        tk.Label(bottom, textvariable=total_var,
                 font=("Segoe UI", 14, "bold"),
                 bg=COLORS["white"],
                 fg=COLORS["primary"]).pack(side="left", padx=20)

        def update_item():
            sel = cart_tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select an item to update.")
                return
            item_id = int(sel[0])
            items   = self.db.get_cart_items(cart["id"])
            item    = next(i for i in items if i["id"] == item_id)

            win = tk.Toplevel(self.root)
            win.title("Update Item")
            win.geometry("350x200")
            win.configure(bg=COLORS["white"])
            win.grab_set()
            self._center(win, 350, 200)

            tk.Label(win, text=f"Update: {item['product_name']}",
                     font=APP_FONT_BOLD, bg=COLORS["white"],
                     fg=COLORS["text_dark"]).pack(pady=15)
            f = tk.Frame(win, bg=COLORS["white"])
            f.pack()
            tk.Label(f, text="Qty:", font=APP_FONT,
                     bg=COLORS["white"]).grid(row=0, column=0, padx=10)
            qv = tk.StringVar(value=str(item["quantity"]))
            tk.Entry(f, textvariable=qv, width=8,
                     relief="solid", bd=1).grid(row=0, column=1, ipady=6)
            tk.Label(f, text="Price:", font=APP_FONT,
                     bg=COLORS["white"]).grid(row=1, column=0, padx=10, pady=10)
            pv = tk.StringVar(value=str(item["unit_price"]))
            tk.Entry(f, textvariable=pv, width=8,
                     relief="solid", bd=1).grid(row=1, column=1, ipady=6)

            def save():
                try:
                    self.db.update_cart_item(item_id, int(qv.get()), float(pv.get()))
                    win.destroy()
                    refresh_cart_items()
                except ValueError:
                    messagebox.showerror("Error", "Enter valid numbers.")

            styled_button(win, "Save Changes", save,
                          bg=COLORS["warning"], width=18).pack(pady=10)

        def delete_item():
            sel = cart_tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select an item to remove.")
                return
            if messagebox.askyesno("Remove", "Remove this item from cart?"):
                self.db.delete_cart_item(int(sel[0]))
                refresh_cart_items()

        def checkout():
            items = self.db.get_cart_items(cart["id"])
            if not items:
                messagebox.showwarning("Empty Cart", "Add items before checkout.")
                return
            total = self.db.get_cart_total(cart["id"])

            win = tk.Toplevel(self.root)
            win.title("Checkout")
            win.geometry("350x220")
            win.configure(bg=COLORS["white"])
            win.grab_set()
            self._center(win, 350, 220)

            tk.Label(win, text="💳 Checkout",
                     font=APP_FONT_LARGE, bg=COLORS["white"],
                     fg=COLORS["text_dark"]).pack(pady=15)
            tk.Label(win, text=f"Total: UGX {total:,.0f}",
                     font=("Segoe UI", 14, "bold"), bg=COLORS["white"],
                     fg=COLORS["success"]).pack()

            pm_var = tk.StringVar(value="Cash")
            f2 = tk.Frame(win, bg=COLORS["white"])
            f2.pack(pady=10)
            tk.Label(f2, text="Payment:", font=APP_FONT_BOLD,
                     bg=COLORS["white"]).pack(side="left", padx=5)
            ttk.Combobox(f2, textvariable=pm_var,
                         values=["Cash", "Mobile Money", "Card", "Bank Transfer"],
                         width=15, state="readonly").pack(side="left")

            def confirm():
                self.db.record_sale(cart["id"], self.user["id"],
                                    cart["customer"], total, pm_var.get())
                self.db.close_cart(cart["id"])
                win.destroy()
                # Print receipt
                PrintManager.print_receipt(
                    cart, items, self.user["full_name"], pm_var.get()
                )
                messagebox.showinfo("Sale Complete! 🎉",
                    f"Sale recorded.\nTotal: UGX {total:,.0f}\nReceipt generated!")
                self._show_carts()

            styled_button(win, "✅ Confirm & Print", confirm,
                          bg=COLORS["success"], width=20).pack(pady=10)

        styled_button(bottom, "✏️ Update Item",  update_item, bg=COLORS["warning"],  width=14).pack(side="right", padx=5)
        styled_button(bottom, "🗑 Remove Item",  delete_item, bg=COLORS["danger"],   width=14).pack(side="right", padx=5)
        styled_button(bottom, "✅ Checkout",     checkout,    bg=COLORS["success"],  width=14).pack(side="right", padx=5)
        styled_button(bottom, "← Back",         self._show_carts, bg=COLORS["secondary"], width=10).pack(side="left", padx=10)

    # ── PRODUCTS ──
    def _show_products(self):
        self._clear_content()
        self._page_header("📦 Products Catalogue", "All available products")

        frame = tk.Frame(self.content, bg=COLORS["light"])
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("ID", "Product Name", "Category", "Price (UGX)", "Stock", "Description")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")
        tree.column("Product Name", width=200, anchor="w")
        tree.column("Description",  width=220, anchor="w")

        for p in self.db.get_products():
            tree.insert("", "end", values=(
                p["id"], p["name"], p["category"],
                f"{p['price']:,.0f}", p["stock"], p["description"] or ""
            ))

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ── SALES HISTORY ──
    def _show_sales(self):
        self._clear_content()
        self._page_header("📊 Sales History", "All completed transactions")

        frame = tk.Frame(self.content, bg=COLORS["light"])
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("Sale ID", "Cart", "Customer", "Total (UGX)", "Payment", "Date")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="center")
        tree.column("Customer", width=200, anchor="w")

        sales = self.db.get_sales(self.user["id"])
        total_rev = 0
        for s in sales:
            tree.insert("", "end", values=(
                f"#{s['id']:03d}", f"#{s['cart_id']:03d}",
                s["customer"], f"{s['total_amount']:,.0f}",
                s["payment_method"], s["sold_at"][:16]
            ))
            total_rev += s["total_amount"]

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Label(self.content,
                 text=f"Total Revenue:  UGX {total_rev:,.0f}",
                 font=("Segoe UI", 13, "bold"),
                 bg=COLORS["light"], fg=COLORS["success"]).pack(
            anchor="e", padx=25, pady=8)

    # ── LOGOUT ──
    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            start()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
def start():
    db = Database()

    def on_login(user):
        SalesApp(db, user)

    AuthWindow(db, on_login)


if __name__ == "__main__":
    start()