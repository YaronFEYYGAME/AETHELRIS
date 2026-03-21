import pygame
import sys
from utils import draw_pixel_text, draw_button
from ui import UI
from sound import SoundManager
from network import GameServer, GameClient, get_local_ip, ip_to_code, scan_for_host


def start_menu(screen):
    """Retourne (music_vol, sfx_vol, mode, net_obj).
    mode = 'solo' | 'host' | 'join'
    net_obj = GameServer | GameClient | None"""
    clock = pygame.time.Clock()

    ui = UI(screen)
    sound_manager = SoundManager()

    screen_width = screen.get_width()
    screen_height = screen.get_height()

    button_width = 200
    button_height = 55
    button_x = (screen_width - button_width) // 2

    play_button     = pygame.Rect(button_x, 290, button_width, button_height)
    host_button     = pygame.Rect(button_x, 355, button_width, button_height)
    join_button     = pygame.Rect(button_x, 420, button_width, button_height)
    settings_button = pygame.Rect(button_x, 485, button_width, button_height)
    quit_button     = pygame.Rect(button_x, 550, button_width, button_height)

    title = "AETHELRIS"
    scale = 2
    x_title = 50
    y_title = 50

    try:
        bg_image = pygame.image.load("assets/images/acceuil.jpeg").convert()
        bg_image = pygame.transform.scale(bg_image, (screen_width, screen_height))
    except FileNotFoundError:
        bg_image = None

    music_vol = 0.5
    sfx_vol = 0.8
    in_settings = False
    pause_rects = {}

    try:
        pygame.mixer.music.load("assets/sounds/menu_music.mp3")
        pygame.mixer.music.set_volume(music_vol)
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    while True:
        if bg_image:
            screen.blit(bg_image, (0, 0))
        else:
            screen.fill((15, 10, 25))

        draw_pixel_text(screen, title, x_title, y_title, scale, (150, 100, 255))

        if not in_settings:
            draw_button(screen, play_button,     "JOUER")
            draw_button(screen, host_button,     "HÉBERGER")
            draw_button(screen, join_button,     "REJOINDRE")
            draw_button(screen, settings_button, "PARAMÈTRES")
            draw_button(screen, quit_button,     "QUITTER")
        else:
            pause_rects = ui.draw_pause_menu(music_vol, sfx_vol, "Retour")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not in_settings:
                    if play_button.collidepoint(event.pos):
                        pygame.mixer.music.stop()
                        return music_vol, sfx_vol, 'solo', None

                    if host_button.collidepoint(event.pos):
                        result = _hosting_screen(screen, music_vol, sfx_vol)
                        if result:
                            server_obj = result
                            pygame.mixer.music.stop()
                            return music_vol, sfx_vol, 'host', server_obj

                    if join_button.collidepoint(event.pos):
                        result = _join_screen(screen, music_vol, sfx_vol)
                        if result:
                            client_obj = result
                            pygame.mixer.music.stop()
                            return music_vol, sfx_vol, 'join', client_obj

                    if settings_button.collidepoint(event.pos):
                        in_settings = True

                    if quit_button.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()
                else:
                    if pause_rects:
                        pos = event.pos
                        if pause_rects["mus_min"].collidepoint(pos):
                            music_vol = max(0.0, music_vol - 0.1)
                            pygame.mixer.music.set_volume(music_vol)
                        elif pause_rects["mus_pl"].collidepoint(pos):
                            music_vol = min(1.0, music_vol + 0.1)
                            pygame.mixer.music.set_volume(music_vol)
                        elif pause_rects["sfx_min"].collidepoint(pos):
                            sfx_vol = max(0.0, sfx_vol - 0.1)
                            sound_manager.update_sfx_volume(sfx_vol)
                        elif pause_rects["sfx_pl"].collidepoint(pos):
                            sfx_vol = min(1.0, sfx_vol + 0.1)
                            sound_manager.update_sfx_volume(sfx_vol)
                        elif pause_rects["quit"].collidepoint(pos):
                            in_settings = False

        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# Écran "Héberger" : démarre le serveur, affiche le code, attend le client
# ---------------------------------------------------------------------------

def _hosting_screen(screen, music_vol, sfx_vol):
    """Affiche le code d'accès et attend qu'un client se connecte.
    Retourne le GameServer connecté, ou None si annulé."""
    clock = pygame.time.Clock()
    font_big  = pygame.font.SysFont(None, 80)
    font_med  = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 28)

    local_ip = get_local_ip()
    code = ip_to_code(local_ip)
    code_str = f"{code:03d}"

    server = GameServer()
    try:
        server.start()
    except Exception as e:
        _show_error(screen, f"Impossible de démarrer le serveur : {e}")
        return None

    btn_cancel = pygame.Rect(screen.get_width() // 2 - 100, screen.get_height() // 2 + 120, 200, 50)

    dots = 0
    dot_timer = 0

    while True:
        dt = clock.tick(60)
        dot_timer += dt
        if dot_timer > 400:
            dots = (dots + 1) % 4
            dot_timer = 0

        # Client connecté ?
        if server.client_arrived:
            return server

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                server.stop()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                server.stop()
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_cancel.collidepoint(event.pos):
                    server.stop()
                    return None

        screen.fill((15, 10, 25))

        # Titre
        t = font_med.render("EN ATTENTE D'UN JOUEUR", True, (200, 180, 255))
        screen.blit(t, t.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 120)))

        # Code
        label = font_small.render("Code à communiquer :", True, (180, 180, 180))
        screen.blit(label, label.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 60)))

        code_surf = font_big.render(code_str, True, (255, 220, 50))
        screen.blit(code_surf, code_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)))

        # IP info
        ip_surf = font_small.render(f"(IP locale : {local_ip})", True, (120, 120, 120))
        screen.blit(ip_surf, ip_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 55)))

        # Attente animée
        wait_str = "Attente" + "." * dots
        wait_surf = font_small.render(wait_str, True, (150, 150, 150))
        screen.blit(wait_surf, wait_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 85)))

        # Bouton annuler
        draw_button(screen, btn_cancel, "Annuler")

        pygame.display.flip()


# ---------------------------------------------------------------------------
# Écran "Rejoindre" : saisie du code à 3 chiffres, connexion au serveur
# ---------------------------------------------------------------------------

def _join_screen(screen, music_vol, sfx_vol):
    """Affiche un champ de saisie pour le code à 3 chiffres.
    Retourne le GameClient connecté, ou None si annulé."""
    clock = pygame.time.Clock()
    font_big   = pygame.font.SysFont(None, 80)
    font_med   = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 28)

    code_input = ""
    status_msg = ""
    status_color = (200, 200, 200)
    searching = False

    btn_connect = pygame.Rect(screen.get_width() // 2 - 100, screen.get_height() // 2 + 100, 200, 50)
    btn_cancel  = pygame.Rect(screen.get_width() // 2 - 100, screen.get_height() // 2 + 165, 200, 50)

    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_BACKSPACE:
                    code_input = code_input[:-1]
                    status_msg = ""
                elif event.key == pygame.K_RETURN:
                    result = _try_connect(code_input)
                    if result is None:
                        status_msg = "Hôte introuvable. Vérifiez le code."
                        status_color = (255, 80, 80)
                    else:
                        return result
                elif event.unicode.isdigit() and len(code_input) < 3:
                    code_input += event.unicode
                    status_msg = ""

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_connect.collidepoint(event.pos):
                    result = _try_connect(code_input)
                    if result is None:
                        status_msg = "Hôte introuvable. Vérifiez le code."
                        status_color = (255, 80, 80)
                    else:
                        return result
                if btn_cancel.collidepoint(event.pos):
                    return None

        screen.fill((15, 10, 25))

        # Titre
        t = font_med.render("ENTREZ LE CODE DE L'HÔTE", True, (200, 180, 255))
        screen.blit(t, t.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 120)))

        label = font_small.render("Code à 3 chiffres :", True, (180, 180, 180))
        screen.blit(label, label.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 60)))

        # Champ de saisie
        display = code_input.ljust(3, '_')
        code_surf = font_big.render(display, True, (255, 220, 50))
        screen.blit(code_surf, code_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)))

        # Message de statut
        if status_msg:
            st_surf = font_small.render(status_msg, True, status_color)
            screen.blit(st_surf, st_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 60)))

        draw_button(screen, btn_connect, "Connexion")
        draw_button(screen, btn_cancel, "Annuler")

        pygame.display.flip()


def _try_connect(code_input):
    """Tente de se connecter à l'hôte identifié par le code.
    Retourne GameClient connecté ou None."""
    if len(code_input) != 3 or not code_input.isdigit():
        return None
    code = int(code_input)
    host_ip = scan_for_host(code)
    if host_ip is None:
        return None
    client = GameClient()
    if client.connect(host_ip, timeout=5):
        return client
    return None


def _show_error(screen, message):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return
        screen.fill((30, 0, 0))
        surf = font.render(message, True, (255, 100, 100))
        screen.blit(surf, surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)))
        pygame.display.flip()
        clock.tick(60)
