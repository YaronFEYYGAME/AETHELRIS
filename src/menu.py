import pygame
import sys
import threading
from utils import draw_pixel_text, draw_button
from ui import UI
from sound import SoundManager
from network import GameServer, GameClient, get_local_ip, ip_to_code, resolve_host


def start_menu(screen):
    """Retourne (music_vol, sfx_vol, mode, net_obj).
    mode = 'solo' | 'host' | 'join'
    net_obj = GameServer | GameClient | None"""
    clock = pygame.time.Clock()

    ui = UI(screen)
    sound_manager = SoundManager()

    screen_width  = screen.get_width()
    screen_height = screen.get_height()

    button_width  = 200
    button_height = 55
    button_x = (screen_width - button_width) // 2

    play_button     = pygame.Rect(button_x, 290, button_width, button_height)
    host_button     = pygame.Rect(button_x, 355, button_width, button_height)
    join_button     = pygame.Rect(button_x, 420, button_width, button_height)
    settings_button = pygame.Rect(button_x, 485, button_width, button_height)
    quit_button     = pygame.Rect(button_x, 550, button_width, button_height)

    title   = "AETHELRIS"
    x_title = 50
    y_title = 50

    try:
        bg_image = pygame.image.load("assets/images/acceuil.jpeg").convert()
        bg_image = pygame.transform.scale(bg_image, (screen_width, screen_height))
    except FileNotFoundError:
        bg_image = None

    music_vol   = 0.5
    sfx_vol     = 0.8
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

        draw_pixel_text(screen, title, x_title, y_title, 2, (150, 100, 255))

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
                        result = _hosting_screen(screen)
                        if result:
                            pygame.mixer.music.stop()
                            return music_vol, sfx_vol, 'host', result

                    if join_button.collidepoint(event.pos):
                        result = _join_screen(screen)
                        if result:
                            pygame.mixer.music.stop()
                            return music_vol, sfx_vol, 'join', result

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
# Écran "Héberger"
# ---------------------------------------------------------------------------

def _hosting_screen(screen):
    """Démarre le serveur, affiche le code + l'IP, attend un client.
    Retourne le GameServer une fois connecté, ou None si annulé."""
    clock      = pygame.time.Clock()
    font_big   = pygame.font.SysFont(None, 90)
    font_med   = pygame.font.SysFont(None, 38)
    font_small = pygame.font.SysFont(None, 28)
    font_hint  = pygame.font.SysFont(None, 24)

    local_ip = get_local_ip()
    code     = ip_to_code(local_ip)
    code_str = f"{code:03d}"

    server = GameServer()
    try:
        server.start()
    except Exception as e:
        _show_error(screen, f"Impossible de démarrer le serveur :\n{e}")
        return None

    sw, sh = screen.get_size()
    cy     = sh // 2
    btn_cancel = pygame.Rect(sw // 2 - 100, cy + 140, 200, 50)

    dots      = 0
    dot_timer = 0

    while True:
        dt = clock.tick(60)
        dot_timer += dt
        if dot_timer > 450:
            dots      = (dots + 1) % 4
            dot_timer = 0

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

        _draw_centered(screen, font_med,   "EN ATTENTE D'UN JOUEUR",   cy - 140, (200, 180, 255))
        _draw_centered(screen, font_small, "Donnez ce code à l'autre joueur :", cy - 80, (180, 180, 180))

        # Code (grand, jaune)
        code_surf = font_big.render(code_str, True, (255, 220, 50))
        screen.blit(code_surf, code_surf.get_rect(center=(sw // 2, cy - 20)))

        # IP complète (pour saisie directe)
        _draw_centered(screen, font_small, f"IP locale : {local_ip}", cy + 50, (160, 200, 255))
        _draw_centered(screen, font_hint,
                       "L'autre joueur peut entrer le code OU l'IP complète",
                       cy + 78, (110, 110, 130))

        # Animation d'attente
        wait_str  = "Attente" + "." * dots
        _draw_centered(screen, font_hint, wait_str, cy + 105, (130, 130, 130))

        draw_button(screen, btn_cancel, "Annuler")
        pygame.display.flip()


# ---------------------------------------------------------------------------
# Écran "Rejoindre"
# ---------------------------------------------------------------------------

def _join_screen(screen):
    """Affiche un champ de saisie (code OU IP).
    Retourne le GameClient connecté, ou None si annulé."""
    clock      = pygame.time.Clock()
    font_big   = pygame.font.SysFont(None, 72)
    font_med   = pygame.font.SysFont(None, 38)
    font_small = pygame.font.SysFont(None, 28)
    font_hint  = pygame.font.SysFont(None, 24)

    sw, sh = screen.get_size()
    cy     = sh // 2

    user_input   = ""   # code (3 chiffres) OU IP complète
    status_msg   = ""
    status_color = (255, 80, 80)

    btn_connect = pygame.Rect(sw // 2 - 105, cy + 110, 200, 50)
    btn_cancel  = pygame.Rect(sw // 2 - 105, cy + 175, 200, 50)

    # État de la tentative de connexion async
    connecting    = [False]
    result_box    = [None]   # GameClient ou None
    error_box     = [""]

    def _do_connect(inp):
        connecting[0] = True
        ip = resolve_host(inp)
        if ip is None:
            error_box[0] = (
                f"Entrée invalide : \"{inp}\"\n"
                "Entrez un code à 3 chiffres (ex: 047) ou une IP (ex: 192.168.1.47)"
            )
            result_box[0] = None
            connecting[0] = False
            return
        client = GameClient()
        ok = client.connect(ip, timeout=5)
        if ok:
            result_box[0] = client
        else:
            error_box[0] = client.last_error
            result_box[0] = None
        connecting[0] = False

    while True:
        clock.tick(60)

        # Connexion en cours → spinner bloquant
        if connecting[0]:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            screen.fill((15, 10, 25))
            _draw_centered(screen, font_med, "Connexion en cours…", cy - 20, (200, 180, 255))
            ip_preview = resolve_host(user_input) or user_input
            _draw_centered(screen, font_small, ip_preview, cy + 20, (160, 200, 255))
            pygame.display.flip()
            continue

        # Résultat disponible ?
        if result_box[0] is not None:
            return result_box[0]
        if error_box[0]:
            status_msg   = error_box[0]
            status_color = (255, 80, 80)
            error_box[0] = ""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                    status_msg = ""
                elif event.key == pygame.K_RETURN:
                    if user_input:
                        status_msg = ""
                        t = threading.Thread(target=_do_connect, args=(user_input,), daemon=True)
                        t.start()
                elif event.unicode and len(user_input) < 15:
                    c = event.unicode
                    # N'accepte que chiffres et points (pour IP ou code)
                    if c.isdigit() or c == '.':
                        user_input += c
                        status_msg = ""

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_connect.collidepoint(event.pos) and user_input:
                    status_msg = ""
                    t = threading.Thread(target=_do_connect, args=(user_input,), daemon=True)
                    t.start()
                if btn_cancel.collidepoint(event.pos):
                    return None

        screen.fill((15, 10, 25))

        _draw_centered(screen, font_med, "REJOINDRE UNE PARTIE", cy - 130, (200, 180, 255))

        _draw_centered(screen, font_small, "Code (3 chiffres) ou IP complète :", cy - 75, (180, 180, 180))
        _draw_centered(screen, font_hint,  "Exemple :  047   ou   192.168.1.47",  cy - 50, (110, 110, 130))

        # Champ de saisie
        display   = user_input if user_input else "___"
        field_col = (255, 220, 50) if user_input else (100, 100, 80)
        field_surf = font_big.render(display, True, field_col)
        screen.blit(field_surf, field_surf.get_rect(center=(sw // 2, cy + 5)))

        # Prévisualisation de l'IP résolue
        if user_input:
            preview_ip = resolve_host(user_input)
            if preview_ip and '.' in user_input:
                pass  # IP directe, pas de prévisualisation nécessaire
            elif preview_ip:
                prev_surf = font_hint.render(f"→ {preview_ip}", True, (100, 200, 100))
                screen.blit(prev_surf, prev_surf.get_rect(center=(sw // 2, cy + 50)))
            else:
                prev_surf = font_hint.render("Entrée invalide", True, (200, 100, 100))
                screen.blit(prev_surf, prev_surf.get_rect(center=(sw // 2, cy + 50)))

        # Message de statut (erreur)
        if status_msg:
            # Affiche sur 2 lignes si besoin (le message peut contenir \n)
            lines = status_msg.split('\n')
            for i, line in enumerate(lines[:2]):
                s = font_hint.render(line, True, status_color)
                screen.blit(s, s.get_rect(center=(sw // 2, cy + 72 + i * 20)))

        draw_button(screen, btn_connect, "Connexion")
        draw_button(screen, btn_cancel,  "Annuler")

        pygame.display.flip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_centered(surface, font, text, cy, color):
    surf = font.render(text, True, color)
    surface.blit(surf, surf.get_rect(center=(surface.get_width() // 2, cy)))


def _show_error(screen, message):
    """Affiche un message d'erreur plein écran pendant 4 secondes."""
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont(None, 30)
    start  = pygame.time.get_ticks()
    lines  = message.split('\n')
    while pygame.time.get_ticks() - start < 4000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        screen.fill((40, 0, 0))
        cy = screen.get_height() // 2 - (len(lines) - 1) * 18
        for i, line in enumerate(lines):
            s = font.render(line, True, (255, 120, 120))
            screen.blit(s, s.get_rect(center=(screen.get_width() // 2, cy + i * 36)))
        pygame.display.flip()
        clock.tick(60)
