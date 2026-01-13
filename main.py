import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pygame
from menu import start_menu
from game import run_game

def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    pygame.display.set_caption("AETHELRIS")

    start_menu(screen)
    run_game(screen)
    pygame.quit()

if __name__ == "__main__":
    main()

