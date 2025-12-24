import pygame
import pytmx
import pyscroll
from src.player import Player

def main():
    pygame.init()
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Donjon test")
    clock = pygame.time.Clock()
    tmx_data = pytmx.util_pygame.load_pygame("assets/maps/donjon.tmx")
    map_data = pyscroll.data.TiledMapData(tmx_data)
    map_layer = pyscroll.BufferedRenderer(map_data, (screen_width,screen_height))
    map_layer.zoom = 2
    player = Player(100,100)
    group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=3)
    group.add(player)
    running = True
    while running:
        
        keys = pygame.key.get_pressed()

        if keys[pygame.K_z] :
            player.move_up()
        elif keys[pygame.K_s] :
            player.move_down()

        if keys[pygame.K_q] :
            player.move_left()
        elif keys[pygame.K_d] :
            player.move_right()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.update()
        group.center(player.rect.center)   
        group.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
