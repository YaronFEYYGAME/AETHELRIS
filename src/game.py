import pygame
import pytmx
import pyscroll
import random

from player import Player, RemotePlayer
from sound import SoundManager
from enemy import Enemy, RemoteEnemy
from bosses import BigEnemy, Necromancer, Spirit, Medusa, KingBoss, SbireNeant
from mobs import Orc, Fairy, Skeleton, Slime, OrcRider, EliteOrc, GreatswordSkeleton, SkeletonArcher
from ui import UI
from item import Item
from projectile import Projectile, HomingProjectile, HealEffect, InstantAOE, FloatingText
from obstacle import Rock, RockParticle, BloodParticle, SmokeParticle, DarkParticle, Chest
from characters import get_character_def
from character_select import character_select_screen_host, character_select_screen_client, character_select_screen_solo
from resource_manager import ResourceManager

# Fonction utilitaire pour dessiner les hitboxes par-dessus le zoom de la caméra
def draw_debug_rect(screen, world_rect, color, camera_x, camera_y, zoom, screen_width, screen_height):
    if not world_rect: return
    screen_x = (world_rect.x - camera_x) * zoom + screen_width / 2
    screen_y = (world_rect.y - camera_y) * zoom + screen_height / 2
    screen_w = world_rect.width * zoom
    screen_h = world_rect.height * zoom
    pygame.draw.rect(screen, color, (screen_x, screen_y, screen_w, screen_h), 2)


def _spawn_damage_number(enemy, actual_damage, attacker, group, particles_group, is_crit=False):
    """Crée un texte flottant de dégâts au-dessus de l'ennemi touché.
    La couleur dépend du ratio dégâts réels / dégâts de base du personnage.
    La taille de police est proportionnelle au scale_factor de l'ennemi."""
    # Dégâts de base du personnage (melee ou ranged selon l'arme courante)
    base_dmg = 1
    if attacker and hasattr(attacker, 'char_def'):
        if getattr(attacker, 'current_weapon', 'melee') == 'ranged':
            base_dmg = attacker.char_def.get('ranged_damage', 10.5)
        else:
            base_dmg = attacker.char_def.get('melee_damage', 10)
        # Pour les personnages à skills (Wizard, Priest) dont melee/ranged_damage = 0,
        # on prend le dégât brut minimum de leurs abilities comme base de référence.
        if base_dmg <= 0:
            base_dmg = max(attacker.char_def.get('melee_damage', 0),
                           attacker.char_def.get('ranged_damage', 0))
            if base_dmg <= 0:
                abilities = attacker.char_def.get('abilities', {})
                skill_dmgs = [s.get('damage', 0) for s in abilities.values() if s.get('damage', 0) > 0]
                base_dmg = min(skill_dmgs) if skill_dmgs else 1

    # Couleur selon le ratio de bonus
    if actual_damage >= 2.5 * base_dmg:
        color = (200, 50, 255)    # Violet — +150% ou plus
    elif actual_damage >= 2.0 * base_dmg:
        color = (255, 230, 0)     # Jaune — +100%
    elif actual_damage >= 1.5 * base_dmg:
        color = (255, 150, 0)     # Orange — +50%
    else:
        color = (255, 50, 50)     # Rouge — normal
    # Un coup critique garantit au minimum la couleur jaune
    if is_crit and color == (255, 50, 50):
        color = (255, 230, 0)

    # Taille de police proportionnelle à l'ennemi
    scale = getattr(enemy, 'scale_factor', 1.7)
    font_size = max(12, min(32, int(12 * scale)))

    # Position : côté gauche ou droit au hasard, jamais centré
    # Les boss (aggro_radius) ont un grand sprite → offset plus large et plus haut
    is_boss = hasattr(enemy, 'aggro_radius')
    side = random.choice((-1, 1))
    if is_boss:
        ox = side * random.randint(40, 70)
        oy = random.randint(-15, 5)
        # Partir du centre du rect pour être au milieu du sprite, pas aux pieds
        x = enemy.rect.centerx + ox
        y = enemy.rect.centery + 30 + oy  # +30 pour descendre légèrement, FloatingText ajoute -40
    else:
        ox = side * random.randint(15, 30)
        oy = random.randint(-10, 10)
        x = enemy.feet.centerx + ox
        y = enemy.feet.centery + 30 + oy  # +30 pour compenser le -40 de FloatingText

    ft = FloatingText(x, y, text=str(int(actual_damage)),
                      duration=500, color=color, font_size=font_size)
    group.add(ft)
    particles_group.add(ft)


class Decoy(pygame.sprite.Sprite):
    """Leurre immobile créé par la Cape de l'assassin.
    Sprite = idle frame du joueur, teinté marron. Attire l'aggro des ennemis."""

    _tint_cache = {}  # cache partagé pour éviter de recalculer la teinte chaque frame

    def __init__(self, x, y, player):
        super().__init__()
        # Récupérer la frame idle du joueur (direction courante)
        idle_anim = player.animations.get(player.facing, {}).get('idle', [])
        if idle_anim:
            base_frame = idle_anim[0]
        else:
            base_frame = player.image

        # Teinte marron via cache
        cache_key = (id(base_frame), player.facing)
        if cache_key not in Decoy._tint_cache:
            tinted = base_frame.copy()
            tinted.fill((140, 80, 40, 255), special_flags=pygame.BLEND_RGBA_MULT)
            Decoy._tint_cache[cache_key] = tinted
        self.image = Decoy._tint_cache[cache_key]

        self.rect = self.image.get_rect()
        # Hitbox pieds — même position que le joueur au moment de l'activation
        self.feet = pygame.Rect(0, 0, 15, 15)
        self.feet.midbottom = player.feet.midbottom
        # Positionner le rect comme le joueur : rect.bottom = feet.bottom
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom
        self.health = 50
        self.max_health = 50
        self.position = pygame.math.Vector2(self.feet.centerx, self.feet.bottom)
        self._is_player_decoy = True  # Immunité aux attaques du joueur propriétaire

    def damage(self, amount, source_enemy=None):
        """Le leurre encaisse les coups."""
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.kill()


def run_game(screen, start_music_vol=0.5, start_sfx_vol=0.8):
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    ui = UI(screen)
    sound_manager = SoundManager()
    font = ResourceManager.get_font(60, None)

    death_font = ResourceManager.get_font(120, "old english text mt, garamond, times new roman, serif") 
    
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
    DEBUG_HITBOXES = True

    # Items déjà droppés par les coffres (persiste entre niveaux, pas de doublon)
    chest_dropped_items = set()
    CHEST_DROPPABLE_ITEMS = [
        'boots', 'redgem', 'bluegem', 'mirror', 'kitsune_mask',
        'cursed_brand', 'travelers_cap', 'zhonya', 'rabadon',
    ]

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
        chests_group = pygame.sprite.Group()

        walls = []
        exit_zones = []
        player_x, player_y = 100, 100

        for obj in tmx_data.objects:
            # Robustesse Tiled : obj.type OU obj.name selon la version de Tiled
            obj_type = (obj.type or obj.name or "").lower()

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
                print(f"[SPAWN] Enemy en ({obj.x}, {obj.y})")
            elif obj_type == "orc":
                new_enemy = Orc(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] Orc en ({obj.x}, {obj.y})")
            elif obj_type == "slime":
                new_enemy = Slime(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] Slime en ({obj.x}, {obj.y})")
            elif obj_type == "skeleton":
                new_enemy = Skeleton(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] Skeleton en ({obj.x}, {obj.y})")
            elif obj_type == "orc_rider":
                new_enemy = OrcRider(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] OrcRider en ({obj.x}, {obj.y})")
            elif obj_type == "elite_orc":
                new_enemy = EliteOrc(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] EliteOrc en ({obj.x}, {obj.y})")
            elif obj_type == "greatsword_skeleton":
                new_enemy = GreatswordSkeleton(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] GreatswordSkeleton en ({obj.x}, {obj.y})")
            elif obj_type == "skeleton_archer":
                new_enemy = SkeletonArcher(obj.x, obj.y)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
                print(f"[SPAWN] SkeletonArcher en ({obj.x}, {obj.y})")
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
            elif obj_type == "medusa":
                new_enemy = Medusa(obj.x, obj.y)
                if hasattr(new_enemy, 'update_volumes'):
                    new_enemy.update_volumes(global_music_vol, global_sfx_vol)
                group.add(new_enemy)
                enemies_group.add(new_enemy)
            elif obj_type == "sbire_neant":
                new_enemy = SbireNeant(obj.x, obj.y)
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
            elif obj_type == "travelers_cap":
                new_item = Item(obj.x, obj.y, 'travelers_cap')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "zhonya":
                new_item = Item(obj.x, obj.y, 'zhonya')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "rabadon":
                new_item = Item(obj.x, obj.y, 'rabadon')
                group.add(new_item)
                items_group.add(new_item)
            elif obj_type == "obstacle_rock":
                new_rock = Rock(obj.x, obj.y)
                group.add(new_rock)
                rocks_group.add(new_rock)
                walls.append(new_rock.hitbox)
            elif obj_type == "chest_right":
                c = Chest(obj.x, obj.y, flipped=False)
                group.add(c); chests_group.add(c)
                walls.append(c.hitbox)
            elif obj_type == "chest_left":
                c = Chest(obj.x, obj.y, flipped=True)
                group.add(c); chests_group.add(c)
                walls.append(c.hitbox)

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

        # --- Interface d'obtention d'item (coffre) ---
        chest_ui_active = False
        chest_ui_item = None
        chest_ui_start_time = 0
        chest_ui_closing = False
        chest_ui_close_time = 0
        CHEST_UI_FADE_IN = 300
        CHEST_UI_FADE_OUT = 300

        # --- Arrêt du temps (Casquette du voyageur) ---
        time_stop_active = False
        time_stop_end_time = 0
        time_stop_activator = None
        time_stop_return_sound_played = False
        time_stop_player_cache = {}      # cache des sprites joueur scalés par frame d'anim

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
                            
                        if player.health > 0 and not player.is_stunned:
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

                                # --- Interaction coffres (solo) ---
                                if not time_stop_active:
                                    for chest in chests_group:
                                        if not chest.opened and not chest.opening:
                                            if player.feet.colliderect(chest.hitbox.inflate(40, 40)):
                                                chest.open()
                                                _grant_xp(50, [player], group, particles_group, sound_manager)
                                                available = [it for it in CHEST_DROPPABLE_ITEMS
                                                             if it not in chest_dropped_items]
                                                if available:
                                                    chosen = random.choice(available)
                                                    chest_dropped_items.add(chosen)
                                                    if player.add_inventory_item(chosen):
                                                        pass  # ajouté à l'inventaire
                                                    else:
                                                        drop = Item(chest.rect.centerx, chest.rect.bottom + 10, chosen)
                                                        group.add(drop); items_group.add(drop)
                                                    # Afficher l'interface d'obtention
                                                    chest_ui_active = True
                                                    chest_ui_item = chosen
                                                    chest_ui_start_time = pygame.time.get_ticks()
                                                    chest_ui_closing = False
                                                    sound_manager.play_ui_get_item()
                                                break

                            if event.key == pygame.K_RETURN:
                                if chest_ui_active and not chest_ui_closing:
                                    chest_ui_closing = True
                                    chest_ui_close_time = pygame.time.get_ticks()

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_j: show_mmo = False

            if not level_running:
                continue

            if is_paused:
                group.draw(screen)
                ui.draw_health_bar(player.health, player.max_health)
                ui.draw_stamina_bar(player.stamina, player.max_stamina)
                ui.draw_xp_bar(player.xp, player.xp_to_next_level, player.level)
                _lu_elapsed = pygame.time.get_ticks() - player.level_up_time
                if _lu_elapsed < 2000:
                    ui.draw_level_up_message(_lu_elapsed / 2000.0, screen_width // 2, screen_height // 2)
                ui.draw_weapon_icon(player.current_weapon)
                ui.draw_pickaxe_icon(player.has_pickaxe)
                ui.draw_ammo_count(player.current_weapon, player.arrows)

                cooldown_ratio = (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown
                cooldown_ratio = min(1.0, max(0.0, cooldown_ratio))
                ui.draw_boots_icon(player.has_boots, cooldown_ratio)

                for enemy in enemies_group:
                    if getattr(enemy, 'has_aggro', False) and getattr(enemy, 'health', 0) > 0:
                        if isinstance(enemy, Medusa):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Médusa")
                        elif isinstance(enemy, SbireNeant):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Sbire du neant")
                        elif isinstance(enemy, BigEnemy):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Gardien des profondeurs")
                        elif isinstance(enemy, Necromancer):
                            ui.draw_boss_health_bar(enemy.health, enemy.max_health, "La Faucheuse")

                for enemy in enemies_group:
                    dialogue_text = getattr(enemy, 'get_current_dialogue', lambda: None)()
                    if dialogue_text:
                        ui.draw_boss_dialogue(dialogue_text, getattr(enemy, 'boss_display_name', None))
                        break

                pause_rects = ui.draw_pause_menu(global_music_vol, global_sfx_vol)
                pygame.display.flip()
                clock.tick(60)
                continue 

            player.update()
            player.update_stamina()
            player.move(walls)

            ppos = (player.feet.centerx, player.feet.centery)

            # --- Arrêt du temps : expiration ---
            if time_stop_active:
                now_ts = pygame.time.get_ticks()
                if not time_stop_return_sound_played and now_ts >= time_stop_end_time - 500:
                    sound_manager.play_ui_return_time()
                    time_stop_return_sound_played = True
                if now_ts >= time_stop_end_time:
                    time_stop_active = False
                    time_stop_activator = None
                    time_stop_player_cache = {}
                    sound_manager.exit_time_stop()
                    # Prolonger les timers figés de 5 secondes
                    for enemy in enemies_group:
                        if getattr(enemy, 'paralyzed', False) and hasattr(enemy, 'paralyze_end_time'):
                            enemy.paralyze_end_time += 5000
                        if hasattr(enemy, 'last_attack_time'):
                            enemy.last_attack_time += 5000

            if not time_stop_active:
                # Snapshot des spirits avant update pour détecter ceux qui meurent
                spirits_before = {id(e): e for e in enemies_group if isinstance(e, Spirit)}

                for enemy in list(enemies_group):
                    # Sauvegarder la position du spirit avant update (au cas où il se kill)
                    spirit_pos = None
                    if isinstance(enemy, Spirit):
                        spirit_pos = (enemy.rect.centerx, enemy.rect.centery)

                    if isinstance(enemy, (KingBoss, SbireNeant)):
                        enemy.update(player, walls, player2=None)
                    else:
                        enemy.update(player, walls)

                    # SbireNeant : particules de teleportation
                    if isinstance(enemy, SbireNeant) and enemy.pending_teleports:
                        for (fx, fy, tx, ty) in enemy.pending_teleports:
                            for _ in range(15):
                                p = SmokeParticle(fx + random.randint(-15, 15), fy + random.randint(-15, 5))
                                group.add(p); particles_group.add(p)
                            for _ in range(15):
                                p = SmokeParticle(tx + random.randint(-15, 15), ty + random.randint(-15, 5))
                                group.add(p); particles_group.add(p)
                        enemy.pending_teleports.clear()

                    # Spirit qui a explosé ou est mort : spawner des particules rouges
                    if isinstance(enemy, Spirit) and getattr(enemy, 'pending_particles', False):
                        if spirit_pos:
                            for _ in range(15):
                                particle = BloodParticle(spirit_pos[0], spirit_pos[1])
                                group.add(particle)
                                particles_group.add(particle)

                    if hasattr(enemy, 'pending_summons') and enemy.pending_summons:
                        owner_ref = enemy if isinstance(enemy, Necromancer) else None
                        for sx, sy in enemy.pending_summons:
                            new_spirit = Spirit(sx, sy, owner_necromancer=owner_ref)
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
                            elif bs == 'necro_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/necromancer_song.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'medusa_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/medusa_ost.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'king_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/king_boss_ost.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'sbire_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/sbire_neant.mp3")
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
            chests_group.update()

            show_rock_dialogue = False
            if not player.has_pickaxe and player.health > 0:
                for rock in rocks_group:
                    detect_zone = rock.hitbox.inflate(40, 40)
                    if player.feet.colliderect(detect_zone):
                        show_rock_dialogue = True
                        break

            show_chest_dialogue = False
            if player.health > 0 and not time_stop_active:
                for chest in chests_group:
                    if not chest.opened and not chest.opening:
                        if player.feet.colliderect(chest.hitbox.inflate(40, 40)):
                            show_chest_dialogue = True
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
                    if type_attack == 'no_stamina':
                        _now = pygame.time.get_ticks()
                        if _now - player._last_no_stamina_ft_time > 1000:
                            player._last_no_stamina_ft_time = _now
                            ft = FloatingText(player.feet.centerx, player.feet.centery, text="Endurance insuffisante...")
                            group.add(ft); particles_group.add(ft)
                    elif type_attack == 'melee':
                        sound_manager.play_spatial('sword', ppos, ppos)
                        for enemy in enemies_group:
                            if getattr(enemy, 'health', 0) > 0 and data.colliderect(enemy.feet):
                                dmg = player.melee_damage * player.get_damage_multiplier(target_enemy=enemy)
                                enemy.damage(dmg)
                                _spawn_damage_number(enemy, dmg, player, group, particles_group)
                                player.lifesteal(dmg)

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
                                    # --- XP ---
                                    if not getattr(enemy, '_xp_granted', False):
                                        enemy._xp_granted = True
                                        xp = _get_enemy_xp(enemy)
                                        _grant_xp(xp, [player], group, particles_group, sound_manager)

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
                        ext = 50 if isinstance(enemy, (BigEnemy, Necromancer, Medusa, KingBoss, SbireNeant)) else 25
                        body_hitbox.height += ext
                        body_hitbox.y -= ext
                        if projectile.hitbox.colliderect(body_hitbox):
                            # Piercing : skip les ennemis déjà touchés
                            if getattr(projectile, 'piercing', False):
                                if id(enemy) in projectile._hit_enemies:
                                    continue
                                projectile._hit_enemies.add(id(enemy))

                            hit_pos = (projectile.hitbox.centerx, projectile.hitbox.centery)
                            sound_manager.play_spatial('shot', hit_pos, ppos)
                            proj_dmg = projectile.damage_amount * player.get_damage_multiplier(target_enemy=enemy)
                            enemy.damage(proj_dmg)
                            _spawn_damage_number(enemy, proj_dmg, player, group, particles_group)

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
                                # --- XP ---
                                if not getattr(enemy, '_xp_granted', False):
                                    enemy._xp_granted = True
                                    xp = _get_enemy_xp(enemy)
                                    _grant_xp(xp, [player], group, particles_group, sound_manager)

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

            # --- Effet visuel arrêt du temps (overlay gris + joueur en couleur) ---
            if time_stop_active:
                # Overlay gris semi-transparent sur tout l'écran
                ts_overlay = _get_overlay(screen_width, screen_height)
                ts_overlay.fill((0, 0, 0, 110))
                screen.blit(ts_overlay, (0, 0))

                # Joueur activateur en couleur par-dessus (cache par frame d'anim)
                p_sx = (player.rect.x - camera_x) * zoom_level + screen_width / 2
                p_sy = (player.rect.y - camera_y) * zoom_level + screen_height / 2
                cache_key = (int(player.frame_index), player.facing, player.state)
                if cache_key not in time_stop_player_cache:
                    time_stop_player_cache[cache_key] = pygame.transform.scale(
                        player.image,
                        (int(player.rect.width * zoom_level),
                         int(player.rect.height * zoom_level))
                    )
                screen.blit(time_stop_player_cache[cache_key], (p_sx, p_sy))

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
            ui.draw_stamina_bar(player.stamina, player.max_stamina)
            ui.draw_xp_bar(player.xp, player.xp_to_next_level, player.level)
            _lu_elapsed = pygame.time.get_ticks() - player.level_up_time
            if _lu_elapsed < 2000:
                ui.draw_level_up_message(_lu_elapsed / 2000.0, screen_width // 2, screen_height // 2)
            ui.draw_weapon_icon(player.current_weapon)
            ui.draw_pickaxe_icon(player.has_pickaxe)
            ui.draw_ammo_count(player.current_weapon, player.arrows)

            cooldown_ratio = (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown
            cooldown_ratio = min(1.0, max(0.0, cooldown_ratio))
            ui.draw_boots_icon(player.has_boots, cooldown_ratio)
            
            for enemy in enemies_group:
                if getattr(enemy, 'has_aggro', False) and getattr(enemy, 'health', 0) > 0:
                    if isinstance(enemy, SbireNeant):
                        ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Sbire du neant")
                    elif isinstance(enemy, BigEnemy):
                        ui.draw_boss_health_bar(enemy.health, enemy.max_health, "Gardien des profondeurs")
                    elif isinstance(enemy, Necromancer):
                        ui.draw_boss_health_bar(enemy.health, enemy.max_health, "La Faucheuse")

            # Dialogues de boss
            for enemy in enemies_group:
                dialogue_text = getattr(enemy, 'get_current_dialogue', lambda: None)()
                if dialogue_text:
                    ui.draw_boss_dialogue(dialogue_text, getattr(enemy, 'boss_display_name', None))
                    break

            if show_exit_dialogue:
                ui.draw_dialogue("Voulez vous rentrer ? (A)")
            elif show_rock_dialogue:
                ui.draw_dialogue("Le chemin semble bloqué...")
            elif show_chest_dialogue:
                ui.draw_dialogue("Appuyer sur F pour ouvrir")

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

            # --- Interface coffre (solo) ---
            if chest_ui_active:
                now = pygame.time.get_ticks()
                if chest_ui_closing:
                    elapsed = now - chest_ui_close_time
                    if elapsed >= CHEST_UI_FADE_OUT:
                        chest_ui_active = False
                    else:
                        alpha = int(255 * (1.0 - elapsed / CHEST_UI_FADE_OUT))
                        ui.draw_chest_item_ui(chest_ui_item, alpha)
                else:
                    elapsed = now - chest_ui_start_time
                    alpha = min(255, int(255 * elapsed / CHEST_UI_FADE_IN))
                    ui.draw_chest_item_ui(chest_ui_item, alpha)

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
        # max_health invariant (toujours 100) → non transmis chaque frame
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
        'has_travelers_cap': p.has_travelers_cap,
        'travelers_cap_cr': p.get_travelers_cap_cooldown_ratio(),
        'has_zhonya':     p.has_zhonya,
        'zhonya_cr':      p.get_zhonya_cooldown_ratio(),
        'has_rabadon':    p.has_rabadon,
        'arrows':         p.arrows,
        'dash_cr':        dash_cr,
        'arrow_regen_cr': p.get_arrow_regen_cooldown_ratio(),
        # char_type invariant — le client connaît déjà son propre type via la sélection
        'skill_cooldowns': skill_crs,
        'inventory_items': getattr(p, 'inventory_items', []),
        'item_start_key': p.char_def.get('item_start_key', 2),
        'is_stunned': getattr(p, 'is_stunned', False),
        'stamina': getattr(p, 'stamina', 100),
        'max_stamina': getattr(p, 'max_stamina', 100),
        'xp': getattr(p, 'xp', 0),
        'xp_to_next_level': getattr(p, 'xp_to_next_level', 100),
        'level': getattr(p, 'level', 1),
        'level_up_time': getattr(p, 'level_up_time', 0),
    }


def _serialize_enemy(e):
    if isinstance(e, Medusa):
        etype = 'medusa'
    elif isinstance(e, SbireNeant):
        etype = 'sbire'
    elif isinstance(e, KingBoss):
        etype = 'king'
    elif isinstance(e, Necromancer):
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
        'mob_name':  getattr(e, 'name', None),
        'has_aggro': getattr(e, 'has_aggro', False),
        'paralyzed': getattr(e, 'paralyzed', False),
        'dialogue_text': getattr(e, 'get_current_dialogue', lambda: None)(),
        'boss_display_name': getattr(e, 'boss_display_name', None),
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
    player_inv_items = []
    player2_inv_items = []
    player_has_melee = False
    player_has_ranged = False
    player_arrows = 0

    global_music_vol = start_music_vol
    global_sfx_vol   = start_sfx_vol
    is_paused  = False
    pause_rects = {}
    zoom_level = 3.8
    DEBUG_HITBOXES = True

    chest_dropped_items = set()
    CHEST_DROPPABLE_ITEMS = [
        'boots', 'redgem', 'bluegem', 'mirror', 'kitsune_mask',
        'cursed_brand', 'travelers_cap', 'zhonya', 'rabadon',
    ]

    sound_manager.update_sfx_volume(global_sfx_vol)
    pygame.mixer.music.set_volume(global_music_vol)

    _mp_id_counter = [0]

    def _next_id():
        _mp_id_counter[0] += 1
        return _mp_id_counter[0]

    font = ResourceManager.get_font(36, None)

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
        enemy_projectiles_group = pygame.sprite.Group()
        enemies_group     = pygame.sprite.Group()
        items_group       = pygame.sprite.Group()
        rocks_group       = pygame.sprite.Group()
        particles_group   = pygame.sprite.Group()
        fairies_group     = pygame.sprite.Group()
        chests_group      = pygame.sprite.Group()
        walls = []
        exit_zones = []
        player_x, player_y = 100, 100

        for obj in tmx_data.objects:
            # Robustesse Tiled : obj.type OU obj.name selon la version de Tiled
            obj_type = (obj.type or obj.name or "").lower()
            if obj_type == "collision":
                walls.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "exit":
                exit_zones.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj_type == "player":
                player_x, player_y = obj.x, obj.y
            elif obj_type == "enemy":
                e = Enemy(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] Enemy en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "orc":
                e = Orc(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] Orc en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "slime":
                e = Slime(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] Slime en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "skeleton":
                e = Skeleton(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] Skeleton en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "orc_rider":
                e = OrcRider(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] OrcRider en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "elite_orc":
                e = EliteOrc(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] EliteOrc en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "greatsword_skeleton":
                e = GreatswordSkeleton(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] GreatswordSkeleton en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "skeleton_archer":
                e = SkeletonArcher(obj.x, obj.y); e._mp_id = _next_id()
                group.add(e); enemies_group.add(e)
                print(f"[SPAWN] SkeletonArcher en ({obj.x:.0f}, {obj.y:.0f})")
            elif obj_type == "bigenemy":
                e = BigEnemy(obj.x, obj.y); e._mp_id = _next_id()
                if hasattr(e, 'update_volumes'): e.update_volumes(global_music_vol, global_sfx_vol)
                group.add(e); enemies_group.add(e)
            elif obj_type == "necromancer":
                e = Necromancer(obj.x, obj.y); e._mp_id = _next_id()
                if hasattr(e, 'update_volumes'): e.update_volumes(global_music_vol, global_sfx_vol)
                group.add(e); enemies_group.add(e)
            elif obj_type == "medusa":
                e = Medusa(obj.x, obj.y); e._mp_id = _next_id()
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
            elif obj_type == "travelers_cap":
                it = Item(obj.x, obj.y, 'travelers_cap'); group.add(it); items_group.add(it)
            elif obj_type == "zhonya":
                it = Item(obj.x, obj.y, 'zhonya'); group.add(it); items_group.add(it)
            elif obj_type == "rabadon":
                it = Item(obj.x, obj.y, 'rabadon'); group.add(it); items_group.add(it)
            elif obj_type == "cap_assassin":
                it = Item(obj.x, obj.y, 'cap_assassin'); group.add(it); items_group.add(it)
            elif obj_type == "king_boss":
                kb = KingBoss(obj.x, obj.y); group.add(kb); enemies_group.add(kb)
            elif obj_type == "sbire_neant":
                sn = SbireNeant(obj.x, obj.y); group.add(sn); enemies_group.add(sn)
            elif obj_type == "fee_1":
                f = Fairy(obj.x, obj.y, 1); group.add(f); fairies_group.add(f)
            elif obj_type == "fee_2":
                f = Fairy(obj.x, obj.y, 2); group.add(f); fairies_group.add(f)
            elif obj_type == "fee_3":
                f = Fairy(obj.x, obj.y, 3); group.add(f); fairies_group.add(f)
            elif obj_type == "obstacle_rock":
                r = Rock(obj.x, obj.y); group.add(r); rocks_group.add(r); walls.append(r.hitbox)
            elif obj_type == "chest_right":
                c = Chest(obj.x, obj.y, flipped=False); group.add(c); chests_group.add(c)
                walls.append(c.hitbox)
            elif obj_type == "chest_left":
                c = Chest(obj.x, obj.y, flipped=True); group.add(c); chests_group.add(c)
                walls.append(c.hitbox)

        # Joueur local (serveur) — avec le personnage choisi
        player = Player(player_x, player_y, char_type=host_char_type)
        player.health = player_health
        player.has_melee = player_has_melee or player.has_melee
        player.has_ranged = player_has_ranged or player.has_ranged
        player.arrows = player_arrows or player.arrows
        for inv_item in player_inv_items:
            player.add_inventory_item(inv_item)
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

        # --- Interface d'obtention d'item (coffre) ---
        chest_ui_active = False
        chest_ui_item = None
        chest_ui_start_time = 0
        chest_ui_closing = False
        chest_ui_close_time = 0
        CHEST_UI_FADE_IN = 300
        CHEST_UI_FADE_OUT = 300

        # --- Arrêt du temps (Casquette du voyageur) ---
        time_stop_active = False
        time_stop_end_time = 0
        time_stop_activator = None       # référence au Player qui a activé
        time_stop_activator_idx = -1     # 0 = host, 1 = client
        time_stop_return_sound_played = False
        time_stop_player_cache = {}

        # --- Surfaces pré-allouées (évite 60+ allocations/sec en boucle) ---
        # Time-stop : overlay fixe pré-rempli, simplement blitté à chaque frame active
        _ts_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        _ts_overlay.fill((0, 0, 0, 110))
        # Death fade : surface opaque, l'alpha global varie via set_alpha()
        _death_overlay = pygame.Surface((screen_width, screen_height))
        _death_overlay.fill((100, 0, 0))
        # Compteur de frames réseau (tick rate 30/s = 1 envoi tous les 2 frames à 60fps)
        _net_frame_counter = 0
        NET_TICK_EVERY = 2

        # --- Cape de l'assassin (leurre / decoy) ---
        active_decoy = None  # référence au Decoy sprite actif
        decoy_owner = None   # joueur qui a activé la cape

        death_font = ResourceManager.get_font(120, "old english text mt, garamond, times new roman, serif")
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
                        if player.inventory_open:
                            player.inventory_open = False
                            player.inventory_grabbed = False
                        else:
                            is_paused = not is_paused
                        continue
                    # Touche I : ouvrir/fermer inventaire
                    if event.key == pygame.K_i and not is_paused and player.health > 0:
                        player.inventory_open = not player.inventory_open
                        player.inventory_grabbed = False
                        if player.inventory_open:
                            player.inventory_cursor = 0
                        continue
                    # Gestion de l'inventaire ouvert
                    if player.inventory_open and not is_paused:
                        if event.key == pygame.K_e:
                            # Saisir / relâcher l'item
                            if player.inventory_items:
                                from player import ACTIVE_ITEMS
                                cur_item = player.inventory_items[player.inventory_cursor] if player.inventory_cursor < len(player.inventory_items) else None
                                if player.inventory_grabbed:
                                    player.inventory_grabbed = False
                                elif cur_item and cur_item in ACTIVE_ITEMS:
                                    player.inventory_grabbed = True
                        elif event.key == pygame.K_q:
                            if player.inventory_grabbed:
                                player.inventory_swap(-1)
                            else:
                                player.inventory_cursor = max(0, player.inventory_cursor - 1)
                        elif event.key == pygame.K_d:
                            if player.inventory_grabbed:
                                player.inventory_swap(1)
                            else:
                                player.inventory_cursor = min(len(player.inventory_items) - 1, player.inventory_cursor + 1)
                        elif event.key == pygame.K_a:
                            # Jeter l'item
                            if player.inventory_items and player.inventory_cursor < len(player.inventory_items):
                                dropped_type = player.inventory_items[player.inventory_cursor]
                                player.remove_inventory_item(dropped_type)
                                player.inventory_grabbed = False
                                # Créer un item au sol
                                drop_item = Item(player.feet.centerx, player.feet.centery, dropped_type)
                                group.add(drop_item); items_group.add(drop_item)
                                if not player.inventory_items:
                                    player.inventory_open = False
                        continue
                    # Skip dialogue avec Entrée (boss + fées)
                    if event.key == pygame.K_RETURN and not is_paused:
                        skipped = False
                        for enemy in enemies_group:
                            if hasattr(enemy, 'skip_dialogue') and enemy.skip_dialogue():
                                skipped = True; break
                        if not skipped:
                            for fairy in fairies_group:
                                if fairy.skip_dialogue():
                                    break

                    if not is_paused and player.health > 0 and not player.is_stunned:
                        if event.key == pygame.K_a and can_exit:
                            player_health  = player.health
                            player_inv_items = list(player.inventory_items)
                            player_has_melee = player.has_melee
                            player_has_ranged = player.has_ranged
                            player_arrows = player.arrows
                            if player2:
                                player2_health = player2.health
                                player2_inv_items = list(player2.inventory_items)
                            current_level_index += 1
                            level_running = False
                            break
                        # Items actifs : touches dynamiques
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
                                elif item_name == 'travelers_cap':
                                    if not time_stop_active and player.activate_travelers_cap():
                                        time_stop_active = True
                                        time_stop_end_time = pygame.time.get_ticks() + 5000
                                        time_stop_activator = player
                                        time_stop_activator_idx = 0
                                        time_stop_return_sound_played = False
                                        time_stop_player_cache = {}
                                        sound_manager.enter_time_stop()
                                        sound_manager.play_ui_time_stop()
                                        sound_events.append({'sound': 'time_stop', 'x': player.feet.centerx, 'y': player.feet.centery})
                                elif item_name == 'zhonya':
                                    if player.activate_zhonya():
                                        # Trouver l'ennemi le plus proche dans un rayon de 200
                                        # Comparaison au carré : pas de sqrt() dans la boucle
                                        nearest_enemy = None
                                        nearest_dist_sq = float('inf')
                                        ZHONYA_RADIUS_SQ = 200 ** 2
                                        px, py = player.feet.centerx, player.feet.centery
                                        for e in enemies_group:
                                            if getattr(e, 'health', 0) > 0 and not getattr(e, 'paralyzed', False):
                                                ex, ey = e.feet.centerx, e.feet.centery
                                                d_sq = (px - ex) ** 2 + (py - ey) ** 2
                                                if d_sq <= ZHONYA_RADIUS_SQ and d_sq < nearest_dist_sq:
                                                    nearest_dist_sq = d_sq
                                                    nearest_enemy = e
                                        if nearest_enemy:
                                            stun_dur = 3000
                                            nearest_enemy.paralyze(stun_dur)
                                            nearest_enemy._zhonya_gold = True
                                            e_pos = (nearest_enemy.feet.centerx, nearest_enemy.feet.centery)
                                            host_pos = (player.feet.centerx, player.feet.centery)
                                            sound_manager.play_spatial('zhonya', e_pos, host_pos)
                                            sound_events.append({'sound': 'zhonya', 'x': e_pos[0], 'y': e_pos[1]})
                                        else:
                                            # Pas d'ennemi à portée : annuler le cooldown
                                            player.last_zhonya_time = -20000
                                            ft = FloatingText(player.feet.centerx, player.feet.centery,
                                                              text="Aucun ennemi à portée")
                                            group.add(ft); particles_group.add(ft)
                                elif item_name == 'cap_assassin':
                                    if player.activate_cap_assassin():
                                        # Détruire l'ancien leurre s'il existait
                                        if active_decoy:
                                            active_decoy.kill()
                                        decoy = Decoy(player.feet.centerx, player.feet.centery, player)
                                        group.add(decoy)
                                        active_decoy = decoy
                                        decoy_owner = player
                                        # Particules de fumée à l'activation
                                        for _ in range(15):
                                            smoke = SmokeParticle(player.feet.centerx + random.randint(-15, 15),
                                                                  player.feet.bottom + random.randint(-10, 5))
                                            group.add(smoke); particles_group.add(smoke)
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
                                    else:
                                        # Inventaire plein : texte flottant
                                        ft = FloatingText(player.feet.centerx, player.feet.centery,
                                                          text="Inventaire plein...")
                                        group.add(ft); particles_group.add(ft)
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
                            # Interaction fée (host)
                            for fairy in fairies_group:
                                if player.feet.colliderect(fairy.rect.inflate(30, 30)):
                                    fairy.interact(player, 0)
                                    break
                            # Interaction coffre (host)
                            if not time_stop_active:
                                for chest in chests_group:
                                    if not chest.opened and not chest.opening:
                                        if player.feet.colliderect(chest.hitbox.inflate(40, 40)):
                                            chest.open()
                                            _players = [player, player2] if player2 else [player]
                                            _grant_xp(50, _players, group, particles_group, sound_manager)
                                            available = [it for it in CHEST_DROPPABLE_ITEMS
                                                         if it not in chest_dropped_items]
                                            if available:
                                                chosen = random.choice(available)
                                                chest_dropped_items.add(chosen)
                                                if not player.add_inventory_item(chosen):
                                                    drop = Item(chest.rect.centerx, chest.rect.bottom + 10, chosen)
                                                    group.add(drop); items_group.add(drop)
                                                chest_ui_active = True
                                                chest_ui_item = chosen
                                                chest_ui_start_time = pygame.time.get_ticks()
                                                chest_ui_closing = False
                                                sound_manager.play_ui_get_item()
                                            break
                        if event.key == pygame.K_RETURN:
                            if chest_ui_active and not chest_ui_closing:
                                chest_ui_closing = True
                                chest_ui_close_time = pygame.time.get_ticks()

            if not level_running:
                continue

            if is_paused:
                group.draw(screen)
                ui.draw_health_bar(player.health, player.max_health)
                ui.draw_stamina_bar(player.stamina, player.max_stamina)
                ui.draw_xp_bar(player.xp, player.xp_to_next_level, player.level)
                _lu_elapsed = pygame.time.get_ticks() - player.level_up_time
                if _lu_elapsed < 2000:
                    ui.draw_level_up_message(_lu_elapsed / 2000.0, screen_width // 2, screen_height // 2)
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

                # Attaque player2 — nouveau système de bindings
                if player2.health > 0:
                    for binding, inp_key in [('mouse', 'attack_mouse'),
                                              ('e', 'attack_e'),
                                              ('1', 'attack_1'),
                                              ('2', 'attack_2')]:
                        if net_inputs.get(inp_key):
                            res = player2.trigger_attack(binding)
                            if res:
                                typ, data = res
                                if typ == 'no_stamina':
                                    _now = pygame.time.get_ticks()
                                    if _now - player2._last_no_stamina_ft_time > 1000:
                                        player2._last_no_stamina_ft_time = _now
                                        ft = FloatingText(player2.feet.centerx, player2.feet.centery, text="Endurance insuffisante...")
                                        group.add(ft); particles_group.add(ft)
                                elif typ == 'melee':
                                    p2_pos = (player2.feet.centerx, player2.feet.centery)
                                    sound_manager.play_spatial('sword', p2_pos, host_pos)
                                    for e in list(enemies_group):
                                        if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                            dmg2 = player2.melee_damage * player2.get_damage_multiplier(target_enemy=e)
                                            e.damage(dmg2)
                                            _spawn_damage_number(e, dmg2, player2, group, particles_group)
                                            player2.lifesteal(dmg2)
                                            if e.health <= 0:
                                                e_pos = (e.feet.centerx, e.feet.centery)
                                                sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                            _handle_enemy_death(e, group, items_group, particles_group)
                                            if e.health <= 0 and not getattr(e, '_xp_granted', False):
                                                e._xp_granted = True
                                                xp = _get_enemy_xp(e)
                                                _players = [player, player2] if player2 else [player]
                                                _grant_xp(xp, _players, group, particles_group, sound_manager)
                                elif typ == 'skill':
                                    p2_pos = (player2.feet.centerx, player2.feet.centery)
                                    sound_manager.play_spatial('sword', p2_pos, host_pos)
                                break

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
                # Travelers cap player2
                if net_inputs.get('travelers_cap') and player2.has_travelers_cap:
                    if not time_stop_active and player2.activate_travelers_cap():
                        time_stop_active = True
                        time_stop_end_time = pygame.time.get_ticks() + 5000
                        time_stop_activator = player2
                        time_stop_activator_idx = 1
                        time_stop_return_sound_played = False
                        time_stop_player_cache = {}
                        sound_manager.enter_time_stop()
                        sound_manager.play_ui_time_stop()
                        sound_events.append({'sound': 'time_stop', 'x': player2.feet.centerx, 'y': player2.feet.centery})
                # Zhonya player2
                if net_inputs.get('zhonya') and player2.has_zhonya:
                    if player2.activate_zhonya():
                        # Comparaison au carré : pas de sqrt() dans la boucle
                        nearest_enemy = None
                        nearest_dist_sq = float('inf')
                        ZHONYA_RADIUS_SQ = 200 ** 2
                        p2x, p2y = player2.feet.centerx, player2.feet.centery
                        for e in enemies_group:
                            if getattr(e, 'health', 0) > 0 and not getattr(e, 'paralyzed', False):
                                ex, ey = e.feet.centerx, e.feet.centery
                                d_sq = (p2x - ex) ** 2 + (p2y - ey) ** 2
                                if d_sq <= ZHONYA_RADIUS_SQ and d_sq < nearest_dist_sq:
                                    nearest_dist_sq = d_sq
                                    nearest_enemy = e
                        if nearest_enemy:
                            stun_dur = 3000
                            nearest_enemy.paralyze(stun_dur)
                            nearest_enemy._zhonya_gold = True
                            e_pos = (nearest_enemy.feet.centerx, nearest_enemy.feet.centery)
                            sound_manager.play_spatial('zhonya', e_pos, host_pos)
                            sound_events.append({'sound': 'zhonya', 'x': e_pos[0], 'y': e_pos[1]})
                        else:
                            player2.last_zhonya_time = -20000
                # Skip dialogue (client)
                if net_inputs.get('skip_dialogue'):
                    skipped = False
                    for enemy in enemies_group:
                        if hasattr(enemy, 'skip_dialogue') and enemy.skip_dialogue():
                            skipped = True; break
                    if not skipped:
                        for fairy in fairies_group:
                            if fairy.skip_dialogue():
                                break
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
                    # Interaction fée (client)
                    for fairy in fairies_group:
                        if player2.feet.colliderect(fairy.rect.inflate(30, 30)):
                            fairy.interact(player2, 1)
                            break
                    # Interaction coffre (player2)
                    if not time_stop_active:
                        for chest in chests_group:
                            if not chest.opened and not chest.opening:
                                if player2.feet.colliderect(chest.hitbox.inflate(40, 40)):
                                    chest.open()
                                    _players = [player, player2] if player2 else [player]
                                    _grant_xp(50, _players, group, particles_group, sound_manager)
                                    available = [it for it in CHEST_DROPPABLE_ITEMS
                                                 if it not in chest_dropped_items]
                                    if available:
                                        chosen = random.choice(available)
                                        chest_dropped_items.add(chosen)
                                        if not player2.add_inventory_item(chosen):
                                            drop = Item(chest.rect.centerx, chest.rect.bottom + 10, chosen)
                                            group.add(drop); items_group.add(drop)
                                        sound_events.append({'sound': 'get_item',
                                                             'x': chest.rect.centerx,
                                                             'y': chest.rect.centery,
                                                             'chest_item': chosen})
                                    break

                # Drop items player2
                if net_inputs.get('drop_item'):
                    drop_type = net_inputs['drop_item']
                    if drop_type in player2.inventory_items:
                        player2.remove_inventory_item(drop_type)
                        drop_item = Item(player2.feet.centerx, player2.feet.centery, drop_type)
                        group.add(drop_item); items_group.add(drop_item)

                # Attaque à distance player2
                new_proj2 = player2.check_ranged_attack()
                if new_proj2:
                    new_proj2._mp_id = _next_id()
                    new_proj2._owner = player2
                    group.add(new_proj2); projectiles_group.add(new_proj2)

                # Régénération de flèches player2 (Archer)
                player2.update_arrow_regen()
                player2.update_stamina()

            # --- Joueur local ---
            player.update()
            player.update_stamina()
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

            # --- Arrêt du temps : expiration (MP) ---
            if time_stop_active:
                now_ts = pygame.time.get_ticks()
                if not time_stop_return_sound_played and now_ts >= time_stop_end_time - 500:
                    sound_manager.play_ui_return_time()
                    sound_events.append({'sound': 'return_time', 'x': 0, 'y': 0})
                    time_stop_return_sound_played = True
                if now_ts >= time_stop_end_time:
                    time_stop_active = False
                    time_stop_activator = None
                    time_stop_activator_idx = -1
                    time_stop_player_cache = {}
                    sound_manager.exit_time_stop()
                    for enemy in enemies_group:
                        if getattr(enemy, 'paralyzed', False) and hasattr(enemy, 'paralyze_end_time'):
                            enemy.paralyze_end_time += 5000
                        if hasattr(enemy, 'last_attack_time'):
                            enemy.last_attack_time += 5000

            # --- Cape de l'assassin : fin d'invisibilité + destruction du leurre ---
            if decoy_owner and decoy_owner.stealth_active:
                if pygame.time.get_ticks() >= decoy_owner.stealth_end_time:
                    decoy_owner.end_stealth()
            if decoy_owner and not decoy_owner.stealth_active:
                if active_decoy and active_decoy.alive():
                    # Particules de fumée à la disparition du leurre
                    for _ in range(10):
                        smoke = SmokeParticle(active_decoy.feet.centerx + random.randint(-10, 10),
                                              active_decoy.feet.bottom + random.randint(-10, 5))
                        group.add(smoke); particles_group.add(smoke)
                    active_decoy.kill()
                active_decoy = None
                decoy_owner = None

            # --- Ennemis (figés pendant time stop) ---
            if not time_stop_active:
              for e in list(enemies_group):
                # Ciblage : leurre prioritaire si actif, sinon joueurs vivants
                if active_decoy and active_decoy.alive():
                    decoy_dist = (pygame.math.Vector2(active_decoy.feet.center)
                                  - pygame.math.Vector2(e.feet.center)).length()
                    # Les mobs ont detection_radius, les boss ont aggro_radius
                    _detect_r = getattr(e, 'detection_radius', getattr(e, 'aggro_radius', 300))
                    if decoy_dist < _detect_r:
                        target = active_decoy
                    else:
                        all_players = [player] + ([player2] if player2 else [])
                        live = [p for p in all_players if p.health > 0 and not getattr(p, 'stealth_active', False)]
                        target = min(live, key=lambda p: (
                            pygame.math.Vector2(p.feet.center) - pygame.math.Vector2(e.feet.center)
                        ).length()) if live else player
                else:
                    all_players = [player] + ([player2] if player2 else [])
                    live = [p for p in all_players if p.health > 0 and not getattr(p, 'stealth_active', False)]
                    if not live:
                        live = [p for p in all_players if p.health > 0]
                    target = min(live, key=lambda p: (
                        pygame.math.Vector2(p.feet.center) - pygame.math.Vector2(e.feet.center)
                    ).length()) if live else player

                # Sauvegarder position du spirit avant update
                spirit_pos = None
                if isinstance(e, Spirit):
                    spirit_pos = (e.rect.centerx, e.rect.centery)

                if isinstance(e, (KingBoss, SbireNeant)):
                    e.update(target, walls, player2=player2 if not solo_mode else None)
                else:
                    e.update(target, walls)

                # SbireNeant : particules de teleportation
                if isinstance(e, SbireNeant) and e.pending_teleports:
                    for (fx, fy, tx, ty) in e.pending_teleports:
                        for _ in range(15):
                            p = SmokeParticle(fx + random.randint(-15, 15), fy + random.randint(-15, 5))
                            group.add(p); particles_group.add(p)
                        for _ in range(15):
                            p = SmokeParticle(tx + random.randint(-15, 15), ty + random.randint(-15, 5))
                            group.add(p); particles_group.add(p)
                    e.pending_teleports.clear()

                # KingBoss : stun global
                if isinstance(e, KingBoss) and e.pending_global_stun:
                    e.pending_global_stun = False
                    if player.health > 0:
                        player.apply_stun(3000)
                    if player2 and player2.health > 0:
                        player2.apply_stun(3000)

                # Spirit qui a explosé/mort : particules rouges
                if isinstance(e, Spirit) and getattr(e, 'pending_particles', False):
                    if spirit_pos:
                        for _ in range(15):
                            p = BloodParticle(spirit_pos[0], spirit_pos[1])
                            group.add(p); particles_group.add(p)
                # Dégâts sur le joueur non-ciblé (boss avec get_attack_hitbox)
                # KingBoss gère les 2 joueurs dans son update, pas besoin ici
                if player2 and not isinstance(e, (KingBoss, SbireNeant)):
                    other = player2 if target is player else player
                    if hasattr(e, 'get_attack_hitbox') and getattr(e, 'is_attacking', False) and other.health > 0:
                        atk = e.get_attack_hitbox()
                        now = pygame.time.get_ticks()
                        last_mp = getattr(e, '_mp_other_dmg_time', 0)
                        if atk and atk.colliderect(other.feet) and now - last_mp > getattr(e, 'attack_cooldown', 1500):
                            # Médusa special : stun + vol de vie sur l'autre joueur aussi
                            if isinstance(e, Medusa) and getattr(e, 'state', '') == 'special':
                                other.damage(e.special_damage, source_enemy=e)
                                other.apply_stun(3000)
                                missing_hp = e.max_health - e.health
                                e.health = min(e.max_health, e.health + missing_hp * 0.5)
                            else:
                                other.damage(getattr(e, 'damage_amount', 10), source_enemy=e)
                            e._mp_other_dmg_time = now
                if hasattr(e, 'pending_summons') and e.pending_summons:
                    owner_ref = e if isinstance(e, Necromancer) else None
                    for sx, sy in e.pending_summons:
                        ns = Spirit(sx, sy, owner_necromancer=owner_ref); ns._mp_id = _next_id()
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
                            elif bs == 'necro_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/necromancer_song.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'medusa_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/medusa_ost.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'king_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/king_boss_ost.mp3")
                                    pygame.mixer.music.set_volume(global_music_vol)
                                    pygame.mixer.music.play(-1)
                                except Exception:
                                    pass
                            elif bs == 'sbire_bgm_start':
                                try:
                                    pygame.mixer.music.load("assets/sounds/sbire_neant.mp3")
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
            if not time_stop_active:
                enemy_projectiles_group.update()

                # --- Skeleton Archer : tir de flèche au milieu de l'animation d'attaque ---
                for e in enemies_group:
                    if isinstance(e, SkeletonArcher) and e.is_attacking and not e._arrow_fired:
                        anim = e.animations[e.facing].get('attack', [])
                        if anim and int(e.frame_index) >= len(anim) // 2:
                            e.fire_arrow(player, group, enemy_projectiles_group)

                # --- Collision flèches ennemies → joueur ---
                for proj in list(enemy_projectiles_group):
                    if not hasattr(proj, 'hitbox'):
                        continue
                    if player.health > 0:
                        body = player.feet.copy()
                        body.height += 25
                        body.y -= 25
                        if proj.hitbox.colliderect(body):
                            player.damage(proj.damage_amount)
                            proj.kill()
                            continue
                    # Collision avec les murs
                    for wall in walls:
                        if proj.hitbox.colliderect(wall):
                            proj.kill()
                            break

            particles_group.update()
            fairies_group.update()
            chests_group.update()

            # --- Attaque locale (serveur) — nouveau système de bindings ---
            keys = pygame.key.get_pressed()
            mouse_buttons = pygame.mouse.get_pressed()
            if player.health > 0 and not player.inventory_open:
                # Clic gauche → attaque de base (mouse binding)
                # E → compétence E, 1 → compétence 1, 2 → compétence 2
                for binding, pressed in [('mouse', mouse_buttons[0]),
                                          ('e', keys[pygame.K_e]),
                                          ('1', keys[pygame.K_1]),
                                          ('2', keys[pygame.K_2])]:
                    if pressed:
                        res = player.trigger_attack(binding)
                        if res:
                            typ, data = res
                            if typ == 'no_stamina':
                                _now = pygame.time.get_ticks()
                                if _now - player._last_no_stamina_ft_time > 1000:
                                    player._last_no_stamina_ft_time = _now
                                    ft = FloatingText(player.feet.centerx, player.feet.centery, text="Endurance insuffisante...")
                                    group.add(ft); particles_group.add(ft)
                            elif typ == 'melee':
                                sound_manager.play_spatial('sword', host_pos, host_pos)
                                sound_events.append({'sound': 'sword', 'x': host_pos[0], 'y': host_pos[1]})
                                was_crit = player.stealth_crit_active
                                hit_any_melee = False
                                for e in list(enemies_group):
                                    if getattr(e, '_is_player_decoy', False): continue
                                    if getattr(e, 'health', 0) > 0 and data.colliderect(e.feet):
                                        hit_any_melee = True
                                        dmg = player.melee_damage * player.get_damage_multiplier(target_enemy=e)
                                        e.damage(dmg)
                                        _spawn_damage_number(e, dmg, player, group, particles_group, is_crit=was_crit)
                                        player.lifesteal(dmg)
                                        if e.health <= 0:
                                            e_pos = (e.feet.centerx, e.feet.centery)
                                            sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                        _handle_enemy_death(e, group, items_group, particles_group)
                                        if e.health <= 0 and not getattr(e, '_xp_granted', False):
                                            e._xp_granted = True
                                            xp = _get_enemy_xp(e)
                                            _players = [player, player2] if player2 else [player]
                                            _grant_xp(xp, _players, group, particles_group, sound_manager)
                                player.stealth_crit_active = False  # consommé après application
                                if was_crit and hit_any_melee:
                                    crit_ft = FloatingText(player.feet.centerx, player.feet.centery + 10,
                                                           text="CRIT!", duration=800,
                                                           color=(255, 255, 0))
                                    group.add(crit_ft); particles_group.add(crit_ft)
                            elif typ == 'skill':
                                sound_manager.play_spatial('sword', host_pos, host_pos)
                                sound_events.append({'sound': 'sword', 'x': host_pos[0], 'y': host_pos[1]})
                            break  # Un seul déclenchement par frame

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
                new_proj._is_crit = player.stealth_crit_active
                player.stealth_crit_active = False  # consommé au tir
                group.add(new_proj); projectiles_group.add(new_proj)

            # Régénération de flèches (Archer)
            player.update_arrow_regen()

            for proj in list(projectiles_group):
                # HomingProjectile — dégâts en zone quand il explose
                if isinstance(proj, HomingProjectile):
                    if proj.has_exploded and not getattr(proj, '_damage_dealt', False):
                        proj._damage_dealt = True
                        owner = getattr(proj, '_owner', None)
                        was_crit_homing = getattr(proj, '_is_crit', False)
                        hit_any = False
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0:
                                dist = pygame.math.Vector2(
                                    e.feet.centerx - proj.rect.centerx,
                                    e.feet.centery - proj.rect.centery
                                ).length()
                                if dist <= proj.explosion_radius:
                                    aoe_dmg = proj.damage_amount
                                    if owner:
                                        aoe_dmg *= owner.get_damage_multiplier(target_enemy=e)
                                    e.damage(aoe_dmg)
                                    _spawn_damage_number(e, aoe_dmg, owner, group, particles_group, is_crit=was_crit_homing)
                                    hit_any = True
                                    if e.health <= 0:
                                        e_pos = (e.feet.centerx, e.feet.centery)
                                        sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                    _handle_enemy_death(e, group, items_group, particles_group)
                                    if e.health <= 0 and not getattr(e, '_xp_granted', False):
                                        e._xp_granted = True
                                        xp = _get_enemy_xp(e)
                                        _players = [player, player2] if player2 else [player]
                                        _grant_xp(xp, _players, group, particles_group, sound_manager)
                        if was_crit_homing and hit_any and owner:
                            crit_ft = FloatingText(owner.feet.centerx, owner.feet.centery + 10,
                                                   text="CRIT!", duration=800, color=(255, 255, 0))
                            group.add(crit_ft); particles_group.add(crit_ft)
                    continue

                # InstantAOE — dégâts en zone immédiatement
                if isinstance(proj, InstantAOE):
                    if not getattr(proj, '_damage_dealt', False):
                        proj._damage_dealt = True
                        owner = getattr(proj, '_owner', None)
                        was_crit_aoe = getattr(proj, '_is_crit', False)
                        hit_any_aoe = False
                        for e in list(enemies_group):
                            if getattr(e, 'health', 0) > 0:
                                dist = pygame.math.Vector2(
                                    e.feet.centerx - proj.rect.centerx,
                                    e.feet.centery - proj.rect.centery
                                ).length()
                                if dist <= proj.explosion_radius:
                                    aoe_dmg = proj.damage_amount
                                    if owner:
                                        aoe_dmg *= owner.get_damage_multiplier(target_enemy=e)
                                    e.damage(aoe_dmg)
                                    _spawn_damage_number(e, aoe_dmg, owner, group, particles_group, is_crit=was_crit_aoe)
                                    hit_any_aoe = True
                                    # Paralysie (orbe cristal wizard)
                                    paralyze_dur = getattr(proj, '_paralyze_duration', 0)
                                    if paralyze_dur and e.health > 0 and hasattr(e, 'paralyze'):
                                        # Boss : durée réduite à 1.5s
                                        if isinstance(e, (BigEnemy, Necromancer, Medusa, KingBoss, SbireNeant)):
                                            e.paralyze(paralyze_dur // 2)
                                        else:
                                            e.paralyze(paralyze_dur)
                                    if e.health <= 0:
                                        e_pos = (e.feet.centerx, e.feet.centery)
                                        sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                                    _handle_enemy_death(e, group, items_group, particles_group)
                                    if e.health <= 0 and not getattr(e, '_xp_granted', False):
                                        e._xp_granted = True
                                        xp = _get_enemy_xp(e)
                                        _players = [player, player2] if player2 else [player]
                                        _grant_xp(xp, _players, group, particles_group, sound_manager)
                        if was_crit_aoe and hit_any_aoe and owner:
                            crit_ft = FloatingText(owner.feet.centerx, owner.feet.centery + 10,
                                                   text="CRIT!", duration=800, color=(255, 255, 0))
                            group.add(crit_ft); particles_group.add(crit_ft)
                    continue

                # HealEffect — juste un visuel, pas de collision
                if isinstance(proj, HealEffect):
                    continue

                # Projectiles linéaires classiques (flèches, boules de feu)
                if not hasattr(proj, 'hitbox'):
                    continue
                for e in list(enemies_group):
                    if getattr(e, '_is_player_decoy', False): continue
                    if getattr(e, 'health', 0) > 0:
                        body = e.feet.copy()
                        ext = 50 if isinstance(e, (BigEnemy, Necromancer, Medusa, KingBoss, SbireNeant)) else 25
                        body.height += ext; body.y -= ext
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
                            was_crit_proj = getattr(proj, '_is_crit', False)
                            if owner:
                                proj_dmg *= owner.get_damage_multiplier(target_enemy=e)
                            e.damage(proj_dmg)
                            _spawn_damage_number(e, proj_dmg, owner, group, particles_group, is_crit=was_crit_proj)
                            if was_crit_proj and owner:
                                crit_ft = FloatingText(owner.feet.centerx, owner.feet.centery + 10,
                                                       text="CRIT!", duration=800,
                                                       color=(255, 255, 0))
                                group.add(crit_ft); particles_group.add(crit_ft)
                            if owner and hasattr(owner, 'lifesteal'):
                                owner.lifesteal(proj_dmg)
                            if e.health <= 0:
                                e_pos = (e.feet.centerx, e.feet.centery)
                                sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
                            _handle_enemy_death(e, group, items_group, particles_group)
                            if e.health <= 0 and not getattr(e, '_xp_granted', False):
                                e._xp_granted = True
                                xp = _get_enemy_xp(e)
                                _players = [player, player2] if player2 else [player]
                                _grant_xp(xp, _players, group, particles_group, sound_manager)
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

            show_chest_dialogue = False
            if player.health > 0 and not time_stop_active:
                for chest in chests_group:
                    if not chest.opened and not chest.opening:
                        if player.feet.colliderect(chest.hitbox.inflate(40, 40)):
                            show_chest_dialogue = True
                            break

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

            # --- Effet visuel arrêt du temps (overlay gris + joueur en couleur) ---
            if time_stop_active:
                activator = time_stop_activator if time_stop_activator else player
                # Surface pré-allouée et pré-remplie — pas de fill() à chaque frame
                screen.blit(_ts_overlay, (0, 0))

                act_sx = (activator.rect.x - cam_x) * zoom_level + screen_width / 2
                act_sy = (activator.rect.y - cam_y) * zoom_level + screen_height / 2
                cache_key = (int(activator.frame_index), activator.facing, activator.state)
                if cache_key not in time_stop_player_cache:
                    time_stop_player_cache[cache_key] = pygame.transform.scale(
                        activator.image,
                        (int(activator.rect.width * zoom_level),
                         int(activator.rect.height * zoom_level))
                    )
                screen.blit(time_stop_player_cache[cache_key], (act_sx, act_sy))

            # --- DEBUG HITBOXES ---
            if DEBUG_HITBOXES:
                draw_debug_rect(screen, player.feet, (0, 255, 0), cam_x, cam_y, zoom_level, screen_width, screen_height)
                if player.is_attacking and player.current_weapon == 'melee':
                    attack_rect = pygame.Rect(0, 0, 70, 70)
                    attack_rect.center = player.feet.center
                    draw_debug_rect(screen, attack_rect, (255, 255, 0), cam_x, cam_y, zoom_level, screen_width, screen_height)
                if player2:
                    draw_debug_rect(screen, player2.feet, (0, 200, 0), cam_x, cam_y, zoom_level, screen_width, screen_height)
                for enemy in enemies_group:
                    if hasattr(enemy, 'feet'):
                        draw_debug_rect(screen, enemy.feet, (255, 0, 0), cam_x, cam_y, zoom_level, screen_width, screen_height)
                    if getattr(enemy, 'is_attacking', False) and hasattr(enemy, 'get_attack_hitbox'):
                        draw_debug_rect(screen, enemy.get_attack_hitbox(), (255, 165, 0), cam_x, cam_y, zoom_level, screen_width, screen_height)
                for proj in projectiles_group:
                    if hasattr(proj, 'hitbox'):
                        draw_debug_rect(screen, proj.hitbox, (0, 0, 255), cam_x, cam_y, zoom_level, screen_width, screen_height)
                for rock in rocks_group:
                    if hasattr(rock, 'hitbox'):
                        draw_debug_rect(screen, rock.hitbox, (0, 255, 255), cam_x, cam_y, zoom_level, screen_width, screen_height)

            # --- Marque Kitsune : griffe au-dessus des ennemis sous 40% PV ---
            if player.has_kitsune_mask:
                for e in enemies_group:
                    if getattr(e, 'health', 0) > 0 and e.health <= e.max_health * 0.4:
                        ex = (e.rect.centerx - cam_x) * zoom_level + screen_width / 2
                        mark_y_offset = 5
                        if isinstance(e, (KingBoss, SbireNeant)):
                            mark_y_offset = -15
                        ey = (e.feet.top + mark_y_offset - cam_y) * zoom_level + screen_height / 2
                        mark_size = max(36, int(max(e.rect.width, e.rect.height) * 0.6))
                        if isinstance(e, Medusa):
                            mark_size = max(mark_size, 120)
                        mark = _get_kitsune_mark(mark_size)
                        screen.blit(mark, (ex - mark_size // 2, ey - mark_size // 2))

            # --- HUD ---
            ui.draw_health_bar(player.health, player.max_health)
            ui.draw_stamina_bar(player.stamina, player.max_stamina)
            ui.draw_xp_bar(player.xp, player.xp_to_next_level, player.level)
            _lu_elapsed = pygame.time.get_ticks() - player.level_up_time
            if _lu_elapsed < 2000:
                ui.draw_level_up_message(_lu_elapsed / 2000.0, screen_width // 2, screen_height // 2)
            cr = min(1.0, max(0.0, (pygame.time.get_ticks() - player.last_dash_time) / player.dash_cooldown))
            skill_crs = {sk: player.get_skill_cooldown_ratio(sk) for sk in player.abilities}
            ui.draw_character_hud(player.char_type, player.current_weapon,
                                  skill_cooldowns=skill_crs, arrows=player.arrows,
                                  inventory_items=player.inventory_items,
                                  dash_cr=cr,
                                  blue_gem_cr=player.get_blue_gem_cooldown_ratio(),
                                  cursed_brand_cr=player.get_cursed_brand_cooldown_ratio(),
                                  arrow_regen_cr=player.get_arrow_regen_cooldown_ratio(),
                                  travelers_cap_cr=player.get_travelers_cap_cooldown_ratio(),
                                  zhonya_cr=player.get_zhonya_cooldown_ratio(),
                                  cap_assassin_cr=player.get_cap_assassin_cooldown_ratio(),
                                  item_start_key=player.char_def.get('item_start_key', 2))
            # Barre de vie player2 (en haut à droite)
            if player2:
                _draw_remote_health(screen, player2.health, player2.max_health)

            for e in enemies_group:
                if getattr(e, 'has_aggro', False) and getattr(e, 'health', 0) > 0:
                    if isinstance(e, Medusa):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Médusa")
                    elif isinstance(e, SbireNeant):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Sbire du neant")
                    elif isinstance(e, KingBoss):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Roi reprouve")
                    elif isinstance(e, BigEnemy):
                        ui.draw_boss_health_bar(e.health, e.max_health, "Gardien des profondeurs")
                    elif isinstance(e, Necromancer):
                        ui.draw_boss_health_bar(e.health, e.max_health, "La Faucheuse")

            # Dialogues de boss (serveur multi)
            for e in enemies_group:
                dialogue_text = getattr(e, 'get_current_dialogue', lambda: None)()
                if dialogue_text:
                    ui.draw_boss_dialogue(dialogue_text, getattr(e, 'boss_display_name', None))
                    break

            # Dialogues de fées
            for fairy in fairies_group:
                ftxt = fairy.get_current_dialogue()
                if ftxt:
                    ui.draw_boss_dialogue(ftxt, "Fee")
                    break

            if show_exit_dialogue:
                ui.draw_dialogue("Voulez vous rentrer ? (A)")
            elif show_chest_dialogue:
                ui.draw_dialogue("Appuyer sur F pour ouvrir")

            # --- Écran inventaire ---
            if player.inventory_open and player.health > 0:
                bindings = player.char_def.get('bindings', {})
                ui.draw_inventory_screen(
                    player.inventory_items,
                    player.inventory_cursor,
                    player.inventory_grabbed,
                    item_start_key=player.char_def.get('item_start_key', 2),
                    skill_1_exists=bindings.get('1') is not None)

            # --- Indicateur mode ---
            if not solo_mode:
                mp_surf = ResourceManager.get_font(24, None).render("● MULTIJOUEUR", True, (80, 200, 80))
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
                    # Surface pré-allouée : set_alpha() remplace le fill() variable chaque frame
                    _death_overlay.set_alpha(int(200 * prog))
                    screen.blit(_death_overlay, (0, 0))
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
                    gem_base = _get_redgem_anim_img()
                    gem_img = gem_base.copy()
                    gem_img.set_alpha(alpha)
                    gem_rect = gem_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    # Flash rouge léger en fond
                    overlay = _get_overlay(screen_width, screen_height)
                    overlay.fill((255, 50, 50, int(alpha * 0.4)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(gem_img, gem_rect)
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
                    mir_base = _get_mirror_anim_img()
                    mir_img = mir_base.copy()
                    mir_img.set_alpha(alpha)
                    mir_rect = mir_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    overlay = _get_overlay(screen_width, screen_height)
                    overlay.fill((180, 180, 255, int(alpha * 0.3)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(mir_img, mir_rect)
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
                    cb_base = _get_cursed_brand_anim_img()
                    cb_img = cb_base.copy()
                    cb_img.set_alpha(alpha)
                    cb_rect = cb_img.get_rect(center=(screen_width // 2, screen_height // 2))
                    overlay = _get_overlay(screen_width, screen_height)
                    overlay.fill((150, 50, 150, int(alpha * 0.3)))
                    screen.blit(overlay, (0, 0))
                    screen.blit(cb_img, cb_rect)
                else:
                    cursed_brand_animating = False

            # --- Envoi état au client (tick rate 30/s = 1 frame sur 2 à 60fps) ---
            _net_frame_counter += 1
            if not solo_mode and server and (_net_frame_counter % NET_TICK_EVERY == 0):
                players_list = [_serialize_player(player)]
                if player2:
                    players_list.append(_serialize_player(player2))
                # Sérialiser dialogues de fées actifs
                fairy_dialogues = []
                for fairy in fairies_group:
                    ftxt = fairy.get_current_dialogue()
                    if ftxt:
                        fairy_dialogues.append(ftxt)

                state = {
                    'level':       current_level_index,
                    'players':     players_list,
                    'enemies':     [_serialize_enemy(e)        for e    in enemies_group],
                    'items':       [_serialize_item(it)        for it   in items_group],
                    'projectiles': [_serialize_projectile(pr)  for pr   in projectiles_group
                                    if not isinstance(pr, HealEffect)],
                    'chests':      [{'x': c.rect.centerx, 'y': c.rect.centery,
                                     'opened': c.opened, 'opening': c.opening,
                                     'frame': int(c.frame_index),
                                     'flipped': c.flipped} for c in chests_group],
                    'game_over':   game_over,
                    'events':      {'dashes': dash_events, 'sounds': sound_events},
                    'time_stop_active': time_stop_active,
                    'time_stop_activator_idx': time_stop_activator_idx,
                    'fairy_dialogues': fairy_dialogues,
                }
                server.send_state(state)

            # --- Interface coffre (host MP) ---
            if chest_ui_active:
                now = pygame.time.get_ticks()
                if chest_ui_closing:
                    elapsed = now - chest_ui_close_time
                    if elapsed >= CHEST_UI_FADE_OUT:
                        chest_ui_active = False
                    else:
                        alpha = int(255 * (1.0 - elapsed / CHEST_UI_FADE_OUT))
                        ui.draw_chest_item_ui(chest_ui_item, alpha)
                else:
                    elapsed = now - chest_ui_start_time
                    alpha = min(255, int(255 * elapsed / CHEST_UI_FADE_IN))
                    ui.draw_chest_item_ui(chest_ui_item, alpha)

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

    font_small = ResourceManager.get_font(24, None)
    death_font = ResourceManager.get_font(120, "old english text mt, garamond, times new roman, serif")

    # Interface d'obtention d'item (coffre) côté client
    chest_ui_active = False
    chest_ui_item = None
    chest_ui_start_time = 0
    chest_ui_closing = False
    chest_ui_close_time = 0
    CHEST_UI_FADE_IN = 300
    CHEST_UI_FADE_OUT = 300

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
        t = ResourceManager.get_font(36, None).render("Connexion en cours…", True, (200, 200, 200))
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

    # --- Surfaces pré-allouées côté client (même logique que le serveur) ---
    _client_ts_overlay    = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    _client_ts_overlay.fill((0, 0, 0, 110))
    _client_death_overlay = pygame.Surface((screen_width, screen_height))
    _client_death_overlay.fill((100, 0, 0))

    # État précédent du joueur local pour détecter les changements d'inventaire
    prev_lp = {'current_weapon': None, 'has_melee': False, 'has_ranged': False,
               'has_pickaxe': False, 'has_boots': False, 'has_red_gem': False,
               'has_blue_gem': False, 'has_mirror': False, 'has_kitsune_mask': False,
               'has_cursed_brand': False, 'has_travelers_cap': False, 'arrows': 0, 'health': 100}
    client_was_walking = False
    client_rp_was_walking = False
    client_red_gem_animating = False
    client_red_gem_anim_start = 0
    # --- Arrêt du temps côté client ---
    client_prev_time_stop = False
    client_ts_player_cache = {}

    while True:
        if not client.connected:
            _cleanup_client_audio(); _show_disconnected(screen); return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _cleanup_client_audio(); client.stop(); pygame.quit(); import sys; sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                is_paused_client = not is_paused_client   # toggle, ne quitte PAS
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                run_game_mp_client._skip_dialogue = True
                if chest_ui_active and not chest_ui_closing:
                    chest_ui_closing = True
                    chest_ui_close_time = pygame.time.get_ticks()

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
            remote_chests         = {}   # (x,y) → Chest
            client_particles_grp  = pygame.sprite.Group()

        players_state  = state.get('players',     [{}, {}])
        enemies_state  = state.get('enemies',     [])
        items_state    = state.get('items',       [])
        projs_state    = state.get('projectiles', [])
        chests_state   = state.get('chests',      [])

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
                re = RemoteEnemy(etype, mob_name=edata.get('mob_name'))
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

        # --- Coffres distants ---
        for cd in chests_state:
            ckey = (cd['x'], cd['y'])
            if ckey not in remote_chests:
                c = Chest(cd['x'], cd['y'], flipped=cd.get('flipped', False))
                group.add(c)
                remote_chests[ckey] = c
            rc = remote_chests[ckey]
            if cd['opened']:
                rc.opened = True
                rc.opening = False
                rc.image = rc.open_img
                rc.rect = rc.image.get_rect(center=rc.rect.center)
            elif cd['opening']:
                rc.opening = True
                rc.frame_index = cd['frame']
                idx = min(cd['frame'], rc.num_frames - 1)
                rc.image = rc.anim_frames[idx]
                rc.rect = rc.image.get_rect(center=rc.rect.center)

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
                    rp._layer = 99
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
            elif snd_name == 'necro_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/necromancer_song.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd_name == 'medusa_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/medusa_ost.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd_name == 'king_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/king_boss_ost.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd_name == 'sbire_bgm_start':
                try:
                    pygame.mixer.music.load("assets/sounds/sbire_neant.mp3")
                    pygame.mixer.music.set_volume(global_music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            elif snd_name == 'boss_bgm_stop':
                try:
                    pygame.mixer.music.fadeout(4000)
                except Exception:
                    pass
            elif snd_name == 'get_item':
                # Le client a ouvert un coffre → afficher l'interface
                chest_item = snd_event.get('chest_item') if isinstance(snd_event, dict) else None
                if chest_item:
                    chest_ui_active = True
                    chest_ui_item = chest_item
                    chest_ui_start_time = pygame.time.get_ticks()
                    chest_ui_closing = False
                sound_manager.play_ui_get_item()
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

        # Avancer les animations locales (pyscroll ne call pas update() via group.draw)
        if remote_player:
            remote_player.update()
        if local_player:
            local_player.update()
        for re in remote_enemies.values():
            re.update()

        group.draw(screen)

        # --- Effet visuel arrêt du temps côté client ---
        client_time_stop = state.get('time_stop_active', False)
        client_ts_activator_idx = state.get('time_stop_activator_idx', -1)

        # Détection entrée / sortie du time stop côté client
        if client_time_stop and not client_prev_time_stop:
            client_ts_player_cache = {}
            sound_manager.enter_time_stop()
            sound_manager.play_ui_time_stop()
        elif not client_time_stop and client_prev_time_stop:
            client_ts_player_cache = {}
            sound_manager.exit_time_stop()
        client_prev_time_stop = client_time_stop

        if client_time_stop:
            # Déterminer le sprite de l'activateur
            ts_activator_sprite = None
            if client_ts_activator_idx == 1 and local_player:
                ts_activator_sprite = local_player
            elif client_ts_activator_idx == 0 and remote_player:
                ts_activator_sprite = remote_player

            # Overlay pré-alloué et pré-rempli — pas de fill() à chaque frame
            screen.blit(_client_ts_overlay, (0, 0))

            # Re-blitter l'activateur en couleur
            if ts_activator_sprite and hasattr(ts_activator_sprite, 'rect') and local_player:
                _vw = screen_width / zoom_level
                _vh = screen_height / zoom_level
                _cx = local_player.feet.centerx
                _cy = local_player.feet.centery - 30
                if map_pixel_width < _vw: _cx = map_pixel_width // 2
                else: _cx = max(_vw // 2, min(_cx, map_pixel_width - _vw // 2))
                if map_pixel_height < _vh: _cy = map_pixel_height // 2
                else: _cy = max(_vh // 2, min(_cy, map_pixel_height - _vh // 2))
                act_sx = (ts_activator_sprite.rect.x - _cx) * zoom_level + screen_width / 2
                act_sy = (ts_activator_sprite.rect.y - _cy) * zoom_level + screen_height / 2
                ck = (int(getattr(ts_activator_sprite, 'frame_index', 0)),
                      getattr(ts_activator_sprite, 'facing', 'down'),
                      getattr(ts_activator_sprite, 'state', 'idle'))
                if ck not in client_ts_player_cache:
                    client_ts_player_cache[ck] = pygame.transform.scale(
                        ts_activator_sprite.image,
                        (int(ts_activator_sprite.rect.width * zoom_level),
                         int(ts_activator_sprite.rect.height * zoom_level))
                    )
                screen.blit(client_ts_player_cache[ck], (act_sx, act_sy))

        # --- Marque Kitsune côté client ---
        lp_now = players_state[1] if len(players_state) >= 2 else {}
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
                if edata.get('health', 0) > 0 and edata['health'] <= edata.get('max_health', 1) * 0.4:
                    ex = (edata['x'] - _cam_x) * zoom_level + screen_width / 2
                    # edata['y'] = feet.bottom, donc feet.top ≈ y - 15
                    ey_offset = -20
                    if edata.get('etype') in ('king', 'sbire'):
                        ey_offset = -40
                    ey_world = edata['y'] + ey_offset
                    ey = (ey_world - _cam_y) * zoom_level + screen_height / 2
                    mark_size = 40
                    if edata.get('etype') == 'medusa':
                        mark_size = 120
                    elif edata.get('etype') in ('bigenemy', 'necromancer', 'king'):
                        mark_size = max(mark_size, 80)
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

        # Son d'attaque immédiat côté client — nouveau système de bindings
        mouse_buttons = pygame.mouse.get_pressed()
        attacking_now = (mouse_buttons[0] or keys[pygame.K_e] or keys[pygame.K_1] or keys[pygame.K_2])
        if attacking_now and lp_now.get('health', 0) > 0:
            if not getattr(run_game_mp_client, '_client_attacking', False):
                sound_manager.play_spatial('sword', client_listener, client_listener)
                run_game_mp_client._client_attacking = True
        else:
            run_game_mp_client._client_attacking = False

        # Items actifs : touches dynamiques basées sur inventory_items
        from player import ACTIVE_ITEMS
        gem_blue_pressed = False
        cursed_brand_pressed = False
        travelers_cap_pressed = False
        zhonya_pressed = False
        dash_pressed = bool(keys[pygame.K_LSHIFT])
        inv_items = lp_now.get('inventory_items', [])
        item_start = lp_now.get('item_start_key', 2)
        active_key = item_start
        for it in inv_items:
            if it in ACTIVE_ITEMS:
                if keys[getattr(pygame, f'K_{active_key}', 0)]:
                    if it == 'boots':
                        dash_pressed = True
                    elif it == 'bluegem':
                        gem_blue_pressed = True
                    elif it == 'cursed_brand':
                        cursed_brand_pressed = True
                    elif it == 'travelers_cap':
                        travelers_cap_pressed = True
                    elif it == 'zhonya':
                        zhonya_pressed = True
                active_key += 1

        # Détection du skip dialogue (event-based, pas key state)
        skip_dialogue_pressed = getattr(run_game_mp_client, '_skip_dialogue', False)
        run_game_mp_client._skip_dialogue = False

        inputs = {
            'up':       bool(keys[pygame.K_z]),
            'down':     bool(keys[pygame.K_s]),
            'left':     bool(keys[pygame.K_q]),
            'right':    bool(keys[pygame.K_d]),
            'attack_mouse': bool(mouse_buttons[0]),
            'attack_e': bool(keys[pygame.K_e]),
            'attack_1': bool(keys[pygame.K_1]),
            'attack_2': bool(keys[pygame.K_2]),
            'interact': bool(keys[pygame.K_f]),
            'dash':     dash_pressed,
            'gem_blue': gem_blue_pressed,
            'cursed_brand': cursed_brand_pressed,
            'travelers_cap': travelers_cap_pressed,
            'zhonya':   zhonya_pressed,
            'skip_dialogue': skip_dialogue_pressed,
        }
        client.send_inputs(inputs)

        # --- HUD joueur local (complet) ---
        lp_state = players_state[1] if len(players_state) >= 2 else {}
        ui.draw_health_bar(lp_state.get('health', 100), lp_state.get('max_health', 100))
        ui.draw_stamina_bar(lp_state.get('stamina', 100), lp_state.get('max_stamina', 100))
        ui.draw_xp_bar(lp_state.get('xp', 0), lp_state.get('xp_to_next_level', 100), lp_state.get('level', 1))
        _lu_elapsed = pygame.time.get_ticks() - lp_state.get('level_up_time', 0)
        if _lu_elapsed < 2000:
            ui.draw_level_up_message(_lu_elapsed / 2000.0, screen_width // 2, screen_height // 2)
        lp_char = lp_state.get('char_type', client_char_type)
        ui.draw_character_hud(lp_char, lp_state.get('current_weapon'),
                              skill_cooldowns=lp_state.get('skill_cooldowns', {}),
                              arrows=lp_state.get('arrows', 0),
                              inventory_items=lp_state.get('inventory_items', []),
                              dash_cr=lp_state.get('dash_cr', 1.0),
                              blue_gem_cr=lp_state.get('blue_gem_cr', 1.0),
                              cursed_brand_cr=lp_state.get('cursed_brand_cr', 1.0),
                              arrow_regen_cr=lp_state.get('arrow_regen_cr', 1.0),
                              travelers_cap_cr=lp_state.get('travelers_cap_cr', 1.0),
                              zhonya_cr=lp_state.get('zhonya_cr', 1.0),
                              item_start_key=lp_state.get('item_start_key', 2))

        # Barre de vie du joueur hôte (en haut à droite)
        rp_state = players_state[0] if len(players_state) >= 1 else {}
        _draw_remote_health(screen, rp_state.get('health', 100), rp_state.get('max_health', 100), label='HÔTE')

        # Barre de vie du boss (uniquement si aggro et vivant)
        for edata in enemies_state:
            if (edata.get('etype') in ('bigenemy', 'necromancer', 'medusa', 'king', 'sbire')
                    and edata.get('has_aggro', False)
                    and edata.get('health', 0) > 0):
                boss_names = {'bigenemy': "Gardien des profondeurs", 'necromancer': "La Faucheuse",
                              'medusa': "Médusa", 'king': "Roi reprouve", 'sbire': "Sbire du neant"}
                boss_name = boss_names.get(edata['etype'], "Boss")
                ui.draw_boss_health_bar(edata['health'], edata['max_health'], boss_name)
                break  # un seul boss à la fois

        # Dialogues de boss (côté client)
        for edata in enemies_state:
            dtxt = edata.get('dialogue_text')
            if dtxt:
                ui.draw_boss_dialogue(dtxt, edata.get('boss_display_name'))
                break

        # Dialogues de fées (côté client)
        for ftxt in state.get('fairy_dialogues', []):
            ui.draw_boss_dialogue(ftxt, "Fee")
            break

        # Dialogue coffre (côté client)
        if local_player and lp_state.get('health', 0) > 0 and not state.get('time_stop_active', False):
            for cd in chests_state:
                if not cd['opened'] and not cd['opening']:
                    ckey = (cd['x'], cd['y'])
                    rc = remote_chests.get(ckey)
                    if rc and local_player.feet.colliderect(rc.hitbox.inflate(40, 40)):
                        ui.draw_dialogue("Appuyer sur F pour ouvrir")
                        break

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
                # Surface pré-allouée — set_alpha() remplace le fill() variable
                _client_death_overlay.set_alpha(int(200 * prog))
                screen.blit(_client_death_overlay, (0, 0))
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
                gem_base = _get_redgem_anim_img()
                gem_img = gem_base.copy()
                gem_img.set_alpha(alpha)
                gem_rect = gem_img.get_rect(center=(screen_width // 2, screen_height // 2))
                overlay = _get_overlay(screen_width, screen_height)
                overlay.fill((255, 50, 50, int(alpha * 0.4)))
                screen.blit(overlay, (0, 0))
                screen.blit(gem_img, gem_rect)
            else:
                client_red_gem_animating = False

        # --- Animation Mirror (fullscreen côté client) ---
        if getattr(run_game_mp_client, '_client_mirror_animating', False):
            elapsed_m = pygame.time.get_ticks() - run_game_mp_client._client_mirror_anim_start
            if elapsed_m < 800:
                if elapsed_m < 200: alpha = int(255 * (elapsed_m / 200.0))
                elif elapsed_m < 500: alpha = 255
                else: alpha = int(255 * (1.0 - (elapsed_m - 500) / 300.0))
                mir_base = _get_mirror_anim_img()
                mir_img = mir_base.copy()
                mir_img.set_alpha(alpha)
                mir_rect = mir_img.get_rect(center=(screen_width // 2, screen_height // 2))
                overlay = _get_overlay(screen_width, screen_height)
                overlay.fill((180, 180, 255, int(alpha * 0.3)))
                screen.blit(overlay, (0, 0))
                screen.blit(mir_img, mir_rect)
            else:
                run_game_mp_client._client_mirror_animating = False

        # --- Animation Cursed Brand (fullscreen côté client) ---
        if getattr(run_game_mp_client, '_client_cb_animating', False):
            elapsed_cb = pygame.time.get_ticks() - run_game_mp_client._client_cb_anim_start
            if elapsed_cb < 800:
                if elapsed_cb < 200: alpha = int(255 * (elapsed_cb / 200.0))
                elif elapsed_cb < 500: alpha = 255
                else: alpha = int(255 * (1.0 - (elapsed_cb - 500) / 300.0))
                cb_base = _get_cursed_brand_anim_img()
                cb_img = cb_base.copy()
                cb_img.set_alpha(alpha)
                cb_rect = cb_img.get_rect(center=(screen_width // 2, screen_height // 2))
                overlay = _get_overlay(screen_width, screen_height)
                overlay.fill((150, 50, 150, int(alpha * 0.3)))
                screen.blit(overlay, (0, 0))
                screen.blit(cb_img, cb_rect)
            else:
                run_game_mp_client._client_cb_animating = False

        # --- Interface coffre (client) ---
        if chest_ui_active:
            now = pygame.time.get_ticks()
            if chest_ui_closing:
                elapsed = now - chest_ui_close_time
                if elapsed >= CHEST_UI_FADE_OUT:
                    chest_ui_active = False
                else:
                    alpha = int(255 * (1.0 - elapsed / CHEST_UI_FADE_OUT))
                    ui.draw_chest_item_ui(chest_ui_item, alpha)
            else:
                elapsed = now - chest_ui_start_time
                alpha = min(255, int(255 * elapsed / CHEST_UI_FADE_IN))
                ui.draw_chest_item_ui(chest_ui_item, alpha)

        pygame.display.flip()
        clock.tick(60)


# =============================================================================
# HELPERS PARTAGÉS
# =============================================================================

_kitsune_mark_cache = {}  # size → Surface
_kitsune_mark_base = None

_mirror_anim_img = None

def _get_mirror_anim_img():
    """Retourne l'image miroir mise en cache pour l'animation fullscreen."""
    global _mirror_anim_img
    if _mirror_anim_img is None:
        try:
            _mirror_anim_img = ResourceManager.get_image("assets/images/mirror.png")
            _mirror_anim_img = pygame.transform.scale(_mirror_anim_img, (128, 128))
        except Exception:
            _mirror_anim_img = pygame.Surface((128, 128), pygame.SRCALPHA)
    return _mirror_anim_img

_redgem_anim_img = None

def _get_redgem_anim_img():
    """Retourne l'image red gem mise en cache pour l'animation fullscreen."""
    global _redgem_anim_img
    if _redgem_anim_img is None:
        try:
            _redgem_anim_img = ResourceManager.get_image("assets/images/redgem.png")
            _redgem_anim_img = pygame.transform.scale(_redgem_anim_img, (128, 128))
        except Exception:
            _redgem_anim_img = pygame.Surface((128, 128), pygame.SRCALPHA)
    return _redgem_anim_img

_cursed_brand_anim_img = None

def _get_cursed_brand_anim_img():
    """Retourne l'image cursed brand mise en cache pour l'animation fullscreen."""
    global _cursed_brand_anim_img
    if _cursed_brand_anim_img is None:
        try:
            _cursed_brand_anim_img = ResourceManager.get_image("assets/images/cursed_brand.png")
            _cursed_brand_anim_img = pygame.transform.scale(_cursed_brand_anim_img, (128, 128))
        except Exception:
            _cursed_brand_anim_img = pygame.Surface((128, 128), pygame.SRCALPHA)
    return _cursed_brand_anim_img

_overlay_cache = {}

def _get_overlay(width, height):
    """Retourne une surface overlay SRCALPHA mise en cache pour la taille donnée."""
    key = (width, height)
    if key not in _overlay_cache:
        _overlay_cache[key] = pygame.Surface((width, height), pygame.SRCALPHA)
    return _overlay_cache[key]

def _get_kitsune_mark(size):
    """Retourne la marque kitsune mise en cache pour une taille donnée."""
    global _kitsune_mark_base
    if size in _kitsune_mark_cache:
        return _kitsune_mark_cache[size]
    if _kitsune_mark_base is None:
        try:
            _kitsune_mark_base = ResourceManager.get_image("assets/images/griffe_passif.png")
        except Exception:
            _kitsune_mark_base = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(_kitsune_mark_base, (255, 50, 50, 200), (16, 16), 16)
    mark = pygame.transform.scale(_kitsune_mark_base, (size, size))
    _kitsune_mark_cache[size] = mark
    return mark


def _get_active_item_keys(player):
    """Retourne la liste des items actifs avec leur touche assignée.
    Utilise le nouveau système inventory_items du joueur."""
    return player.get_active_items_with_keys()


def _count_inventory_items(player):
    """Compte le nombre total d'items dans l'inventaire."""
    return len(player.inventory_items)


def _apply_skill_result(skill_result, caster, group, projectiles_group,
                        particles_group, enemies_group, items_group,
                        sound_manager, sound_events, listener_pos, next_id_fn):
    """Applique les résultats d'une compétence active."""
    # Dégâts de mêlée en zone (Swordsman)
    was_crit_skill = getattr(caster, 'stealth_crit_active', False)
    for enemy, damage in skill_result.get('melee_hits', []):
        dmg = damage * caster.get_damage_multiplier(target_enemy=enemy)
        enemy.damage(dmg)
        _spawn_damage_number(enemy, dmg, caster, group, particles_group, is_crit=was_crit_skill)
    if skill_result.get('melee_hits'):
        caster.stealth_crit_active = False  # consommé après application
        caster.lifesteal(dmg)
        if enemy.health <= 0:
            e_pos = (enemy.feet.centerx, enemy.feet.centery)
            sound_events.append({'sound': 'enemy_death', 'x': e_pos[0], 'y': e_pos[1]})
        _handle_enemy_death(enemy, group, items_group, particles_group)
        if enemy.health <= 0 and not getattr(enemy, '_xp_granted', False):
            enemy._xp_granted = True
            xp = _get_enemy_xp(enemy)
            _grant_xp(xp, [caster], group, particles_group, sound_manager)
    if was_crit_skill and skill_result.get('melee_hits'):
        crit_ft = FloatingText(caster.feet.centerx, caster.feet.centery + 10,
                               text="CRIT!", duration=800, color=(255, 255, 0))
        group.add(crit_ft); particles_group.add(crit_ft)

    # Projectile (Wizard fireball, Archer golden arrow)
    proj = skill_result.get('projectile')
    if proj:
        proj._mp_id = next_id_fn()
        proj._owner = caster
        proj._is_crit = getattr(caster, 'stealth_crit_active', False)
        caster.stealth_crit_active = False  # consommé au tir
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
        aoe._is_crit = getattr(caster, 'stealth_crit_active', False)
        caster.stealth_crit_active = False  # consommé au tir
        aoe._paralyze_duration = homing.get('paralyze', 0)
        aoe._layer = 99
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
        if sound_manager: sound_manager.play_ui_equip_sword()
        return True
    elif item.item_type == 'ranged':
        if not player.has_ranged: player.arrows += 10
        player.has_ranged = True
        if sound_manager: sound_manager.play_ui_equip_bow()
        return True

    # Items d'inventaire : utilise le nouveau système
    if not player.add_inventory_item(item.item_type):
        return False  # Inventaire plein (5 items max)
    if sound_manager and item.item_type != 'pickaxe':
        sound_manager.play_ui_equipement()
    return True


def _grant_xp(amount, players, group, particles_group, sound_manager):
    """Distribue l'XP à tous les joueurs vivants et affiche les textes flottants."""
    if amount <= 0:
        return
    for p in players:
        if not hasattr(p, 'gain_xp') or getattr(p, 'health', 0) <= 0:
            continue
        leveled = p.gain_xp(amount)
        # FloatingText "+X XP" au-dessus du joueur
        ft = FloatingText(p.feet.centerx, p.feet.centery + 10,
                          text=f"+{amount} XP", duration=600,
                          color=(255, 255, 255), font_size=16)
        group.add(ft); particles_group.add(ft)
        if leveled and sound_manager:
            sound_manager.play_ui_levelup()


def _get_enemy_xp(enemy):
    """Retourne le montant d'XP selon le type d'ennemi."""
    if isinstance(enemy, (BigEnemy, Necromancer, Medusa, KingBoss, SbireNeant)):
        return 200  # Boss
    if isinstance(enemy, (EliteOrc, GreatswordSkeleton)):
        return 30   # Mobs élites
    if isinstance(enemy, Spirit):
        return 0    # Spirits du Necromancer, pas d'XP
    return 15       # Mobs normaux


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
    font = ResourceManager.get_font(20, None)
    lbl = font.render(label, True, (200, 200, 200))
    screen.blit(lbl, (x - lbl.get_width() - 5, y))


def _show_disconnected(screen):
    clock = pygame.time.Clock()
    font = ResourceManager.get_font(48, None)
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