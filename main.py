import sys
import os
import pygame

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from menu import start_menu
from game import run_game, run_game_mp_server, run_game_mp_client, run_game_solo

def show_splash_screen(screen, logo_path, total_duration_ms=3000):
    fade_in_time = 1000
    fade_out_time = 1000
    hold_time = total_duration_ms - fade_in_time - fade_out_time

    if hold_time < 0:
        return

    try:
        logo_img = pygame.image.load(logo_path).convert_alpha()
        logo_rect = logo_img.get_rect(center=screen.get_rect().center)
    except FileNotFoundError:
        return

    clock = pygame.time.Clock()
    running_splash = True
    start_time = pygame.time.get_ticks()

    while running_splash:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running_splash = False
                return 

        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - start_time
        alpha = 0

        if elapsed_time < fade_in_time:
            alpha = int((elapsed_time / fade_in_time) * 255)
        elif elapsed_time < (fade_in_time + hold_time):
            alpha = 255
        elif elapsed_time < total_duration_ms:
            time_in_fade_out = elapsed_time - (fade_in_time + hold_time)
            alpha = int(255 - (time_in_fade_out / fade_out_time) * 255)
        else:
            running_splash = False
            alpha = 0

        screen.fill((0, 0, 0))
        logo_img.set_alpha(alpha)
        screen.blit(logo_img, logo_rect)
        pygame.display.flip()
        
        clock.tick(60)

def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass
    
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("AETHELRIS")

    show_splash_screen(screen, "assets/images/logo.png", total_duration_ms=3000)

    while True:
        result = start_menu(screen)
        if not result:
            continue
        music_v, sfx_v, mode, net_obj = result

        if mode == 'solo':
            run_game_solo(screen, start_music_vol=music_v, start_sfx_vol=sfx_v)
        elif mode == 'host' and net_obj is not None:
            run_game_mp_server(screen, net_obj, start_music_vol=music_v, start_sfx_vol=sfx_v)
            net_obj.stop()
        elif mode == 'join' and net_obj is not None:
            run_game_mp_client(screen, net_obj, start_music_vol=music_v, start_sfx_vol=sfx_v)
            net_obj.stop()

if __name__ == "__main__":
    main()