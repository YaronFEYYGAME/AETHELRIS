import pygame
import math
from characters import CHARACTER_DEFS
from resource_manager import ResourceManager


ITEM_LORE = {
    'redgem': (
        "Pierre philosophale",
        "L'ultime rempart contre le néant. Se consume intégralement pour vous arracher aux griffes de la mort une dernière fois."
    ),
    'bluegem': (
        "Anneau des cieux",
        "Votre existence devient un mirage céleste. Les lames et les sorts vous traversent sans jamais troubler votre grâce divine."
    ),
    'kitsune_mask': (
        "Masque du Kitsune",
        "Imprégné de la ruse des anciens esprits, ce masque vous murmure où frapper pour achever ceux qui chancellent déjà."
    ),
    'cursed_brand': (
        "Marque du sacrifice",
        "Un pacte gravé dans la chair : la vitalité de l'autre devient la lame qui frappe l'ennemi."
    ),
    'mirror': (
        "Miroir de Thémis",
        "Un éclat d'ordre divin qui renvoie la violence à sa source avec une impartialité absolue."
    ),
    'boots': (
        "Bottes du rayon cosmique",
        "Forgées dans l'éclat d'une étoile mourante, ces bottes permettent à leur porteur de glisser entre les dimensions le temps d'un battement de cœur."
    ),
    'travelers_cap': (
        "Casquette du voyageur",
        "Yare Yare Daze..."
    ),
    'zhonya': (
        "Sablier de Zhonya",
        "Le sable se fige, le destin de votre proie aussi. Figez l'instant présent dans une inertie dorée pour mieux briser l'avenir."
    ),
    'rabadon': (
        "Coiffe de Rabadon",
        "Une couronne de soie imprégnée de siècles de savoir interdit. Insufflez une puissance démesurée à vos armes par la seule force de l'esprit."
    ),
}


class UI:
    def __init__(self, screen):
        self.screen = screen
        self.font = ResourceManager.get_font(30, None)

        # Icônes par défaut (soldier)
        self._icon_cache = {}
        self._load_default_icons()

    def _load_default_icons(self):
        """Charge les icônes par défaut du soldier."""
        try:
            self.sword_img = ResourceManager.get_image("assets/images/sword_icon.png")
            self.sword_img = pygame.transform.scale(self.sword_img, (64, 64))

            self.bow_img = ResourceManager.get_image("assets/images/arc_icon.png")
            self.bow_img = pygame.transform.scale(self.bow_img, (64, 64))

            self.pickaxe_img = ResourceManager.get_image("assets/images/pickaxe_icon.png")
            self.pickaxe_img = pygame.transform.scale(self.pickaxe_img, (64, 64))

            self.boots_img = ResourceManager.get_image("assets/images/hermesboots.png")
            self.boots_img = pygame.transform.scale(self.boots_img, (64, 64))

            self.redgem_img = ResourceManager.get_image("assets/images/redgem.png")
            self.redgem_img = pygame.transform.scale(self.redgem_img, (64, 64))

            self.bluegem_img = ResourceManager.get_image("assets/images/bluegem.png")
            self.bluegem_img = pygame.transform.scale(self.bluegem_img, (64, 64))

            self.mirror_img = ResourceManager.get_image("assets/images/mirror.png")
            self.mirror_img = pygame.transform.scale(self.mirror_img, (64, 64))

            _km_raw = ResourceManager.get_image("assets/images/kitsune_mask.png")
            _km_raw = pygame.transform.scale(_km_raw, (48, 48))
            self.kitsune_mask_img = pygame.Surface((64, 64), pygame.SRCALPHA)
            self.kitsune_mask_img.blit(_km_raw, (8, 8))  # centré dans le slot 64x64

            self.cursed_brand_img = ResourceManager.get_image("assets/images/cursed_brand.png")
            self.cursed_brand_img = pygame.transform.scale(self.cursed_brand_img, (64, 64))

            self.travelers_cap_img = ResourceManager.get_image("assets/images/travelers_cap.png")
            self.travelers_cap_img = pygame.transform.scale(self.travelers_cap_img, (64, 64))

            self.zhonya_img = ResourceManager.get_image("assets/images/zhonya.png")
            self.zhonya_img = pygame.transform.scale(self.zhonya_img, (52, 52))

            self.rabadon_img = ResourceManager.get_image("assets/images/rabadon.png")
            self.rabadon_img = pygame.transform.scale(self.rabadon_img, (52, 52))
        except FileNotFoundError:
            self.sword_img = pygame.Surface((64, 64)); self.sword_img.fill((200, 200, 200))
            self.bow_img = pygame.Surface((64, 64)); self.bow_img.fill((150, 100, 50))
            self.pickaxe_img = pygame.Surface((64, 64)); self.pickaxe_img.fill((100, 100, 100))
            self.boots_img = pygame.Surface((64, 64)); self.boots_img.fill((100, 150, 200))
            self.redgem_img = pygame.Surface((64, 64)); self.redgem_img.fill((200, 50, 50))
            self.bluegem_img = pygame.Surface((64, 64)); self.bluegem_img.fill((50, 50, 200))
            self.mirror_img = pygame.Surface((64, 64)); self.mirror_img.fill((180, 180, 220))
            self.kitsune_mask_img = pygame.Surface((64, 64)); self.kitsune_mask_img.fill((220, 150, 50))
            self.cursed_brand_img = pygame.Surface((64, 64)); self.cursed_brand_img.fill((150, 50, 150))
            self.travelers_cap_img = pygame.Surface((64, 64)); self.travelers_cap_img.fill((100, 50, 150))
            self.zhonya_img = pygame.Surface((52, 52)); self.zhonya_img.fill((200, 180, 50))
            self.rabadon_img = pygame.Surface((52, 52)); self.rabadon_img.fill((80, 0, 160))

    def load_character_icons(self, char_type):
        """Charge les icônes spécifiques à un personnage."""
        if char_type in self._icon_cache:
            return self._icon_cache[char_type]

        char_def = CHARACTER_DEFS.get(char_type, CHARACTER_DEFS['soldier'])
        icons = {}
        for slot, path in char_def.get('icons', {}).items():
            try:
                img = ResourceManager.get_image(path)
                img = pygame.transform.scale(img, (64, 64))
                icons[slot] = img
            except FileNotFoundError:
                surf = pygame.Surface((64, 64)); surf.fill((100, 100, 100))
                icons[slot] = surf
        self._icon_cache[char_type] = icons
        return icons

    def draw_health_bar(self, current_health, max_health):
        bar_width = 200
        bar_height = 22
        x, y = 20, 18

        ratio = current_health / max_health if max_health > 0 else 0

        # Fond sombre semi-transparent
        bg = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 20, 30, 220), (0, 0, bar_width, bar_height), border_radius=4)
        self.screen.blit(bg, (x, y))

        # Barre de remplissage avec dégradé
        if ratio > 0:
            fill_w = max(4, int(bar_width * ratio))
            if ratio >= 0.6:
                c1, c2 = (40, 180, 60), (70, 220, 90)
            elif ratio >= 0.3:
                c1, c2 = (200, 180, 40), (220, 200, 60)
            else:
                c1, c2 = (180, 40, 40), (220, 70, 50)
            fill = pygame.Surface((fill_w, bar_height), pygame.SRCALPHA)
            pygame.draw.rect(fill, (*c1, 230), (0, 0, fill_w, bar_height), border_radius=4)
            # Reflet en haut
            highlight = pygame.Surface((fill_w, bar_height // 3), pygame.SRCALPHA)
            pygame.draw.rect(highlight, (*c2, 80), (0, 0, fill_w, bar_height // 3), border_radius=3)
            fill.blit(highlight, (0, 2))
            self.screen.blit(fill, (x, y))

        # Double bordure style inventaire
        pygame.draw.rect(self.screen, (180, 150, 100), (x, y, bar_width, bar_height), 2, border_radius=4)
        pygame.draw.rect(self.screen, (100, 80, 50, 120), (x + 1, y + 1, bar_width - 2, bar_height - 2), 1, border_radius=3)

        # Texte PV
        if not hasattr(self, '_hp_font'):
            self._hp_font = ResourceManager.get_font(18, None)
        hp_text = f"{int(current_health)}/{int(max_health)}"
        shadow = self._hp_font.render(hp_text, True, (0, 0, 0))
        txt = self._hp_font.render(hp_text, True, (255, 240, 200))
        tx = x + bar_width // 2 - txt.get_width() // 2
        ty = y + bar_height // 2 - txt.get_height() // 2
        self.screen.blit(shadow, (tx + 1, ty + 1))
        self.screen.blit(txt, (tx, ty))

    def _get_item_icon(self, item_type):
        """Retourne l'icône 64x64 pour un type d'item."""
        icon_map = {
            'boots': self.boots_img, 'bluegem': self.bluegem_img,
            'cursed_brand': self.cursed_brand_img, 'pickaxe': self.pickaxe_img,
            'redgem': self.redgem_img, 'mirror': self.mirror_img,
            'kitsune_mask': self.kitsune_mask_img,
            'travelers_cap': self.travelers_cap_img,
            'zhonya': self.zhonya_img,
            'rabadon': self.rabadon_img,
        }
        return icon_map.get(item_type)

    def draw_character_hud(self, char_type, current_weapon, skill_cooldowns=None,
                           arrows=0, inventory_items=None,
                           dash_cr=1.0, blue_gem_cr=1.0, cursed_brand_cr=1.0,
                           arrow_regen_cr=1.0, travelers_cap_cr=1.0,
                           zhonya_cr=1.0, item_start_key=2):
        """Dessine le HUD : skill E → skill 1 → items actifs → items passifs."""
        icons = self.load_character_icons(char_type)
        char_def = CHARACTER_DEFS.get(char_type, CHARACTER_DEFS['soldier'])
        abilities = char_def.get('abilities', {})
        bindings = char_def.get('bindings', {})
        if inventory_items is None:
            inventory_items = []

        x_offset = 20
        y = 50
        slot_size = 64
        gap = 8

        # --- Slot E (compétence E) ---
        e_weapon = bindings.get('e')
        e_cr = 1.0
        e_show_cd = False
        if e_weapon:
            if e_weapon in abilities:
                e_cr = skill_cooldowns.get(e_weapon, 1.0) if skill_cooldowns else 1.0
                e_show_cd = True
            elif e_weapon == 'ranged' and arrows <= 0:
                e_cr = arrow_regen_cr
                e_show_cd = True
        self._draw_slot(x_offset, y, slot_size, icons.get('e'),
                        is_active=False, cooldown_ratio=e_cr,
                        show_cooldown=e_show_cd, label='E')
        # Compteur de flèches pour le slot E (soldier/archer)
        if e_weapon == 'ranged':
            self._draw_counter(x_offset, y, slot_size, arrows)
        x_offset += slot_size + gap

        # --- Slot 1 (compétence touche 1, si le personnage en a une) ---
        skill_1_weapon = bindings.get('1')
        if skill_1_weapon:
            s1_cr = 1.0
            s1_show_cd = False
            if skill_1_weapon in abilities:
                s1_cr = skill_cooldowns.get(skill_1_weapon, 1.0) if skill_cooldowns else 1.0
                s1_show_cd = True
            elif skill_1_weapon == 'ranged' and arrows <= 0:
                s1_cr = arrow_regen_cr
                s1_show_cd = True
            self._draw_slot(x_offset, y, slot_size, icons.get('1'),
                            is_active=False, cooldown_ratio=s1_cr,
                            show_cooldown=s1_show_cd, label='1')
            if skill_1_weapon == 'ranged':
                self._draw_counter(x_offset, y, slot_size, arrows)
            x_offset += slot_size + gap

        # --- Slot 2 (compétence touche 2, swordsman uniquement) ---
        skill_2_weapon = bindings.get('2')
        if skill_2_weapon:
            s2_cr = 1.0
            s2_show_cd = False
            if skill_2_weapon in abilities:
                s2_cr = skill_cooldowns.get(skill_2_weapon, 1.0) if skill_cooldowns else 1.0
                s2_show_cd = True
            self._draw_slot(x_offset, y, slot_size, icons.get('2'),
                            is_active=False, cooldown_ratio=s2_cr,
                            show_cooldown=s2_show_cd, label='2')
            x_offset += slot_size + gap

        # --- Items d'inventaire (ordre de la liste) ---
        from player import ACTIVE_ITEMS
        key_counter = item_start_key
        # Skip key 1 si déjà utilisé par skill_1
        if skill_1_weapon and key_counter == 1:
            key_counter = 2

        cooldown_map = {
            'boots': dash_cr, 'bluegem': blue_gem_cr,
            'cursed_brand': cursed_brand_cr,
            'travelers_cap': travelers_cap_cr,
            'zhonya': zhonya_cr,
        }

        for item_type in inventory_items:
            icon = self._get_item_icon(item_type)
            if item_type in ACTIVE_ITEMS:
                cr = cooldown_map.get(item_type, 1.0)
                self._draw_slot(x_offset, y, slot_size, icon,
                                is_active=False, cooldown_ratio=cr,
                                show_cooldown=True, label=str(key_counter))
                key_counter += 1
            else:
                self._draw_slot(x_offset, y, slot_size, icon,
                                is_active=False, cooldown_ratio=1.0,
                                show_cooldown=False)
            x_offset += slot_size + gap

    def draw_inventory_screen(self, inventory_items, cursor_idx, grabbed,
                              item_start_key=2, skill_1_exists=False):
        """Dessine l'écran d'inventaire (overlay, le jeu continue derrière)."""
        from player import ACTIVE_ITEMS
        sw = self.screen.get_width()
        sh = self.screen.get_height()

        # Overlay semi-transparent
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # Panneau central
        panel_w = 500
        panel_h = 340
        px = (sw - panel_w) // 2
        py = (sh - panel_h) // 2

        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_bg.fill((20, 20, 30, 220))
        self.screen.blit(panel_bg, (px, py))
        pygame.draw.rect(self.screen, (180, 150, 100), (px, py, panel_w, panel_h), 2, border_radius=6)

        # Titre
        if not hasattr(self, '_inv_title_font'):
            self._inv_title_font = ResourceManager.get_font(28, None)
        title = self._inv_title_font.render("INVENTAIRE", True, (255, 255, 240))
        self.screen.blit(title, (px + panel_w // 2 - title.get_width() // 2, py + 15))

        # Slots
        slot_size = 72
        gap = 12
        key_counter = item_start_key
        if skill_1_exists and key_counter == 1:
            key_counter = 2
        n = max(len(inventory_items), 1)
        total_slots_w = n * slot_size + (n - 1) * gap
        slot_x_start = px + (panel_w - total_slots_w) // 2
        slot_y = py + (panel_h - slot_size) // 2 - 10

        for i, item_type in enumerate(inventory_items):
            sx = slot_x_start + i * (slot_size + gap)
            icon = self._get_item_icon(item_type)

            # Surbrillance du curseur
            is_cursor = (i == cursor_idx)
            is_grabbed_slot = (is_cursor and grabbed)

            # Fond du slot
            bg = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA)
            if is_grabbed_slot:
                bg_color = (80, 60, 30, 230)
            elif is_cursor:
                bg_color = (60, 60, 80, 220)
            else:
                bg_color = (40, 40, 40, 180)
            pygame.draw.rect(bg, bg_color, (0, 0, slot_size, slot_size), border_radius=5)
            self.screen.blit(bg, (sx, slot_y))

            # Bordure
            if is_grabbed_slot:
                pygame.draw.rect(self.screen, (255, 200, 50), (sx, slot_y, slot_size, slot_size), 3, border_radius=5)
            elif is_cursor:
                pygame.draw.rect(self.screen, (100, 200, 255), (sx, slot_y, slot_size, slot_size), 2, border_radius=5)
            else:
                pygame.draw.rect(self.screen, (150, 150, 150), (sx, slot_y, slot_size, slot_size), 1, border_radius=5)

            # Icône
            if icon:
                scaled = pygame.transform.scale(icon, (slot_size - 8, slot_size - 8))
                self.screen.blit(scaled, (sx + 4, slot_y + 4))

            # Label de touche
            if item_type in ACTIVE_ITEMS:
                lbl = self._inv_title_font.render(str(key_counter), True, (200, 200, 200))
                self.screen.blit(lbl, (sx + 4, slot_y + 2))
                key_counter += 1

        # Message si inventaire vide
        if not inventory_items:
            empty_txt = self._inv_title_font.render("Inventaire vide", True, (150, 150, 150))
            self.screen.blit(empty_txt, (px + panel_w // 2 - empty_txt.get_width() // 2, slot_y + 25))

        # Nom et description de l'item sous le curseur
        if inventory_items and 0 <= cursor_idx < len(inventory_items):
            selected_type = inventory_items[cursor_idx]
            lore = ITEM_LORE.get(selected_type)
            if lore:
                item_name, item_desc = lore
                if not hasattr(self, '_inv_name_font'):
                    self._inv_name_font = ResourceManager.get_font(24, None)
                    self._inv_desc_font = ResourceManager.get_font(20, None)

                name_surf = self._inv_name_font.render(item_name, True, (255, 220, 150))
                name_y = slot_y + slot_size + 12
                self.screen.blit(name_surf, (px + panel_w // 2 - name_surf.get_width() // 2, name_y))

                # Description en italique, découpée en lignes
                desc_y = name_y + name_surf.get_height() + 4
                max_text_w = panel_w - 30
                words = item_desc.split()
                lines = []
                current_line = ""
                for word in words:
                    test = current_line + (" " if current_line else "") + word
                    if self._inv_desc_font.size(test)[0] <= max_text_w:
                        current_line = test
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)

                for line in lines:
                    line_surf = self._inv_desc_font.render(line, True, (180, 180, 190))
                    self.screen.blit(line_surf, (px + panel_w // 2 - line_surf.get_width() // 2, desc_y))
                    desc_y += line_surf.get_height() + 2

        # Instructions en bas
        if not hasattr(self, '_inv_help_font'):
            self._inv_help_font = ResourceManager.get_font(22, None)
        help_text = "[E] Saisir   [Q/D] Deplacer   [A] Jeter   [I/Echap] Fermer"
        help_surf = self._inv_help_font.render(help_text, True, (180, 180, 180))
        self.screen.blit(help_surf, (px + panel_w // 2 - help_surf.get_width() // 2,
                                     py + panel_h - 30))

    def _draw_slot(self, x, y, size, icon, is_active=False, cooldown_ratio=1.0,
                   show_cooldown=False, label=None):
        """Dessine un slot d'inventaire avec cooldown optionnel (cercle horaire)."""
        # Fond
        bg_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        bg_color = (50, 50, 60, 200) if is_active else (40, 40, 40, 180)
        pygame.draw.rect(bg_surface, bg_color, (0, 0, size, size), border_radius=5)
        self.screen.blit(bg_surface, (x, y))

        # Bordure
        border_color = (200, 200, 100) if is_active else (200, 200, 200)
        pygame.draw.rect(self.screen, border_color, (x, y, size, size), 2, border_radius=5)

        if icon is None:
            return

        # Centrer l'icône dans le slot
        ix = x + (size - icon.get_width()) // 2
        iy = y + (size - icon.get_height()) // 2

        if show_cooldown and cooldown_ratio < 1.0:
            # Icône assombrie
            dark_img = icon.copy()
            dark_img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(dark_img, (ix, iy))

            # Cercle de progression horaire par-dessus
            if cooldown_ratio > 0.0:
                self._draw_cooldown_arc(x, y, size, cooldown_ratio)
        else:
            self.screen.blit(icon, (ix, iy))

        # Label de touche
        if label:
            lbl_font = ResourceManager.get_font(18, None)
            lbl_surf = lbl_font.render(label, True, (200, 200, 200))
            self.screen.blit(lbl_surf, (x + 3, y + 2))

    def _draw_cooldown_arc(self, x, y, size, ratio):
        """Dessine un arc de cercle horaire semi-transparent indiquant la progression du cooldown."""
        cx = x + size // 2
        cy = y + size // 2
        radius = size // 2 - 4

        # Angle de départ : midi (−90°), sens horaire
        start_angle_deg = 90  # pygame mesure en sens trigo, 90° = midi
        sweep_deg = ratio * 360

        # Dessiner l'arc avec des segments de polygone pour un rendu propre
        overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        local_cx = size // 2
        local_cy = size // 2

        num_segments = max(8, int(sweep_deg / 4))
        points = [(local_cx, local_cy)]

        for i in range(num_segments + 1):
            angle_deg = start_angle_deg - (sweep_deg * i / num_segments)
            angle_rad = math.radians(angle_deg)
            px = local_cx + radius * math.cos(angle_rad)
            py = local_cy - radius * math.sin(angle_rad)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(overlay, (255, 255, 200, 80), points)
            # Contour de l'arc
            arc_points = points[1:]  # sans le centre
            if len(arc_points) >= 2:
                pygame.draw.lines(overlay, (255, 255, 200, 180), False, arc_points, 2)

        self.screen.blit(overlay, (x, y))

    def _draw_counter(self, x, y, size, count):
        """Dessine un compteur (flèches) en bas à droite du slot."""
        text_surf = self.font.render(str(count), True, (255, 255, 255))
        text_shadow = self.font.render(str(count), True, (0, 0, 0))
        pos_x = x + size - text_surf.get_width() - 5
        pos_y = y + size - text_surf.get_height() - 2
        self.screen.blit(text_shadow, (pos_x + 1, pos_y + 1))
        self.screen.blit(text_surf, (pos_x, pos_y))

    # --- Anciennes fonctions gardées pour compatibilité solo ---

    def draw_weapon_icon(self, current_weapon):
        x, y = 20, 50
        bg_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (40, 40, 40, 180), (0, 0, 64, 64), border_radius=5)
        self.screen.blit(bg_surface, (x, y))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, 64, 64), 2, border_radius=5)

        if current_weapon == 'melee': self.screen.blit(self.sword_img, (x, y))
        elif current_weapon == 'ranged': self.screen.blit(self.bow_img, (x, y))

    def draw_pickaxe_icon(self, has_pickaxe):
        if not has_pickaxe: return
        x, y = 20, 120
        bg_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (40, 40, 40, 180), (0, 0, 64, 64), border_radius=5)
        self.screen.blit(bg_surface, (x, y))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, 64, 64), 2, border_radius=5)
        self.screen.blit(self.pickaxe_img, (x, y))

    def draw_ammo_count(self, current_weapon, arrows):
        if current_weapon != 'ranged': return
        text_surf = self.font.render(str(arrows), True, (255, 255, 255))
        text_shadow = self.font.render(str(arrows), True, (0, 0, 0))
        pos_x = 20 + 64 - text_surf.get_width() - 5
        pos_y = 50 + 64 - text_surf.get_height() - 2
        self.screen.blit(text_shadow, (pos_x + 1, pos_y + 1))
        self.screen.blit(text_surf, (pos_x, pos_y))

    def draw_boots_icon(self, has_boots, cooldown_ratio):
        if not has_boots: return
        self._draw_slot(95, 50, 64, self.boots_img, cooldown_ratio=cooldown_ratio,
                        show_cooldown=True)

    def draw_boss_dialogue(self, text, boss_name=None):
        """Boîte de dialogue RPG en bas de l'écran pour les dialogues de boss.
        Word wrap automatique si le texte est trop long."""
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        box_w = min(700, sw - 60)
        padding = 14
        max_text_w = box_w - padding * 2

        if not hasattr(self, '_boss_dialogue_font'):
            self._boss_dialogue_font = ResourceManager.get_font(26, "garamond, times new roman, serif")
        if not hasattr(self, '_boss_name_font'):
            self._boss_name_font = ResourceManager.get_font(22, "garamond, times new roman, serif")

        # Calculer la hauteur du nom
        name_h = 0
        if boss_name:
            name_surf = self._boss_name_font.render(boss_name, True, (255, 200, 100))
            name_h = name_surf.get_height() + 4

        # Word wrap : découper le texte en lignes
        words = text.split(' ')
        lines = []
        current_line = ''
        for word in words:
            test = (current_line + ' ' + word).strip()
            if self._boss_dialogue_font.size(test)[0] <= max_text_w:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        line_h = self._boss_dialogue_font.get_linesize()
        text_block_h = line_h * len(lines)

        # Hauteur de la boîte adaptée au contenu
        box_h = name_h + text_block_h + padding * 2 + 4
        box_h = max(box_h, 70)

        x = (sw - box_w) // 2
        y = sh - box_h - 30

        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((10, 10, 20, 210))
        self.screen.blit(bg, (x, y))

        pygame.draw.rect(self.screen, (180, 150, 100), (x, y, box_w, box_h), 2, border_radius=4)
        pygame.draw.rect(self.screen, (120, 100, 70), (x + 2, y + 2, box_w - 4, box_h - 4), 1, border_radius=3)

        # Nom du boss
        if boss_name:
            self.screen.blit(name_surf, (x + padding, y + padding))

        # Texte (centré horizontalement, sous le nom)
        text_start_y = y + padding + name_h
        for i, line in enumerate(lines):
            line_surf = self._boss_dialogue_font.render(line, True, (255, 255, 240))
            line_rect = line_surf.get_rect(centerx=x + box_w // 2, y=text_start_y + i * line_h)
            self.screen.blit(line_surf, line_rect)

    def draw_dialogue(self, text):
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        box_width = 350
        box_height = 50
        x = (screen_width - box_width) // 2
        y = screen_height - 100

        # Fond style inventaire/pause
        bg_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (20, 20, 30, 220), (0, 0, box_width, box_height), border_radius=6)
        self.screen.blit(bg_surface, (x, y))
        # Double bordure dorée
        pygame.draw.rect(self.screen, (180, 150, 100), (x, y, box_width, box_height), 2, border_radius=6)
        pygame.draw.rect(self.screen, (100, 80, 50), (x + 2, y + 2, box_width - 4, box_height - 4), 1, border_radius=5)

        text_surf = self.font.render(text, True, (255, 220, 150))
        text_rect = text_surf.get_rect(center=(x + box_width // 2, y + box_height // 2))
        self.screen.blit(text_surf, text_rect)

    def draw_boss_health_bar(self, current_health, max_health, boss_name="Gardien des profondeurs"):
        bar_width = 600
        bar_height = 32
        screen_width = self.screen.get_width()
        x = (screen_width - bar_width) // 2
        y = 14

        ratio = current_health / max_health if max_health > 0 else 0

        # Nom du boss au-dessus de la barre (style doré)
        if not hasattr(self, '_boss_bar_name_font'):
            self._boss_bar_name_font = ResourceManager.get_font(24, "garamond, times new roman, serif")
        name_surf = self._boss_bar_name_font.render(boss_name, True, (255, 220, 150))
        name_shadow = self._boss_bar_name_font.render(boss_name, True, (0, 0, 0))
        nx = screen_width // 2 - name_surf.get_width() // 2
        ny = y - name_surf.get_height() - 2
        if ny < 4:
            ny = 4
            y = ny + name_surf.get_height() + 4
        self.screen.blit(name_shadow, (nx + 1, ny + 1))
        self.screen.blit(name_surf, (nx, ny))

        # Fond sombre semi-transparent
        bg = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 20, 30, 220), (0, 0, bar_width, bar_height), border_radius=5)
        self.screen.blit(bg, (x, y))

        # Barre de remplissage avec dégradé
        if ratio > 0:
            fill_w = max(6, int(bar_width * ratio))
            if ratio >= 0.6:
                c1, c2 = (40, 180, 60), (70, 220, 90)
            elif ratio >= 0.3:
                c1, c2 = (200, 180, 40), (220, 200, 60)
            else:
                c1, c2 = (180, 40, 40), (220, 70, 50)
            fill = pygame.Surface((fill_w, bar_height), pygame.SRCALPHA)
            pygame.draw.rect(fill, (*c1, 230), (0, 0, fill_w, bar_height), border_radius=5)
            # Reflet lumineux en haut
            highlight = pygame.Surface((fill_w, bar_height // 3), pygame.SRCALPHA)
            pygame.draw.rect(highlight, (*c2, 80), (0, 0, fill_w, bar_height // 3), border_radius=4)
            fill.blit(highlight, (0, 2))
            self.screen.blit(fill, (x, y))

        # Double bordure style inventaire
        pygame.draw.rect(self.screen, (180, 150, 100), (x, y, bar_width, bar_height), 2, border_radius=5)
        pygame.draw.rect(self.screen, (100, 80, 50, 120), (x + 1, y + 1, bar_width - 2, bar_height - 2), 1, border_radius=4)

        # Texte PV centré dans la barre
        if not hasattr(self, '_boss_hp_font'):
            self._boss_hp_font = ResourceManager.get_font(22, None)
        hp_text = f"{int(current_health)} / {int(max_health)}"
        shadow = self._boss_hp_font.render(hp_text, True, (0, 0, 0))
        txt = self._boss_hp_font.render(hp_text, True, (255, 240, 200))
        tx = screen_width // 2 - txt.get_width() // 2
        ty = y + bar_height // 2 - txt.get_height() // 2
        self.screen.blit(shadow, (tx + 1, ty + 1))
        self.screen.blit(txt, (tx, ty))

    def _draw_styled_button(self, rect, text, font=None):
        """Bouton style inventaire : fond semi-transparent, bordure dorée au survol."""
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        if font is None:
            font = ResourceManager.get_font(30, None)

        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        if hovered:
            pygame.draw.rect(bg, (60, 55, 45, 230), (0, 0, rect.width, rect.height), border_radius=5)
        else:
            pygame.draw.rect(bg, (30, 28, 35, 200), (0, 0, rect.width, rect.height), border_radius=5)
        self.screen.blit(bg, rect.topleft)

        border_color = (200, 170, 100) if hovered else (120, 110, 90)
        pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=5)

        txt_color = (255, 240, 200) if hovered else (220, 215, 200)
        txt = font.render(text, True, txt_color)
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def draw_pause_menu(self, music_vol, sfx_vol, action_text=None):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        menu_w, menu_h = 450, 300
        x = (self.screen.get_width() - menu_w) // 2
        y = (self.screen.get_height() - menu_h) // 2

        # Fond semi-transparent style inventaire
        panel = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 20, 30, 220), (0, 0, menu_w, menu_h), border_radius=6)
        self.screen.blit(panel, (x, y))
        pygame.draw.rect(self.screen, (180, 150, 100), (x, y, menu_w, menu_h), 2, border_radius=6)
        pygame.draw.rect(self.screen, (100, 80, 50), (x + 2, y + 2, menu_w - 4, menu_h - 4), 1, border_radius=5)

        # Titre
        title_font = ResourceManager.get_font(36, None)
        title_text = "PAUSE" if action_text != "Retour" else "PARAMÈTRES"
        title = title_font.render(title_text, True, (255, 220, 150))
        self.screen.blit(title, (x + menu_w // 2 - title.get_width() // 2, y + 18))

        # Ligne décorative sous le titre
        line_y = y + 52
        pygame.draw.line(self.screen, (180, 150, 100), (x + 30, line_y), (x + menu_w - 30, line_y), 1)

        # Labels volume
        label_font = ResourceManager.get_font(28, None)
        music_txt = label_font.render(f"Musique : {int(music_vol * 100)}%", True, (220, 215, 200))
        self.screen.blit(music_txt, (x + 30, y + 75))

        sfx_txt = label_font.render(f"Effets : {int(sfx_vol * 100)}%", True, (220, 215, 200))
        self.screen.blit(sfx_txt, (x + 30, y + 135))

        # Boutons +/- volume (style inventaire)
        btn_font = ResourceManager.get_font(30, None)
        btn_mus_min = pygame.Rect(x + 300, y + 68, 40, 40)
        btn_mus_pl = pygame.Rect(x + 360, y + 68, 40, 40)
        self._draw_styled_button(btn_mus_min, "-", btn_font)
        self._draw_styled_button(btn_mus_pl, "+", btn_font)

        btn_sfx_min = pygame.Rect(x + 300, y + 128, 40, 40)
        btn_sfx_pl = pygame.Rect(x + 360, y + 128, 40, 40)
        self._draw_styled_button(btn_sfx_min, "-", btn_font)
        self._draw_styled_button(btn_sfx_pl, "+", btn_font)

        rects = {
            "mus_min": btn_mus_min, "mus_pl": btn_mus_pl,
            "sfx_min": btn_sfx_min, "sfx_pl": btn_sfx_pl
        }

        if action_text == "Retour":
            btn_quit = pygame.Rect(x + menu_w // 2 - 75, y + 230, 150, 50)
            self._draw_styled_button(btn_quit, action_text, btn_font)
            rects["quit"] = btn_quit
        else:
            btn_resume = pygame.Rect(x + menu_w // 2 - 160, y + 230, 150, 50)
            btn_quit = pygame.Rect(x + menu_w // 2 + 10, y + 230, 150, 50)
            self._draw_styled_button(btn_resume, "Reprendre", btn_font)
            self._draw_styled_button(btn_quit, "Quitter", btn_font)
            rects["resume"] = btn_resume
            rects["quit"] = btn_quit

        return rects

    # --- Interface d'obtention d'item (coffre) ---

    def draw_chest_item_ui(self, item_type, alpha):
        """Dessine l'interface d'obtention d'item de coffre avec le niveau d'opacité donné (0-255)."""
        if alpha <= 0:
            return
        sw = self.screen.get_width()
        sh = self.screen.get_height()

        # Panneau 3/4 de l'écran
        panel_w = int(sw * 0.75)
        panel_h = int(sh * 0.6)
        px = (sw - panel_w) // 2
        py = (sh - panel_h) // 2

        # Overlay sombre
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(130 * alpha / 255)))
        self.screen.blit(overlay, (0, 0))

        # Panneau principal
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 20, 30, int(220 * alpha / 255)),
                         (0, 0, panel_w, panel_h), border_radius=8)
        self.screen.blit(panel, (px, py))

        # Bordures dorées
        border_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (180, 150, 100, alpha),
                         (0, 0, panel_w, panel_h), 2, border_radius=8)
        pygame.draw.rect(border_surf, (100, 80, 50, alpha),
                         (2, 2, panel_w - 4, panel_h - 4), 1, border_radius=7)
        self.screen.blit(border_surf, (px, py))

        # --- Titre "Nouvel objet" ---
        if not hasattr(self, '_chest_title_font'):
            self._chest_title_font = ResourceManager.get_font(56, "garamond, times new roman, serif")
        title = self._chest_title_font.render("Nouvel objet", True, (255, 220, 150))
        title.set_alpha(alpha)
        title_shadow = self._chest_title_font.render("Nouvel objet", True, (0, 0, 0))
        title_shadow.set_alpha(alpha)
        tx = px + panel_w // 2 - title.get_width() // 2
        ty = py + 22
        self.screen.blit(title_shadow, (tx + 2, ty + 2))
        self.screen.blit(title, (tx, ty))

        # Ligne décorative
        line_y = ty + title.get_height() + 12
        line_surf = pygame.Surface((panel_w - 60, 1), pygame.SRCALPHA)
        line_surf.fill((180, 150, 100, alpha))
        self.screen.blit(line_surf, (px + 30, line_y))

        # --- Zone contenu : 2 colonnes ---
        content_y = line_y + 18
        content_h = panel_h - (content_y - py) - 50  # marge bas pour hint
        left_col_w = int(panel_w * 0.33)
        right_col_x = px + left_col_w + 10

        # --- Colonne gauche : icône en grand dans un cadre ---
        icon_size = min(left_col_w - 50, content_h - 20)
        icon_size = max(icon_size, 80)
        icon = self._get_item_icon(item_type)
        if icon:
            big_icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
            big_icon.set_alpha(alpha)
            icon_x = px + (left_col_w - icon_size) // 2
            icon_y = content_y + (content_h - icon_size) // 2
            # Cadre
            pad = 10
            frame_surf = pygame.Surface((icon_size + pad * 2, icon_size + pad * 2), pygame.SRCALPHA)
            pygame.draw.rect(frame_surf, (35, 35, 45, int(200 * alpha / 255)),
                             (0, 0, frame_surf.get_width(), frame_surf.get_height()), border_radius=6)
            pygame.draw.rect(frame_surf, (180, 150, 100, alpha),
                             (0, 0, frame_surf.get_width(), frame_surf.get_height()), 2, border_radius=6)
            pygame.draw.rect(frame_surf, (100, 80, 50, alpha),
                             (2, 2, frame_surf.get_width() - 4, frame_surf.get_height() - 4), 1, border_radius=5)
            self.screen.blit(frame_surf, (icon_x - pad, icon_y - pad))
            self.screen.blit(big_icon, (icon_x, icon_y))

        # --- Colonne droite : nom + description ---
        info = ITEM_LORE.get(item_type, (item_type, ""))
        item_name, item_desc = info

        if not hasattr(self, '_chest_name_font'):
            self._chest_name_font = ResourceManager.get_font(42, "garamond, times new roman, serif")
            self._chest_desc_font = ResourceManager.get_font(30, None)
            self._chest_hint_font = ResourceManager.get_font(22, None)

        text_x = right_col_x + 15
        text_max_w = (px + panel_w - 30) - text_x

        # Nom de l'item
        name_y = content_y + 15
        name_surf = self._chest_name_font.render(item_name, True, (255, 220, 150))
        name_surf.set_alpha(alpha)
        name_shadow = self._chest_name_font.render(item_name, True, (0, 0, 0))
        name_shadow.set_alpha(alpha)
        self.screen.blit(name_shadow, (text_x + 2, name_y + 2))
        self.screen.blit(name_surf, (text_x, name_y))

        # Ligne séparatrice sous le nom
        sep_y = name_y + name_surf.get_height() + 10
        sep_surf = pygame.Surface((text_max_w, 1), pygame.SRCALPHA)
        sep_surf.fill((100, 80, 50, alpha))
        self.screen.blit(sep_surf, (text_x, sep_y))

        # Description (word-wrap)
        desc_y = sep_y + 14
        words = item_desc.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test = current_line + (" " if current_line else "") + word
            if self._chest_desc_font.size(test)[0] > text_max_w and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        for i, line_text in enumerate(lines):
            ls = self._chest_desc_font.render(line_text, True, (210, 210, 220))
            ls.set_alpha(alpha)
            self.screen.blit(ls, (text_x, desc_y + i * 34))

        # --- Indication "Entrée pour skip" ---
        hint = self._chest_hint_font.render("Entrée pour skip", True, (150, 150, 150))
        hint.set_alpha(alpha)
        self.screen.blit(hint, (px + panel_w - hint.get_width() - 20,
                                py + panel_h - hint.get_height() - 15))
