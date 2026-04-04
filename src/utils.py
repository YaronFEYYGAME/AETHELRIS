import pygame
from resource_manager import ResourceManager

def draw_pixel_text(surface, text, x, y, scale, color):
    font = {
        "A": ["0110","1001","1111","1001","1001"],
        "E": ["1111","1000","1110","1000","1111"],
        "T": ["1111","0010","0010","0010","0010"],
        "H": ["1001","1001","1111","1001","1001"],
        "L": ["1000","1000","1000","1000","1111"],
        "R": ["1110","1001","1110","1010","1001"],
        "I": ["111","010","010","010","111"],
        "S": ["0111","1000","0110","0001","1110"]
    }

    cursor_x = x
    for char in text:
        if char == " ":
            cursor_x += 20 * scale
            continue
        pattern = font[char]
        for row, line in enumerate(pattern):
            for col, pixel in enumerate(line):
                if pixel == "1":
                    pygame.draw.rect(
                        surface,
                        color,
                        (cursor_x + col*scale*8, y + row*scale*8, scale*8, scale*8)
                    )
        cursor_x += (len(pattern[0]) + 1) * scale * 8

def draw_button(surface, rect, text):
    """Bouton style inventaire : fond semi-transparent, bordure dorée au survol."""
    mouse_pos = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mouse_pos)

    # Fond semi-transparent
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if hovered:
        pygame.draw.rect(bg, (60, 55, 45, 230), (0, 0, rect.width, rect.height), border_radius=5)
    else:
        pygame.draw.rect(bg, (30, 28, 35, 200), (0, 0, rect.width, rect.height), border_radius=5)
    surface.blit(bg, rect.topleft)

    # Bordure
    border_color = (200, 170, 100) if hovered else (120, 110, 90)
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=5)

    # Texte
    font = ResourceManager.get_font(30, None)
    txt_color = (255, 240, 200) if hovered else (220, 215, 200)
    txt = font.render(text, True, txt_color)
    surface.blit(txt, txt.get_rect(center=rect.center))