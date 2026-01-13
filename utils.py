import pygame

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
    pygame.draw.rect(surface, (40,40,40), rect)
    pygame.draw.rect(surface, (255,255,255), rect, 3)
    font = pygame.font.SysFont(None, 40)
    txt = font.render(text, True, (255,255,255))
    surface.blit(txt, txt.get_rect(center=rect.center))