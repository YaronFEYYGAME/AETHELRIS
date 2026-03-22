"""
Écran de sélection de personnage pour le multijoueur.
Affiche les 5 personnages avec synchronisation réseau en temps réel.
"""
import pygame
from characters import CHARACTER_DEFS, get_all_character_types


def _load_preview(char_type, size=96):
    """Charge la première frame idle d'un personnage en guise de preview."""
    char_def = CHARACTER_DEFS[char_type]
    path, num_frames = char_def['animations']['idle']
    try:
        sheet = pygame.image.load(path).convert_alpha()
        fw = sheet.get_width() // num_frames
        fh = sheet.get_height()
        frame = sheet.subsurface((0, 0, fw, fh))
        frame = pygame.transform.scale(frame, (size, size))
        return frame
    except FileNotFoundError:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((80, 80, 80))
        return surf


def character_select_screen_host(screen, server):
    """Écran de sélection pour l'hôte. Retourne (host_char, client_char) ou None."""
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()
    font = pygame.font.SysFont(None, 30)
    font_big = pygame.font.SysFont(None, 40)
    font_small = pygame.font.SysFont(None, 24)

    char_types = get_all_character_types()
    previews = {ct: _load_preview(ct) for ct in char_types}

    # Disposition : 5 carrés en ligne
    card_size = 140
    gap = 20
    total_w = len(char_types) * card_size + (len(char_types) - 1) * gap
    start_x = (sw - total_w) // 2
    start_y = (sh - card_size) // 2 - 30

    cards = []
    for i, ct in enumerate(char_types):
        x = start_x + i * (card_size + gap)
        cards.append({'type': ct, 'rect': pygame.Rect(x, start_y, card_size, card_size)})

    host_choice = None
    client_choice = None
    hover_idx = -1

    while True:
        if not server.connected:
            return None

        # Récupérer le choix du client
        inputs = server.get_inputs()
        if inputs.get('char_select'):
            client_choice = inputs['char_select']

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                server.stop()
                pygame.quit()
                import sys; sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

            if event.type == pygame.MOUSEMOTION:
                hover_idx = -1
                for i, card in enumerate(cards):
                    if card['rect'].collidepoint(event.pos):
                        hover_idx = i

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, card in enumerate(cards):
                    if card['rect'].collidepoint(event.pos):
                        ct = card['type']
                        # Ne pas choisir le même que le client
                        if ct != client_choice:
                            host_choice = ct

        # Envoyer l'état de sélection au client
        select_state = {
            'char_select_state': {
                'host_choice': host_choice,
                'client_choice': client_choice,
                'confirmed': host_choice is not None and client_choice is not None,
            }
        }
        server.send_state(select_state)

        # Les deux ont choisi → lancer la partie
        if host_choice and client_choice and host_choice != client_choice:
            # Petit délai pour que le client reçoive la confirmation
            pygame.time.delay(300)
            select_state['char_select_state']['confirmed'] = True
            server.send_state(select_state)
            return (host_choice, client_choice)

        # --- Rendu ---
        screen.fill((15, 10, 25))

        # Titre
        title = font_big.render("CHOISISSEZ VOTRE PERSONNAGE", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(sw // 2, start_y - 60)))

        for i, card in enumerate(cards):
            ct = card['type']
            r = card['rect']
            char_def = CHARACTER_DEFS[ct]

            # Fond de la carte
            bg_color = (40, 40, 50)
            border_color = (100, 100, 120)

            is_taken_by_client = (ct == client_choice)
            is_selected_by_host = (ct == host_choice)

            if is_selected_by_host:
                bg_color = (30, 60, 30)
                border_color = (80, 200, 80)
            elif is_taken_by_client:
                bg_color = (80, 20, 20)
                border_color = (200, 60, 60)
            elif i == hover_idx and not is_taken_by_client:
                bg_color = (50, 40, 70)
                border_color = (150, 120, 200)

            # Dessiner la carte avec bords arrondis
            card_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, bg_color, (0, 0, r.width, r.height), border_radius=12)
            screen.blit(card_surf, r.topleft)
            pygame.draw.rect(screen, border_color, r, 3, border_radius=12)

            # Nom du personnage
            name = font.render(char_def['name'], True, (255, 255, 255))
            screen.blit(name, name.get_rect(center=(r.centerx, r.top + 18)))

            # Preview du sprite
            preview = previews[ct]
            preview_rect = preview.get_rect(center=(r.centerx, r.centery + 12))
            screen.blit(preview, preview_rect)

            # Marqueur si pris par le client
            if is_taken_by_client:
                taken_surf = pygame.Surface((r.width - 6, r.height - 6), pygame.SRCALPHA)
                taken_surf.fill((200, 30, 30, 100))
                screen.blit(taken_surf, (r.x + 3, r.y + 3))
                taken_text = font_small.render("Personnage", True, (255, 200, 200))
                taken_text2 = font_small.render("déjà pris", True, (255, 200, 200))
                screen.blit(taken_text, taken_text.get_rect(center=(r.centerx, r.centery - 5)))
                screen.blit(taken_text2, taken_text2.get_rect(center=(r.centerx, r.centery + 15)))

        # Instructions
        if host_choice:
            status = f"Votre choix : {CHARACTER_DEFS[host_choice]['name']}"
            if not client_choice:
                status += " — En attente de l'autre joueur..."
            status_color = (100, 255, 100)
        else:
            status = "Cliquez sur un personnage pour le sélectionner"
            status_color = (200, 200, 200)

        status_surf = font.render(status, True, status_color)
        screen.blit(status_surf, status_surf.get_rect(center=(sw // 2, start_y + card_size + 40)))

        pygame.display.flip()
        clock.tick(60)


def character_select_screen_client(screen, client):
    """Écran de sélection pour le client. Retourne (host_char, client_char) ou None."""
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()
    font = pygame.font.SysFont(None, 30)
    font_big = pygame.font.SysFont(None, 40)
    font_small = pygame.font.SysFont(None, 24)

    char_types = get_all_character_types()
    previews = {ct: _load_preview(ct) for ct in char_types}

    card_size = 140
    gap = 20
    total_w = len(char_types) * card_size + (len(char_types) - 1) * gap
    start_x = (sw - total_w) // 2
    start_y = (sh - card_size) // 2 - 30

    cards = []
    for i, ct in enumerate(char_types):
        x = start_x + i * (card_size + gap)
        cards.append({'type': ct, 'rect': pygame.Rect(x, start_y, card_size, card_size)})

    client_choice = None
    host_choice = None
    hover_idx = -1

    while True:
        if not client.connected:
            return None

        # Récupérer l'état depuis le serveur
        state = client.get_state()
        if state and 'char_select_state' in state:
            css = state['char_select_state']
            host_choice = css.get('host_choice')
            # Si confirmé par le serveur, la partie est prête
            if css.get('confirmed') and host_choice and client_choice:
                return (host_choice, client_choice)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.stop()
                pygame.quit()
                import sys; sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

            if event.type == pygame.MOUSEMOTION:
                hover_idx = -1
                for i, card in enumerate(cards):
                    if card['rect'].collidepoint(event.pos):
                        hover_idx = i

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, card in enumerate(cards):
                    if card['rect'].collidepoint(event.pos):
                        ct = card['type']
                        if ct != host_choice:
                            client_choice = ct
                            # Envoyer le choix au serveur via les inputs
                            client.send_inputs({'char_select': ct})

        # --- Rendu ---
        screen.fill((15, 10, 25))

        title = font_big.render("CHOISISSEZ VOTRE PERSONNAGE", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(sw // 2, start_y - 60)))

        for i, card in enumerate(cards):
            ct = card['type']
            r = card['rect']
            char_def = CHARACTER_DEFS[ct]

            bg_color = (40, 40, 50)
            border_color = (100, 100, 120)

            is_taken_by_host = (ct == host_choice)
            is_selected_by_client = (ct == client_choice)

            if is_selected_by_client:
                bg_color = (30, 60, 30)
                border_color = (80, 200, 80)
            elif is_taken_by_host:
                bg_color = (80, 20, 20)
                border_color = (200, 60, 60)
            elif i == hover_idx and not is_taken_by_host:
                bg_color = (50, 40, 70)
                border_color = (150, 120, 200)

            card_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, bg_color, (0, 0, r.width, r.height), border_radius=12)
            screen.blit(card_surf, r.topleft)
            pygame.draw.rect(screen, border_color, r, 3, border_radius=12)

            name = font.render(char_def['name'], True, (255, 255, 255))
            screen.blit(name, name.get_rect(center=(r.centerx, r.top + 18)))

            preview = previews[ct]
            preview_rect = preview.get_rect(center=(r.centerx, r.centery + 12))
            screen.blit(preview, preview_rect)

            if is_taken_by_host:
                taken_surf = pygame.Surface((r.width - 6, r.height - 6), pygame.SRCALPHA)
                taken_surf.fill((200, 30, 30, 100))
                screen.blit(taken_surf, (r.x + 3, r.y + 3))
                taken_text = font_small.render("Personnage", True, (255, 200, 200))
                taken_text2 = font_small.render("déjà pris", True, (255, 200, 200))
                screen.blit(taken_text, taken_text.get_rect(center=(r.centerx, r.centery - 5)))
                screen.blit(taken_text2, taken_text2.get_rect(center=(r.centerx, r.centery + 15)))

        if client_choice:
            status = f"Votre choix : {CHARACTER_DEFS[client_choice]['name']}"
            if not host_choice:
                status += " — En attente de l'autre joueur..."
            status_color = (100, 255, 100)
        else:
            status = "Cliquez sur un personnage pour le sélectionner"
            status_color = (200, 200, 200)

        status_surf = font.render(status, True, status_color)
        screen.blit(status_surf, status_surf.get_rect(center=(sw // 2, start_y + card_size + 40)))

        pygame.display.flip()
        clock.tick(60)
