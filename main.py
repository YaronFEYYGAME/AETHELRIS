import pygame
import pytmx
import pyscroll
from src.player import Player


def main():
    pygame.init()
    pygame.mixer.init()
    mmo_sound = pygame.mixer.Sound("assets/sounds/clear-combo-7-394494-_1_.wav")
    step_sound = pygame.mixer.Sound("assets/sounds/walking-on-concrete-ver-2-268513.wav")
    step_sound.set_volume(0.4)

    walking = False

    font = pygame.font.SysFont(None, 60)
    show_mmo = False

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
        moving = False
        keys = pygame.key.get_pressed()

        if keys[pygame.K_z] :
            player.move_up()
            moving = True
        elif keys[pygame.K_s] :
            player.move_down()
            moving = True

        if keys[pygame.K_q] :
            player.move_left()
            moving = True
        elif keys[pygame.K_d] :
            player.move_right()
            moving = True
            
        if moving and not walking:
            step_sound.play(-1)  # boucle
            walking = True

        elif not moving and walking:
            step_sound.stop()
            walking = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_j:
                    mmo_sound.play()
                    show_mmo = True

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_j:
                    show_mmo = False


        player.update()
        group.center(player.rect.center)   
        group.draw(screen)
        
        if show_mmo:
            text = font.render("MENU", True, (255, 255, 255))
            screen.blit(text, (20, 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
