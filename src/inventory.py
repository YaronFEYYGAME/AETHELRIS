import pygame
from resource_manager import ResourceManager

class Inventory:
    def __init__(self, screen, width=3, slot_image_path="assets/images/inventaire.png", slot_size=50, padding=10):
        self.screen = screen
        self.width = width
        self.slot_size = slot_size
        self.padding = padding
        self.items = [None] * width  # Liste pour stocker les items (images)
        self.selected_index = None    # Case sélectionnée

        # Charger l'image de la case
        self.slot_image = ResourceManager.get_image(slot_image_path)
        self.slot_image = pygame.transform.scale(self.slot_image, (slot_size, slot_size))

        # Position de l'inventaire (bas au milieu)
        screen_width, screen_height = self.screen.get_size()
        total_width = width * slot_size + (width - 1) * padding
        self.x = (screen_width - total_width) // 2
        self.y = screen_height - slot_size - 10  # 10 px du bas

    def draw(self):
        for i in range(self.width):
            rect = pygame.Rect(
                self.x + i * (self.slot_size + self.padding),
                self.y,
                self.slot_size,
                self.slot_size
            )
            # Dessine l'image de la case
            self.screen.blit(self.slot_image, rect.topleft)

            # Si un item est présent, dessine l'item dessus
            if self.items[i]:
                self.screen.blit(self.items[i], rect.topleft)

            # Si cette case est sélectionnée, on fait un contour rouge
            if self.selected_index == i:
                pygame.draw.rect(self.screen, (255,0,0), rect, 3)

    def handle_event(self, event):
        # Permet de cliquer sur les cases
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # clic gauche
            mx, my = event.pos
            for i in range(self.width):
                rect = pygame.Rect(
                    self.x + i * (self.slot_size + self.padding),
                    self.y,
                    self.slot_size,
                    self.slot_size
                )
                if rect.collidepoint(mx, my):
                    # Sélectionne ou désélectionne la case
                    if self.selected_index == i:
                        self.selected_index = None
                    else:
                        self.selected_index = i
                    return i  # retourne l'index de la case cliquée
        return None

    def add_item(self, item_image):
        # Ajoute un item dans la première case vide
        for i in range(self.width):
            if self.items[i] is None:
                self.items[i] = item_image
                return True
        return False  # inventaire plein

