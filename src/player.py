import pygame

class Player(pygame.sprite.Sprite) :
    def __init__(self, x, y) :
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect()
        self.position = [x,y]
        self.feet = pygame.Rect(0, 0, self.rect.width * 0.5, 12)

    def get_image(self, x, y,) :
        image = pygame.Surface([32,32])
        image.blit(self.sprite_sheet, (0,0), (x,y,32,32))
        return image
    
    def update(self) :
        self.rect.topleft = self.position
        self.feet.midbottom = self.rect.midbottom

    def move_right(self) : self.position[0] += 2
    def move_left(self) : self.position[0] -= 2
    def move_up(self) : self.position[1] -= 2
    def move_down(self) : self.position[1] += 2

