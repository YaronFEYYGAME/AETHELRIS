import pygame

class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        
        self.speed = 8
        # --- DÉGÂTS RÉDUITS DE 30% ---
        self.damage_amount = 10.5 # (Était à 15)
        self.direction = direction
        
        try:
            arrow_img = pygame.image.load("assets/images/Arrow01(32x32).png").convert_alpha()
            if self.direction == "left":
                self.image = pygame.transform.flip(arrow_img, True, False)
                self.velocity_x = -self.speed
            else:
                self.image = arrow_img
                self.velocity_x = self.speed
                
        except FileNotFoundError:
            print("⚠️ Erreur: Fichier Arrow01(32x32).png introuvable.")
            self.image = pygame.Surface((10, 10))
            self.image.fill((255, 255, 255))
            self.velocity_x = -self.speed if direction == "left" else self.speed

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.rect.y -= 5

        self.hitbox = pygame.Rect(0, 0, 15, 4)
        self.hitbox.center = self.rect.center

    def update(self):
        self.rect.x += self.velocity_x
        self.hitbox.center = self.rect.center