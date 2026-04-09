import pygame
from resource_manager import ResourceManager

class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, item_type):
        super().__init__()
        self.item_type = item_type 
        
        try:
            if self.item_type == 'melee':
                img = ResourceManager.get_image("assets/images/sword_icon.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'ranged':
                img = ResourceManager.get_image("assets/images/arc_icon.png")
                self.image = pygame.transform.scale(img, (24, 24))
            elif self.item_type == 'pickaxe':
                img = ResourceManager.get_image("assets/images/pickaxe_icon.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'arrow':
                img = ResourceManager.get_image("assets/images/Arrow01(32x32).png")
                self.image = pygame.transform.scale(img, (32, 32))
            elif self.item_type == 'apple': 
                img = ResourceManager.get_image("assets/images/apple.png")
                self.image = pygame.transform.scale(img, (16, 16))
            # --- NOUVEAU : LES BOTTES ---
            elif self.item_type == 'boots':
                img = ResourceManager.get_image("assets/images/hermesboots.png")
                self.image = pygame.transform.scale(img, (24, 24))
            elif self.item_type == 'redgem':
                img = ResourceManager.get_image("assets/images/redgem.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'bluegem':
                img = ResourceManager.get_image("assets/images/bluegem.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'mirror':
                img = ResourceManager.get_image("assets/images/mirror.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'kitsune_mask':
                img = ResourceManager.get_image("assets/images/kitsune_mask.png")
                self.image = pygame.transform.scale(img, (18, 18))
            elif self.item_type == 'cursed_brand':
                img = ResourceManager.get_image("assets/images/cursed_brand.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'travelers_cap':
                img = ResourceManager.get_image("assets/images/travelers_cap.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'zhonya':
                img = ResourceManager.get_image("assets/images/zhonya.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'rabadon':
                img = ResourceManager.get_image("assets/images/rabadon.png")
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'cap_assassin':
                img = ResourceManager.get_image("assets/images/cap_assassin.png")
                self.image = pygame.transform.scale(img, (20, 20))
        except FileNotFoundError:
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 255, 0)) 
            print(f"⚠️ Image introuvable pour l'item : {self.item_type}")
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)