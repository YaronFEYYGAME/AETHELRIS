import pygame
from projectile import Projectile
from characters import get_character_def


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, char_type='soldier'):
        super().__init__()
        self.char_type = char_type
        self.char_def = get_character_def(char_type)

        self.scale_factor = self.char_def['scale_factor']
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.2

        self.empty_space_below = self.char_def['empty_space_below'] * self.scale_factor

        # Charger toutes les animations définies pour ce personnage
        for anim_name, (path, num_frames) in self.char_def['animations'].items():
            self.load_animation(anim_name, path, num_frames)

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        # Hitbox identique pour tous les personnages
        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

        self.velocity = pygame.math.Vector2(0, 0)
        self.speed = 2.5
        self.max_health = 100
        self.health = 100

        # Armes de base selon la classe (déjà équipées)
        self.has_melee = self.char_def['has_melee']
        self.has_ranged = self.char_def['has_ranged']
        self.current_weapon = self.char_def['current_weapon']
        self.arrows = self.char_def['arrows']
        self.melee_damage = self.char_def['melee_damage']
        self.ranged_damage = self.char_def.get('ranged_damage', 10.5)

        self.attack_cooldown = self.char_def.get('attack_cooldown_melee', 600)
        self.last_attack_time = 0
        self.facing = "right"
        self.is_attacking = False
        self.arrow_fired = False

        self.has_pickaxe = False

        # Boots / dash
        self.has_boots = False
        self.dash_cooldown = 4000
        self.last_dash_time = 0

        # Gems
        self.has_red_gem = False
        self.red_gem_triggered = False  # flag pour l'animation fullscreen
        self.has_blue_gem = False
        self.blue_gem_active = False
        self.blue_gem_end_time = 0
        self.blue_gem_cooldown = 30000  # 30 secondes
        self.last_blue_gem_time = -30000  # prêt immédiatement

        self.is_hit = False
        self.last_hit_time = 0

        # --- Compétences (skills) ---
        self.abilities = self.char_def.get('abilities', {})
        self.skill_cooldowns = {}  # skill_name → last_use_time
        self.skill_hit_flags = {}  # skill_name → set of frames already hit
        self.active_skill = None   # skill en cours d'exécution
        self.skill_fired = False   # pour les projectiles de compétence

        for skill_name in self.abilities:
            self.skill_cooldowns[skill_name] = -999999  # prêt immédiatement

        # Archer : régénération de flèches
        self.arrow_regen_time = self.char_def.get('arrow_regen_time', 0)
        self.arrow_regen_amount = self.char_def.get('arrow_regen_amount', 0)
        self._arrow_empty_time = 0  # timestamp quand arrows est tombé à 0

    def load_animation(self, state_name, path, num_frames):
        try:
            sprite_sheet = pygame.image.load(path).convert_alpha()
            frame_width = sprite_sheet.get_width() // num_frames
            frame_height = sprite_sheet.get_height()
            frames_right = []
            frames_left = []
            for i in range(num_frames):
                frame = sprite_sheet.subsurface((i * frame_width, 0, frame_width, frame_height))
                new_width = int(frame_width * self.scale_factor)
                new_height = int(frame_height * self.scale_factor)
                frame = pygame.transform.scale(frame, (new_width, new_height))

                shifted_frame = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
                shifted_frame.blit(frame, (0, int(self.empty_space_below)))

                frames_right.append(shifted_frame)
                frames_left.append(pygame.transform.flip(shifted_frame, True, False))
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"Erreur: Fichier {path} introuvable.")

    def switch_weapon(self, weapon_name):
        """Changer d'arme/compétence active."""
        if weapon_name == 'melee' and self.has_melee:
            self.current_weapon = 'melee'
        elif weapon_name == 'ranged' and self.has_ranged:
            self.current_weapon = 'ranged'
        elif weapon_name in self.abilities:
            self.current_weapon = weapon_name

    def input(self):
        if self.state == 'death' or self.is_attacking:
            self.velocity.xy = 0, 0
            return

        keys = pygame.key.get_pressed()
        self.velocity.xy = 0, 0

        if keys[pygame.K_z]: self.velocity.y -= 1
        elif keys[pygame.K_s]: self.velocity.y += 1
        if keys[pygame.K_q]:
            self.velocity.x -= 1
            self.facing = "left"
        elif keys[pygame.K_d]:
            self.velocity.x += 1
            self.facing = "right"

        if self.velocity.length() > 0:
            self.velocity = self.velocity.normalize() * self.speed

    def move(self, walls):
        if self.state == 'death' or self.is_attacking:
            return

        self.position.x += self.velocity.x
        self.feet.centerx = round(self.position.x)
        for wall in walls:
            if self.feet.colliderect(wall):
                if self.velocity.x > 0: self.feet.right = wall.left
                elif self.velocity.x < 0: self.feet.left = wall.right
                self.position.x = self.feet.centerx

        self.position.y += self.velocity.y
        self.feet.bottom = round(self.position.y)
        for wall in walls:
            if self.feet.colliderect(wall):
                if self.velocity.y > 0: self.feet.bottom = wall.top
                elif self.velocity.y < 0: self.feet.top = wall.bottom
                self.position.y = self.feet.bottom

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

    def dash(self, walls):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_dash_time < self.dash_cooldown:
            return False

        self.last_dash_time = current_time
        dash_distance = 150
        step = 10

        if self.velocity.length() > 0:
            dir_vec = self.velocity.normalize()
        else:
            dir_vec = pygame.math.Vector2(1 if self.facing == 'right' else -1, 0)

        for _ in range(int(dash_distance / step)):
            self.feet.x += dir_vec.x * step
            if any(self.feet.colliderect(w) for w in walls):
                self.feet.x -= dir_vec.x * step
            else:
                self.position.x = self.feet.centerx

            self.feet.y += dir_vec.y * step
            if any(self.feet.colliderect(w) for w in walls):
                self.feet.y -= dir_vec.y * step
            else:
                self.position.y = self.feet.bottom

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom
        return True

    def animate(self):
        if self.health <= 0:
            self.state = 'death'
        elif self.is_attacking:
            if self.active_skill:
                self.state = self.active_skill
            elif self.current_weapon == 'melee':
                self.state = 'attack_melee'
            elif self.current_weapon == 'ranged':
                self.state = 'attack_ranged'
            elif self.current_weapon in self.abilities:
                # Attaque de base via compétence
                anim = self.abilities[self.current_weapon].get('anim', 'idle')
                self.state = anim
        elif self.velocity.length() > 0:
            self.state = 'walk'
        else:
            self.state = 'idle'

        # Fallback si l'animation n'existe pas
        if self.state not in self.animations.get(self.facing, {}):
            self.state = 'idle'

        animation = self.animations[self.facing][self.state]
        speed = self.animation_speed * 1.5 if self.is_attacking else self.animation_speed
        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
            elif self.is_attacking:
                self.is_attacking = False
                self.active_skill = None
                self.skill_fired = False
                self.skill_hit_flags = {}
                self.frame_index = 0
            else:
                self.frame_index = 0

        self.image = animation[int(self.frame_index)].copy()

        if self.is_hit:
            if pygame.time.get_ticks() - self.last_hit_time < 200:
                mask = pygame.mask.from_surface(self.image)
                red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
                self.image.blit(red_overlay, (0, 0))
            else:
                self.is_hit = False

        # Blue Gem : teinte bleue pendant l'invincibilité
        if self.blue_gem_active:
            if pygame.time.get_ticks() < self.blue_gem_end_time:
                mask = pygame.mask.from_surface(self.image)
                blue_overlay = mask.to_surface(setcolor=(50, 100, 255, 120), unsetcolor=(0, 0, 0, 0))
                self.image.blit(blue_overlay, (0, 0))
            else:
                self.blue_gem_active = False

    def attack(self):
        """Attaque de base (E). Retourne ('melee', rect), ('ranged', None), ou None."""
        if self.state == 'death' or self.is_attacking or self.current_weapon is None:
            return None

        current_time = pygame.time.get_ticks()

        # Si l'arme courante est une compétence, utiliser use_skill
        if self.current_weapon in self.abilities:
            return self.use_skill(self.current_weapon)

        if self.current_weapon == 'melee':
            cooldown = self.char_def.get('attack_cooldown_melee', 600)
            if current_time - self.last_attack_time > cooldown:
                self.last_attack_time = current_time
                self.is_attacking = True
                self.frame_index = 0
                attack_size = 70
                attack_rect = pygame.Rect(0, 0, attack_size, attack_size)
                attack_rect.center = self.feet.center
                return ('melee', attack_rect)

        elif self.current_weapon == 'ranged':
            cooldown = self.char_def.get('attack_cooldown_ranged', 800)
            if current_time - self.last_attack_time > cooldown:
                if self.arrows <= 0:
                    return None
                self.last_attack_time = current_time
                self.is_attacking = True
                self.frame_index = 0
                self.arrow_fired = False
                return ('ranged', None)

        return None

    def use_skill(self, skill_name):
        """Active une compétence. Retourne ('skill', skill_name) ou None."""
        if self.state == 'death' or self.is_attacking:
            return None
        if skill_name not in self.abilities:
            return None

        skill = self.abilities[skill_name]
        current_time = pygame.time.get_ticks()
        cooldown = skill.get('cooldown', 1000)
        last_use = self.skill_cooldowns.get(skill_name, -999999)

        if current_time - last_use < cooldown:
            return None

        self.skill_cooldowns[skill_name] = current_time
        self.is_attacking = True
        self.active_skill = skill.get('anim', skill_name)
        self.frame_index = 0
        self.skill_fired = False
        self.skill_hit_flags = {}
        return ('skill', skill_name)

    def reset_skill_cooldown(self, skill_name):
        """Annule le cooldown d'une compétence (utilisé quand elle échoue)."""
        self.skill_cooldowns[skill_name] = -999999

    def check_ranged_attack(self):
        """Vérifie si un projectile doit être tiré (attaque à distance standard)."""
        fire_frame = self.char_def.get('ranged_fire_frame', 6)
        if (self.state == 'attack_ranged'
                and int(self.frame_index) == fire_frame
                and not self.arrow_fired):
            self.arrow_fired = True
            self.arrows -= 1
            proj_img = self.char_def.get('projectile_img', 'assets/images/Arrow01(32x32).png')
            projectile = Projectile(self.feet.centerx, self.feet.centery, self.facing,
                                    img_path=proj_img, damage=self.ranged_damage)
            return projectile
        return None

    def check_skill_attack(self, skill_name, enemies_group=None, ally_player=None):
        """Vérifie et retourne les résultats d'une compétence active.

        Retourne un dict d'événements :
        {
            'melee_hits': [(enemy, damage), ...],
            'projectile': Projectile or None,
            'homing': {'target_pos': (x,y), 'damage': d, 'radius': r, ...} or None,
            'heal': {'target': player, 'amount': a, ...} or None,
        }
        """
        result = {'melee_hits': [], 'projectile': None, 'homing': None, 'heal': None}

        if skill_name not in self.abilities or not self.is_attacking:
            return result

        skill = self.abilities[skill_name]
        anim_name = skill.get('anim', skill_name)
        if self.state != anim_name:
            return result

        current_frame = int(self.frame_index)
        skill_type = skill.get('type', 'melee_aoe')

        # --- Compétences de mêlée en zone (Swordsman) ---
        if skill_type == 'melee_aoe' or 'hit_frames' in skill:
            hit_frames = skill.get('hit_frames', [])
            for hf in hit_frames:
                if current_frame == hf and hf not in self.skill_hit_flags:
                    self.skill_hit_flags[hf] = True
                    attack_range = skill.get('range', 80)
                    attack_rect = pygame.Rect(0, 0, attack_range, attack_range)
                    attack_rect.center = self.feet.center
                    if self.facing == 'right':
                        attack_rect.left = self.feet.centerx
                    else:
                        attack_rect.right = self.feet.centerx
                    if enemies_group:
                        for e in enemies_group:
                            if getattr(e, 'health', 0) > 0 and attack_rect.colliderect(e.feet):
                                result['melee_hits'].append((e, skill.get('damage', 10)))

        # --- Projectile (Wizard fireball, Archer golden arrow) ---
        elif skill_type == 'projectile':
            fire_frame = skill.get('fire_frame', 3)
            if current_frame == fire_frame and not self.skill_fired:
                self.skill_fired = True
                proj_img = skill.get('projectile_img')
                damage = skill.get('damage', 15)
                piercing = skill.get('piercing', False)
                proj = Projectile(self.feet.centerx, self.feet.centery, self.facing,
                                  img_path=proj_img, damage=damage, piercing=piercing)
                result['projectile'] = proj

        # --- Instant AOE (orbe de cristal wizard, onde priest) ---
        # Spawn directement sur l'ennemi le plus proche et explose en zone
        elif skill_type == 'homing':
            fire_frame = skill.get('fire_frame', 3)
            if current_frame == fire_frame and not self.skill_fired:
                self.skill_fired = True
                # Trouver l'ennemi le plus proche (zone de détection élargie)
                target_pos = None
                detect_range = skill.get('detect_range', 400)
                if enemies_group:
                    closest = None
                    closest_dist = float('inf')
                    for e in enemies_group:
                        if getattr(e, 'health', 0) > 0:
                            dist = pygame.math.Vector2(
                                e.feet.centerx - self.feet.centerx,
                                e.feet.centery - self.feet.centery
                            ).length()
                            if dist < closest_dist and dist <= detect_range:
                                closest_dist = dist
                                closest = e
                    if closest:
                        target_pos = (closest.feet.centerx, closest.feet.centery)

                if target_pos:
                    # Taille de l'effet proportionnelle à la taille de l'ennemi
                    target_size = 48  # taille par défaut
                    if closest and hasattr(closest, 'rect'):
                        target_size = max(closest.rect.width, closest.rect.height)
                    result['homing'] = {
                        'target_pos': target_pos,
                        'damage': skill.get('damage', 20),
                        'radius': skill.get('explosion_radius', 60),
                        'effect_img': skill.get('effect_img'),
                        'effect_frames': skill.get('effect_frames', 5),
                        'instant': True,
                        'target_size': target_size,
                        'render_scale': skill.get('render_scale', 1.2),
                    }
                else:
                    # Aucun ennemi à portée → signaler l'échec
                    result['fail'] = True

        # --- Heal (Priest) ---
        elif skill_type == 'heal':
            fire_frame = skill.get('fire_frame', 3)
            if current_frame == fire_frame and not self.skill_fired:
                self.skill_fired = True
                heal_range = skill.get('heal_range', 120)
                if ally_player and ally_player.health > 0:
                    dist = pygame.math.Vector2(
                        ally_player.feet.centerx - self.feet.centerx,
                        ally_player.feet.centery - self.feet.centery
                    ).length()
                    if dist <= heal_range:
                        heal_amount = ally_player.max_health * skill.get('heal_amount', 0.30)
                        result['heal'] = {
                            'target': ally_player,
                            'amount': heal_amount,
                            'effect_img': skill.get('effect_img'),
                            'effect_frames': skill.get('effect_frames', 4),
                            'target_pos': (ally_player.feet.centerx, ally_player.feet.centery),
                        }

        return result

    def get_skill_cooldown_ratio(self, skill_name):
        """Retourne le ratio de cooldown (0.0 = vient d'être utilisé, 1.0 = prêt)."""
        if skill_name not in self.abilities:
            return 1.0
        skill = self.abilities[skill_name]
        cooldown = skill.get('cooldown', 1000)
        last_use = self.skill_cooldowns.get(skill_name, -999999)
        elapsed = pygame.time.get_ticks() - last_use
        return min(1.0, max(0.0, elapsed / cooldown))

    def update_arrow_regen(self):
        """Archer : regagne des flèches automatiquement après un délai."""
        if self.arrow_regen_time <= 0:
            return
        current_time = pygame.time.get_ticks()
        if self.arrows <= 0:
            if self._arrow_empty_time == 0:
                self._arrow_empty_time = current_time
            elif current_time - self._arrow_empty_time >= self.arrow_regen_time:
                self.arrows = self.arrow_regen_amount
                self._arrow_empty_time = 0
        else:
            self._arrow_empty_time = 0

    def is_moving(self):
        return self.velocity.length() > 0

    def damage(self, amount):
        if self.state != 'death':
            # Blue Gem : invincibilité active → ignore les dégâts
            if self.blue_gem_active and pygame.time.get_ticks() < self.blue_gem_end_time:
                return
            self.health -= amount
            self.is_hit = True
            self.last_hit_time = pygame.time.get_ticks()
            if self.health <= 0:
                # Red Gem : empêche la mort et restaure 100% PV
                if self.has_red_gem:
                    self.health = self.max_health
                    self.has_red_gem = False
                    self.red_gem_triggered = True
                    return
                self.health = 0
                self.frame_index = 0

    def activate_blue_gem(self):
        """Active la Blue Gem : 5 secondes d'invincibilité."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_blue_gem_time < self.blue_gem_cooldown:
            return False
        self.last_blue_gem_time = current_time
        self.blue_gem_active = True
        self.blue_gem_end_time = current_time + 5000
        return True

    def get_blue_gem_cooldown_ratio(self):
        """Retourne le ratio de cooldown de la blue gem (0.0 = vient d'être utilisé, 1.0 = prêt)."""
        elapsed = pygame.time.get_ticks() - self.last_blue_gem_time
        return min(1.0, max(0.0, elapsed / self.blue_gem_cooldown))

    def heal(self, amount):
        if self.state != 'death':
            self.health += amount
            if self.health > self.max_health:
                self.health = self.max_health

    def apply_network_inputs(self, inputs):
        """Pilote le joueur depuis des inputs réseau."""
        if self.state == 'death' or self.is_attacking:
            self.velocity.xy = 0, 0
            return
        self.velocity.xy = 0, 0
        if inputs.get('up'):
            self.velocity.y -= 1
        if inputs.get('down'):
            self.velocity.y += 1
        if inputs.get('left'):
            self.velocity.x -= 1
            self.facing = 'left'
        if inputs.get('right'):
            self.velocity.x += 1
            self.facing = 'right'
        if self.velocity.length() > 0:
            self.velocity = self.velocity.normalize() * self.speed

    def update(self):
        self.input()
        self.animate()
        self.update_arrow_regen()


class RemotePlayer(pygame.sprite.Sprite):
    """Sprite du joueur distant : rendu uniquement, piloté par l'état réseau."""

    def __init__(self, x, y, char_type='soldier'):
        super().__init__()
        self.char_type = char_type
        self.char_def = get_character_def(char_type)
        self.scale_factor = self.char_def['scale_factor']
        self.animations = {'right': {}, 'left': {}}
        self.empty_space_below = self.char_def['empty_space_below'] * self.scale_factor

        # Charger les animations du personnage
        for anim_name, (path, num_frames) in self.char_def['animations'].items():
            self._load_anim(anim_name, path, num_frames)

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        self.feet.midbottom = (round(x), round(y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

        self.health = 100
        self.max_health = 100

    def _load_anim(self, state_name, path, num_frames):
        try:
            sheet = pygame.image.load(path).convert_alpha()
            fw = sheet.get_width() // num_frames
            fh = sheet.get_height()
            rights, lefts = [], []
            for i in range(num_frames):
                frame = sheet.subsurface((i * fw, 0, fw, fh))
                nw, nh = int(fw * self.scale_factor), int(fh * self.scale_factor)
                frame = pygame.transform.scale(frame, (nw, nh))
                shifted = pygame.Surface((nw, nh), pygame.SRCALPHA)
                shifted.blit(frame, (0, int(self.empty_space_below)))
                rights.append(shifted)
                lefts.append(pygame.transform.flip(shifted, True, False))
            self.animations['right'][state_name] = rights
            self.animations['left'][state_name] = lefts
        except FileNotFoundError:
            pass

    def update_from_state(self, state):
        x = state.get('x', self.feet.centerx)
        y = state.get('y', self.feet.bottom)
        direction = state.get('direction', 'right')
        anim_state = state.get('state', 'idle')
        frame = state.get('frame', 0)
        self.health = state.get('health', 100)
        self.max_health = state.get('max_health', 100)

        self.feet.midbottom = (round(x), round(y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

        anims = self.animations.get(direction, self.animations['right'])
        if anim_state not in anims:
            anim_state = 'idle'
        frames = anims[anim_state]
        self.image = frames[int(frame) % len(frames)].copy()

        # Blue Gem : teinte bleue si invincibilité active
        if state.get('blue_gem_active', False):
            mask = pygame.mask.from_surface(self.image)
            blue_overlay = mask.to_surface(setcolor=(50, 100, 255, 120), unsetcolor=(0, 0, 0, 0))
            self.image.blit(blue_overlay, (0, 0))

    def update(self):
        pass
