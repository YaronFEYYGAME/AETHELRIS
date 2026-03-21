import pygame
import pytmx
import pyscroll
import random

from player import Player, RemotePlayer
from sound import SoundManager
from enemy import Enemy, BigEnemy, Necromancer, Spirit, RemoteEnemy
from ui import UI
from item import Item
from projectile import Projectile
from obstacle import Rock, RockParticle, BloodParticle, SmokeParticle, DarkParticle

# Fonction utilitaire pour dessiner les hitboxes par-dessus le zoom de la caméra
def draw_debug_rect(screen, world_rect, color, camera_x, camera_y, zoom, screen_width, screen_height):
    if not world_rect: return
    screen_x = (world_rect.x - camera_x) * zoom + screen_width / 2
    screen_y = (world_rect.y - camera_y) * zoom + screen_height / 2
    screen_w = world_rect.width * zoom
    screen_h = world_rect.height * zoom
    pygame.draw.rect(screen, color, (screen_x, screen_y, screen_w, screen_h), 2)

def run_game(screen, start_music_vol=0.5, start_sfx_vol=0.8):
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    ui = UI(screen)
    sound_manager = SoundManager()
    font = pygame.font.SysFont(None, 60)
    
    death_font = pygame.font.SysFont("old english text mt, garamond, times new roman, serif", 120) 
    
    levels = ["assets/maps/test_map.tmx", "assets/maps/map1.tmx"] 
    current_level_index = 0
    
    player_inventory = {'melee': False, 'ranged': False, 'pickaxe': False, 'boots': False, 'current': None, 'arrows': 0}
    player_health = 100
    
    global_music_vol = start_music_vol
    global_sfx_vol = start_sfx_vol
    is_paused = False
    pause_rects = {}
    
    # --- TOGGLE DEBUG DES HITBOXES ---
    DEBUG_HITBOXES = True # Passe-le à False pour cacher les rectangles colorés !

    sound_manager.update_sfx_volume(global_sfx_vol)
    pygame.mixer.music.set_volume(global_music_vol)

    while current_level_index < len(levels):
        try:
            tmx_data = pytmx.util_pygame.load_pygame(levels[current_level_index])
        except Exception as e:
            print(f"Erreur de chargement de la carte {levels[current_level_index]}: {e}")
            return 

        map_data = pyscroll.data.TiledMapData(tmx_data)
        map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
        
        zoom_level = 3.8 
        map_layer.zoom = zoom_level

        group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=1)
        projectiles_group = pygame.sprite.Group()
        enemies_group = pygame.sprite.Group()
        items_group = pygame.sprite.Group() 
        rocks_group = pygame.sprite.Group() 
        particles_group = pygame.sprite.Group() 
        
        walls = []
        exit_zones = [] 
        player_x, player_y = 100, 100 
        
        for obj in tmx_data.objects:
            obj_type = obj.type.lower() if obj.type else ""
            
            if obj_type == "collision":
                walls.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "exit": 
                exit_zones.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "player":
                player_x = obj.x
                player_y = obj.y
            elif obj_type == "enemy":
                new_enemy = Enemy(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
            elif obj_type == "bigenemy":
                new_enemy = BigEnemy(obj.x, obj.y)
                if hasattr(new_enemy, 'update_volumes'):
                    new_enemy.update_volumes(global_music_vol, global_sfx_vol)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
            elif obj_type == "necromancer":
                new_enemy = Necromancer(obj.x, obj.y)
                if hasattr(new_enemy, 'update_volumes'):
                    new_enemy.update_volumes(global_music_vol, global_sfx_vol)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
            elif obj_type == "item_melee":
                new_item = Item(obj.x, obj.y, 'melee')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "item_ranged":
                new_item = Item(obj.x, obj.y, 'ranged')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "item_pickaxe":
                new_item = Item(obj.x, obj.y, 'pickaxe')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "item_arrow": 
                new_item = Item(obj.x, obj.y, 'arrow')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "item_apple":
                new_item = Item(obj.x, obj.y, 'apple')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "item_boots":
                new_item = Item(obj.x, obj.y, 'boots')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "obstacle_rock":
                new_rock = Rock(obj.x, obj.y)
                group.add(new_rock)
                rocks_group.add(new_rock)
                walls.append(new_rock.hitbox)

        player = Player(player_x, player_y)
        player.has_melee = player_inventory['melee']
        player.has_ranged = player_inventory['ranged']
        player.has_pickaxe = player_inventory['pickaxe']
        player.has_boots = player_inventory['boots']
        player.current_weapon = player_inventory['current']
        player.arrows = player_inventory['arrows'] 
        player.health = player_health
        
        group.add(player)
        
        show_mmo = False
        level_running = True
        was_walking = False
        death_time = None 
        death_sound_played = False 

        EUREKA_EVENT = pygame.USEREVENT + 1

        map_pixel_width = tmx_data.width * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        while level_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == EUREKA_EVENT:
                    if not is_paused: 
                        sound_manager.play_eureka()
                        
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if is_paused and pause_rects:
                        pos = event.pos
                        if pause_rects.get("mus_min") and pause_rects["mus_min"].collidepoint(pos):
                            global_music_vol = max(0.0, global_music_vol - 0.1)
                            pygame.mixer.music.set_volume(global_music_vol)
                        elif pause_rects.get("mus_pl") and pause_rects["mus_pl"].collidepoint(pos):
                            global_music_vol = min(1.0, global_music_vol + 0.1)
                            pygame.mixer.music.set_volume(global_music_vol)
                        elif pause_rects.get("sfx_min") and pause_rects["sfx_min"].collidepoint(pos):
                            global_sfx_vol = max(0.0, global_sfx_vol - 0.1)
                            sound_manager.update_sfx_volume(global_sfx_vol)
                            for enemy in enemies_group:
                                if hasattr(enemy, 'update_volumes'):
                                    enemy.update_volumes(global_music_vol, global_sfx_vol)
                        elif pause_rects.get("sfx_pl") and pause_rects["sfx_pl"].collidepoint(pos):
                            global_sfx_vol = min(1.0, global_sfx_vol + 0.1)
                            sound_manager.update_sfx_volume(global_sfx_vol)
                            for enemy in enemies_group:
                                if hasattr(enemy, 'update_volumes'):
                                    enemy.update_volumes(global_music_vol, global_sfx_vol)
                        elif "resume" in pause_rects and pause_rects["resume"].collidepoint(pos):
                            is_paused = False
                        elif pause_rects.get("quit") and pause_rects["quit"].collidepoint(pos):
                            return
                            
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: 
                        is_paused = not is_paused 
                        continue
                    
                    if not is_paused:
                        if event.key == pygame.K_j:
                            sound_manager.play_mmo_sound()
                            show_mmo = True
                            
                        if player.health > 0:
                            if event.key == pygame.K_1: 
                                if player.has_melee and player.current_weapon != 'melee':
                                    player.switch_weapon('melee')
                                    sound_manager.play_equip_sword()
                                    
                            if event.key == pygame.K_2: 
                                if player.has_ranged and player.current_weapon != 'ranged':
                                    player.switch_weapon('ranged')
                                    sound_manager.play_equip_bow()
                                    
                            if event.key == pygame.K_a and can_exit:
                                player_inventory['melee'] = player.has_melee
                                player_inventory['ranged'] = player.has_ranged
                                player_inventory['pickaxe'] = player.has_pickaxe
                                player_inventory['boots'] = player.has_boots
                                player_inventory['current'] = player.current_weapon
                                player_inventory['arrows'] = player.arrows 
                                player_health = player.health
                                
                                current_level_index += 1
                                level_running = False 
                                break
                                
                            if event.key == pygame.K_LSHIFT:
                                if player.has_boots:
                                    if player.dash(walls):
                                        sound_manager.play_dash_sound()
                                        for _ in range(20):
                                            offset_x = random.randint(-15, 15)
                                            offset_y = random.randint(-15, 5) 
                                            smoke = SmokeParticle(player.feet.centerx + offset_x, player.feet.bottom + offset_y)
                                            group.add(smoke)
                                            particles_group.add(smoke)
                                
                            if event.key == pygame.K_f:
                                for item in items_group:
                                    if player.feet.colliderect(item.rect):
                                        if item.item_type == 'melee':
                                            player.has_melee = True
                                            if player.current_weapon != 'melee':
                                                player.current_weapon = 'melee'
                                                sound_manager.play_equip_sword()
                                        elif item.item_type == 'ranged':
                                            if not player.has_ranged:
                                                player.arrows += 10
                                            player.has_ranged = True
                                            if player.current_weapon != 'ranged':
                                                player.current_weapon = 'ranged'
                                                sound_manager.play_equip_bow()
                                        elif item.item_type == 'pickaxe':
                                            player.has_pickaxe = True
                                        elif item.item_type == 'arrow':
                                            nb_arrows = random.randint(1, 4)
                                            player.arrows += nb_arrows
                                            sound_manager.play_equip_bow() 
                                        elif item.item_type == 'apple':
                                            heal_amount = player.max_health * 0.10
                                            player.heal(heal_amount)
                                            sound_manager.play_eating()
                                        elif item.item_type == 'boots':
                                            player.has_boots = True
                                            sound_manager.play_equipement() 
                                        
                                        item.kill() 
                                        break 
                                        
                                if player.has_pickaxe:
                                    for rock in rocks_group:
                                        detect_zone = rock.hitbox.inflate(40, 40)
                                        if player.feet.colliderect(detect_zone):
                                            for _ in range(15):
                                                particle = RockParticle(rock.rect.centerx, rock.rect.centery)
                                                group.add(particle)
                                                particles_group.add(particle)
                                            
                                            rock.kill() 
                                            if rock.hitbox in walls:
                                                walls.remove(rock.hitbox) 
                                            
                                            player.has_pickaxe = False 
                                            sound_manager.play_rock_broke()
                                            pygame.time.set_timer(EUREKA_EVENT, 250, 1)
                                            break

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_j: show_mmo = False

            if not level_running:
                continue 

            if is_paused:
                group.draw(screen)
                ui.draw_health_bar(player.health, player.max_health)
                ui.draw_weapon_icon(player.current_weapon)
                ui.draw_pickaxe_icon(player.has_pickaxe)
                ui.draw_ammo_count(player.current_weapon, player.arrows)
                
                cooldown_ratio = (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown
                cooldown_ratio = min(1.0, max(0.0, cooldown_ratio))
                ui.draw_boots_icon(player.has_boots, cooldown_ratio)
                
                for enemy in enemies_group:
                    if getattr(enemy, 'has_aggro', False) and getattr(enemy, 'health', 0) > 0:
                        if isinstance(enemy, BigEnemy):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Gardien des profondeurs")
                        elif isinstance(enemy, Necromancer):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "La Faucheuse")
                
                pause_rects = ui.draw_pause_menu(global_music_vol, global_sfx_vol)
                pygame.display.flip()
                clock.tick(60)
                continue 

            player.update()
            player.move(walls)
            
            for enemy in enemies_group:
                enemy.update(player, walls)
                
                if hasattr(enemy, 'pending_summons') and enemy.pending_summons:
                    for sx, sy in enemy.pending_summons:
                        new_spirit = Spirit(sx, sy)
                        group.add(new_spirit)
                        enemies_group.add(new_spirit)
                    enemy.pending_summons.clear()
                
            projectiles_group.update()
            particles_group.update()

            show_rock_dialogue = False
            if not player.has_pickaxe and player.health > 0:
                for rock in rocks_group:
                    detect_zone = rock.hitbox.inflate(40, 40)
                    if player.feet.colliderect(detect_zone):
                        show_rock_dialogue = True
                        break
                        
            can_exit = False
            show_exit_dialogue = False
            if player.health > 0:
                for zone in exit_zones:
                    if player.feet.colliderect(zone):
                        can_exit = True
                        show_exit_dialogue = True
                        break

            keys = pygame.key.get_pressed()
            if keys[pygame.K_e] and player.current_weapon is not None and player.health > 0:
                attack_result = player.attack()
                if attack_result:
                    type_attack, data = attack_result
                    if type_attack == 'melee':
                        sound_manager.play_sword_sound()
                        for enemy in enemies_group:
                            if getattr(enemy, 'health', 0) > 0 and data.colliderect(enemy.feet):
                                enemy.damage(player.melee_damage)
                                
                                if hasattr(enemy, 'pending_drop') and enemy.pending_drop:
                                    drop = Item(enemy.rect.centerx, enemy.rect.centery, enemy.pending_drop)
                                    group.add(drop)
                                    items_group.add(drop)
                                    enemy.pending_drop = None
                                
                                if enemy.health <= 0:
                                    # --- PARTICULES SOMBRES POUR LES MAGIENS, SANG POUR LE RESTE ---
                                    ParticleClass = DarkParticle if isinstance(enemy, (Necromancer, Spirit)) else BloodParticle
                                    for _ in range(20):
                                        particle = ParticleClass(enemy.rect.centerx, enemy.rect.centery)
                                        group.add(particle)
                                        particles_group.add(particle)
                                
            new_projectile = player.check_ranged_attack()
            if new_projectile:
                group.add(new_projectile)
                projectiles_group.add(new_projectile)

            for projectile in projectiles_group:
                for enemy in enemies_group:
                    if getattr(enemy, 'health', 0) > 0: 
                        body_hitbox = enemy.feet.copy()
                        body_hitbox.height += 25  
                        body_hitbox.y -= 25       
                        if projectile.hitbox.colliderect(body_hitbox):
                            sound_manager.play_projectile_sound()
                            enemy.damage(projectile.damage_amount)
                            
                            if hasattr(enemy, 'pending_drop') and enemy.pending_drop:
                                drop = Item(enemy.rect.centerx, enemy.rect.centery, enemy.pending_drop)
                                group.add(drop)
                                items_group.add(drop)
                                enemy.pending_drop = None
                                
                            if enemy.health <= 0:
                                # --- PARTICULES SOMBRES ICI AUSSI ---
                                ParticleClass = DarkParticle if isinstance(enemy, (Necromancer, Spirit)) else BloodParticle
                                for _ in range(20):
                                    particle = ParticleClass(enemy.rect.centerx, enemy.rect.centery)
                                    group.add(particle)
                                    particles_group.add(particle)
                                    
                            projectile.kill() 
                            break 
                            
                if projectile.alive():
                    for wall in walls:
                        if projectile.hitbox.colliderect(wall):
                            sound_manager.play_projectile_sound()
                            projectile.kill()
                            break 

            if player.is_moving() and not was_walking:
                sound_manager.play_step()
                was_walking = True
            elif not player.is_moving() and was_walking:
                sound_manager.stop_step()
                was_walking = False

            view_w = screen_width / zoom_level
            view_h = screen_height / zoom_level
            
            camera_x = player.feet.centerx
            camera_y = player.feet.centery - 30

            if map_pixel_width < view_w: camera_x = map_pixel_width // 2
            else: camera_x = max(view_w // 2, min(camera_x, map_pixel_width - view_w // 2))

            if map_pixel_height < view_h: camera_y = map_pixel_height // 2
            else: camera_y = max(view_h // 2, min(camera_y, map_pixel_height - view_h // 2))

            group.center((camera_x, camera_y))

            group.draw(screen)
            
            # =================================================================
            # --- DEBUG HITBOXES (POUR RÉGLER TES COLLISIONS) ---
            # =================================================================
            if DEBUG_HITBOXES:
                # Joueur (Vert)
                draw_debug_rect(screen, player.feet, (0, 255, 0), camera_x, camera_y, zoom_level, screen_width, screen_height)
                # Attaque du joueur (Jaune)
                if player.is_attacking and player.current_weapon == 'melee':
                    attack_rect = pygame.Rect(0, 0, 70, 70)
                    attack_rect.center = player.feet.center
                    draw_debug_rect(screen, attack_rect, (255, 255, 0), camera_x, camera_y, zoom_level, screen_width, screen_height)
                
                # Ennemis (Rouge) & leurs attaques (Orange)
                for enemy in enemies_group:
                    if hasattr(enemy, 'feet'):
                        draw_debug_rect(screen, enemy.feet, (255, 0, 0), camera_x, camera_y, zoom_level, screen_width, screen_height)
                    if getattr(enemy, 'is_attacking', False) and hasattr(enemy, 'get_attack_hitbox'):
                        draw_debug_rect(screen, enemy.get_attack_hitbox(), (255, 165, 0), camera_x, camera_y, zoom_level, screen_width, screen_height)
                
                # Projectiles (Bleu)
                for proj in projectiles_group:
                    if hasattr(proj, 'hitbox'):
                        draw_debug_rect(screen, proj.hitbox, (0, 0, 255), camera_x, camera_y, zoom_level, screen_width, screen_height)
                        
                # Obstacles / Rochers (Cyan)
                for rock in rocks_group:
                    if hasattr(rock, 'hitbox'):
                        draw_debug_rect(screen, rock.hitbox, (0, 255, 255), camera_x, camera_y, zoom_level, screen_width, screen_height)
            # =================================================================
            
            ui.draw_health_bar(player.health, player.max_health)
            ui.draw_weapon_icon(player.current_weapon)
            ui.draw_pickaxe_icon(player.has_pickaxe)
            ui.draw_ammo_count(player.current_weapon, player.arrows)
            
            cooldown_ratio = (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown
            cooldown_ratio = min(1.0, max(0.0, cooldown_ratio))
            ui.draw_boots_icon(player.has_boots, cooldown_ratio)
            
            for enemy in enemies_group:
                if getattr(enemy, 'has_aggro', False) and getattr(enemy, 'health', 0) > 0:
                    if isinstance(enemy, BigEnemy):
                        ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Gardien des profondeurs")
                    elif isinstance(enemy, Necromancer):
                        ui.draw_boss_health_bar(enemy.health, enemy.max_health, "La Faucheuse")

            if show_exit_dialogue:
                ui.draw_dialogue("Voulez vous rentrer ? (A)")
            elif show_rock_dialogue:
                ui.draw_dialogue("Le chemin semble bloqué...")

            if show_mmo:
                text = font.render("MENU", True, (255, 255, 255))
                screen.blit(text, (20, 20))

            if player.health <= 0:
                if death_time is None:
                    death_time = pygame.time.get_ticks() 
                
                time_since_death = pygame.time.get_ticks() - death_time
                
                if time_since_death > 1000:
                    if not death_sound_played:
                        sound_manager.play_death()
                        death_sound_played = True

                    fade_duration = 2000.0 
                    fade_progress = (time_since_death - 1000) / fade_duration
                    if fade_progress > 1.0:
                        fade_progress = 1.0

                    bg_alpha = int(200 * fade_progress)
                    red_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    red_surface.fill((100, 0, 0, bg_alpha)) 
                    screen.blit(red_surface, (0, 0))
                    
                    text_alpha = int(255 * fade_progress)
                    death_text = death_font.render("Vous êtes mort", True, (255, 255, 255))
                    death_text.set_alpha(text_alpha) 
                    death_rect = death_text.get_rect(center=(screen_width // 2, screen_height // 2))
                    screen.blit(death_text, death_rect)
                    
                if time_since_death > 5000:
                    return 

            pygame.display.flip()
            clock.tick(60)

    print("Félicitations, vous avez terminé toutes les zones !")


# =============================================================================
# UTILITAIRES MULTIJOUEUR
# =============================================================================

def _serialize_player(p):
    dash_cr = min(1.0, max(0.0,
        (pygame.time.get_ticks() - p.last_dash_time) / p.dash_cooldown
    ))
    return {
        'x': p.feet.centerx,
        'y': p.feet.bottom,
        'state': p.state,
        'direction': p.facing,
        'frame': p.frame_index,
        'health': p.health,
        'max_health': p.max_health,
        # Inventaire pour le HUD côté client
        'current_weapon': p.current_weapon,
        'has_melee':      p.has_melee,
        'has_ranged':     p.has_ranged,
        'has_pickaxe':    p.has_pickaxe,
        'has_boots':      p.has_boots,
        'arrows':         p.arrows,
        'dash_cr':        dash_cr,
    }


def _serialize_enemy(e):
    if isinstance(e, Necromancer):
        etype = 'necromancer'
    elif isinstance(e, BigEnemy):
        etype = 'bigenemy'
    elif isinstance(e, Spirit):
        etype = 'spirit'
    else:
        etype = 'enemy'
    health = getattr(e, 'health', 1)
    return {
        'id':        getattr(e, '_mp_id', id(e)),
        'x':         getattr(e.feet, 'centerx', 0) if hasattr(e, 'feet') else 0,
        'y':         getattr(e.feet, 'bottom',  0) if hasattr(e, 'feet') else 0,
        'state':     getattr(e, 'state',       'idle'),
        'direction': getattr(e, 'facing',      'right'),
        'frame':     getattr(e, 'frame_index', 0),
        'health':    health,
        'max_health': getattr(e, 'max_health', health),
        'etype':     etype,
        'has_aggro': getattr(e, 'has_aggro', False),
    }


def _serialize_item(item):
    return {'x': item.rect.x, 'y': item.rect.y, 'type': item.item_type}


def _serialize_projectile(proj):
    return {
        'id':        getattr(proj, '_mp_id', id(proj)),
        'x':         proj.rect.centerx,
        'y':         proj.rect.centery,
        'direction': getattr(proj, 'direction', 'right'),
    }


def _load_level(level_path, screen_width, screen_height):
    """Charge une carte TMX et retourne (tmx_data, map_layer, group + entités)."""
    tmx_data = pytmx.util_pygame.load_pygame(level_path)
    map_data = pyscroll.data.TiledMapData(tmx_data)
    map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
    map_layer.zoom = 3.8
    return tmx_data, map_layer


# =============================================================================
# BOUCLE SERVEUR MULTIJOUEUR
# =============================================================================

def run_game_mp_server(screen, server, start_music_vol=0.5, start_sfx_vol=0.8):
    """Boucle de jeu côté serveur. Autoritaire sur la simulation."""
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    ui = UI(screen)
    sound_manager = SoundManager()

    levels = ["assets/maps/test_map.tmx", "assets/maps/map1.tmx"]
    current_level_index = 0

    player_inventory  = {'melee': False, 'ranged': False, 'pickaxe': False, 'boots': False, 'current': None, 'arrows': 0}
    player2_inventory = {'melee': False, 'ranged': False, 'pickaxe': False, 'boots': False, 'current': None, 'arrows': 0}
    player_health  = 100
    player2_health = 100

    global_music_vol = start_music_vol
    global_sfx_vol   = start_sfx_vol
    is_paused  = False
    pause_rects = {}
    zoom_level = 3.8
    DEBUG_HITBOXES = False

    sound_manager.update_sfx_volume(global_sfx_vol)
    pygame.mixer.music.set_volume(global_music_vol)

    _mp_id_counter = [0]

    def _next_id():
        _mp_id_counter[0] += 1
        return _mp_id_counter[0]

    font = pygame.font.SysFont(None, 36)

    while current_level_index < len(levels):
        if not server.connected:
            return

        try:
            tmx_data = pytmx.util_pygame.load_pygame(levels[current_level_index])
        except Exception as e:
            print(f"Erreur carte : {e}")
            return

        map_data  = pyscroll.data.TiledMapData(tmx_data)
        map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
        map_layer.zoom = zoom_level
        group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=1)

        projectiles_group = pygame.sprite.Group()
        enemies_group     = pygame.sprite.Group()
        items_group       = pygame.sprite.Group()
        rocks_group       = pygame.sprite.Group()
        particles_group   = pygame.sprite.Group()
        walls = []
        exit_zones = []
        player_x, player_y = 100, 100

        for obj in tmx_data.objects:
            obj_type = obj.type.lower() if obj.type else ""
            if obj_type == "collision":
                walls.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "exit":
                exit_zones.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "player":
                player_x, player_y = obj.x, obj.y
            elif obj_type == "enemy":
                e = Enemy(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
            elif obj_type == "bigenemy":
                e = BigEnemy(obj.x, obj.y); e._mp_id = _next_id()
                if hasattr(e, 'update_volumes'): e.update_volumes(global_music_vol, global_sfx_vol)
                group.add(e); enemies_group.add(e)
            elif obj_type == "necromancer":
                e = Necromancer(obj.x, obj.y); e._mp_id = _next_id()
                if hasattr(e, 'update_volumes'): e.update_volumes(global_music_vol, global_sfx_vol)
                group.add(e); enemies_group.add(e)
            elif obj_type == "item_melee":
                it = Item(obj.x, obj.y, 'melee'); group.add(it); items_group.add(it)
            elif obj_type == "item_ranged":
                it = Item(obj.x, obj.y, 'ranged'); group.add(it); items_group.add(it)
            elif obj_type == "item_pickaxe":
                it = Item(obj.x, obj.y, 'pickaxe'); group.add(it); items_group.add(it)
            elif obj_type == "item_arrow":
                it = Item(obj.x, obj.y, 'arrow'); group.add(it); items_group.add(it)
            elif obj_type == "item_apple":
                it = Item(obj.x, obj.y, 'apple'); group.add(it); items_group.add(it)
            elif obj_type == "item_boots":
                it = Item(obj.x, obj.y, 'boots'); group.add(it); items_group.add(it)
            elif obj_type == "obstacle_rock":
                r = Rock(obj.x, obj.y); group.add(r); rocks_group.add(r); walls.append(r.hitbox)

        # Joueur local (serveur)
        player = Player(player_x, player_y)
        player.has_melee   = player_inventory['melee']
        player.has_ranged  = player_inventory['ranged']
        player.has_pickaxe = player_inventory['pickaxe']
        player.has_boots   = player_inventory['boots']
        player.current_weapon = player_inventory['current']
        player.arrows = player_inventory['arrows']
        player.health = player_health
        group.add(player)

        # Joueur distant (client, piloté par inputs réseau)
        player2 = Player(player_x + 20, player_y)
        player2.has_melee   = player2_inventory['melee']
        player2.has_ranged  = player2_inventory['ranged']
        player2.has_pickaxe = player2_inventory['pickaxe']
        player2.has_boots   = player2_inventory['boots']
        player2.current_weapon = player2_inventory['current']
        player2.arrows = player2_inventory['arrows']
        player2.health = player2_health
        group.add(player2)

        map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        level_running  = True
        was_walking    = False
        death_time     = None
        death_sound_played = False
        both_dead_time = None
        can_exit       = False
        show_exit_dialogue = False

        death_font = pygame.font.SysFont("old english text mt, garamond, times new roman, serif", 120)
        EUREKA_EVENT = pygame.USEREVENT + 1

        while level_running:
            # --- Déconnexion client ---
            if not server.connected:
                _show_disconnected(screen)
                return

            dash_events  = []  # événements de dash à envoyer au client ce frame
            sound_events = []  # sons à jouer côté client ce frame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    server.stop()
                    return
                elif event.type == EUREKA_EVENT:
                    if not is_paused:
                        sound_manager.play_eureka()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if is_paused and pause_rects:
                        pos = event.pos
                        if pause_rects.get("mus_min") and pause_rects["mus_min"].collidepoint(pos):
                            global_music_vol = max(0.0, global_music_vol - 0.1)
                            pygame.mixer.music.set_volume(global_music_vol)
                        elif pause_rects.get("mus_pl") and pause_rects["mus_pl"].collidepoint(pos):
                            global_music_vol = min(1.0, global_music_vol + 0.1)
                            pygame.mixer.music.set_volume(global_music_vol)
                        elif pause_rects.get("sfx_min") and pause_rects["sfx_min"].collidepoint(pos):
                            global_sfx_vol = max(0.0, global_sfx_vol - 0.1)
                            sound_manager.update_sfx_volume(global_sfx_vol)
                        elif pause_rects.get("sfx_pl") and pause_rects["sfx_pl"].collidepoint(pos):
                            global_sfx_vol = min(1.0, global_sfx_vol + 0.1)
                            sound_manager.update_sfx_volume(global_sfx_vol)
                        elif "resume" in pause_rects and pause_rects["resume"].collidepoint(pos):
                            is_paused = False
                        elif pause_rects.get("quit") and pause_rects["quit"].collidepoint(pos):
                            server.stop()
                            return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        is_paused = not is_paused
                        continue
                    if not is_paused and player.health > 0:
                        if event.key == pygame.K_1 and player.has_melee and player.current_weapon != 'melee':
                            player.switch_weapon('melee'); sound_manager.play_equip_sword()
                        if event.key == pygame.K_2 and player.has_ranged and player.current_weapon != 'ranged':
                            player.switch_weapon('ranged'); sound_manager.play_equip_bow()
                        if event.key == pygame.K_a and can_exit:
                            player_inventory  = {'melee': player.has_melee, 'ranged': player.has_ranged,
                                                 'pickaxe': player.has_pickaxe, 'boots': player.has_boots,
                                                 'current': player.current_weapon, 'arrows': player.arrows}
                            player2_inventory = {'melee': player2.has_melee, 'ranged': player2.has_ranged,
                                                 'pickaxe': player2.has_pickaxe, 'boots': player2.has_boots,
                                                 'current': player2.current_weapon, 'arrows': player2.arrows}
                            player_health  = player.health
                            player2_health = player2.health
                            current_level_index += 1
                            level_running = False
                            break
                        if event.key == pygame.K_LSHIFT and player.has_boots:
                            if player.dash(walls):
                                sound_manager.play_dash_sound()
                                sound_events.append('dash')
                                dash_events.append({'player': 0, 'x': player.feet.centerx, 'y': player.feet.bottom})
                                for _ in range(20):
                                    smoke = SmokeParticle(player.feet.centerx + random.randint(-15, 15),
                                                         player.feet.bottom + random.randint(-15, 5))
                                    group.add(smoke); particles_group.add(smoke)
                        if event.key == pygame.K_f:
                            for item in list(items_group):
                                if player.feet.colliderect(item.rect):
                                    _pickup_item(player, item, sound_manager)
                                    item.kill(); break
                            if player.has_pickaxe:
                                for rock in list(rocks_group):
                                    if player.feet.colliderect(rock.hitbox.inflate(40, 40)):
                                        for _ in range(15):
                                            p = RockParticle(rock.rect.centerx, rock.rect.centery)
                                            group.add(p); particles_group.add(p)
                                        rock.kill()
                                        if rock.hitbox in walls: walls.remove(rock.hitbox)
                                        player.has_pickaxe = False
                                        sound_manager.play_rock_broke()
                                        pygame.time.set_timer(EUREKA_EVENT, 250, 1)
                                        break

            if not level_running:
                continue

            if is_paused:
                group.draw(screen)
                ui.draw_health_bar(player.health, player.max_health)
                pause_rects = ui.draw_pause_menu(global_music_vol, global_sfx_vol)
                pygame.display.flip()
                clock.tick(60)
                continue

            # --- Inputs réseau → player2 ---
            net_inputs = server.get_inputs()
            player2.apply_network_inputs(net_inputs)
            player2.animate()
            player2.move(walls)

            # Attaque player2
            if net_inputs.get('attack') and player2.current_weapon and player2.health > 0:
                res = player2.attack()
                if res:
                    typ, data = res
                    if typ == 'melee':
                        sound_manager.play_sword_sound()
                        # Ne pas envoyer 'sword' au client : il le joue déjà localement
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                e.damage(player2.melee_damage)
                                if e.health <= 0:
                                    sound_events.append('enemy_death')
                                _handle_enemy_death(e, group, items_group, particles_group)

            # Dash player2
            if net_inputs.get('dash') and player2.has_boots:
                if player2.dash(walls):
                    sound_manager.play_dash_sound()
                    sound_events.append('dash')
                    dash_events.append({'player': 1, 'x': player2.feet.centerx, 'y': player2.feet.bottom})
                    for _ in range(20):
                        smoke = SmokeParticle(player2.feet.centerx + random.randint(-15, 15),
                                             player2.feet.bottom + random.randint(-15, 5))
                        group.add(smoke); particles_group.add(smoke)

            # Ramasser objet player2
            if net_inputs.get('interact') and player2.health > 0:
                for item in list(items_group):
                    if player2.feet.colliderect(item.rect):
                        _pickup_item(player2, item, sound_manager)
                        item.kill(); break
                if player2.has_pickaxe:
                    for rock in list(rocks_group):
                        if player2.feet.colliderect(rock.hitbox.inflate(40, 40)):
                            for _ in range(15):
                                p = RockParticle(rock.rect.centerx, rock.rect.centery)
                                group.add(p); particles_group.add(p)
                            rock.kill()
                            if rock.hitbox in walls: walls.remove(rock.hitbox)
                            player2.has_pickaxe = False
                            sound_manager.play_rock_broke()
                            pygame.time.set_timer(EUREKA_EVENT, 250, 1)
                            break

            # Changement d'arme player2
            if net_inputs.get('weapon1') and player2.has_melee and player2.current_weapon != 'melee':
                player2.switch_weapon('melee'); sound_manager.play_equip_sword()
            if net_inputs.get('weapon2') and player2.has_ranged and player2.current_weapon != 'ranged':
                player2.switch_weapon('ranged'); sound_manager.play_equip_bow()

            # Attaque à distance player2
            new_proj2 = player2.check_ranged_attack()
            if new_proj2:
                new_proj2._mp_id = _next_id()
                group.add(new_proj2); projectiles_group.add(new_proj2)

            # --- Joueur local ---
            player.update()
            player.move(walls)

            # --- Ennemis ---
            for e in list(enemies_group):
                # Ciblage : seulement les joueurs vivants
                live = [p for p in [player, player2] if p.health > 0]
                if live:
                    target = min(live, key=lambda p: (
                        pygame.math.Vector2(p.feet.center) - pygame.math.Vector2(e.feet.center)
                    ).length())
                else:
                    target = player  # les deux morts, peu importe
                e.update(target, walls)
                # Dégâts sur le joueur non-ciblé (boss avec get_attack_hitbox), une fois par cooldown
                other = player2 if target is player else player
                if hasattr(e, 'get_attack_hitbox') and getattr(e, 'is_attacking', False) and other.health > 0:
                    atk = e.get_attack_hitbox()
                    now = pygame.time.get_ticks()
                    last_mp = getattr(e, '_mp_other_dmg_time', 0)
                    if atk and atk.colliderect(other.feet) and now - last_mp > getattr(e, 'attack_cooldown', 1500):
                        other.damage(getattr(e, 'damage_amount', 10))
                        e._mp_other_dmg_time = now
                if hasattr(e, 'pending_summons') and e.pending_summons:
                    for sx, sy in e.pending_summons:
                        ns = Spirit(sx, sy); ns._mp_id = _next_id()
                        group.add(ns); enemies_group.add(ns)
                    e.pending_summons.clear()
                # Collecter les sons des boss pour les envoyer au client
                if hasattr(e, 'pending_sounds') and e.pending_sounds:
                    sound_events.extend(e.pending_sounds)
                    e.pending_sounds.clear()

            projectiles_group.update()
            particles_group.update()

            # --- Attaque locale (serveur) ---
            keys = pygame.key.get_pressed()
            if keys[pygame.K_e] and player.current_weapon and player.health > 0:
                res = player.attack()
                if res:
                    typ, data = res
                    if typ == 'melee':
                        sound_manager.play_sword_sound()
                        sound_events.append('sword')
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                e.damage(player.melee_damage)
                                if e.health <= 0:
                                    sound_events.append('enemy_death')
                                _handle_enemy_death(e, group, items_group, particles_group)

            new_proj = player.check_ranged_attack()
            if new_proj:
                new_proj._mp_id = _next_id()
                group.add(new_proj); projectiles_group.add(new_proj)

            for proj in list(projectiles_group):
                for e in list(enemies_group):
                    if getattr(e, 'health', 0) > 0:
                        body = e.feet.copy(); body.height += 25; body.y -= 25
                        if proj.hitbox.colliderect(body):
                            sound_manager.play_projectile_sound()
                            sound_events.append('arrow')
                            e.damage(proj.damage_amount)
                            if e.health <= 0:
                                sound_events.append('enemy_death')
                            _handle_enemy_death(e, group, items_group, particles_group)
                            proj.kill(); break
                if proj.alive():
                    for wall in walls:
                        if proj.hitbox.colliderect(wall):
                            sound_manager.play_projectile_sound()
                            sound_events.append('arrow')
                            proj.kill(); break


            can_exit = False
            show_exit_dialogue = False
            if player.health > 0:
                for zone in exit_zones:
                    if player.feet.colliderect(zone):
                        can_exit = True; show_exit_dialogue = True; break

            if player.is_moving() and not was_walking:
                sound_manager.play_step(); was_walking = True
            elif not player.is_moving() and was_walking:
                sound_manager.stop_step(); was_walking = False

            # --- Caméra (suit joueur local) ---
            view_w = screen_width / zoom_level
            view_h = screen_height / zoom_level
            cam_x = player.feet.centerx
            cam_y = player.feet.centery - 30
            if map_pixel_width  < view_w: cam_x = map_pixel_width  // 2
            else: cam_x = max(view_w // 2, min(cam_x, map_pixel_width  - view_w // 2))
            if map_pixel_height < view_h: cam_y = map_pixel_height // 2
            else: cam_y = max(view_h // 2, min(cam_y, map_pixel_height - view_h // 2))
            group.center((cam_x, cam_y))
            group.draw(screen)

            # --- HUD ---
            ui.draw_health_bar(player.health, player.max_health)
            ui.draw_weapon_icon(player.current_weapon)
            ui.draw_pickaxe_icon(player.has_pickaxe)
            ui.draw_ammo_count(player.current_weapon, player.arrows)
            cr = min(1.0, max(0.0, (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown))
            ui.draw_boots_icon(player.has_boots, cr)
            # Barre de vie player2 (en haut à droite)
            _draw_remote_health(screen, player2.health, player2.max_health)

            for e in enemies_group:
                if getattr(e, 'has_aggro', False) and getattr(e, 'health', 0) > 0:
                    if isinstance(e, BigEnemy):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Gardien des profondeurs")
                    elif isinstance(e, Necromancer):
                        ui.draw_boss_health_bar(e.health, e.max_health, "La Faucheuse")

            if show_exit_dialogue:
                ui.draw_dialogue("Voulez vous rentrer ? (A)")

            # --- Indicateur "multijoueur" ---
            mp_surf = pygame.font.SysFont(None, 24).render("● MULTIJOUEUR", True, (80, 200, 80))
            screen.blit(mp_surf, (screen_width - mp_surf.get_width() - 10, 10))

            # --- Mort joueur local (serveur) ---
            server_dead = player.health <= 0
            client_dead = player2.health <= 0
            game_over   = server_dead and client_dead

            if server_dead:
                if death_time is None: death_time = pygame.time.get_ticks()
                elapsed = pygame.time.get_ticks() - death_time
                if elapsed > 1000:
                    if not death_sound_played:
                        sound_manager.play_death(); death_sound_played = True
                    prog = min(1.0, (elapsed - 1000) / 2000.0)
                    surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    surf.fill((100, 0, 0, int(200 * prog)))
                    screen.blit(surf, (0, 0))
                    dt_surf = death_font.render("Vous êtes mort", True, (255, 255, 255))
                    dt_surf.set_alpha(int(255 * prog))
                    screen.blit(dt_surf, dt_surf.get_rect(center=(screen_width // 2, screen_height // 2)))
            else:
                death_time = None
                death_sound_played = False

            # Fin de partie : les DEUX joueurs sont morts
            if game_over:
                if both_dead_time is None: both_dead_time = pygame.time.get_ticks()
                if pygame.time.get_ticks() - both_dead_time > 5000:
                    server.stop(); return

            # --- Envoi état au client ---
            state = {
                'level':       current_level_index,
                'players':     [_serialize_player(player), _serialize_player(player2)],
                'enemies':     [_serialize_enemy(e)        for e    in enemies_group],
                'items':       [_serialize_item(it)        for it   in items_group],
                'projectiles': [_serialize_projectile(pr)  for pr   in projectiles_group],
                'game_over':   game_over,
                'events':      {'dashes': dash_events, 'sounds': sound_events},
            }
            server.send_state(state)

            pygame.display.flip()
            clock.tick(60)


# =============================================================================
# BOUCLE CLIENT MULTIJOUEUR
# =============================================================================

def run_game_mp_client(screen, client, start_music_vol=0.5, start_sfx_vol=0.8):
    """Boucle de jeu côté client. Rendu pur piloté par l'état serveur."""
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    ui = UI(screen)
    sound_manager = SoundManager()

    global_music_vol = start_music_vol
    global_sfx_vol   = start_sfx_vol
    zoom_level = 3.8

    sound_manager.update_sfx_volume(global_sfx_vol)
    pygame.mixer.music.set_volume(global_music_vol)

    font_small = pygame.font.SysFont(None, 24)
    death_font = pygame.font.SysFont("old english text mt, garamond, times new roman, serif", 120)

    # Attendre le premier état pour connaître le niveau
    wait_start = pygame.time.get_ticks()
    first_state = None
    while first_state is None:
        if not client.connected:
            _show_disconnected(screen); return
        first_state = client.get_state() if client.get_state() else None
        if pygame.time.get_ticks() - wait_start > 10000:
            _show_disconnected(screen); return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.stop(); pygame.quit(); import sys; sys.exit()
        screen.fill((10, 10, 20))
        t = pygame.font.SysFont(None, 36).render("Connexion en cours…", True, (200, 200, 200))
        screen.blit(t, t.get_rect(center=(screen_width // 2, screen_height // 2)))
        pygame.display.flip()
        clock.tick(60)

    levels = ["assets/maps/test_map.tmx", "assets/maps/map1.tmx"]
    current_level_index = first_state.get('level', 0)
    loaded_level = -1

    group = None
    remote_enemies     = {}   # id  → RemoteEnemy sprite
    remote_items       = {}   # (x,y,type) → Item sprite
    remote_projectiles = {}   # id  → Projectile sprite
    remote_player = None      # sprite du joueur serveur
    local_player  = None      # sprite du joueur client (pos de référence caméra)

    map_pixel_width  = 0
    map_pixel_height = 0

    death_time = None
    death_sound_played = False
    is_paused_client   = False
    pause_rects_client = {}

    while True:
        if not client.connected:
            _show_disconnected(screen); return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.stop(); pygame.quit(); import sys; sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                is_paused_client = not is_paused_client   # toggle, ne quitte PAS

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_paused_client and pause_rects_client:
                    pos = event.pos
                    if pause_rects_client.get("mus_min") and pause_rects_client["mus_min"].collidepoint(pos):
                        global_music_vol = max(0.0, global_music_vol - 0.1)
                        pygame.mixer.music.set_volume(global_music_vol)
                    elif pause_rects_client.get("mus_pl") and pause_rects_client["mus_pl"].collidepoint(pos):
                        global_music_vol = min(1.0, global_music_vol + 0.1)
                        pygame.mixer.music.set_volume(global_music_vol)
                    elif pause_rects_client.get("sfx_min") and pause_rects_client["sfx_min"].collidepoint(pos):
                        global_sfx_vol = max(0.0, global_sfx_vol - 0.1)
                        sound_manager.update_sfx_volume(global_sfx_vol)
                    elif pause_rects_client.get("sfx_pl") and pause_rects_client["sfx_pl"].collidepoint(pos):
                        global_sfx_vol = min(1.0, global_sfx_vol + 0.1)
                        sound_manager.update_sfx_volume(global_sfx_vol)
                    elif "resume" in pause_rects_client and pause_rects_client["resume"].collidepoint(pos):
                        is_paused_client = False
                    elif pause_rects_client.get("quit") and pause_rects_client["quit"].collidepoint(pos):
                        client.stop(); return   # seul endroit qui déconnecte

        # Récupérer l'état depuis le serveur
        state = client.get_state()
        if not state:
            clock.tick(60); continue

        new_level = state.get('level', 0)

        # (Re)charger la carte si le niveau change
        if new_level != loaded_level:
            # Nettoyage explicite de tous les anciens sprites avant de recréer le groupe
            for re in remote_enemies.values():
                re.kill()
            for it in remote_items.values():
                it.kill()
            for rp in remote_projectiles.values():
                rp.kill()
            if remote_player: remote_player.kill()
            if local_player:  local_player.kill()

            loaded_level = new_level
            current_level_index = new_level
            if new_level >= len(levels):
                return
            try:
                tmx_data = pytmx.util_pygame.load_pygame(levels[new_level])
            except Exception as e:
                print(f"Erreur carte client : {e}"); return

            map_data  = pyscroll.data.TiledMapData(tmx_data)
            map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
            map_layer.zoom = zoom_level
            group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=1)
            map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
            map_pixel_height = tmx_data.height * tmx_data.tileheight

            remote_player = RemotePlayer(100, 100)
            local_player  = RemotePlayer(100, 100)
            group.add(remote_player)
            group.add(local_player)
            remote_enemies        = {}   # id → RemoteEnemy
            remote_enemy_etypes   = {}   # id → etype (pour particules)
            remote_items          = {}   # (x,y,type) → Item
            remote_projectiles    = {}   # id → Projectile
            client_particles_grp  = pygame.sprite.Group()

        players_state  = state.get('players',     [{}, {}])
        enemies_state  = state.get('enemies',     [])
        items_state    = state.get('items',       [])
        projs_state    = state.get('projectiles', [])

        # --- Joueurs ---
        if len(players_state) >= 1 and remote_player:
            remote_player.update_from_state(players_state[0])
        if len(players_state) >= 2 and local_player:
            local_player.update_from_state(players_state[1])

        # --- Ennemis distants ---
        current_eids = {e['id'] for e in enemies_state}
        for eid in list(remote_enemies.keys()):
            if eid not in current_eids:
                re = remote_enemies[eid]
                # Spawner des particules de mort localement
                etype = remote_enemy_etypes.get(eid, 'enemy')
                ParticleClass = DarkParticle if etype in ('necromancer', 'spirit') else BloodParticle
                for _ in range(15):
                    p = ParticleClass(re.rect.centerx, re.rect.centery)
                    group.add(p)
                    client_particles_grp.add(p)
                re.kill()
                del remote_enemies[eid]
                remote_enemy_etypes.pop(eid, None)
        for edata in enemies_state:
            eid = edata['id']
            if eid not in remote_enemies:
                etype = edata.get('etype', 'enemy')
                re = RemoteEnemy(etype)
                group.add(re)
                remote_enemies[eid]      = re
                remote_enemy_etypes[eid] = etype
            remote_enemies[eid].update_from_state(edata)

        # --- Items distants ---
        # Clé = (x, y, type) : les items ne bougent pas
        current_ikeys = {(d['x'], d['y'], d['type']) for d in items_state}
        for ikey in list(remote_items.keys()):
            if ikey not in current_ikeys:
                remote_items[ikey].kill()
                del remote_items[ikey]
        for d in items_state:
            ikey = (d['x'], d['y'], d['type'])
            if ikey not in remote_items:
                it = Item(0, 0, d['type'])
                it.rect.x = d['x']
                it.rect.y = d['y']
                group.add(it)
                remote_items[ikey] = it

        # --- Projectiles distants ---
        current_pids = {p['id'] for p in projs_state}
        for pid in list(remote_projectiles.keys()):
            if pid not in current_pids:
                remote_projectiles[pid].kill()
                del remote_projectiles[pid]
        for pdata in projs_state:
            pid = pdata['id']
            if pid not in remote_projectiles:
                rp = Projectile(pdata['x'], pdata['y'], pdata['direction'])
                group.add(rp)
                remote_projectiles[pid] = rp
            else:
                rp = remote_projectiles[pid]
                rp.rect.centerx   = pdata['x']
                rp.rect.centery   = pdata['y']
                rp.hitbox.centerx = pdata['x']
                rp.hitbox.centery = pdata['y']

        # --- Événements serveur (particules + sons) ---
        events_recv = state.get('events', {})
        for dash in events_recv.get('dashes', []):
            for _ in range(20):
                p = SmokeParticle(
                    dash['x'] + random.randint(-15, 15),
                    dash['y'] + random.randint(-15, 5)
                )
                group.add(p)
                client_particles_grp.add(p)

        _SOUND_MAP = {
            'sword':           sound_manager.play_sword_sound,
            'arrow':           sound_manager.play_projectile_sound,
            'enemy_death':     sound_manager.play_projectile_sound,
            'dash':            sound_manager.play_dash_sound,
            'boss_activation': sound_manager.play_boss_activation,
            'boss_attack':     sound_manager.play_boss_attack,
            'boss_death':      sound_manager.play_boss_death,
            'boss_talk':       sound_manager.play_boss_talk,
        }
        for snd in events_recv.get('sounds', []):
            if snd == 'boss_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/boss1_soundtrack.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd == 'boss_bgm_stop':
                try:
                    pygame.mixer.music.fadeout(4000)
                except Exception:
                    pass
            else:
                fn = _SOUND_MAP.get(snd)
                if fn:
                    fn()

        # --- Caméra sur le joueur local (index 1) ---
        if local_player:
            view_w = screen_width / zoom_level
            view_h = screen_height / zoom_level
            cam_x = local_player.feet.centerx
            cam_y = local_player.feet.centery - 30
            if map_pixel_width  < view_w: cam_x = map_pixel_width  // 2
            else: cam_x = max(view_w // 2, min(cam_x, map_pixel_width  - view_w // 2))
            if map_pixel_height < view_h: cam_y = map_pixel_height // 2
            else: cam_y = max(view_h // 2, min(cam_y, map_pixel_height - view_h // 2))
            group.center((cam_x, cam_y))

        group.draw(screen)

        # Animer les particules locales (sang, fumée, etc.)
        client_particles_grp.update()

        # --- Pause menu ---
        if is_paused_client:
            # Envoyer des inputs vides pendant la pause
            client.send_inputs({})
            pause_rects_client = ui.draw_pause_menu(global_music_vol, global_sfx_vol)
            pygame.display.flip()
            clock.tick(60)
            continue

        # --- Capturer et envoyer les inputs locaux ---
        keys = pygame.key.get_pressed()
        lp_state_cur = players_state[1] if len(players_state) >= 2 else {}

        # Son d'épée immédiat côté client (pas d'attente réseau)
        if keys[pygame.K_e] and lp_state_cur.get('current_weapon') == 'melee' and lp_state_cur.get('health', 0) > 0:
            if not getattr(run_game_mp_client, '_client_attacking', False):
                sound_manager.play_sword_sound()
                run_game_mp_client._client_attacking = True
        else:
            run_game_mp_client._client_attacking = False

        inputs = {
            'up':      bool(keys[pygame.K_z]),
            'down':    bool(keys[pygame.K_s]),
            'left':    bool(keys[pygame.K_q]),
            'right':   bool(keys[pygame.K_d]),
            'attack':  bool(keys[pygame.K_e]),
            'interact': bool(keys[pygame.K_f]),
            'dash':    bool(keys[pygame.K_LSHIFT]),
            'weapon1': bool(keys[pygame.K_1]),
            'weapon2': bool(keys[pygame.K_2]),
        }
        client.send_inputs(inputs)

        # --- HUD joueur local (complet) ---
        lp_state = players_state[1] if len(players_state) >= 2 else {}
        ui.draw_health_bar(lp_state.get('health', 100), lp_state.get('max_health', 100))
        ui.draw_weapon_icon(lp_state.get('current_weapon', None))
        ui.draw_pickaxe_icon(lp_state.get('has_pickaxe', False))
        ui.draw_ammo_count(lp_state.get('current_weapon', None), lp_state.get('arrows', 0))
        ui.draw_boots_icon(lp_state.get('has_boots', False), lp_state.get('dash_cr', 1.0))

        # Barre de vie du joueur hôte (en haut à droite)
        rp_state = players_state[0] if len(players_state) >= 1 else {}
        _draw_remote_health(screen, rp_state.get('health', 100), rp_state.get('max_health', 100), label='HÔTE')

        # Barre de vie du boss (si présent et vivant)
        for edata in enemies_state:
            if edata.get('etype') in ('bigenemy', 'necromancer') and edata.get('health', 0) > 0:
                boss_name = "Gardien des profondeurs" if edata['etype'] == 'bigenemy' else "La Faucheuse"
                ui.draw_boss_health_bar(edata['health'], edata['max_health'], boss_name)
                break  # un seul boss à la fois

        # Indicateur multijoueur
        mp_surf = font_small.render("● MULTIJOUEUR (CLIENT)", True, (80, 200, 80))
        screen.blit(mp_surf, (screen_width - mp_surf.get_width() - 10, 10))

        # --- Mort joueur local ---
        lp_health  = lp_state.get('health', 100)
        game_over  = state.get('game_over', False)
        if lp_health <= 0:
            if death_time is None: death_time = pygame.time.get_ticks()
            elapsed = pygame.time.get_ticks() - death_time
            if elapsed > 1000:
                if not death_sound_played:
                    sound_manager.play_death(); death_sound_played = True
                prog = min(1.0, (elapsed - 1000) / 2000.0)
                surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                surf.fill((100, 0, 0, int(200 * prog)))
                screen.blit(surf, (0, 0))
                dt_surf = death_font.render("Vous êtes mort", True, (255, 255, 255))
                dt_surf.set_alpha(int(255 * prog))
                screen.blit(dt_surf, dt_surf.get_rect(center=(screen_width // 2, screen_height // 2)))
            # Ne quitter que lorsque les DEUX joueurs sont morts (signal serveur)
            if game_over and elapsed > 5000:
                client.stop(); return
        else:
            death_time = None
            death_sound_played = False

        pygame.display.flip()
        clock.tick(60)


# =============================================================================
# HELPERS PARTAGÉS
# =============================================================================

def _pickup_item(player, item, sound_manager):
    if item.item_type == 'melee':
        player.has_melee = True
        if player.current_weapon != 'melee':
            player.current_weapon = 'melee'; sound_manager.play_equip_sword()
    elif item.item_type == 'ranged':
        if not player.has_ranged: player.arrows += 10
        player.has_ranged = True
        if player.current_weapon != 'ranged':
            player.current_weapon = 'ranged'; sound_manager.play_equip_bow()
    elif item.item_type == 'pickaxe':
        player.has_pickaxe = True
    elif item.item_type == 'arrow':
        player.arrows += random.randint(1, 4); sound_manager.play_equip_bow()
    elif item.item_type == 'apple':
        player.heal(player.max_health * 0.10); sound_manager.play_eating()
    elif item.item_type == 'boots':
        player.has_boots = True; sound_manager.play_equipement()


def _handle_enemy_death(enemy, group, items_group, particles_group):
    if hasattr(enemy, 'pending_drop') and enemy.pending_drop:
        drop = Item(enemy.rect.centerx, enemy.rect.centery, enemy.pending_drop)
        group.add(drop); items_group.add(drop)
        enemy.pending_drop = None
    if enemy.health <= 0:
        ParticleClass = DarkParticle if isinstance(enemy, (Necromancer, Spirit)) else BloodParticle
        for _ in range(20):
            p = ParticleClass(enemy.rect.centerx, enemy.rect.centery)
            group.add(p); particles_group.add(p)


def _draw_remote_health(screen, health, max_health, label='P2'):
    """Barre de vie du joueur distant, affichée en haut à droite."""
    bar_w, bar_h = 150, 15
    x = screen.get_width() - bar_w - 20
    y = 20
    ratio = health / max_health if max_health > 0 else 0
    color = (50, 200, 50) if ratio >= 0.8 else (200, 200, 50) if ratio >= 0.3 else (200, 50, 50)
    pygame.draw.rect(screen, (50, 50, 50), (x, y, bar_w, bar_h))
    pygame.draw.rect(screen, color, (x, y, int(bar_w * ratio), bar_h))
    pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_w, bar_h), 2)
    font = pygame.font.SysFont(None, 20)
    lbl = font.render(label, True, (200, 200, 200))
    screen.blit(lbl, (x - lbl.get_width() - 5, y))


def _show_disconnected(screen):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); import sys; sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return
        screen.fill((20, 0, 0))
        msg = font.render("Partenaire déconnecté — retour au menu", True, (255, 100, 100))
        screen.blit(msg, msg.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)))
        pygame.display.flip()
        clock.tick(60)