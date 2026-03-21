import pygame

class UI:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(None, 30)

        try:
            self.sword_img = pygame.image.load("assets/images/sword_icon.png").convert_alpha()
            self.sword_img = pygame.transform.scale(self.sword_img, (64, 64)) 
            
            self.bow_img = pygame.image.load("assets/images/arc_icon.png").convert_alpha()
            self.bow_img = pygame.transform.scale(self.bow_img, (64, 64))
            
            self.pickaxe_img = pygame.image.load("assets/images/pickaxe_icon.png").convert_alpha()
            self.pickaxe_img = pygame.transform.scale(self.pickaxe_img, (64, 64))
            
            # --- NOUVEAU : CHARGEMENT DES BOTTES ---
            self.boots_img = pygame.image.load("assets/images/hermesboots.png").convert_alpha()
            self.boots_img = pygame.transform.scale(self.boots_img, (64, 64))
        except FileNotFoundError:
            self.sword_img = pygame.Surface((64, 64))
            self.sword_img.fill((200, 200, 200))
            self.bow_img = pygame.Surface((64, 64))
            self.bow_img.fill((150, 100, 50))
            self.pickaxe_img = pygame.Surface((64, 64))
            self.pickaxe_img.fill((100, 100, 100))
            self.boots_img = pygame.Surface((64, 64))
            self.boots_img.fill((100, 150, 200))

    def draw_health_bar(self, current_health, max_health):
        bar_width = 200
        bar_height = 20
        x, y = 20, 20
        
        ratio = current_health / max_health
        if ratio >= 0.8: color = (50, 200, 50)
        elif ratio >= 0.3: color = (200, 200, 50)
        else: color = (200, 50, 50)
            
        pygame.draw.rect(self.screen, (50, 50, 50), (x, y, bar_width, bar_height))
        pygame.draw.rect(self.screen, color, (x, y, bar_width * ratio, bar_height))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2) 

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
        
    # --- NOUVEAU : AFFICHAGE DU DASH (AVEC JAUGE DE COOLDOWN) ---
    def draw_boots_icon(self, has_boots, cooldown_ratio):
        if not has_boots: return
        x, y = 95, 50 # Placée juste à droite de l'arme
        
        bg_surface = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (40, 40, 40, 180), (0, 0, 64, 64), border_radius=5)
        self.screen.blit(bg_surface, (x, y))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, 64, 64), 2, border_radius=5)
        
        if cooldown_ratio >= 1.0:
            self.screen.blit(self.boots_img, (x, y)) # Prêt !
        else:
            # Assombrit l'icône de base
            dark_img = self.boots_img.copy()
            dark_img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(dark_img, (x, y))
            
            # Dessine la partie originale par-dessus, de bas en haut
            fill_height = int(64 * cooldown_ratio)
            if fill_height > 0:
                crop_rect = pygame.Rect(0, 64 - fill_height, 64, fill_height)
                self.screen.blit(self.boots_img, (x, y + 64 - fill_height), area=crop_rect)

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
        # --- BARRE PLUS GRANDE ---
        bar_width = 600 
        bar_height = 40 
        screen_width = self.screen.get_width()
        x = (screen_width - bar_width) // 2
        y = 40
        
        ratio = current_health / max_health
        if ratio >= 0.8: color = (50, 200, 50)
        elif ratio >= 0.3: color = (200, 200, 50)
        else: color = (200, 50, 50)
            
        # Fond sombre
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, bar_width, bar_height))
        
        # Jauge de couleur
        if ratio > 0:
            pygame.draw.rect(self.screen, color, (x, y, bar_width * ratio, bar_height))
            
        # Contour blanc
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2) 
        
        # Ombre du texte
        text_shadow = self.font.render(boss_name, True, (0, 0, 0))
        shadow_rect = text_shadow.get_rect(center=(screen_width // 2 + 2, y + bar_height // 2 + 2))
        self.screen.blit(text_shadow, shadow_rect)
        
        # Texte principal
        text_surf = self.font.render(boss_name, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(screen_width // 2, y + bar_height // 2))
        self.screen.blit(text_surf, text_rect)

    def draw_pause_menu(self, music_vol, sfx_vol, action_text=None):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        menu_w, menu_h = 450, 300
        x = (self.screen.get_width() - menu_w) // 2
        y = (self.screen.get_height() - menu_h) // 2
        
        pygame.draw.rect(self.screen, (40, 40, 40), (x, y, menu_w, menu_h))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, menu_w, menu_h), 2)
        
        title = self.font.render("PAUSE" if action_text != "Retour" else "PARAMÈTRES", True, (255, 255, 255))
        self.screen.blit(title, (x + menu_w//2 - title.get_width()//2, y + 20))
        
        music_txt = self.font.render(f"Musique : {int(music_vol*100)}%", True, (255, 255, 255))
        self.screen.blit(music_txt, (x + 30, y + 100))
        
        btn_mus_min = pygame.Rect(x + 300, y + 95, 40, 40)
        btn_mus_pl = pygame.Rect(x + 360, y + 95, 40, 40)
        pygame.draw.rect(self.screen, (100, 100, 100), btn_mus_min)
        pygame.draw.rect(self.screen, (100, 100, 100), btn_mus_pl)
        
        min_lbl = self.font.render("-", True, (255, 255, 255))
        pl_lbl = self.font.render("+", True, (255, 255, 255))
        self.screen.blit(min_lbl, (btn_mus_min.centerx - min_lbl.get_width()//2, btn_mus_min.centery - min_lbl.get_height()//2))
        self.screen.blit(pl_lbl, (btn_mus_pl.centerx - pl_lbl.get_width()//2, btn_mus_pl.centery - pl_lbl.get_height()//2))
        
        sfx_txt = self.font.render(f"Effets : {int(sfx_vol*100)}%", True, (255, 255, 255))
        self.screen.blit(sfx_txt, (x + 30, y + 160))
        
        btn_sfx_min = pygame.Rect(x + 300, y + 155, 40, 40)
        btn_sfx_pl = pygame.Rect(x + 360, y + 155, 40, 40)
        pygame.draw.rect(self.screen, (100, 100, 100), btn_sfx_min)
        pygame.draw.rect(self.screen, (100, 100, 100), btn_sfx_pl)
        
        self.screen.blit(min_lbl, (btn_sfx_min.centerx - min_lbl.get_width()//2, btn_sfx_min.centery - min_lbl.get_height()//2))
        self.screen.blit(pl_lbl, (btn_sfx_pl.centerx - pl_lbl.get_width()//2, btn_sfx_pl.centery - pl_lbl.get_height()//2))
        
        rects = {
            "mus_min": btn_mus_min, "mus_pl": btn_mus_pl, 
            "sfx_min": btn_sfx_min, "sfx_pl": btn_sfx_pl
        }
        
        if action_text == "Retour":
            btn_quit = pygame.Rect(x + menu_w//2 - 75, y + 230, 150, 50)
            pygame.draw.rect(self.screen, (200, 50, 50), btn_quit)
            quit_lbl = self.font.render(action_text, True, (255, 255, 255))
            if quit_lbl.get_width() > 130:
                quit_lbl = pygame.transform.scale(quit_lbl, (130, 30))
            self.screen.blit(quit_lbl, (btn_quit.centerx - quit_lbl.get_width()//2, btn_quit.centery - quit_lbl.get_height()//2))
            rects["quit"] = btn_quit
        else:
            btn_resume = pygame.Rect(x + menu_w//2 - 160, y + 230, 150, 50)
            btn_quit = pygame.Rect(x + menu_w//2 + 10, y + 230, 150, 50)
            
            pygame.draw.rect(self.screen, (50, 150, 50), btn_resume)
            pygame.draw.rect(self.screen, (200, 50, 50), btn_quit)
            
            resume_lbl = self.font.render("Reprendre", True, (255, 255, 255))
            quit_lbl = self.font.render("Quitter", True, (255, 255, 255))
            
            self.screen.blit(resume_lbl, (btn_resume.centerx - resume_lbl.get_width()//2, btn_resume.centery - resume_lbl.get_height()//2))
            self.screen.blit(quit_lbl, (btn_quit.centerx - quit_lbl.get_width()//2, btn_quit.centery - quit_lbl.get_height()//2))
            
            rects["resume"] = btn_resume
            rects["quit"] = btn_quit
            
        return rects