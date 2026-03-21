import pygame
import random

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