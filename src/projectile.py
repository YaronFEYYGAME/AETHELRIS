import pygame
import math
from resource_manager import ResourceManager


class Projectile(pygame.sprite.Sprite):
    """Projectile linéaire (flèche, boule de feu, etc.)."""

    def __init__(self, x, y, direction, img_path=None, damage=10.5, piercing=False):
        super().__init__()

        self.speed = 8
        self.damage_amount = damage
        self.direction = direction
        self.piercing = piercing
        self._hit_enemies = set()  # pour les projectiles traversants

        if img_path is None:
            img_path = "assets/images/Arrow01(32x32).png"
        self._img_path = img_path

        # Déterminer la taille d'affichage selon le type de projectile
        is_effect = 'Effect' in img_path or 'effect' in img_path
        display_size = 128 if is_effect else 32

        try:
            arrow_img = ResourceManager.get_image(img_path)
            # Les effets de wizard sont des sprite sheets, prendre la première frame
            if arrow_img.get_width() > arrow_img.get_height() * 1.5:
                frame_size = arrow_img.get_height()
                arrow_img = arrow_img.subsurface((0, 0, frame_size, frame_size))
                arrow_img = pygame.transform.scale(arrow_img, (display_size, display_size))
            if self.direction == "left":
                self.image = pygame.transform.flip(arrow_img, True, False)
                self.velocity_x = -self.speed
            else:
                self.image = arrow_img
                self.velocity_x = self.speed

        except FileNotFoundError:
            print(f"Erreur: Fichier {img_path} introuvable.")
            self.image = pygame.Surface((10, 10))
            self.image.fill((255, 255, 255))
            self.velocity_x = -self.speed if direction == "left" else self.speed

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.rect.y -= 5

        hitbox_w = 30 if is_effect else 15
        hitbox_h = 16 if is_effect else 4
        self.hitbox = pygame.Rect(0, 0, hitbox_w, hitbox_h)
        self.hitbox.center = self.rect.center

    def update(self):
        self.rect.x += self.velocity_x
        self.hitbox.center = self.rect.center


class HomingProjectile(pygame.sprite.Sprite):
    """Projectile qui se dirige vers une cible et explose en zone."""

    def __init__(self, start_x, start_y, target_x, target_y, damage=20,
                 explosion_radius=60, img_path=None, effect_frames=5):
        super().__init__()

        self.damage_amount = damage
        self.explosion_radius = explosion_radius
        self.speed = 4
        self.has_exploded = False
        self.exploding = False
        self.explosion_timer = 0
        self.explosion_duration = 300  # ms

        self.target = pygame.math.Vector2(target_x, target_y)
        self.pos = pygame.math.Vector2(start_x, start_y)

        # Charger l'image du projectile
        self._frames = []
        if img_path:
            try:
                sheet = ResourceManager.get_image(img_path)
                fh = sheet.get_height()
                fw = fh  # frames carrées
                num = sheet.get_width() // fw
                for i in range(num):
                    frame = sheet.subsurface((i * fw, 0, fw, fh))
                    frame = pygame.transform.scale(frame, (32, 32))
                    self._frames.append(frame)
            except FileNotFoundError:
                pass

        if not self._frames:
            surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(surf, (100, 150, 255), (8, 8), 8)
            self._frames = [surf]

        self._frame_index = 0
        self._anim_speed = 0.15
        self.image = self._frames[0]
        self.rect = self.image.get_rect(center=(start_x, start_y))
        self.hitbox = pygame.Rect(0, 0, 20, 20)
        self.hitbox.center = self.rect.center

    def update(self):
        if self.exploding:
            self.explosion_timer += 16  # ~1 frame at 60fps
            if self.explosion_timer >= self.explosion_duration:
                self.kill()
            else:
                # Animation d'explosion (cercle qui s'agrandit)
                progress = self.explosion_timer / self.explosion_duration
                radius = int(self.explosion_radius * progress)
                size = max(radius * 2, 4)
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                alpha = int(200 * (1 - progress))
                pygame.draw.circle(surf, (255, 200, 100, alpha), (size // 2, size // 2), radius)
                self.image = surf
                self.rect = self.image.get_rect(center=self.rect.center)
            return

        # Mouvement vers la cible
        direction = self.target - self.pos
        if direction.length() < self.speed * 2:
            # Arrivé à destination → exploser
            self.exploding = True
            self.has_exploded = True
            self.explosion_timer = 0
            return

        direction = direction.normalize() * self.speed
        self.pos += direction
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.hitbox.center = self.rect.center

        # Animer le sprite
        self._frame_index += self._anim_speed
        if self._frame_index >= len(self._frames):
            self._frame_index = 0
        self.image = self._frames[int(self._frame_index)]


class HealEffect(pygame.sprite.Sprite):
    """Effet visuel de soin sur un joueur."""

    def __init__(self, x, y, img_path=None, effect_frames=4):
        super().__init__()
        self._img_path = img_path

        self._frames = []
        if img_path:
            try:
                sheet = ResourceManager.get_image(img_path)
                fh = sheet.get_height()
                fw = fh
                num = sheet.get_width() // fw
                for i in range(num):
                    frame = sheet.subsurface((i * fw, 0, fw, fh))
                    frame = pygame.transform.scale(frame, (48, 48))
                    self._frames.append(frame)
            except FileNotFoundError:
                pass

        if not self._frames:
            surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(surf, (100, 255, 100, 180), (16, 16), 16)
            self._frames = [surf]

        self._frame_index = 0
        self._anim_speed = 0.12
        self.image = self._frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.duration = len(self._frames) / self._anim_speed * 16  # durée en ms
        self.start_time = pygame.time.get_ticks()

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed > self.duration:
            self.kill()
            return
        self._frame_index += self._anim_speed
        if self._frame_index >= len(self._frames):
            self._frame_index = len(self._frames) - 1
        self.image = self._frames[int(self._frame_index)]


class InstantAOE(pygame.sprite.Sprite):
    """Effet qui spawn directement sur une position et explose en zone."""

    def __init__(self, x, y, damage=20, explosion_radius=60, img_path=None, effect_frames=5, target_size=48, render_scale=1.2):
        super().__init__()

        self.damage_amount = damage
        self.explosion_radius = explosion_radius
        self._img_path = img_path
        self.has_exploded = True  # Dégâts appliqués immédiatement
        self.exploding = True

        # Taille de l'effet proportionnelle à la cible
        render_size = max(48, int(target_size * render_scale))

        self._frames = []
        if img_path:
            try:
                sheet = ResourceManager.get_image(img_path)
                fh = sheet.get_height()
                fw = fh
                num = sheet.get_width() // fw
                for i in range(num):
                    frame = sheet.subsurface((i * fw, 0, fw, fh))
                    frame = pygame.transform.scale(frame, (render_size, render_size))
                    self._frames.append(frame)
            except FileNotFoundError:
                pass

        if not self._frames:
            surf = pygame.Surface((render_size, render_size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 200, 100, 200), (render_size // 2, render_size // 2), render_size // 2)
            self._frames = [surf]

        self._frame_index = 0
        self._anim_speed = 0.15
        self.image = self._frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.hitbox = pygame.Rect(0, 0, explosion_radius * 2, explosion_radius * 2)
        self.hitbox.center = self.rect.center
        self.start_time = pygame.time.get_ticks()
        self.duration = 400  # ms

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed > self.duration:
            self.kill()
            return
        self._frame_index += self._anim_speed
        if self._frame_index >= len(self._frames):
            self._frame_index = len(self._frames) - 1
        self.image = self._frames[int(self._frame_index)]


class FloatingText(pygame.sprite.Sprite):
    """Texte flottant qui apparaît brièvement au-dessus d'un personnage."""

    def __init__(self, x, y, text="fail...", duration=700, color=(255, 100, 100),
                 font_size=22, raw_pos=False):
        super().__init__()
        self._font = ResourceManager.get_font(font_size, None)
        self._text = text
        self._color = color
        # raw_pos=True : y utilisé tel quel (damage numbers déjà positionnés)
        # raw_pos=False : comportement historique avec offset -40
        y_init = y if raw_pos else y - 40
        self._base_y = y_init
        self.start_time = pygame.time.get_ticks()
        self.duration = duration
        self.image = self._font.render(text, True, color)
        self.rect = self.image.get_rect(center=(x, y_init))

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed > self.duration:
            self.kill()
            return
        progress = elapsed / self.duration
        # _base_y intègre déjà l'offset initial (raw_pos ou -40 historique)
        self.rect.centery = self._base_y - int(15 * progress)
        alpha = max(0, int(255 * (1.0 - progress)))
        self.image = self._font.render(self._text, True, self._color)
        self.image.set_alpha(alpha)
