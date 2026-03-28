import pygame

class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, item_type):
        super().__init__()
        self.item_type = item_type 
        
        try:
            if self.item_type == 'melee':
                img = pygame.image.load("assets/images/sword_icon.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'ranged':
                img = pygame.image.load("assets/images/arc_icon.png").convert_alpha()
                self.image = pygame.transform.scale(img, (24, 24))
            elif self.item_type == 'pickaxe':
                img = pygame.image.load("assets/images/pickaxe_icon.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'arrow':
                img = pygame.image.load("assets/images/Arrow01(32x32).png").convert_alpha()
                self.image = pygame.transform.scale(img, (32, 32))
            elif self.item_type == 'apple': 
                img = pygame.image.load("assets/images/apple.png").convert_alpha()
                self.image = pygame.transform.scale(img, (16, 16))
            # --- NOUVEAU : LES BOTTES ---
            elif self.item_type == 'boots':
                img = pygame.image.load("assets/images/hermesboots.png").convert_alpha()
                self.image = pygame.transform.scale(img, (24, 24))
            elif self.item_type == 'redgem':
                img = pygame.image.load("assets/images/redgem.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'bluegem':
                img = pygame.image.load("assets/images/bluegem.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'mirror':
                img = pygame.image.load("assets/images/mirror.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'kitsune_mask':
                img = pygame.image.load("assets/images/kitsune_mask.png").convert_alpha()
                self.image = pygame.transform.scale(img, (18, 18))
            elif self.item_type == 'cursed_brand':
                img = pygame.image.load("assets/images/cursed_brand.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
            elif self.item_type == 'travelers_cap':
                img = pygame.image.load("assets/images/travelers_cap.png").convert_alpha()
                self.image = pygame.transform.scale(img, (20, 20))
        except FileNotFoundError:
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 255, 0)) 
            print(f"⚠️ Image introuvable pour l'item : {self.item_type}")
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)