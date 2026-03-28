import pygame
from characters import CHARACTER_DEFS


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
}


class UI:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(None, 30)

        # Icônes par défaut (soldier)
        self._icon_cache = {}
        self._load_default_icons()

    def _load_default_icons(self):
        """Charge les icônes par défaut du soldier."""
        try:
            self.sword_img = pygame.image.load("assets/images/sword_icon.png").convert_alpha()
            self.sword_img = pygame.transform.scale(self.sword_img, (64, 64))

            self.bow_img = pygame.image.load("assets/images/arc_icon.png").convert_alpha()
            self.bow_img = pygame.transform.scale(self.bow_img, (64, 64))

            self.pickaxe_img = pygame.image.load("assets/images/pickaxe_icon.png").convert_alpha()
            self.pickaxe_img = pygame.transform.scale(self.pickaxe_img, (64, 64))

            self.boots_img = pygame.image.load("assets/images/hermesboots.png").convert_alpha()
            self.boots_img = pygame.transform.scale(self.boots_img, (64, 64))

            self.redgem_img = pygame.image.load("assets/images/redgem.png").convert_alpha()
            self.redgem_img = pygame.transform.scale(self.redgem_img, (64, 64))

            self.bluegem_img = pygame.image.load("assets/images/bluegem.png").convert_alpha()
            self.bluegem_img = pygame.transform.scale(self.bluegem_img, (64, 64))

            self.mirror_img = pygame.image.load("assets/images/mirror.png").convert_alpha()
            self.mirror_img = pygame.transform.scale(self.mirror_img, (64, 64))

            _km_raw = pygame.image.load("assets/images/kitsune_mask.png").convert_alpha()
            _km_raw = pygame.transform.scale(_km_raw, (48, 48))
            self.kitsune_mask_img = pygame.Surface((64, 64), pygame.SRCALPHA)
            self.kitsune_mask_img.blit(_km_raw, (8, 8))  # centré dans le slot 64x64

            self.cursed_brand_img = pygame.image.load("assets/images/cursed_brand.png").convert_alpha()
            self.cursed_brand_img = pygame.transform.scale(self.cursed_brand_img, (64, 64))
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

    def load_character_icons(self, char_type):
        """Charge les icônes spécifiques à un personnage."""
        if char_type in self._icon_cache:
            return self._icon_cache[char_type]

        char_def = CHARACTER_DEFS.get(char_type, CHARACTER_DEFS['soldier'])
        icons = {}
        for slot, path in char_def.get('icons', {}).items():
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (64, 64))
                icons[slot] = img
            except FileNotFoundError:
                surf = pygame.Surface((64, 64)); surf.fill((100, 100, 100))
                icons[slot] = surf
        self._icon_cache[char_type] = icons
        return icons

    def draw_health_bar(self, current_health, max_health):
        bar_width = 200
        bar_height = 20
        x, y = 20, 20

        ratio = current_health / max_health if max_health > 0 else 0
        if ratio >= 0.8: color = (50, 200, 50)
        elif ratio >= 0.3: color = (200, 200, 50)
        else: color = (200, 50, 50)

        pygame.draw.rect(self.screen, (50, 50, 50), (x, y, bar_width, bar_height))
        pygame.draw.rect(self.screen, color, (x, y, bar_width * ratio, bar_height))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)

    def _get_item_icon(self, item_type):
        """Retourne l'icône 64x64 pour un type d'item."""
        icon_map = {
            'boots': self.boots_img, 'bluegem': self.bluegem_img,
            'cursed_brand': self.cursed_brand_img, 'pickaxe': self.pickaxe_img,
            'redgem': self.redgem_img, 'mirror': self.mirror_img,
            'kitsune_mask': self.kitsune_mask_img,
        }
        return icon_map.get(item_type)

    def draw_character_hud(self, char_type, current_weapon, skill_cooldowns=None,
                           arrows=0, inventory_items=None,
                           dash_cr=1.0, blue_gem_cr=1.0, cursed_brand_cr=1.0,
                           arrow_regen_cr=1.0, item_start_key=2):
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
            self._inv_title_font = pygame.font.SysFont(None, 28)
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
                    self._inv_name_font = pygame.font.SysFont(None, 24, bold=True)
                    self._inv_desc_font = pygame.font.SysFont(None, 20, italic=True)

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
            self._inv_help_font = pygame.font.SysFont(None, 22)
        help_text = "[E] Saisir   [Q/D] Deplacer   [A] Jeter   [I/Echap] Fermer"
        help_surf = self._inv_help_font.render(help_text, True, (180, 180, 180))
        self.screen.blit(help_surf, (px + panel_w // 2 - help_surf.get_width() // 2,
                                     py + panel_h - 30))

    def _draw_slot(self, x, y, size, icon, is_active=False, cooldown_ratio=1.0,
                   show_cooldown=False, label=None):
        """Dessine un slot d'inventaire avec cooldown optionnel."""
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

        if show_cooldown and cooldown_ratio < 1.0:
            # Icône assombrie
            dark_img = icon.copy()
            dark_img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(dark_img, (x, y))

            # Remplissage progressif de bas en haut
            fill_height = int(size * cooldown_ratio)
            if fill_height > 0:
                crop_rect = pygame.Rect(0, size - fill_height, size, fill_height)
                self.screen.blit(icon, (x, y + size - fill_height), area=crop_rect)
        else:
            self.screen.blit(icon, (x, y))

        # Label de touche
        if label:
            lbl_font = pygame.font.SysFont(None, 18)
            lbl_surf = lbl_font.render(label, True, (200, 200, 200))
            self.screen.blit(lbl_surf, (x + 3, y + 2))

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
        x, y = 95, 50
        bg_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (40, 40, 40, 180), (0, 0, 64, 64), border_radius=5)
        self.screen.blit(bg_surface, (x, y))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, 64, 64), 2, border_radius=5)
        if cooldown_ratio >= 1.0:
            self.screen.blit(self.boots_img, (x, y))
        else:
            dark_img = self.boots_img.copy()
            dark_img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(dark_img, (x, y))
            fill_height = int(64 * cooldown_ratio)
            if fill_height > 0:
                crop_rect = pygame.Rect(0, 64 - fill_height, 64, fill_height)
                self.screen.blit(self.boots_img, (x, y + 64 - fill_height), area=crop_rect)

    def draw_boss_dialogue(self, text, boss_name=None):
        """Boîte de dialogue RPG en bas de l'écran pour les dialogues de boss.
        Word wrap automatique si le texte est trop long."""
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        box_w = min(700, sw - 60)
        padding = 14
        max_text_w = box_w - padding * 2

        if not hasattr(self, '_boss_dialogue_font'):
            self._boss_dialogue_font = pygame.font.SysFont(
                "garamond, times new roman, serif", 26)
        if not hasattr(self, '_boss_name_font'):
            self._boss_name_font = pygame.font.SysFont(
                "garamond, times new roman, serif", 22, bold=True)

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

        bg_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (20, 20, 20, 200), (0, 0, box_width, box_height), border_radius=10)
        self.screen.blit(bg_surface, (x, y))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, box_width, box_height), 2, border_radius=10)

        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(x + box_width // 2, y + box_height // 2))
        self.screen.blit(text_surf, text_rect)

    def draw_boss_health_bar(self, current_health, max_health, boss_name="Gardien des profondeurs"):
        bar_width = 600
        bar_height = 40
        screen_width = self.screen.get_width()
        x = (screen_width - bar_width) // 2
        y = 40

        ratio = current_health / max_health if max_health > 0 else 0
        if ratio >= 0.8: color = (50, 200, 50)
        elif ratio >= 0.3: color = (200, 200, 50)
        else: color = (200, 50, 50)

        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, bar_width, bar_height))
        if ratio > 0:
            pygame.draw.rect(self.screen, color, (x, y, bar_width * ratio, bar_height))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)

        text_shadow = self.font.render(boss_name, True, (0, 0, 0))
        shadow_rect = text_shadow.get_rect(center=(screen_width // 2 + 2, y + bar_height // 2 + 2))
        self.screen.blit(text_shadow, shadow_rect)

        text_surf = self.font.render(boss_name, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(screen_width // 2, y + bar_height // 2))
        self.screen.blit(text_surf, text_rect)

    def _draw_styled_button(self, rect, text, font=None):
        """Bouton style inventaire : fond semi-transparent, bordure dorée au survol."""
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        if font is None:
            font = pygame.font.SysFont(None, 30)

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
        title_font = pygame.font.SysFont(None, 36)
        title_text = "PAUSE" if action_text != "Retour" else "PARAMÈTRES"
        title = title_font.render(title_text, True, (255, 220, 150))
        self.screen.blit(title, (x + menu_w // 2 - title.get_width() // 2, y + 18))

        # Ligne décorative sous le titre
        line_y = y + 52
        pygame.draw.line(self.screen, (180, 150, 100), (x + 30, line_y), (x + menu_w - 30, line_y), 1)

        # Labels volume
        label_font = pygame.font.SysFont(None, 28)
        music_txt = label_font.render(f"Musique : {int(music_vol * 100)}%", True, (220, 215, 200))
        self.screen.blit(music_txt, (x + 30, y + 75))

        sfx_txt = label_font.render(f"Effets : {int(sfx_vol * 100)}%", True, (220, 215, 200))
        self.screen.blit(sfx_txt, (x + 30, y + 135))

        # Boutons +/- volume (style inventaire)
        btn_font = pygame.font.SysFont(None, 30)
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
