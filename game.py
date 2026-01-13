import pygame
import pytmx
import pyscroll
from src.player import Player
from inventory import Inventory

def run_game(screen):
    clock = pygame.time.Clock()
    mmo_sound = pygame.mixer.Sound("assets/sounds/clear-combo-7-394494-_1_.wav")
    step_sound = pygame.mixer.Sound("assets/sounds/walking-on-concrete-ver-2-268513.wav")
    step_sound.set_volume(0.4)
    walking = False
    font = pygame.font.SysFont(None, 60)
    show_mmo = False

    tmx_data = pytmx.util_pygame.load_pygame("assets/maps/donjon.tmx")
    map_data = pyscroll.data.TiledMapData(tmx_data)
    screen_width, screen_height = screen.get_size()
    map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
    map_layer.zoom = 2
    map_layer.set_size((screen_width, screen_height))

    player = Player(100,100)
    group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=3)
    group.add(player)
    inventory = Inventory(screen, width=3, slot_image_path="assets/images/inventaire.png")

    map_width = tmx_data.width * tmx_data.tilewidth
    map_height = tmx_data.height * tmx_data.tileheight
    running = True
    # Exemple : charger une image d'item
    item_image = pygame.image.load("assets/images/epee1.png").convert_alpha()
    item_image = pygame.transform.scale(item_image, (50,50))  # taille = slot_size
    inventory.add_item(item_image)  # ajoute l'item dans la première case vide

    while running:
        moving = False
        keys = pygame.key.get_pressed()
        if keys[pygame.K_z]: player.move_up(); moving=True
        if keys[pygame.K_s]: player.move_down(); moving=True
        if keys[pygame.K_q]: player.move_left(); moving=True
        if keys[pygame.K_d]: player.move_right(); moving=True

        if moving and not walking: step_sound.play(-1); walking=True
        elif not moving and walking: step_sound.stop(); walking=False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running=False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_j:
                    mmo_sound.play()
                    show_mmo = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_j:
                    show_mmo = False
            inventory.handle_event(event)
        player.update()
        x = max(screen_width//2, min(player.rect.centerx, map_width - screen_width//2))
        y = max(screen_height//2, min(player.rect.centery, map_height - screen_height//2))
        group.center((x,y))
        group.draw(screen)
        inventory.draw()


        if show_mmo:
            text = font.render("MENU", True, (255,255,255))
            screen.blit(text, (20,20))

        pygame.display.flip()
        clock.tick(60)
