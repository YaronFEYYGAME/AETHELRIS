import pygame
from utils import draw_pixel_text, draw_button

def start_menu(screen):
    clock = pygame.time.Clock()
    button = pygame.Rect(300, 380, 200, 70)

    title = "AETHELRIS"
    scale = 2
    letter_width = 5 * scale * 8
    spacing = scale * 8
    title_width = len(title) * (letter_width + spacing)

    screen_width = screen.get_width()
    x_title = (screen_width - title_width) // 2
    y_title = 140

    while True:
        screen.fill((15, 10, 25))
        draw_pixel_text(screen, title, x_title, y_title, scale, (150, 100, 255))
        draw_button(screen, button, "JOUER")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button.collidepoint(event.pos):
                    return

        pygame.display.flip()
        clock.tick(60)
