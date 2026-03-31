import pygame
import random
import os

class Rock(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        try:
            raw_image = pygame.image.load("assets/images/rock.png").convert_alpha()
            bbox = raw_image.get_bounding_rect()
            cropped_image = raw_image.subsurface(bbox)
            self.image = pygame.transform.scale(cropped_image, (80, 80))
        except FileNotFoundError:
            self.image = pygame.Surface((80, 80))
            self.image.fill((100, 100, 100))
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        self.hitbox = self.rect.copy()
        self.hitbox.inflate_ip(20, 40)

class RockParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = random.randint(4, 12)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        color = random.choice([(100, 100, 100), (120, 110, 100), (80, 80, 80), (60, 60, 60)])
        self.image.fill(color)
        
        self.rect = self.image.get_rect(center=(x, y))
        
        self.velocity_x = random.uniform(-4, 4)
        self.velocity_y = random.uniform(-6, -2)
        self.gravity = 0.4 
        
        self.life = 255 

    def update(self):
        self.velocity_y += self.gravity
        self.rect.x += self.velocity_x
        self.rect.y += self.velocity_y
        
        self.life -= 10
        if self.life <= 0:
            self.kill() 
        else:
            self.image.set_alpha(self.life)

class BloodParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = random.randint(3, 8)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        color = random.choice([(200, 0, 0), (150, 0, 0), (120, 0, 0)])
        self.image.fill(color)
        
        self.rect = self.image.get_rect(center=(x, y))
        
        self.velocity_x = random.uniform(-4, 4)
        self.velocity_y = random.uniform(-5, -1)
        self.gravity = 0.5 
        
        self.life = 255 

    def update(self):
        self.velocity_y += self.gravity
        self.rect.x += self.velocity_x
        self.rect.y += self.velocity_y
        
        self.life -= 15
        if self.life <= 0:
            self.kill() 
        else:
            self.image.set_alpha(self.life)

class SmokeParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = random.randint(6, 14)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        color_val = random.randint(180, 230)
        self.image.fill((color_val, color_val, color_val))
        
        self.rect = self.image.get_rect(center=(x, y))
        
        self.velocity_x = random.uniform(-1.5, 1.5)
        self.velocity_y = random.uniform(-2.5, -0.5)
        
        self.life = 255 
        self.fade_speed = random.randint(15, 25) 

    def update(self):
        self.rect.x += self.velocity_x
        self.rect.y += self.velocity_y
        
        self.life -= self.fade_speed
        if self.life <= 0:
            self.kill() 
        else:
            self.image.set_alpha(self.life)

# --- NOUVEAU : PARTICULES SOMBRES POUR LES BOSS MAGIQUES ---
class DarkParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = random.randint(3, 8)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)

        # Nuances de noir et gris très sombre
        color = random.choice([(20, 20, 20), (40, 40, 40), (10, 10, 10)])
        self.image.fill(color)

        self.rect = self.image.get_rect(center=(x, y))

        self.velocity_x = random.uniform(-4, 4)
        self.velocity_y = random.uniform(-5, -1)
        self.gravity = 0.5

        self.life = 255

    def update(self):
        self.velocity_y += self.gravity
        self.rect.x += self.velocity_x
        self.rect.y += self.velocity_y

        self.life -= 15
        if self.life <= 0:
            self.kill()
        else:
            self.image.set_alpha(self.life)


class Chest(pygame.sprite.Sprite):
    """Coffre interactif avec animation d'ouverture."""

    CLOSED_PATH = "assets/images/Chest/Chest.png"
    OPEN_PATH = "assets/images/Chest/ChestOpen.png"
    ANIM_DIR = "assets/images/Chest/Open"
    SCALE = 1.2

    def __init__(self, x, y, flipped=False):
        super().__init__()
        self.flipped = flipped
        self.opened = False
        self.opening = False
        self.frame_index = 0.0
        self.anim_speed = 12  # frames par seconde

        def _load_and_scale(path):
            img = pygame.image.load(path).convert_alpha()
            w, h = img.get_size()
            scaled = pygame.transform.scale(img, (int(w * self.SCALE), int(h * self.SCALE)))
            if flipped:
                scaled = pygame.transform.flip(scaled, True, False)
            return scaled

        try:
            self.closed_img = _load_and_scale(self.CLOSED_PATH)
            self.open_img = _load_and_scale(self.OPEN_PATH)
            # Frames d'animation triées numériquement
            import re
            anim_files = sorted(os.listdir(self.ANIM_DIR),
                                key=lambda f: int(re.search(r'(\d+)', f).group(1)))
            self.anim_frames = [_load_and_scale(os.path.join(self.ANIM_DIR, f))
                                for f in anim_files if f.endswith('.png')]
        except Exception:
            fallback = pygame.Surface((int(64 * self.SCALE), int(32 * self.SCALE)), pygame.SRCALPHA)
            fallback.fill((139, 90, 43))
            self.closed_img = fallback
            self.open_img = fallback
            self.anim_frames = [fallback]

        self.num_frames = len(self.anim_frames)
        self.image = self.closed_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        # Hitbox de collision solide — alignée sur le bas du sprite (corps du coffre)
        hb_w = int(self.rect.width * 0.55)
        hb_h = int(self.rect.height * 0.4)
        self.hitbox = pygame.Rect(0, 0, hb_w, hb_h)
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom

    def open(self):
        """Déclenche l'animation d'ouverture."""
        if self.opened or self.opening:
            return
        self.opening = True
        self.frame_index = 0.0

    def update(self):
        if self.opening and not self.opened:
            self.frame_index += self.anim_speed / 60.0
            idx = int(self.frame_index)
            if idx >= self.num_frames:
                self.opened = True
                self.opening = False
                self.image = self.open_img
            else:
                self.image = self.anim_frames[idx]
            self.rect = self.image.get_rect(center=self.rect.center)