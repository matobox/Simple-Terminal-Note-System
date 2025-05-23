import tkinter as tk
import os
import sys
import time
import datetime
import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageTk

# Déterminer le chemin de base de l'application
if getattr(sys, 'frozen', False):
    # Si l'app est packagée avec PyInstaller
    application_path = os.path.dirname(sys.executable)
else:
    # Si l'app est exécutée comme script Python
    application_path = os.path.dirname(os.path.abspath(__file__))

# Utiliser des chemins absolus basés sur l'emplacement de l'application
NOTES_DIR = os.path.join(application_path, "notes")
VERSION = "1.0"
FAVORITES_FILE = os.path.join(application_path, "favorites.json")

# Couleurs Fallout authentiques
TERMINAL_BG = "#0F0F0F"  # Noir légèrement adouci
TERMINAL_FG = "#4CFF4C"  # Vert terminal de Fallout
TERMINAL_HEADER = "#4CFF4C"  # Pour les titres
TERMINAL_SELECTED = "#FFFFFF"  # Blanc pour la sélection

# Constantes de l'interface
MIN_WIDTH = 650
MIN_HEIGHT = 650
FONT_FAMILY = "Courier"  # Police monospace classique
FONT_SIZE_NORMAL = 13
FONT_SIZE_HEADER = 15
PADDING = 10

if not os.path.exists(NOTES_DIR):
    os.makedirs(NOTES_DIR)

def create_window_icon(size=32, color="#4CFF4C", bg_color="#0F0F0F"):
    """Crée une icône de terminal pour l'en-tête de la fenêtre"""
    # Créer une image avec un fond transparent
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Convertir les couleurs hex en RGB
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    bg_rgb = hex_to_rgb(bg_color)
    color_rgb = hex_to_rgb(color)

    # Calculer le padding
    padding = int(size * 0.1)

    # Dessiner le fond du terminal (rectangle arrondi)
    draw.rectangle(
        [(padding, padding), (size - padding, size - padding)],
        fill=bg_rgb + (255,),  # Ajouter alpha=255
        outline=color_rgb + (255,),
        width=2
    )

    # Dessiner la barre de titre
    title_height = int(size * 0.2)
    draw.rectangle(
        [(padding, padding), (size - padding, padding + title_height)],
        fill=color_rgb + (255,),
        outline=None
    )

    # Dessiner les boutons de la barre de titre
    circle_size = int(size * 0.05)
    for pos_x in [0.2, 0.35, 0.5]:
        center_x = int(size * pos_x)
        center_y = padding + title_height // 2
        draw.ellipse(
            [(center_x - circle_size, center_y - circle_size),
             (center_x + circle_size, center_y + circle_size)],
            fill=bg_rgb + (255,),
            outline=None
        )

    # Dessiner le prompt ">"
    prompt_y = int(size * 0.5)
    font_size = int(size * 0.2)
    draw.text(
        (int(size * 0.25), prompt_y - font_size // 2),
        ">",
        fill=color_rgb + (255,),
    )

    # Dessiner le curseur clignotant
    cursor_width = int(size * 0.1)
    cursor_height = int(size * 0.03)
    cursor_x = int(size * 0.35)
    cursor_y = prompt_y
    draw.rectangle(
        [(cursor_x, cursor_y - cursor_height),
         (cursor_x + cursor_width, cursor_y + cursor_height)],
        fill=color_rgb + (255,),
        outline=None
    )

    # Dessiner quelques lignes de "code"
    for i in range(3):
        line_y = int(size * (0.65 + i * 0.1))
        line_length = int((0.3 + i * 0.15) * (size - 2 * padding))
        draw.line(
            [(int(size * 0.25), line_y),
             (int(size * 0.25) + line_length, line_y)],
            fill=color_rgb + (255,),
            width=1
        )

    return img


class TerminalNotesApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Simple Terminal Note System")
        self.master.configure(bg=TERMINAL_BG)

        # Création et définition de l'icône de la fenêtre
        window_icon = create_window_icon(size=64, color=TERMINAL_FG, bg_color=TERMINAL_BG)
        # Convertir l'image en format PhotoImage pour Tkinter
        icon_data = ImageTk.PhotoImage(window_icon)
        # Conserver une référence à l'icône pour éviter le garbage collection
        self.icon_ref = icon_data
        # Définir l'icône de la fenêtre
        self.master.iconphoto(True, icon_data)

        # Dimensionnement avec taille minimale
        self.master.geometry("800x600")
        self.master.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Variables d'état
        self.mode = "menu"
        self.notes = [f for f in os.listdir(NOTES_DIR) if f.endswith(".txt")]
        self.current_index = 0 if self.notes else -1
        self.save_job = None
        self.favorites = set()  # Ensemble pour stocker les notes favorites
        self.visual_to_index = []  # Mapping de l'ordre visuel vers les indices dans self.notes

        # Charger les favoris
        self.load_favorites()

        # Création de la structure de l'interface
        self.create_layout()

        # Configuration initiale
        self.load_menu()
        self.bind_menu_keys()

        # Lier l'événement de redimensionnement pour mettre à jour l'interface d'aide
        self.master.bind("<Configure>", self.update_help_display)

    def create_layout(self):
        """Crée la structure de l'interface utilisateur"""
        # Création d'un frame pour l'en-tête
        header_frame = tk.Frame(self.master, bg=TERMINAL_BG)
        header_frame.pack(side="top", fill="x")

        # Frame pour les titres
        title_frame = tk.Frame(header_frame, bg=TERMINAL_BG)
        title_frame.pack(side="left", fill="both", expand=True)

        # Barre de titre
        self.header = tk.Label(
            title_frame, 
            text="SIMPLE TERMINAL NOTE SYSTEM",
            bg=TERMINAL_BG, 
            fg=TERMINAL_HEADER, 
            font=(FONT_FAMILY, FONT_SIZE_HEADER, "bold"),
            anchor="center",
            padx=PADDING, 
            pady=PADDING
        )
        self.header.pack(side="top", fill="x")

        # Variable pour indiquer si on affiche le bouton d'aide compact
        self.compact_help = False

        # Sous-titre
        self.subtitle = tk.Label(
            title_frame, 
            text=f"TERMINAL v{VERSION} - COPYRIGHT 2075-2077 ROBCO INDUSTRIES",
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG, 
            font=(FONT_FAMILY, 11),
            anchor="center"
        )
        self.subtitle.pack(side="top", fill="x", pady=(0, PADDING))

        # Séparateur horizontal
        separator = tk.Frame(self.master, height=2, bg=TERMINAL_FG)
        separator.pack(fill="x", padx=PADDING*2, pady=PADDING//2)

        # Frame principale (contient les panneaux gauche et droit)
        self.main_frame = tk.Frame(self.master, bg=TERMINAL_BG)
        self.main_frame.pack(fill="both", expand=True, padx=PADDING, pady=PADDING)

        # Panneau de gauche (liste des notes)
        self.left_frame = tk.Frame(self.main_frame, bg=TERMINAL_BG)
        self.left_frame.pack(side="left", fill="y", padx=(0, PADDING))

        self.left = tk.Text(
            self.left_frame, 
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            width=30, 
            height=25, 
            borderwidth=2, 
            relief="groove",
            insertbackground=TERMINAL_FG,
            padx=PADDING//2, 
            pady=PADDING//2
        )
        self.left.pack(fill="both", expand=True)
        self.left.configure(state="disabled")

        # Séparateur vertical
        self.separator = tk.Frame(self.main_frame, width=2, bg=TERMINAL_FG)
        self.separator.pack(side="left", fill="y")

        # Panneau de droite (contenu de la note)
        self.right_frame = tk.Frame(self.main_frame, bg=TERMINAL_BG)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(PADDING, 0))

        self.right = tk.Text(
            self.right_frame, 
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            insertbackground=TERMINAL_FG, 
            insertwidth=0,  # Curseur invisible par défaut (mode consultation)
            borderwidth=2, 
            relief="groove",
            wrap="word",
            padx=PADDING//2, 
            pady=PADDING//2
        )
        self.right.pack(fill="both", expand=True)

        # Barre d'aide
        self.status_frame = tk.Frame(self.master, bg=TERMINAL_BG, height=30)
        self.status_frame.pack(side="bottom", fill="x", padx=PADDING, pady=PADDING)

        # Aide rapide
        self.help_label = tk.Label(
            self.status_frame, 
            text="↑/↓: Navigation | Entrée: Sélectionner | n: Nouveau | r: Renommer | d: Supprimer | q: Quitter", 
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG, 
            font=(FONT_FAMILY, 11),
            anchor="center"
        )
        self.help_label.pack(fill="x")

    def update_help_display(self, event=None):
        """Met à jour l'affichage de l'aide en fonction de la largeur de la fenêtre"""
        # Ne traiter que les événements de redimensionnement de la fenêtre principale
        if event and event.widget != self.master:
            return

        # Déterminer si on doit passer en mode compact
        window_width = self.master.winfo_width()

        # Seuil de largeur pour le mode compact (ajuster selon vos besoins)
        compact_threshold = 700

        if window_width < compact_threshold and not self.compact_help:
            # Passer en mode compact
            self.compact_help = True
            self.update_status_bar()
        elif window_width >= compact_threshold and self.compact_help:
            # Revenir en mode normal
            self.compact_help = False
            self.update_status_bar()

    def calculate_statistics(self):
        """Calcule les statistiques du texte (nombre de mots, caractères et temps de lecture)"""
        if self.mode != "editor":
            return None

        # Récupérer le contenu du texte
        content = self.right.get("1.0", tk.END)

        # Calculer le nombre de caractères (sans compter les espaces de fin)
        char_count = len(content.rstrip())

        # Calculer le nombre de mots (en divisant par les espaces)
        words = content.split()
        word_count = len(words)

        # Estimer le temps de lecture (basé sur 200 mots par minute)
        reading_time_minutes = word_count / 200

        # Formater le temps de lecture
        if reading_time_minutes < 1:
            reading_time_text = f"{int(reading_time_minutes * 60)} sec"
        else:
            minutes = int(reading_time_minutes)
            seconds = int((reading_time_minutes - minutes) * 60)
            if seconds > 0:
                reading_time_text = f"{minutes} min {seconds} sec"
            else:
                reading_time_text = f"{minutes} min"

        return {
            "word_count": word_count,
            "char_count": char_count,
            "reading_time": reading_time_text
        }

    def update_status_bar(self):
        """Met à jour la barre d'état en fonction du mode et de l'espace disponible"""
        if self.compact_help:
            # Mode compact: un seul bouton d'aide
            self.help_label.config(text="h: Aide / Commandes")
        else:
            # Mode normal: toutes les commandes
            if self.mode == "menu":
                self.help_label.config(text="↑/↓: Navigation | Entrée: Sélectionner | n: Nouveau | r: Renommer | f: Favoris | d: Supprimer | q: Quitter | h: Aide")
            else:  # mode editor
                # Calculer les statistiques
                stats = self.calculate_statistics()
                if stats:
                    stats_text = f"Mots: {stats['word_count']} | Caractères: {stats['char_count']} | Temps de lecture: {stats['reading_time']}"
                    self.help_label.config(text=f"ESC: Retour au menu | {stats_text} | Sauvegarde automatique activée")
                else:
                    self.help_label.config(text="ESC: Retour au menu | Sauvegarde automatique activée")

    def bind_menu_keys(self):
        self.master.bind("<Up>", self.move_up)
        self.master.bind("<Down>", self.move_down)
        self.master.bind("<Return>", self.open_note)
        self.master.bind("n", self.create_new_note)
        self.master.bind("d", self.delete_note)
        self.master.bind("r", self.rename_note)
        self.master.bind("f", self.toggle_favorite)
        self.master.bind("q", self.quit_app)
        self.master.bind("h", self.show_help_popup)

    def unbind_menu_keys(self):
        self.master.unbind("<Up>")
        self.master.unbind("<Down>")
        self.master.unbind("<Return>")
        self.master.unbind("n")
        self.master.unbind("d")
        self.master.unbind("r")
        self.master.unbind("f")
        self.master.unbind("q")
        self.master.unbind("h")

    def bind_editor_keys(self):
        self.master.bind("<Escape>", self.back_to_menu)
        # 'h' binding removed to allow typing 'h' in notes
        # Plus besoin de lier l'effet de frappe

    def unbind_editor_keys(self):
        self.master.unbind("<Escape>")
        # 'h' unbinding removed as it's no longer bound in editor mode

    def get_note_mtime(self, note_filename):
        """Retourne la date de dernière modification d'une note"""
        note_path = os.path.join(NOTES_DIR, note_filename)
        mtime = os.path.getmtime(note_path)
        return datetime.datetime.fromtimestamp(mtime)

    def get_menu_text(self):
        """Génère le contenu du menu principal avec notes regroupées par date"""
        lines = []
        lines.append("** NOTES DISPONIBLES **")
        lines.append("")

        # Réinitialiser le mapping visuel
        self.visual_to_index = []
        visual_position = 0  # Position visuelle courante

        if self.notes:
            # Grouper les notes par date de modification
            notes_by_date = defaultdict(list)
            note_indices = {}  # Pour conserver les indices originaux

            # Trier les notes par date de dernière modification (plus récente d'abord)
            sorted_notes = sorted(
                enumerate(self.notes),
                key=lambda x: self.get_note_mtime(x[1]),
                reverse=True
            )

            # Réorganiser la liste des notes et les indices
            sorted_indices = []
            self.notes = [note for _, note in sorted_notes]

            # Mise à jour de l'index courant si nécessaire
            if self.current_index >= 0:
                # Trouver la nouvelle position de la note sélectionnée
                selected_note = sorted_notes[self.current_index][1] if self.current_index < len(sorted_notes) else None
                if selected_note:
                    self.current_index = self.notes.index(selected_note)

            # Afficher d'abord les favoris
            if self.favorites:
                lines.append("-- FAVORIS --")

                # Filtrer les notes favorites qui existent encore
                valid_favorites = [note for note in self.favorites if note in self.notes]

                # Afficher les notes favorites
                for note in valid_favorites:
                    i = self.notes.index(note)
                    name = note.replace(".txt", "")

                    # Ajouter au mapping visuel
                    self.visual_to_index.append(i)

                    if i == self.current_index:
                        lines.append(f"[ ★ {name} ]")  # Note favorite sélectionnée
                    else:
                        lines.append(f"  ★ {name}  ")  # Note favorite non sélectionnée

                    visual_position += 1

                lines.append("")  # Espace après les favoris

            # Grouper par date
            for i, note in enumerate(self.notes):
                note_date = self.get_note_mtime(note)
                date_str = note_date.strftime("%d/%m/%Y")
                notes_by_date[date_str].append((i, note))

            # Afficher les notes par groupe de date
            for date_str, note_list in notes_by_date.items():
                # Ajouter l'en-tête de date
                lines.append(f"-- {date_str} --")

                # Ajouter les notes de cette date
                for i, note in note_list:
                    # Ne pas afficher à nouveau les favoris
                    if note in self.favorites:
                        continue

                    # Ajouter au mapping visuel
                    self.visual_to_index.append(i)

                    name = note.replace(".txt", "")
                    if i == self.current_index:
                        lines.append(f"[ {name} ]")  # Note sélectionnée entre crochets
                    else:
                        lines.append(f"  {name}  ")  # Note non sélectionnée avec espaces

                    visual_position += 1

                # Ajouter un espace entre les groupes de dates
                lines.append("")
        else:
            lines.append("> AUCUNE NOTE DISPONIBLE")
            lines.append("")
            lines.append("Utilisez 'n' pour créer une nouvelle note")

        return "\n".join(lines)


    def load_menu(self):
        """Charge l'interface du menu principal"""
        self.mode = "menu"

        # Mise à jour de l'en-tête
        self.header.config(text="SIMPLE TERMINAL NOTE SYSTEM")
        self.subtitle.config(text="V1.0 - MATOBO")

        # Mise à jour de l'interface d'aide
        self.update_status_bar()

        # Mise à jour du contenu du menu
        self.left.configure(state="normal")
        self.left.delete("1.0", "end")
        self.left.insert("1.0", self.get_menu_text())
        self.left.configure(state="disabled")

        # Mise à jour de l'aperçu
        self.right.configure(state="normal")  # Temporairement activé pour mise à jour
        self.right.delete("1.0", "end")

        if self.notes and self.current_index >= 0:
            try:
                with open(os.path.join(NOTES_DIR, self.notes[self.current_index]), "r", encoding="utf-8") as f:
                    preview = f.read(800)  # Un peu plus long pour plus de contexte

                    # Formater l'en-tête de l'aperçu
                    note_name = self.notes[self.current_index].replace(".txt", "")
                    self.right.insert("1.0", f">> APERÇU: {note_name} <<\n\n")
                    self.right.tag_add("header", "1.0", "2.0")
                    self.right.tag_config("header", foreground=TERMINAL_HEADER)

                    # Contenu
                    if preview:
                        self.right.insert("end", preview)
                    else:
                        self.right.insert("end", "[ Note vide ]")

                    # Ajoute un indicateur si le contenu est tronqué
                    if len(preview) >= 800:
                        self.right.insert("end", "\n\n[...] Note tronquée, appuyez sur Entrée pour voir tout")
                        self.right.tag_add("truncated", "end-2l", "end")
                        self.right.tag_config("truncated", foreground=TERMINAL_SELECTED)
            except Exception as e:
                self.right.insert("1.0", f"ERREUR: Impossible de lire la note.\n{str(e)}")
        else:
            self.right.insert("1.0", "Créez une note avec la touche 'n' ou sélectionnez une note existante.")

        # Empêcher l'édition tout en permettant l'interaction avec le clavier
        self.right.configure(insertwidth=0)  # Masquer le curseur d'insertion
        # Ajouter un gestionnaire pour empêcher la modification du texte
        self.right.bind("<Key>", lambda e: "break")

        # Remettre le focus sur la fenêtre principale pour permettre les raccourcis
        self.master.focus_set()

        self.bind_menu_keys()


    def get_visual_position(self):
        """Retourne la position visuelle de la note actuellement sélectionnée"""
        if not self.notes or self.current_index < 0:
            return -1

        try:
            return self.visual_to_index.index(self.current_index)
        except ValueError:
            # Si la note n'est pas dans le mapping visuel, retourner -1
            return -1

    def move_up(self, event):
        """Déplace la sélection vers le haut dans la liste des notes"""
        if not self.notes or not self.visual_to_index:
            return

        # Trouver la position visuelle actuelle
        visual_pos = self.get_visual_position()

        # Si la note n'est pas dans le mapping visuel ou est déjà en haut
        if visual_pos <= 0:
            return

        # Déplacer vers le haut dans l'ordre visuel
        new_visual_pos = visual_pos - 1
        self.current_index = self.visual_to_index[new_visual_pos]
        self.load_menu()

    def move_down(self, event):
        """Déplace la sélection vers le bas dans la liste des notes"""
        if not self.notes or not self.visual_to_index:
            return

        # Trouver la position visuelle actuelle
        visual_pos = self.get_visual_position()

        # Si la note n'est pas dans le mapping visuel ou est déjà en bas
        if visual_pos < 0 or visual_pos >= len(self.visual_to_index) - 1:
            return

        # Déplacer vers le bas dans l'ordre visuel
        new_visual_pos = visual_pos + 1
        self.current_index = self.visual_to_index[new_visual_pos]
        self.load_menu()

    def load_favorites(self):
        """Charge la liste des notes favorites depuis le fichier"""
        try:
            if os.path.exists(FAVORITES_FILE):
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    favorites_list = json.load(f)
                    self.favorites = set(favorites_list)
        except Exception as e:
            # En cas d'erreur, on commence avec une liste vide
            self.favorites = set()

    def save_favorites(self):
        """Enregistre la liste des notes favorites dans le fichier"""
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.favorites), f)
        except Exception as e:
            pass  # Ignorer les erreurs d'écriture

    def toggle_favorite(self, event):
        """Marque ou démarque une note comme favorite"""
        if not self.notes or self.current_index < 0:
            return

        note = self.notes[self.current_index]

        # Ajouter ou retirer de l'ensemble des favoris
        if note in self.favorites:
            self.favorites.remove(note)
        else:
            self.favorites.add(note)

        # Sauvegarder les favoris
        self.save_favorites()

        # Mettre à jour l'affichage
        self.load_menu()

    def create_new_note(self, event):
        """Crée une nouvelle note avec un nom basé sur la date et l'heure"""
        # Format plus court mais toujours unique avec secondes pour éviter les doublons
        timestamp = time.strftime("%m%d_%H%M%S")
        name = f"note_{timestamp}.txt"

        # Vérifier si le fichier existe déjà et ajouter un suffixe si nécessaire
        base_path = os.path.join(NOTES_DIR, name)
        counter = 1
        while os.path.exists(base_path):
            name = f"note_{timestamp}_{counter}.txt"
            base_path = os.path.join(NOTES_DIR, name)
            counter += 1

        # Création du fichier vide
        with open(base_path, "w", encoding="utf-8") as f:
            f.write("")

        # Mise à jour de la liste et sélection de la nouvelle note
        self.notes.insert(0, name)  # Ajout au début car c'est la plus récente
        self.current_index = 0

        # Ouvre directement la note pour édition
        self.open_note(None)

    def show_help_popup(self, event=None):
        """Affiche un popup avec toutes les commandes disponibles"""
        # Variables pour stocker les liaisons clavier précédentes
        self.prev_bindings = {}

        # Stocker l'état des liaisons clavier actuelles pour les touches importantes
        for key in ["<Return>", "<Escape>"]:
            self.prev_bindings[key] = self.master.bind(key)
            self.master.unbind(key)

        # Créer un conteneur pour le popup d'aide
        help_container = tk.Frame(
            self.master,
            bg=TERMINAL_BG,
            highlightbackground=TERMINAL_FG,
            highlightthickness=2
        )

        # Créer le cadre du popup d'aide
        help_frame = tk.Frame(
            help_container,
            bg=TERMINAL_BG,
            borderwidth=3,  # Bordure plus épaisse pour meilleure visibilité
            relief="raised"  # Relief en relief pour mieux se détacher du fond
        )
        help_frame.pack(fill="both", expand=True)

        # Positionner le cadre au centre de la fenêtre
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        popup_width = 500
        popup_height = 300

        x_pos = (window_width - popup_width) // 2
        y_pos = (window_height - popup_height) // 2

        help_container.place(
            x=x_pos, y=y_pos,
            width=popup_width, height=popup_height
        )

        # Cadre pour le titre
        header_container = tk.Frame(help_frame, bg=TERMINAL_BG)
        header_container.pack(fill="x", pady=10)

        # Titre du popup
        tk.Label(
            header_container,
            text="AIDE - COMMANDES DISPONIBLES",
            bg=TERMINAL_BG,
            fg=TERMINAL_HEADER,
            font=(FONT_FAMILY, FONT_SIZE_HEADER, "bold")
        ).pack(side="left", fill="x", expand=True, pady=10)

        # Conteneur pour les commandes
        commands_frame = tk.Frame(help_frame, bg=TERMINAL_BG)
        commands_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Liste des commandes selon le mode actuel
        if self.mode == "menu":
            commands = [
                ("↑/↓", "Navigation dans la liste"),
                ("Entrée", "Ouvrir la note sélectionnée"),
                ("n", "Créer une nouvelle note"),
                ("r", "Renommer la note sélectionnée"),
                ("f", "Marquer/Démarquer comme favori"),
                ("d", "Supprimer la note sélectionnée"),
                ("q", "Quitter l'application"),
                ("h", "Afficher cette aide")
            ]
        else:  # mode editor
            commands = [
                ("Échap", "Retour au menu principal"),
                ("", "Sauvegarde automatique activée"),
                ("h", "Afficher cette aide")
            ]

        # Affichage des commandes en deux colonnes
        for i, (key, desc) in enumerate(commands):
            row = i // 1  # Une seule colonne
            col = i % 1

            # Frame pour chaque commande
            cmd_frame = tk.Frame(commands_frame, bg=TERMINAL_BG)
            cmd_frame.pack(anchor="w", pady=5)

            # Touche
            tk.Label(
                cmd_frame,
                text=f"[ {key} ]",
                width=10,
                bg=TERMINAL_BG,
                fg=TERMINAL_HEADER,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                anchor="w"
            ).pack(side="left")

            # Description
            tk.Label(
                cmd_frame,
                text=desc,
                bg=TERMINAL_BG,
                fg=TERMINAL_FG,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                anchor="w"
            ).pack(side="left")

        # Bouton pour fermer le popup
        tk.Button(
            help_frame,
            text="FERMER",
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            relief="raised",  # Relief plus visible
            borderwidth=2,    # Bordure plus épaisse
            highlightbackground=TERMINAL_FG,  # Contour de la même couleur que le texte
            highlightthickness=1,  # Contour visible
            command=lambda: close_help()
        ).pack(pady=15)

        # Fonction pour fermer le popup d'aide
        def close_help():
            # Restaurer les liaisons clavier précédentes
            for key, binding in self.prev_bindings.items():
                if binding:
                    self.master.bind(key, binding)

            # Détruire le popup
            help_container.destroy()

        # Liaison des touches pour fermer le popup
        self.master.bind("<Return>", lambda e: close_help())
        self.master.bind("<Escape>", lambda e: close_help())

    def show_confirmation_popup(self, message, action_callback):
        """Affiche un panneau de confirmation intégré dans la fenêtre principale"""
        # Variables pour stocker les liaisons clavier précédentes
        self.prev_bindings = {}
        self.confirmation_result = None

        # Stocker l'état des liaisons clavier actuelles
        for key in ["<Left>", "<Right>", "<Tab>", "<Return>", "<Escape>", "n", "d", "q"]:
            self.prev_bindings[key] = self.master.bind(key)
            self.master.unbind(key)

        # Variable pour suivre le bouton sélectionné (0: Confirmer, 1: Annuler)
        selected_button = tk.IntVar(value=1)  # Annuler sélectionné par défaut

        # Créer un conteneur externe pour le cadre de confirmation qui ne changera pas de couleur
        confirmation_container = tk.Frame(
            self.master,
            bg=TERMINAL_BG,
            highlightbackground=TERMINAL_FG,
            highlightcolor=TERMINAL_FG,
            highlightthickness=2
        )

        # Créer un cadre de confirmation qui recouvre partiellement l'interface
        self.confirmation_frame = tk.Frame(
            confirmation_container,
            bg=TERMINAL_BG,
            borderwidth=3,  # Bordure plus épaisse
            relief="raised"  # Relief en relief pour mieux se détacher
        )
        self.confirmation_frame.pack(fill="both", expand=True)

        # Positionner le cadre au centre de la fenêtre
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        popup_width = 400
        popup_height = 200

        x_pos = (window_width - popup_width) // 2
        y_pos = (window_height - popup_height) // 2

        confirmation_container.place(
            x=x_pos, y=y_pos,
            width=popup_width, height=popup_height
        )

        # Message de confirmation
        tk.Label(
            self.confirmation_frame, 
            text=message, 
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            wraplength=380,
            pady=20
        ).pack(fill="x")

        # Fonction pour mettre à jour l'affichage des boutons
        def update_buttons():
            confirm_label.config(text="[ CONFIRMER ]" if selected_button.get() == 0 else "  CONFIRMER  ")
            cancel_label.config(text="[ ANNULER ]" if selected_button.get() == 1 else "  ANNULER  ")

        # Fonction pour déplacer la sélection
        def move_selection(direction):
            new_val = (selected_button.get() + direction) % 2
            selected_button.set(new_val)
            update_buttons()

        # Fonction pour fermer le panneau et restaurer l'interface
        def close_confirmation(result=None):
            # Restaurer les liaisons clavier précédentes
            for key, binding in self.prev_bindings.items():
                if binding:
                    self.master.bind(key, binding)

            # Détruire le panneau de confirmation
            confirmation_container.destroy()

            # Exécuter le callback si confirmé
            if result:
                action_callback()

        # Fonction pour activer le bouton sélectionné
        def activate_selection(event=None):
            if selected_button.get() == 0:
                close_confirmation(True)
            else:
                close_confirmation(None)

        # Cadre pour les boutons
        btn_frame = tk.Frame(self.confirmation_frame, bg=TERMINAL_BG)
        btn_frame.pack(pady=20)

        # Label pour le bouton Confirmer
        confirm_label = tk.Label(
            btn_frame, 
            text="  CONFIRMER  ", 
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            padx=10
        )
        confirm_label.pack(side="left", padx=10)

        # Label pour le bouton Annuler
        cancel_label = tk.Label(
            btn_frame, 
            text="[ ANNULER ]",  # Sélectionné par défaut
            bg=TERMINAL_BG, 
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            padx=10
        )
        cancel_label.pack(side="left", padx=10)

        # Liaison des touches clavier pour le panneau
        self.master.bind("<Left>", lambda e: move_selection(-1))
        self.master.bind("<Right>", lambda e: move_selection(1))
        self.master.bind("<Tab>", lambda e: move_selection(1))
        self.master.bind("<Return>", lambda e: activate_selection())
        self.master.bind("<Escape>", lambda e: close_confirmation(None))

        # Afficher immédiatement les boutons selon leur état
        update_buttons()

    def rename_note(self, event):
        """Renomme la note sélectionnée"""
        if not self.notes or self.current_index < 0:
            return

        note = self.notes[self.current_index]
        old_name = note.replace(".txt", "")

        # Variables pour le dialogue de renommage
        self.rename_dialog_active = True
        self.rename_result = None

        # Stocker les liaisons clavier actuelles
        prev_bindings = {}
        for key in ["<Up>", "<Down>", "<Return>", "<Escape>", "n", "r", "d", "q"]:
            prev_bindings[key] = self.master.bind(key)
            self.master.unbind(key)

        # Créer un conteneur externe pour le cadre du dialogue qui ne changera pas de couleur
        outer_container = tk.Frame(
            self.master,
            bg=TERMINAL_BG,
            highlightbackground=TERMINAL_FG,
            highlightcolor=TERMINAL_FG,
            highlightthickness=2
        )

        # Créer le cadre du dialogue à l'intérieur du conteneur
        rename_frame = tk.Frame(
            outer_container,
            bg=TERMINAL_BG,
            borderwidth=3,
            relief="raised"
        )
        rename_frame.pack(fill="both", expand=True)

        # Positionner le cadre au centre
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        popup_width = 400
        popup_height = 200

        x_pos = (window_width - popup_width) // 2
        y_pos = (window_height - popup_height) // 2

        outer_container.place(
            x=x_pos, y=y_pos,
            width=popup_width, height=popup_height
        )

        # Titre du dialogue
        tk.Label(
            rename_frame,
            text=f"Renommer la note: '{old_name}'",
            bg=TERMINAL_BG,
            fg=TERMINAL_HEADER,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            pady=10
        ).pack(fill="x")

        # Message d'instruction
        tk.Label(
            rename_frame,
            text="(sans l'extension .txt)",
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            pady=5
        ).pack(fill="x")

        # Champ de saisie
        input_frame = tk.Frame(rename_frame, bg=TERMINAL_BG)
        input_frame.pack(pady=10)

        # Préfixe pour le style terminal
        tk.Label(
            input_frame,
            text="> ",
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL)
        ).pack(side="left")

        # Champ de saisie du nouveau nom
        entry = tk.Entry(
            input_frame,
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            insertbackground=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            width=30,
            relief="flat",
            highlightthickness=0,
            borderwidth=0
        )
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, old_name)
        entry.select_range(0, "end")
        entry.focus_set()

        # Message d'erreur (initialement vide)
        error_label = tk.Label(
            rename_frame,
            text="",
            bg=TERMINAL_BG,
            fg="#FF4C4C",  # Rouge pour les erreurs
            font=(FONT_FAMILY, 11),
            pady=5
        )
        error_label.pack(fill="x")

        # Fonction pour valider le renommage
        def process_rename():
            new_name = entry.get().strip()

            # Vérification du nom vide
            if not new_name:
                error_label.config(text="ERREUR: Le nom ne peut pas être vide")
                return

            # Vérification des caractères invalides pour un nom de fichier
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(char in new_name for char in invalid_chars):
                error_label.config(text="ERREUR: Nom contient des caractères invalides")
                return

            # Vérification si le nom existe déjà
            new_filename = f"{new_name}.txt"
            if new_filename in self.notes and new_filename != note:
                error_label.config(text="ERREUR: Ce nom de note existe déjà")
                return

            # Tentative de renommage
            try:
                old_path = os.path.join(NOTES_DIR, note)
                new_path = os.path.join(NOTES_DIR, new_filename)

                # Renommer le fichier sur le disque
                os.rename(old_path, new_path)

                # Mettre à jour la liste des notes
                old_index = self.notes.index(note)
                self.notes[old_index] = new_filename
                # Ne pas trier pour conserver l'ordre par date
                self.current_index = old_index

                # Mettre à jour les favoris si nécessaire
                if note in self.favorites:
                    self.favorites.remove(note)
                    self.favorites.add(new_filename)
                    self.save_favorites()

                # Fermer le dialogue
                close_dialog()

                # Mettre à jour l'interface
                self.load_menu()

            except Exception as e:
                error_label.config(text=f"ERREUR: {str(e)}")

        # Fonction pour fermer le dialogue
        def close_dialog():
            # Restaurer les liaisons clavier
            for key, binding in prev_bindings.items():
                if binding:
                    self.master.bind(key, binding)

            # Détruire le cadre du dialogue
            outer_container.destroy()
            self.rename_dialog_active = False

        # Liaison des touches pour le dialogue
        entry.bind("<Return>", lambda e: process_rename())
        entry.bind("<Escape>", lambda e: close_dialog())

        # Cadre pour les boutons
        btn_frame = tk.Frame(rename_frame, bg=TERMINAL_BG)
        btn_frame.pack(pady=10)

        # Bouton Valider
        tk.Label(
            btn_frame,
            text="[ VALIDER ]",
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            padx=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        # Bouton Annuler
        tk.Label(
            btn_frame,
            text="[ ANNULER ]",
            bg=TERMINAL_BG,
            fg=TERMINAL_FG,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            padx=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        # Liaison des clics sur les boutons
        btn_frame.winfo_children()[0].bind("<Button-1>", lambda e: process_rename())
        btn_frame.winfo_children()[1].bind("<Button-1>", lambda e: close_dialog())

    def delete_note(self, event):
        """Supprime la note sélectionnée"""
        if not self.notes or self.current_index < 0:
            return

        note = self.notes[self.current_index]
        note_name = note.replace(".txt", "")

        # Fonction à exécuter si l'utilisateur confirme la suppression
        def do_delete():
            try:
                os.remove(os.path.join(NOTES_DIR, note))
                self.notes.remove(note)

                # Retirer des favoris si présent
                if note in self.favorites:
                    self.favorites.remove(note)
                    self.save_favorites()

                # Ajuste l'index de sélection
                if not self.notes:
                    self.current_index = -1
                elif self.current_index >= len(self.notes):
                    self.current_index = len(self.notes) - 1

                self.load_menu()
            except Exception as e:
                pass

        # Affiche la popup de confirmation
        self.show_confirmation_popup(
            f"Êtes-vous sûr de vouloir supprimer la note '{note_name}' ?\nCette action est irréversible.",
            do_delete
        )

    def open_note(self, event):
        """Ouvre une note pour édition"""
        if not self.notes or self.current_index < 0:
            return

        self.unbind_menu_keys()
        self.mode = "editor"
        self.bind_editor_keys()

        # Chemin de la note
        self.note_path = os.path.join(NOTES_DIR, self.notes[self.current_index])

        # Masque le panneau de gauche et le séparateur
        self.left_frame.pack_forget()
        self.separator.pack_forget()

        # Réorganiser le panneau droit pour qu'il occupe tout l'espace
        self.right_frame.pack_forget()
        self.right_frame.pack(side="left", fill="both", expand=True, padx=0)

        # Mise à jour de l'en-tête
        note_name = os.path.basename(self.note_path).replace(".txt", "")
        self.header.config(text=f"ÉDITION DE NOTE - {note_name}")
        self.subtitle.config(text="APPUYEZ SUR ÉCHAP POUR REVENIR AU MENU - SAUVEGARDE AUTOMATIQUE")

        # Mise à jour de l'aide
        self.update_status_bar()

        # Activer l'édition pour la zone de texte
        self.right.configure(state="normal")
        self.right.configure(insertwidth=1)  # Restaurer le curseur d'insertion
        self.right.unbind("<Key>")  # Supprimer le gestionnaire qui empêche la saisie

        # Chargement du contenu
        self.right.delete("1.0", "end")
        try:
            with open(self.note_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.right.insert("1.0", content)
        except Exception as e:
            self.right.insert("1.0", f"ERREUR: Impossible de lire la note.\n{str(e)}")

        # Configuration de la sauvegarde auto
        self.right.bind("<KeyRelease>", self.defer_save)
        self.save_job = None

        # Focus sur la zone d'édition
        self.right.focus_set()

        # Mettre à jour les statistiques
        self.update_status_bar()

    def back_to_menu(self, event=None):
        """Retourne au menu principal"""
        self.unbind_editor_keys()

        # Sauvegarde avant de quitter l'éditeur
        if self.save_job:
            self.right.after_cancel(self.save_job)
            self.save_now()
            self.save_job = None
        else:
            self.save_now()

        # Désactive la liaison d'événements de sauvegarde
        self.right.unbind("<KeyRelease>")

        # Reconstruction complète de la disposition
        # Détacher temporairement le panneau droit
        self.right_frame.pack_forget()

        # Réafficher le panneau gauche dans le bon ordre
        self.left_frame.pack(side="left", fill="y", padx=(0, PADDING))
        self.separator.pack(side="left", fill="y")

        # Réafficher le panneau droit
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(PADDING, 0))

        # Revient à l'interface du menu
        self.load_menu()

        # S'assurer que le focus est sur la fenêtre principale pour les raccourcis
        self.master.focus_set()

    def defer_save(self, event=None):
        """Diffère la sauvegarde pour ne pas sauvegarder à chaque frappe"""
        if self.save_job:
            self.right.after_cancel(self.save_job)
        self.save_job = self.right.after(500, self.save_now)  # 500ms après la dernière frappe

        # Mettre à jour les statistiques
        self.update_status_bar()

    def save_now(self):
        """Enregistre immédiatement le contenu de la note"""
        try:
            with open(self.note_path, "w", encoding="utf-8") as f:
                f.write(self.right.get("1.0", tk.END))
        except Exception as e:
            pass
        finally:
            self.save_job = None

    def quit_app(self, event=None):
        """Quitte l'application proprement"""
        # Sauvegarde si en mode édition
        if self.mode == "editor" and self.save_job:
            self.right.after_cancel(self.save_job)
            self.save_now()

        # Sauvegarder les favoris
        self.save_favorites()

        self.master.destroy()


# Lancement de l'application
if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg=TERMINAL_BG)  # Assure que le fond est correct même pendant le chargement
    app = TerminalNotesApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)  # Gestion propre de la fermeture
    root.mainloop()
