import pygame
import pytmx
import pyscroll
import random

from player import Player, RemotePlayer
from sound import SoundManager
from enemy import Enemy, BigEnemy, Necromancer, Spirit, RemoteEnemy
from ui import UI
from item import Item
from projectile import Projectile, HomingProjectile, HealEffect, InstantAOE, FloatingText
from obstacle import Rock, RockParticle, BloodParticle, SmokeParticle, DarkParticle
from characters import get_character_def
from character_select import character_select_screen_host, character_select_screen_client, character_select_screen_solo

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
    
    player_inventory = {'melee': False, 'ranged': False, 'pickaxe': False, 'boots': False,
                        'red_gem': False, 'blue_gem': False, 'current': None, 'arrows': 0}
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
            elif obj_type == "redgem":
                new_item = Item(obj.x, obj.y, 'redgem')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "bluegem":
                new_item = Item(obj.x, obj.y, 'bluegem')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "mirror":
                new_item = Item(obj.x, obj.y, 'mirror')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "kitsune_mask":
                new_item = Item(obj.x, obj.y, 'kitsune_mask')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "cursed_brand":
                new_item = Item(obj.x, obj.y, 'cursed_brand')
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
        player.has_red_gem = player_inventory['red_gem']
        player.has_blue_gem = player_inventory['blue_gem']
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
                    pygame.mixer.music.stop(); return
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
                            pygame.mixer.music.stop(); return

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
                                    sound_manager.play_ui_equip_sword()

                            if event.key == pygame.K_2:
                                if player.has_ranged and player.current_weapon != 'ranged':
                                    player.switch_weapon('ranged')
                                    sound_manager.play_ui_equip_bow()
                                    
                            if event.key == pygame.K_a and can_exit:
                                player_inventory['melee'] = player.has_melee
                                player_inventory['ranged'] = player.has_ranged
                                player_inventory['pickaxe'] = player.has_pickaxe
                                player_inventory['boots'] = player.has_boots
                                player_inventory['red_gem'] = player.has_red_gem
                                player_inventory['blue_gem'] = player.has_blue_gem
                                player_inventory['current'] = player.current_weapon
                                player_inventory['arrows'] = player.arrows
                                player_health = player.health
                                
                                current_level_index += 1
                                level_running = False 
                                break
                                
                            if event.key == pygame.K_3:
                                if player.has_blue_gem:
                                    player.activate_blue_gem()
                            if event.key == pygame.K_LSHIFT:
                                if player.has_boots:
                                    if player.dash(walls):
                                        sound_manager.play_spatial_dash(
                                            (player.feet.centerx, player.feet.centery),
                                            (player.feet.centerx, player.feet.centery))
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
                                                sound_manager.play_ui_equip_sword()
                                        elif item.item_type == 'ranged':
                                            if not player.has_ranged:
                                                player.arrows += 10
                                            player.has_ranged = True
                                            if player.current_weapon != 'ranged':
                                                player.current_weapon = 'ranged'
                                                sound_manager.play_ui_equip_bow()
                                        elif item.item_type == 'pickaxe':
                                            player.has_pickaxe = True
                                        elif item.item_type == 'arrow':
                                            nb_arrows = random.randint(1, 4)
                                            player.arrows += nb_arrows
                                            sound_manager.play_ui_equip_bow()
                                        elif item.item_type == 'apple':
                                            heal_amount = player.max_health * 0.10
                                            player.heal(heal_amount)
                                            sound_manager.play_ui_eating()
                                        elif item.item_type == 'boots':
                                            player.has_boots = True
                                            sound_manager.play_ui_equipement()
                                        elif item.item_type == 'redgem':
                                            player.has_red_gem = True
                                            sound_manager.play_ui_equipement()
                                        elif item.item_type == 'bluegem':
                                            player.has_blue_gem = True
                                            sound_manager.play_ui_equipement()

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

                                            rock_pos = (rock.rect.centerx, rock.rect.centery)
                                            rock.kill()
                                            if rock.hitbox in walls:
                                                walls.remove(rock.hitbox)

                                            player.has_pickaxe = False
                                            sound_manager.play_spatial('rock_broke', rock_pos,
                                                                       (player.feet.centerx, player.feet.centery))
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
            
            ppos = (player.feet.centerx, player.feet.centery)
            for enemy in enemies_group:
                enemy.update(player, walls)

                if hasattr(enemy, 'pending_summons') and enemy.pending_summons:
                    for sx, sy in enemy.pending_summons:
                        new_spirit = Spirit(sx, sy)
                        group.add(new_spirit)
                        enemies_group.add(new_spirit)
                    enemy.pending_summons.clear()

                # Jouer les sons des boss via le SpatialAudioManager
                if hasattr(enemy, 'pending_sounds') and enemy.pending_sounds:
                    boss_pos = (enemy.feet.centerx, enemy.feet.centery)
                    for bs in enemy.pending_sounds:
                        if bs == 'boss_bgm_start':
                            try:
                                pygame.mixer.music.load("assets/sounds/boss1_soundtrack.mp3")
                                pygame.mixer.music.set_volume(global_music_vol)
                                pygame.mixer.music.play(-1)
                            except Exception:
                                pass
                        elif bs == 'boss_bgm_stop':
                            try:
                                pygame.mixer.music.fadeout(4000)
                            except Exception:
                                pass
                        else:
                            sound_manager.play_spatial(bs, boss_pos, ppos)
                    enemy.pending_sounds.clear()

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
            ppos = (player.feet.centerx, player.feet.centery)
            if keys[pygame.K_e] and player.current_weapon is not None and player.health > 0:
                attack_result = player.attack()
                if attack_result:
                    type_attack, data = attack_result
                    if type_attack == 'melee':
                        sound_manager.play_spatial('sword', ppos, ppos)
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

            for projectile in list(projectiles_group):
                if not hasattr(projectile, 'hitbox'):
                    continue
                for enemy in enemies_group:
                    if getattr(enemy, 'health', 0) > 0:
                        body_hitbox = enemy.feet.copy()
                        body_hitbox.height += 25
                        body_hitbox.y -= 25
                        if projectile.hitbox.colliderect(body_hitbox):
                            # Piercing : skip les ennemis déjà touchés
                            if getattr(projectile, 'piercing', False):
                                if id(enemy) in projectile._hit_enemies:
                                    continue
                                projectile._hit_enemies.add(id(enemy))

                            hit_pos = (projectile.hitbox.centerx, projectile.hitbox.centery)
                            sound_manager.play_spatial('shot', hit_pos, ppos)
                            enemy.damage(projectile.damage_amount)

                            if hasattr(enemy, 'pending_drop') and enemy.pending_drop:
                                drop = Item(enemy.rect.centerx, enemy.rect.centery, enemy.pending_drop)
                                group.add(drop)
                                items_group.add(drop)
                                enemy.pending_drop = None

                            if enemy.health <= 0:
                                ParticleClass = DarkParticle if isinstance(enemy, (Necromancer, Spirit)) else BloodParticle
                                for _ in range(20):
                                    particle = ParticleClass(enemy.rect.centerx, enemy.rect.centery)
                                    group.add(particle)
                                    particles_group.add(particle)

                            if not getattr(projectile, 'piercing', False):
                                projectile.kill()
                                break

                if projectile.alive():
                    for wall in walls:
                        if projectile.hitbox.colliderect(wall):
                            wall_pos = (projectile.hitbox.centerx, projectile.hitbox.centery)
                            sound_manager.play_spatial('shot', wall_pos, ppos)
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
    # Cooldowns des compétences
    skill_crs = {}
    for sk_name in p.abilities:
        skill_crs[sk_name] = p.get_skill_cooldown_ratio(sk_name)
    return {
        'x': p.feet.centerx,
        'y': p.feet.bottom,
        'state': p.state,
        'direction': p.facing,
        'frame': p.frame_index,
        'health': p.health,
        'max_health': p.max_health,
        'current_weapon': p.current_weapon,
        'has_melee':      p.has_melee,
        'has_ranged':     p.has_ranged,
        'has_pickaxe':    p.has_pickaxe,
        'has_boots':      p.has_boots,
        'has_red_gem':    p.has_red_gem,
        'has_blue_gem':   p.has_blue_gem,
        'blue_gem_active': p.blue_gem_active,
        'blue_gem_cr':    p.get_blue_gem_cooldown_ratio(),
        'red_gem_triggered': getattr(p, 'red_gem_triggered', False),
        'has_mirror':     p.has_mirror,
        'mirror_triggered': getattr(p, 'mirror_triggered', False),
        'has_kitsune_mask': p.has_kitsune_mask,
        'has_cursed_brand': p.has_cursed_brand,
        'cursed_brand_active': p.cursed_brand_active,
        'cursed_brand_cr': p.get_cursed_brand_cooldown_ratio(),
        'cursed_brand_triggered': getattr(p, 'cursed_brand_triggered', False),
        'arrows':         p.arrows,
        'dash_cr':        dash_cr,
        'char_type':      getattr(p, 'char_type', 'soldier'),
        'skill_cooldowns': skill_crs,
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
    data = {
        'id':        getattr(proj, '_mp_id', id(proj)),
        'x':         proj.rect.centerx,
        'y':         proj.rect.centery,
        'direction': getattr(proj, 'direction', 'right'),
    }
    # Transmettre le type et l'image pour le rendu côté client
    if isinstance(proj, InstantAOE):
        data['type'] = 'instant_aoe'
        data['img_path'] = getattr(proj, '_img_path', None)
        data['radius'] = proj.explosion_radius
        data['frame'] = proj._frame_index
        data['duration'] = proj.duration
        data['start_time'] = proj.start_time
    elif isinstance(proj, HomingProjectile):
        data['type'] = 'homing'
    elif isinstance(proj, HealEffect):
        data['type'] = 'heal_effect'
        data['img_path'] = getattr(proj, '_img_path', None)
        data['frame'] = proj._frame_index
    else:
        data['type'] = 'projectile'
        data['img_path'] = getattr(proj, '_img_path', None)
    return data


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

def run_game_solo(screen, start_music_vol=0.5, start_sfx_vol=0.8):
    """Lance une partie solo en réutilisant la boucle serveur."""
    char_type = character_select_screen_solo(screen)
    if char_type is None:
        return
    run_game_mp_server(screen, server=None, start_music_vol=start_music_vol,
                       start_sfx_vol=start_sfx_vol,
                       solo_mode=True, solo_char_type=char_type)


def run_game_mp_server(screen, server, start_music_vol=0.5, start_sfx_vol=0.8,
                       solo_mode=False, solo_char_type='soldier'):
    """Boucle de jeu côté serveur. Autoritaire sur la simulation.
    En mode solo (solo_mode=True), pas de réseau ni de player2."""
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    # --- Sélection de personnage ---
    if solo_mode:
        host_char_type = solo_char_type
        client_char_type = None
    else:
        char_result = character_select_screen_host(screen, server)
        if char_result is None:
            return  # Annulé
        host_char_type, client_char_type = char_result

    ui = UI(screen)
    sound_manager = SoundManager()

    levels = ["assets/maps/test_map.tmx", "assets/maps/map1.tmx"]
    current_level_index = 0

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

    def _cleanup_audio():
        """Stoppe toute musique et sons en boucle avant de quitter."""
        try:
            pygame.mixer.music.stop()
            sound_manager.stop_step()
            sound_manager.stop_remote_step()
        except Exception:
            pass

    while current_level_index < len(levels):
        if not solo_mode and not server.connected:
            _cleanup_audio(); return

        try:
            tmx_data = pytmx.util_pygame.load_pygame(levels[current_level_index])
        except Exception as e:
            print(f"Erreur carte : {e}")
            _cleanup_audio(); return

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
            elif obj_type == "redgem":
                it = Item(obj.x, obj.y, 'redgem'); group.add(it); items_group.add(it)
            elif obj_type == "bluegem":
                it = Item(obj.x, obj.y, 'bluegem'); group.add(it); items_group.add(it)
            elif obj_type == "mirror":
                it = Item(obj.x, obj.y, 'mirror'); group.add(it); items_group.add(it)
            elif obj_type == "kitsune_mask":
                it = Item(obj.x, obj.y, 'kitsune_mask'); group.add(it); items_group.add(it)
            elif obj_type == "cursed_brand":
                it = Item(obj.x, obj.y, 'cursed_brand'); group.add(it); items_group.add(it)
            elif obj_type == "obstacle_rock":
                r = Rock(obj.x, obj.y); group.add(r); rocks_group.add(r); walls.append(r.hitbox)

        # Joueur local (serveur) — avec le personnage choisi
        player = Player(player_x, player_y, char_type=host_char_type)
        player.health = player_health
        group.add(player)

        # Joueur distant (client, piloté par inputs réseau) — avec le personnage choisi
        player2 = None
        if not solo_mode and client_char_type:
            player2 = Player(player_x + 20, player_y, char_type=client_char_type)
            player2.health = player2_health
            group.add(player2)

        map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
        map_pixel_height = tmx_data.height * tmx_data.tileheight

        level_running  = True
        was_walking    = False
        p2_was_walking = False
        death_time     = None
        death_sound_played = False
        both_dead_time = None
        can_exit       = False
        show_exit_dialogue = False
        red_gem_animating = False
        red_gem_anim_start = 0
        mirror_animating = False
        mirror_anim_start = 0
        cursed_brand_animating = False
        cursed_brand_anim_start = 0

        death_font = pygame.font.SysFont("old english text mt, garamond, times new roman, serif", 120)
        EUREKA_EVENT = pygame.USEREVENT + 1

        while level_running:
            # --- Déconnexion client ---
            if not solo_mode and not server.connected:
                _cleanup_audio()
                _show_disconnected(screen)
                return

            dash_events  = []  # événements de dash à envoyer au client ce frame
            sound_events = []  # sons à jouer côté client ce frame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    _cleanup_audio()
                    if server: server.stop()
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
                            _cleanup_audio()
                            if server: server.stop()
                            return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        is_paused = not is_paused
                        continue
                    if not is_paused and player.health > 0:
                        if event.key == pygame.K_1:
                            _handle_weapon_switch(player, 1, sound_manager)
                        if event.key == pygame.K_2:
                            _handle_weapon_switch(player, 2, sound_manager)
                        if event.key == pygame.K_a and can_exit:
                            player_health  = player.health
                            if player2: player2_health = player2.health
                            current_level_index += 1
                            level_running = False
                            break
                        # Items actifs : touches dynamiques (3, 4, 5...)
                        active_items_keys = _get_active_item_keys(player)
                        for key_num, item_name in active_items_keys:
                            if event.key == getattr(pygame, f'K_{key_num}', None):
                                if item_name == 'boots':
                                    if player.dash(walls):
                                        host_pos = (player.feet.centerx, player.feet.centery)
                                        sound_manager.play_spatial_dash(host_pos, host_pos)
                                        sound_events.append({'sound': 'dash', 'x': player.feet.centerx, 'y': player.feet.centery})
                                        dash_events.append({'player': 0, 'x': player.feet.centerx, 'y': player.feet.bottom})
                                        for _ in range(20):
                                            smoke = SmokeParticle(player.feet.centerx + random.randint(-15, 15),
                                                                  player.feet.bottom + random.randint(-15, 5))
                                            group.add(smoke); particles_group.add(smoke)
                                elif item_name == 'bluegem':
                                    player.activate_blue_gem()
                                elif item_name == 'cursed_brand':
                                    ally = player2 if (not solo_mode and player2 and player2.health > 0) else None
                                    player.activate_cursed_brand(ally)
                        if event.key == pygame.K_LSHIFT and player.has_boots:
                            if player.dash(walls):
                                host_pos = (player.feet.centerx, player.feet.centery)
                                sound_manager.play_spatial_dash(host_pos, host_pos)
                                sound_events.append({'sound': 'dash', 'x': player.feet.centerx, 'y': player.feet.centery})
                                dash_events.append({'player': 0, 'x': player.feet.centerx, 'y': player.feet.bottom})
                                for _ in range(20):
                                    smoke = SmokeParticle(player.feet.centerx + random.randint(-15, 15),
                                                         player.feet.bottom + random.randint(-15, 5))
                                    group.add(smoke); particles_group.add(smoke)
                        if event.key == pygame.K_f:
                            for item in list(items_group):
                                if player.feet.colliderect(item.rect):
                                    if _pickup_item(player, item, sound_manager):
                                        item.kill()
                                    break
                            if player.has_pickaxe:
                                for rock in list(rocks_group):
                                    if player.feet.colliderect(rock.hitbox.inflate(40, 40)):
                                        for _ in range(15):
                                            p = RockParticle(rock.rect.centerx, rock.rect.centery)
                                            group.add(p); particles_group.add(p)
                                        rx, ry = rock.rect.centerx, rock.rect.centery
                                        rock.kill()
                                        if rock.hitbox in walls: walls.remove(rock.hitbox)
                                        player.has_pickaxe = False
                                        sound_manager.play_spatial('rock_broke', (rx, ry),
                                                                   (player.feet.centerx, player.feet.centery))
                                        sound_events.append({'sound': 'rock_broke', 'x': rx, 'y': ry})
                                        pygame.time.set_timer(EUREKA_EVENT, 250, 1)
                                        sound_events.append({'sound': 'eureka', 'x': rx, 'y': ry})
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
            host_pos = (player.feet.centerx, player.feet.centery)
            net_inputs = {}
            if not solo_mode and player2:
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
                            p2_pos = (player2.feet.centerx, player2.feet.centery)
                            sound_manager.play_spatial('sword', p2_pos, host_pos)
                            for e in list(enemies_group):
                                if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                    dmg2 = player2.melee_damage * player2.get_damage_multiplier()
                                    if player2.has_kitsune_mask and e.health <= e.max_health * 0.3:
                                        dmg2 *= 1.5
                                    e.damage(dmg2)
                                    if e.health <= 0:
                                        e_pos = (e.feet.centerx, e.feet.centery)
                                        sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                    _handle_enemy_death(e, group, items_group, particles_group)
                        elif typ == 'skill':
                            p2_pos = (player2.feet.centerx, player2.feet.centery)
                            sound_manager.play_spatial('sword', p2_pos, host_pos)

                # Vérifier les compétences actives de player2
                if player2.is_attacking and player2.active_skill:
                    p2_pos = (player2.feet.centerx, player2.feet.centery)
                    skill_result = player2.check_skill_attack(
                        player2.active_skill, enemies_group, ally_player=player)
                    _apply_skill_result(skill_result, player2, group, projectiles_group,
                                        particles_group, enemies_group, items_group,
                                        sound_manager, sound_events, host_pos, _next_id)

            if not solo_mode and player2:
                # Blue gem player2
                if net_inputs.get('gem_blue') and player2.has_blue_gem:
                    player2.activate_blue_gem()
                # Cursed brand player2
                if net_inputs.get('cursed_brand') and player2.has_cursed_brand:
                    player2.activate_cursed_brand(ally_player=player)
                # Dash player2
                if net_inputs.get('dash') and player2.has_boots:
                    if player2.dash(walls):
                        p2_pos = (player2.feet.centerx, player2.feet.centery)
                        sound_manager.play_spatial_dash(p2_pos, host_pos)
                        sound_events.append({'sound': 'dash', 'x': p2_pos[0], 'y': p2_pos[1]})
                        dash_events.append({'player': 1, 'x': player2.feet.centerx, 'y': player2.feet.bottom})
                        for _ in range(20):
                            smoke = SmokeParticle(player2.feet.centerx + random.randint(-15, 15),
                                                 player2.feet.bottom + random.randint(-15, 5))
                            group.add(smoke); particles_group.add(smoke)

                # Ramasser objet player2 (sans son : le client joue ses propres sons)
                if net_inputs.get('interact') and player2.health > 0:
                    for item in list(items_group):
                        if player2.feet.colliderect(item.rect):
                            if _pickup_item(player2, item, None):
                                item.kill()
                            break
                    if player2.has_pickaxe:
                        for rock in list(rocks_group):
                            if player2.feet.colliderect(rock.hitbox.inflate(40, 40)):
                                for _ in range(15):
                                    p = RockParticle(rock.rect.centerx, rock.rect.centery)
                                    group.add(p); particles_group.add(p)
                                rx, ry = rock.rect.centerx, rock.rect.centery
                                rock.kill()
                                if rock.hitbox in walls: walls.remove(rock.hitbox)
                                player2.has_pickaxe = False
                                sound_manager.play_spatial('rock_broke', (rx, ry), host_pos)
                                sound_events.append({'sound': 'rock_broke', 'x': rx, 'y': ry})
                                pygame.time.set_timer(EUREKA_EVENT, 250, 1)
                                sound_events.append({'sound': 'eureka', 'x': rx, 'y': ry})
                                break

                # Changement d'arme/compétence player2
                if net_inputs.get('weapon1'):
                    _handle_weapon_switch(player2, 1, None)
                if net_inputs.get('weapon2'):
                    _handle_weapon_switch(player2, 2, None)

                # Attaque à distance player2
                new_proj2 = player2.check_ranged_attack()
                if new_proj2:
                    new_proj2._mp_id = _next_id()
                    new_proj2._owner = player2
                    group.add(new_proj2); projectiles_group.add(new_proj2)

                # Régénération de flèches player2 (Archer)
                player2.update_arrow_regen()

            # --- Joueur local ---
            player.update()
            player.move(walls)

            # Red gem animation (host) — détecter le déclenchement
            if getattr(player, 'red_gem_triggered', False):
                player.red_gem_triggered = False
                red_gem_anim_start = pygame.time.get_ticks()
                red_gem_animating = True
            if player2 and getattr(player2, 'red_gem_triggered', False):
                player2.red_gem_triggered = False

            # Mirror animation (host)
            if getattr(player, 'mirror_triggered', False):
                player.mirror_triggered = False
                mirror_anim_start = pygame.time.get_ticks()
                mirror_animating = True
            if player2 and getattr(player2, 'mirror_triggered', False):
                player2.mirror_triggered = False

            # Cursed brand animation (host) — l'animation joue sur le joueur qui a subi les dégâts
            if getattr(player, 'cursed_brand_triggered', False):
                player.cursed_brand_triggered = False
                cursed_brand_anim_start = pygame.time.get_ticks()
                cursed_brand_animating = True
            if player2 and getattr(player2, 'cursed_brand_triggered', False):
                player2.cursed_brand_triggered = False

            # --- Ennemis ---
            for e in list(enemies_group):
                # Ciblage : seulement les joueurs vivants
                all_players = [player] + ([player2] if player2 else [])
                live = [p for p in all_players if p.health > 0]
                if live:
                    target = min(live, key=lambda p: (
                        pygame.math.Vector2(p.feet.center) - pygame.math.Vector2(e.feet.center)
                    ).length())
                else:
                    target = player  # tous morts, peu importe
                e.update(target, walls)
                # Dégâts sur le joueur non-ciblé (boss avec get_attack_hitbox)
                if player2:
                    other = player2 if target is player else player
                    if hasattr(e, 'get_attack_hitbox') and getattr(e, 'is_attacking', False) and other.health > 0:
                        atk = e.get_attack_hitbox()
                        now = pygame.time.get_ticks()
                        last_mp = getattr(e, '_mp_other_dmg_time', 0)
                        if atk and atk.colliderect(other.feet) and now - last_mp > getattr(e, 'attack_cooldown', 1500):
                            other.damage(getattr(e, 'damage_amount', 10), source_enemy=e)
                            e._mp_other_dmg_time = now
                if hasattr(e, 'pending_summons') and e.pending_summons:
                    for sx, sy in e.pending_summons:
                        ns = Spirit(sx, sy); ns._mp_id = _next_id()
                        group.add(ns); enemies_group.add(ns)
                    e.pending_summons.clear()
                # Collecter les sons des boss pour les envoyer au client
                if hasattr(e, 'pending_sounds') and e.pending_sounds:
                    boss_pos = (e.feet.centerx, e.feet.centery)
                    for bs in e.pending_sounds:
                        if isinstance(bs, str):
                            if bs == 'boss_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/boss1_soundtrack.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'boss_bgm_stop':
                                try:
                                    pygame.mixer.music.fadeout(4000)
                                except Exception:
                                    pass
                            else:
                                # Son de boss spatialisé pour le host
                                sound_manager.play_spatial(bs, boss_pos, host_pos)
                            sound_events.append({'sound': bs, 'x': boss_pos[0], 'y': boss_pos[1]})
                        else:
                            sound_events.append(bs)
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
                        sound_manager.play_spatial('sword', host_pos, host_pos)
                        sound_events.append({'sound': 'sword', 'x': host_pos[0], 'y': host_pos[1]})
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                dmg = player.melee_damage * player.get_damage_multiplier()
                                if player.has_kitsune_mask and e.health <= e.max_health * 0.3:
                                    dmg *= 1.5
                                e.damage(dmg)
                                if e.health <= 0:
                                    e_pos = (e.feet.centerx, e.feet.centery)
                                    sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                _handle_enemy_death(e, group, items_group, particles_group)
                    elif typ == 'skill':
                        sound_manager.play_spatial('sword', host_pos, host_pos)
                        sound_events.append({'sound': 'sword', 'x': host_pos[0], 'y': host_pos[1]})

            # Vérifier les compétences actives (serveur)
            if player.is_attacking and player.active_skill:
                skill_result = player.check_skill_attack(
                    player.active_skill, enemies_group, ally_player=player2)
                _apply_skill_result(skill_result, player, group, projectiles_group,
                                    particles_group, enemies_group, items_group,
                                    sound_manager, sound_events, host_pos, _next_id)

            new_proj = player.check_ranged_attack()
            if new_proj:
                new_proj._mp_id = _next_id()
                new_proj._owner = player
                group.add(new_proj); projectiles_group.add(new_proj)

            # Régénération de flèches (Archer)
            player.update_arrow_regen()

            for proj in list(projectiles_group):
                # HomingProjectile — dégâts en zone quand il explose
                if isinstance(proj, HomingProjectile):
                    if proj.has_exploded and not getattr(proj, '_damage_dealt', False):
                        proj._damage_dealt = True
                        owner = getattr(proj, '_owner', None)
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0:
                                dist = pygame.math.Vector2(
                                    e.feet.centerx - proj.rect.centerx,
                                    e.feet.centery - proj.rect.centery
                                ).length()
                                if dist <= proj.explosion_radius:
                                    aoe_dmg = proj.damage_amount
                                    if owner:
                                        aoe_dmg *= owner.get_damage_multiplier()
                                        if owner.has_kitsune_mask and e.health <= e.max_health * 0.3:
                                            aoe_dmg *= 1.5
                                    e.damage(aoe_dmg)
                                    if e.health <= 0:
                                        e_pos = (e.feet.centerx, e.feet.centery)
                                        sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                    _handle_enemy_death(e, group, items_group, particles_group)
                    continue

                # InstantAOE — dégâts en zone immédiatement
                if isinstance(proj, InstantAOE):
                    if not getattr(proj, '_damage_dealt', False):
                        proj._damage_dealt = True
                        owner = getattr(proj, '_owner', None)
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0:
                                dist = pygame.math.Vector2(
                                    e.feet.centerx - proj.rect.centerx,
                                    e.feet.centery - proj.rect.centery
                                ).length()
                                if dist <= proj.explosion_radius:
                                    aoe_dmg = proj.damage_amount
                                    if owner:
                                        aoe_dmg *= owner.get_damage_multiplier()
                                        if owner.has_kitsune_mask and e.health <= e.max_health * 0.3:
                                            aoe_dmg *= 1.5
                                    e.damage(aoe_dmg)
                                    if e.health <= 0:
                                        e_pos = (e.feet.centerx, e.feet.centery)
                                        sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                    _handle_enemy_death(e, group, items_group, particles_group)
                    continue

                # HealEffect — juste un visuel, pas de collision
                if isinstance(proj, HealEffect):
                    continue

                # Projectiles linéaires classiques (flèches, boules de feu)
                if not hasattr(proj, 'hitbox'):
                    continue
                for e in list(enemies_group):
                    if getattr(e, 'health', 0) > 0:
                        body = e.feet.copy(); body.height += 25; body.y -= 25
                        if proj.hitbox.colliderect(body):
                            # Piercing : skip les ennemis déjà touchés
                            if getattr(proj, 'piercing', False):
                                if id(e) in proj._hit_enemies:
                                    continue
                                proj._hit_enemies.add(id(e))

                            hit_pos = (proj.hitbox.centerx, proj.hitbox.centery)
                            sound_manager.play_spatial('shot', hit_pos, host_pos)
                            sound_events.append({'sound': 'arrow', 'x': hit_pos[0], 'y': hit_pos[1]})
                            proj_dmg = proj.damage_amount
                            owner = getattr(proj, '_owner', None)
                            if owner:
                                proj_dmg *= owner.get_damage_multiplier()
                                if owner.has_kitsune_mask and e.health <= e.max_health * 0.3:
                                    proj_dmg *= 1.5
                            e.damage(proj_dmg)
                            if e.health <= 0:
                                e_pos = (e.feet.centerx, e.feet.centery)
                                sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                            _handle_enemy_death(e, group, items_group, particles_group)
                            if not getattr(proj, 'piercing', False):
                                proj.kill(); break
                if proj.alive():
                    for wall in walls:
                        if proj.hitbox.colliderect(wall):
                            wall_pos = (proj.hitbox.centerx, proj.hitbox.centery)
                            sound_manager.play_spatial('shot', wall_pos, host_pos)
                            sound_events.append({'sound': 'arrow', 'x': wall_pos[0], 'y': wall_pos[1]})
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

            # Pas spatialisés du joueur distant (player2)
            p2_moving = (player2.is_moving() if player2 and hasattr(player2, 'is_moving') else False)
            if p2_moving and not p2_was_walking:
                p2_pos = (player2.feet.centerx, player2.feet.centery)
                sound_manager.play_remote_step(p2_pos, host_pos)
                p2_was_walking = True
            elif not p2_moving and p2_was_walking:
                sound_manager.stop_remote_step()
                p2_was_walking = False
            elif p2_moving and p2_was_walking:
                # Mise à jour du volume spatial chaque frame
                p2_pos = (player2.feet.centerx, player2.feet.centery)
                sound_manager.update_remote_step_volume(p2_pos, host_pos)

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

            # --- Marque Kitsune : griffe au-dessus des ennemis sous 30% PV ---
            if player.has_kitsune_mask:
                for e in enemies_group:
                    if getattr(e, 'health', 0) > 0 and e.health <= e.max_health * 0.3:
                        ex = (e.feet.centerx - cam_x) * zoom_level + screen_width / 2
                        ey = (e.rect.top - cam_y) * zoom_level + screen_height / 2
                        mark_size = max(28, int(max(e.rect.width, e.rect.height) * 0.5))
                        mark = _get_kitsune_mark(mark_size)
                        screen.blit(mark, (ex - mark_size // 2, ey - mark_size - 4))

            # --- HUD ---
            ui.draw_health_bar(player.health, player.max_health)
            cr = min(1.0, max(0.0, (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown))
            skill_crs = {sk: player.get_skill_cooldown_ratio(sk) for sk in player.abilities}
            ui.draw_character_hud(player.char_type, player.current_weapon,
                                  skill_cooldowns=skill_crs, arrows=player.arrows,
                                  has_pickaxe=player.has_pickaxe, has_boots=player.has_boots,
                                  dash_cr=cr,
                                  has_red_gem=player.has_red_gem,
                                  has_blue_gem=player.has_blue_gem,
                                  blue_gem_cr=player.get_blue_gem_cooldown_ratio(),
                                  has_mirror=player.has_mirror,
                                  has_kitsune_mask=player.has_kitsune_mask,
                                  has_cursed_brand=player.has_cursed_brand,
                                  cursed_brand_cr=player.get_cursed_brand_cooldown_ratio())
            # Barre de vie player2 (en haut à droite)
            if player2:
                _draw_remote_health(screen, player2.health, player2.max_health)

            for e in enemies_group:
                if getattr(e, 'has_aggro', False) and getattr(e, 'health', 0) > 0:
                    if isinstance(e, BigEnemy):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Gardien des profondeurs")
                    elif isinstance(e, Necromancer):
                        ui.draw_boss_health_bar(e.health, e.max_health, "La Faucheuse")

            if show_exit_dialogue:
                ui.draw_dialogue("Voulez vous rentrer ? (A)")

            # --- Indicateur mode ---
            if not solo_mode:
                mp_surf = pygame.font.SysFont(None, 24).render("● MULTIJOUEUR", True, (80, 200, 80))
                screen.blit(mp_surf, (screen_width - mp_surf.get_width() - 10, 10))

            # --- Mort joueur local ---
            server_dead = player.health <= 0
            client_dead = player2.health <= 0 if player2 else True
            game_over = server_dead if solo_mode else (server_dead and client_dead)

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

            # Fin de partie
            if game_over:
                if both_dead_time is None: both_dead_time = pygame.time.get_ticks()
                if pygame.time.get_ticks() - both_dead_time > 5000:
                    _cleanup_audio()
                    if server: server.stop()
                    return

            # --- Animation Red Gem (fullscreen) ---
            if red_gem_animating:
                elapsed_rg = pygame.time.get_ticks() - red_gem_anim_start
                if elapsed_rg < 1000:
                    # Phase 1 : apparition (0-300ms)
                    if elapsed_rg < 300:
                        alpha = int(255 * (elapsed_rg / 300.0))
                    # Phase 2 : visible (300-700ms)
                    elif elapsed_rg < 700:
                        alpha = 255
                    # Phase 3 : fade out (700-1000ms)
                    else:
                        alpha = int(255 * (1.0 - (elapsed_rg - 700) / 300.0))
                    try:
                        gem_img = pygame.image.load("assets/images/redgem.png").convert_alpha()
                        gem_img = pygame.transform.scale(gem_img, (128, 128))
                        gem_img.set_alpha(alpha)
                        gem_rect = gem_img.get_rect(center=(screen_width // 2, screen_height // 2))
                        # Flash rouge léger en fond
                        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                        overlay.fill((255, 50, 50, int(alpha * 0.4)))
                        screen.blit(overlay, (0, 0))
                        screen.blit(gem_img, gem_rect)
                    except Exception:
                        pass
                else:
                    red_gem_animating = False

            # --- Animation Mirror (fullscreen) ---
            if mirror_animating:
                elapsed_m = pygame.time.get_ticks() - mirror_anim_start
                if elapsed_m < 800:
                    if elapsed_m < 200:
                        alpha = int(255 * (elapsed_m / 200.0))
                    elif elapsed_m < 500:
                        alpha = 255
                    else:
                        alpha = int(255 * (1.0 - (elapsed_m - 500) / 300.0))
                    try:
                        mir_img = pygame.image.load("assets/images/mirror.png").convert_alpha()
                        mir_img = pygame.transform.scale(mir_img, (128, 128))
                        mir_img.set_alpha(alpha)
                        mir_rect = mir_img.get_rect(center=(screen_width // 2, screen_height // 2))
                        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                        overlay.fill((180, 180, 255, int(alpha * 0.3)))
                        screen.blit(overlay, (0, 0))
                        screen.blit(mir_img, mir_rect)
                    except Exception:
                        pass
                else:
                    mirror_animating = False

            # --- Animation Cursed Brand (fullscreen) ---
            if cursed_brand_animating:
                elapsed_cb = pygame.time.get_ticks() - cursed_brand_anim_start
                if elapsed_cb < 800:
                    if elapsed_cb < 200:
                        alpha = int(255 * (elapsed_cb / 200.0))
                    elif elapsed_cb < 500:
                        alpha = 255
                    else:
                        alpha = int(255 * (1.0 - (elapsed_cb - 500) / 300.0))
                    try:
                        cb_img = pygame.image.load("assets/images/cursed_brand.png").convert_alpha()
                        cb_img = pygame.transform.scale(cb_img, (128, 128))
                        cb_img.set_alpha(alpha)
                        cb_rect = cb_img.get_rect(center=(screen_width // 2, screen_height // 2))
                        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                        overlay.fill((150, 50, 150, int(alpha * 0.3)))
                        screen.blit(overlay, (0, 0))
                        screen.blit(cb_img, cb_rect)
                    except Exception:
                        pass
                else:
                    cursed_brand_animating = False

            # --- Envoi état au client (multijoueur uniquement) ---
            if not solo_mode and server:
                players_list = [_serialize_player(player)]
                if player2:
                    players_list.append(_serialize_player(player2))
                state = {
                    'level':       current_level_index,
                    'players':     players_list,
                    'enemies':     [_serialize_enemy(e)        for e    in enemies_group],
                    'items':       [_serialize_item(it)        for it   in items_group],
                    'projectiles': [_serialize_projectile(pr)  for pr   in projectiles_group
                                    if not isinstance(pr, HealEffect)],
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

    # --- Sélection de personnage ---
    char_result = character_select_screen_client(screen, client)
    if char_result is None:
        return
    host_char_type, client_char_type = char_result

    ui = UI(screen)
    sound_manager = SoundManager()

    global_music_vol = start_music_vol
    global_sfx_vol   = start_sfx_vol
    zoom_level = 3.8

    sound_manager.update_sfx_volume(global_sfx_vol)
    pygame.mixer.music.set_volume(global_music_vol)

    font_small = pygame.font.SysFont(None, 24)
    death_font = pygame.font.SysFont("old english text mt, garamond, times new roman, serif", 120)

    def _cleanup_client_audio():
        """Stoppe toute musique et sons en boucle côté client."""
        try:
            pygame.mixer.music.stop()
            sound_manager.stop_step()
            sound_manager.stop_remote_step()
        except Exception:
            pass

    # Attendre le premier état pour connaître le niveau
    wait_start = pygame.time.get_ticks()
    first_state = None
    while first_state is None:
        if not client.connected:
            _cleanup_client_audio(); _show_disconnected(screen); return
        first_state = client.get_state() if client.get_state() else None
        if pygame.time.get_ticks() - wait_start > 10000:
            _cleanup_client_audio(); _show_disconnected(screen); return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _cleanup_client_audio(); client.stop(); pygame.quit(); import sys; sys.exit()
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

    # État précédent du joueur local pour détecter les changements d'inventaire
    prev_lp = {'current_weapon': None, 'has_melee': False, 'has_ranged': False,
               'has_pickaxe': False, 'has_boots': False, 'has_red_gem': False,
               'has_blue_gem': False, 'has_mirror': False, 'has_kitsune_mask': False,
               'has_cursed_brand': False, 'arrows': 0, 'health': 100}
    client_was_walking = False
    client_rp_was_walking = False
    client_red_gem_animating = False
    client_red_gem_anim_start = 0

    while True:
        if not client.connected:
            _cleanup_client_audio(); _show_disconnected(screen); return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _cleanup_client_audio(); client.stop(); pygame.quit(); import sys; sys.exit()

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
                        _cleanup_client_audio(); client.stop(); return

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
                _cleanup_client_audio(); return
            try:
                tmx_data = pytmx.util_pygame.load_pygame(levels[new_level])
            except Exception as e:
                print(f"Erreur carte client : {e}"); _cleanup_client_audio(); return

            map_data  = pyscroll.data.TiledMapData(tmx_data)
            map_layer = pyscroll.BufferedRenderer(map_data, (screen_width, screen_height))
            map_layer.zoom = zoom_level
            group = pyscroll.PyscrollGroup(map_layer=map_layer, default_layer=1)
            map_pixel_width  = tmx_data.width  * tmx_data.tilewidth
            map_pixel_height = tmx_data.height * tmx_data.tileheight

            remote_player = RemotePlayer(100, 100, char_type=host_char_type)
            local_player  = RemotePlayer(100, 100, char_type=client_char_type)
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
                ptype = pdata.get('type', 'projectile')
                if ptype == 'instant_aoe':
                    rp = InstantAOE(pdata['x'], pdata['y'],
                                    img_path=pdata.get('img_path'),
                                    explosion_radius=pdata.get('radius', 60))
                elif ptype == 'heal_effect':
                    rp = HealEffect(pdata['x'], pdata['y'],
                                    img_path=pdata.get('img_path'))
                elif ptype == 'homing':
                    # Le homing arrive déjà en explosion côté client
                    rp = Projectile(pdata['x'], pdata['y'], pdata['direction'])
                else:
                    rp = Projectile(pdata['x'], pdata['y'], pdata['direction'],
                                    img_path=pdata.get('img_path'))
                group.add(rp)
                remote_projectiles[pid] = rp
            else:
                rp = remote_projectiles[pid]
                rp.rect.centerx = pdata['x']
                rp.rect.centery = pdata['y']
                if hasattr(rp, 'hitbox'):
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

        # --- Sons spatialisés côté client ---
        # Le joueur local est l'index 1 (client)
        client_listener = (0, 0)
        if local_player:
            client_listener = (local_player.feet.centerx, local_player.feet.centery)

        # Map des noms de sons vers les clés du SoundManager
        _SPATIAL_SOUNDS = {
            'sword': 'sword', 'arrow': 'shot', 'enemy_death': 'shot',
            'dash': None,  # traité séparément (choix aléatoire)
            'rock_broke': 'rock_broke', 'eureka': 'eureka',
            'boss_activation': 'boss_activation', 'boss_attack': 'boss_attack',
            'boss_death': 'boss_death', 'boss_talk': 'boss_talk',
        }

        for snd_event in events_recv.get('sounds', []):
            # Les événements sont maintenant des dicts {'sound': ..., 'x': ..., 'y': ...}
            if isinstance(snd_event, dict):
                snd_name = snd_event.get('sound', '')
                src_pos = (snd_event.get('x', 0), snd_event.get('y', 0))
            else:
                # Compatibilité : anciennes chaînes sans position
                snd_name = snd_event
                src_pos = client_listener  # pas de position → volume max

            if snd_name == 'boss_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/boss1_soundtrack.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd_name == 'boss_bgm_stop':
                try:
                    pygame.mixer.music.fadeout(4000)
                except Exception:
                    pass
            elif snd_name == 'dash':
                sound_manager.play_spatial_dash(src_pos, client_listener)
            else:
                sound_key = _SPATIAL_SOUNDS.get(snd_name)
                if sound_key:
                    sound_manager.play_spatial(sound_key, src_pos, client_listener)

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

        # --- Marque Kitsune côté client ---
        if lp_now.get('has_kitsune_mask', False) and local_player:
            lp_cx = local_player.feet.centerx
            lp_cy = local_player.feet.centery - 30
            # Recalculer la caméra
            _view_w = screen_width / zoom_level
            _view_h = screen_height / zoom_level
            _cam_x = lp_cx
            _cam_y = lp_cy
            if map_pixel_width < _view_w: _cam_x = map_pixel_width // 2
            else: _cam_x = max(_view_w // 2, min(_cam_x, map_pixel_width - _view_w // 2))
            if map_pixel_height < _view_h: _cam_y = map_pixel_height // 2
            else: _cam_y = max(_view_h // 2, min(_cam_y, map_pixel_height - _view_h // 2))
            for edata in enemies_state:
                if edata.get('health', 0) > 0 and edata['health'] <= edata.get('max_health', 1) * 0.3:
                    ex = (edata['x'] - _cam_x) * zoom_level + screen_width / 2
                    ey_world = edata['y'] - 40
                    ey = (ey_world - _cam_y) * zoom_level + screen_height / 2
                    mark_size = 40  # taille par défaut client (pas de rect dispo)
                    mark = _get_kitsune_mark(mark_size)
                    screen.blit(mark, (ex - mark_size // 2, ey - mark_size // 2))

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

        # --- Sons d'inventaire personnels (détection de changements d'état) ---
        lp_now = players_state[1] if len(players_state) >= 2 else {}
        cur_weapon = lp_now.get('current_weapon')
        prev_weapon = prev_lp.get('current_weapon')

        # Changement d'arme (son UI personnel — soldier uniquement)
        if client_char_type == 'soldier' and cur_weapon != prev_weapon and cur_weapon is not None:
            if cur_weapon == 'melee':
                sound_manager.play_ui_equip_sword()
            elif cur_weapon == 'ranged':
                sound_manager.play_ui_equip_bow()

        # Nouvel objet obtenu (son UI personnel)
        if lp_now.get('has_boots') and not prev_lp.get('has_boots'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_pickaxe') and not prev_lp.get('has_pickaxe'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_red_gem') and not prev_lp.get('has_red_gem'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_blue_gem') and not prev_lp.get('has_blue_gem'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_mirror') and not prev_lp.get('has_mirror'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_kitsune_mask') and not prev_lp.get('has_kitsune_mask'):
            sound_manager.play_ui_equipement()
        if lp_now.get('has_cursed_brand') and not prev_lp.get('has_cursed_brand'):
            sound_manager.play_ui_equipement()

        # Red gem triggered → lancer l'animation fullscreen côté client
        if lp_now.get('red_gem_triggered', False):
            client_red_gem_animating = True
            client_red_gem_anim_start = pygame.time.get_ticks()

        # Mirror triggered
        if lp_now.get('mirror_triggered', False):
            if not hasattr(run_game_mp_client, '_client_mirror_animating'):
                run_game_mp_client._client_mirror_animating = False
            run_game_mp_client._client_mirror_animating = True
            run_game_mp_client._client_mirror_anim_start = pygame.time.get_ticks()

        # Cursed brand triggered (sur le joueur client = il subit les dégâts)
        if lp_now.get('cursed_brand_triggered', False):
            if not hasattr(run_game_mp_client, '_client_cb_animating'):
                run_game_mp_client._client_cb_animating = False
            run_game_mp_client._client_cb_animating = True
            run_game_mp_client._client_cb_anim_start = pygame.time.get_ticks()

        # Flèches ramassées (sans changement d'arme — soldier uniquement)
        if client_char_type == 'soldier' and lp_now.get('arrows', 0) > prev_lp.get('arrows', 0) and cur_weapon == prev_weapon:
            sound_manager.play_ui_equip_bow()

        # Pomme mangée (santé augmente sans raison de combat)
        if lp_now.get('health', 0) > prev_lp.get('health', 0) and prev_lp.get('health', 0) > 0:
            sound_manager.play_ui_eating()

        prev_lp = dict(lp_now)

        # --- Son de pas du joueur local (client) ---
        lp_moving = lp_now.get('state') in ('run', 'walk')
        if lp_moving and not client_was_walking:
            sound_manager.play_step()
            client_was_walking = True
        elif not lp_moving and client_was_walking:
            sound_manager.stop_step()
            client_was_walking = False

        # --- Pas spatialisés du joueur distant (host) ---
        rp_state_now = players_state[0] if len(players_state) >= 1 else {}
        rp_moving = rp_state_now.get('state') in ('run', 'walk')
        if rp_moving and not client_rp_was_walking:
            rp_pos = (rp_state_now.get('x', 0), rp_state_now.get('y', 0))
            sound_manager.play_remote_step(rp_pos, client_listener)
            client_rp_was_walking = True
        elif not rp_moving and client_rp_was_walking:
            sound_manager.stop_remote_step()
            client_rp_was_walking = False
        elif rp_moving and client_rp_was_walking:
            rp_pos = (rp_state_now.get('x', 0), rp_state_now.get('y', 0))
            sound_manager.update_remote_step_volume(rp_pos, client_listener)

        # --- Capturer et envoyer les inputs locaux ---
        keys = pygame.key.get_pressed()

        # Son d'attaque immédiat côté client (pas d'attente réseau) — spatialisé sur soi
        cur_wep = lp_now.get('current_weapon')
        if keys[pygame.K_e] and cur_wep and lp_now.get('health', 0) > 0:
            if not getattr(run_game_mp_client, '_client_attacking', False):
                sound_manager.play_spatial('sword', client_listener, client_listener)
                run_game_mp_client._client_attacking = True
        else:
            run_game_mp_client._client_attacking = False

        # Construire les inputs avec touches dynamiques pour items actifs
        # Ordre items actifs : boots, blue_gem, cursed_brand → touches 3, 4, 5...
        gem_blue_pressed = False
        cursed_brand_pressed = False
        dash_pressed = bool(keys[pygame.K_LSHIFT])
        active_key = 3
        if lp_now.get('has_boots'):
            if keys[getattr(pygame, f'K_{active_key}', 0)]:
                dash_pressed = True
            active_key += 1
        if lp_now.get('has_blue_gem'):
            if keys[getattr(pygame, f'K_{active_key}', 0)]:
                gem_blue_pressed = True
            active_key += 1
        if lp_now.get('has_cursed_brand'):
            if keys[getattr(pygame, f'K_{active_key}', 0)]:
                cursed_brand_pressed = True
            active_key += 1

        inputs = {
            'up':       bool(keys[pygame.K_z]),
            'down':     bool(keys[pygame.K_s]),
            'left':     bool(keys[pygame.K_q]),
            'right':    bool(keys[pygame.K_d]),
            'attack':   bool(keys[pygame.K_e]),
            'interact': bool(keys[pygame.K_f]),
            'dash':     dash_pressed,
            'weapon1':  bool(keys[pygame.K_1]),
            'weapon2':  bool(keys[pygame.K_2]),
            'gem_blue': gem_blue_pressed,
            'cursed_brand': cursed_brand_pressed,
        }
        client.send_inputs(inputs)

        # --- HUD joueur local (complet) ---
        lp_state = players_state[1] if len(players_state) >= 2 else {}
        ui.draw_health_bar(lp_state.get('health', 100), lp_state.get('max_health', 100))
        lp_char = lp_state.get('char_type', client_char_type)
        ui.draw_character_hud(lp_char, lp_state.get('current_weapon'),
                              skill_cooldowns=lp_state.get('skill_cooldowns', {}),
                              arrows=lp_state.get('arrows', 0),
                              has_pickaxe=lp_state.get('has_pickaxe', False),
                              has_boots=lp_state.get('has_boots', False),
                              dash_cr=lp_state.get('dash_cr', 1.0),
                              has_red_gem=lp_state.get('has_red_gem', False),
                              has_blue_gem=lp_state.get('has_blue_gem', False),
                              blue_gem_cr=lp_state.get('blue_gem_cr', 1.0),
                              has_mirror=lp_state.get('has_mirror', False),
                              has_kitsune_mask=lp_state.get('has_kitsune_mask', False),
                              has_cursed_brand=lp_state.get('has_cursed_brand', False),
                              cursed_brand_cr=lp_state.get('cursed_brand_cr', 1.0))

        # Barre de vie du joueur hôte (en haut à droite)
        rp_state = players_state[0] if len(players_state) >= 1 else {}
        _draw_remote_health(screen, rp_state.get('health', 100), rp_state.get('max_health', 100), label='HÔTE')

        # Barre de vie du boss (uniquement si aggro et vivant)
        for edata in enemies_state:
            if (edata.get('etype') in ('bigenemy', 'necromancer')
                    and edata.get('has_aggro', False)
                    and edata.get('health', 0) > 0):
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
                _cleanup_client_audio(); client.stop(); return
        else:
            death_time = None
            death_sound_played = False

        # --- Animation Red Gem (fullscreen côté client) ---
        if client_red_gem_animating:
            elapsed_rg = pygame.time.get_ticks() - client_red_gem_anim_start
            if elapsed_rg < 1000:
                if elapsed_rg < 300:
                    alpha = int(255 * (elapsed_rg / 300.0))
                elif elapsed_rg < 700:
                    alpha = 255
                else:
                    alpha = int(255 * (1.0 - (elapsed_rg - 700) / 300.0))
                try:
                    gem_img = pygame.image.load("assets/images/redgem.png").convert_alpha()
                    gem_img = pygame.transform.scale(gem_img, (128, 128))
                    gem_img.set_alpha(alpha)
                    gem_rect = gem_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    overlay.fill((255, 50, 50, int(alpha * 0.4)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(gem_img, gem_rect)
                except Exception:
                    pass
            else:
                client_red_gem_animating = False

        # --- Animation Mirror (fullscreen côté client) ---
        if getattr(run_game_mp_client, '_client_mirror_animating', False):
            elapsed_m = pygame.time.get_ticks() - run_game_mp_client._client_mirror_anim_start
            if elapsed_m < 800:
                if elapsed_m < 200: alpha = int(255 * (elapsed_m / 200.0))
                elif elapsed_m < 500: alpha = 255
                else: alpha = int(255 * (1.0 - (elapsed_m - 500) / 300.0))
                try:
                    mir_img = pygame.image.load("assets/images/mirror.png").convert_alpha()
                    mir_img = pygame.transform.scale(mir_img, (128, 128))
                    mir_img.set_alpha(alpha)
                    mir_rect = mir_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    overlay.fill((180, 180, 255, int(alpha * 0.3)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(mir_img, mir_rect)
                except Exception:
                    pass
            else:
                run_game_mp_client._client_mirror_animating = False

        # --- Animation Cursed Brand (fullscreen côté client) ---
        if getattr(run_game_mp_client, '_client_cb_animating', False):
            elapsed_cb = pygame.time.get_ticks() - run_game_mp_client._client_cb_anim_start
            if elapsed_cb < 800:
                if elapsed_cb < 200: alpha = int(255 * (elapsed_cb / 200.0))
                elif elapsed_cb < 500: alpha = 255
                else: alpha = int(255 * (1.0 - (elapsed_cb - 500) / 300.0))
                try:
                    cb_img = pygame.image.load("assets/images/cursed_brand.png").convert_alpha()
                    cb_img = pygame.transform.scale(cb_img, (128, 128))
                    cb_img.set_alpha(alpha)
                    cb_rect = cb_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    overlay.fill((150, 50, 150, int(alpha * 0.3)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(cb_img, cb_rect)
                except Exception:
                    pass
            else:
                run_game_mp_client._client_cb_animating = False

        pygame.display.flip()
        clock.tick(60)


# =============================================================================
# HELPERS PARTAGÉS
# =============================================================================

_kitsune_mark_cache = {}  # size → Surface
_kitsune_mark_base = None

def _get_kitsune_mark(size):
    """Retourne la marque kitsune mise en cache pour une taille donnée."""
    global _kitsune_mark_base
    if size in _kitsune_mark_cache:
        return _kitsune_mark_cache[size]
    if _kitsune_mark_base is None:
        try:
            _kitsune_mark_base = pygame.image.load("assets/images/griffe_passif.png").convert_alpha()
        except Exception:
            _kitsune_mark_base = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(_kitsune_mark_base, (255, 50, 50, 200), (16, 16), 16)
    mark = pygame.transform.scale(_kitsune_mark_base, (size, size))
    _kitsune_mark_cache[size] = mark
    return mark


def _get_active_item_keys(player):
    """Retourne la liste des items actifs avec leur touche assignée.
    Ordre : boots, blue_gem, cursed_brand. Touches : 3, 4, 5..."""
    items = []
    key_num = 3
    if player.has_boots:
        items.append((key_num, 'boots')); key_num += 1
    if player.has_blue_gem:
        items.append((key_num, 'bluegem')); key_num += 1
    if player.has_cursed_brand:
        items.append((key_num, 'cursed_brand')); key_num += 1
    return items


def _count_inventory_items(player):
    """Compte le nombre total d'items dans l'inventaire."""
    count = 0
    if player.has_pickaxe: count += 1
    if player.has_boots: count += 1
    if player.has_red_gem: count += 1
    if player.has_blue_gem: count += 1
    if player.has_mirror: count += 1
    if player.has_kitsune_mask: count += 1
    if player.has_cursed_brand: count += 1
    return count


def _handle_weapon_switch(player, slot, sound_manager):
    """Gère le changement d'arme/compétence pour un joueur.
    slot: 1 ou 2 (touche clavier)."""
    char_def = player.char_def
    abilities = char_def.get('abilities', {})
    ct = player.char_type

    if ct == 'soldier':
        # Soldier : 1 = épée, 2 = arc
        if slot == 1 and player.has_melee and player.current_weapon != 'melee':
            player.switch_weapon('melee')
            if sound_manager: sound_manager.play_ui_equip_sword()
        elif slot == 2 and player.has_ranged and player.current_weapon != 'ranged':
            player.switch_weapon('ranged')
            if sound_manager: sound_manager.play_ui_equip_bow()

    elif ct == 'swordsman':
        # Swordsman : 1 = skill1 (3 salves), 2 = skill2 (5 salves)
        # Activation directe — le melee de base reste sur E
        if slot == 1 and 'skill1' in abilities:
            player.use_skill('skill1')
        elif slot == 2 and 'skill2' in abilities:
            player.use_skill('skill2')

    elif ct == 'archer':
        # Archer : 1 = arc, 2 = flèche d'or (skill1)
        if slot == 1 and player.has_ranged and player.current_weapon != 'ranged':
            player.switch_weapon('ranged')
        elif slot == 2 and 'skill1' in abilities and player.current_weapon != 'skill1':
            player.switch_weapon('skill1')

    elif ct == 'wizard':
        # Wizard : 1 = skill1 (fireball), 2 = skill2 (cristal)
        if slot == 1 and 'skill1' in abilities and player.current_weapon != 'skill1':
            player.switch_weapon('skill1')
        elif slot == 2 and 'skill2' in abilities and player.current_weapon != 'skill2':
            player.switch_weapon('skill2')

    elif ct == 'priest':
        # Priest : 1 = skill1 (onde), 2 = skill2 (heal)
        if slot == 1 and 'skill1' in abilities and player.current_weapon != 'skill1':
            player.switch_weapon('skill1')
        elif slot == 2 and 'skill2' in abilities and player.current_weapon != 'skill2':
            player.switch_weapon('skill2')


def _apply_skill_result(skill_result, caster, group, projectiles_group,
                        particles_group, enemies_group, items_group,
                        sound_manager, sound_events, listener_pos, next_id_fn):
    """Applique les résultats d'une compétence active."""
    # Dégâts de mêlée en zone (Swordsman)
    for enemy, damage in skill_result.get('melee_hits', []):
        dmg = damage * caster.get_damage_multiplier()
        if caster.has_kitsune_mask and enemy.health <= enemy.max_health * 0.3:
            dmg *= 1.5
        enemy.damage(dmg)
        if enemy.health <= 0:
            e_pos = (enemy.feet.centerx, enemy.feet.centery)
            sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
        _handle_enemy_death(enemy, group, items_group, particles_group)

    # Projectile (Wizard fireball, Archer golden arrow)
    proj = skill_result.get('projectile')
    if proj:
        proj._mp_id = next_id_fn()
        proj._owner = caster
        group.add(proj)
        projectiles_group.add(proj)
        src_pos = (caster.feet.centerx, caster.feet.centery)
        sound_manager.play_spatial('shot', src_pos, listener_pos)
        sound_events.append({'sound': 'arrow', 'x': src_pos[0], 'y': src_pos[1]})

    # Instant AOE (orbe cristal, onde destructrice) — spawn directement sur l'ennemi
    homing = skill_result.get('homing')
    if homing:
        target_pos = homing['target_pos']
        # Créer l'effet d'explosion directement sur la cible
        aoe = InstantAOE(
            target_pos[0], target_pos[1],
            damage=homing['damage'], explosion_radius=homing['radius'],
            img_path=homing.get('effect_img'), effect_frames=homing.get('effect_frames', 5),
            target_size=homing.get('target_size', 48),
            render_scale=homing.get('render_scale', 1.2)
        )
        aoe._mp_id = next_id_fn()
        aoe._owner = caster
        group.add(aoe)
        projectiles_group.add(aoe)
        sound_manager.play_spatial('shot', target_pos, listener_pos)
        sound_events.append({'sound': 'arrow', 'x': target_pos[0], 'y': target_pos[1]})

    # Heal (Priest)
    heal_data = skill_result.get('heal')
    if heal_data and heal_data.get('target'):
        target = heal_data['target']
        target.heal(heal_data['amount'])
        # Effet visuel de soin
        heal_fx = HealEffect(
            heal_data['target_pos'][0], heal_data['target_pos'][1],
            img_path=heal_data.get('effect_img'),
            effect_frames=heal_data.get('effect_frames', 4)
        )
        heal_fx._mp_id = next_id_fn()
        group.add(heal_fx)
        particles_group.add(heal_fx)
        projectiles_group.add(heal_fx)  # pour la sérialisation réseau

    # Échec de compétence homing (aucun ennemi à portée)
    if skill_result.get('fail'):
        # Annuler le cooldown pour que le joueur puisse réessayer
        if caster.active_skill:
            # Trouver le skill_name correspondant à l'animation active
            for sk_name, sk_def in caster.abilities.items():
                if sk_def.get('anim') == caster.active_skill:
                    caster.reset_skill_cooldown(sk_name)
                    break
        # Texte flottant "fail..."
        ft = FloatingText(caster.feet.centerx, caster.feet.centery)
        group.add(ft)
        particles_group.add(ft)


def _pickup_item(player, item, sound_manager):
    """Ramasse un item. sound_manager sert uniquement pour les sons UI du host.
    Passer None pour player2 (le client gère ses propres sons).
    Retourne True si l'item a été ramassé, False sinon."""
    # Items consommables (pas de slot d'inventaire) : toujours ramassables
    if item.item_type == 'arrow':
        player.arrows += random.randint(1, 4)
        if sound_manager: sound_manager.play_ui_equip_bow()
        return True
    elif item.item_type == 'apple':
        player.heal(player.max_health * 0.10)
        if sound_manager: sound_manager.play_ui_eating()
        return True
    elif item.item_type == 'melee':
        player.has_melee = True
        if player.current_weapon != 'melee':
            player.current_weapon = 'melee'
            if sound_manager: sound_manager.play_ui_equip_sword()
        return True
    elif item.item_type == 'ranged':
        if not player.has_ranged: player.arrows += 10
        player.has_ranged = True
        if player.current_weapon != 'ranged':
            player.current_weapon = 'ranged'
            if sound_manager: sound_manager.play_ui_equip_bow()
        return True

    # Items d'inventaire : vérifier la limite de 8 slots
    if _count_inventory_items(player) >= 8:
        return False  # Inventaire plein

    if item.item_type == 'pickaxe':
        player.has_pickaxe = True
    elif item.item_type == 'boots':
        player.has_boots = True
        if sound_manager: sound_manager.play_ui_equipement()
    elif item.item_type == 'redgem':
        player.has_red_gem = True
        if sound_manager: sound_manager.play_ui_equipement()
    elif item.item_type == 'bluegem':
        player.has_blue_gem = True
        if sound_manager: sound_manager.play_ui_equipement()
    elif item.item_type == 'mirror':
        player.has_mirror = True
        if sound_manager: sound_manager.play_ui_equipement()
    elif item.item_type == 'kitsune_mask':
        player.has_kitsune_mask = True
        if sound_manager: sound_manager.play_ui_equipement()
    elif item.item_type == 'cursed_brand':
        player.has_cursed_brand = True
        if sound_manager: sound_manager.play_ui_equipement()
    else:
        return False
    return True


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