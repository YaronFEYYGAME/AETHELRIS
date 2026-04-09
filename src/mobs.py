import pygame
import random
from enemy import Enemy
from projectile import Projectile  # Nécessaire pour l'archer
from resource_manager import ResourceManager

# ==========================================
# MOB 0 : L'ORC CLASSIQUE (L'original refait)
# ==========================================
class Orc(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, name="orc", base_hp=50, base_dmg=7, base_speed=1.0)
        
        self.load_dynamic_animation('idle', "assets/images/Orc-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/Orc-Walk.png")
        self.load_dynamic_animation('attack', "assets/images/Orc-Attack01.png")
        self.load_dynamic_animation('death', "assets/images/Orc-Death.png")
        
        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

# ==========================================
# MOB : FAIRY (Si elle existait dans ton code)
# ==========================================
class Fairy(pygame.sprite.Sprite):
    """PNJ fée de soin. Ne bouge pas, joue son idle en boucle.
    Soigne le joueur une fois par joueur quand il interagit avec F."""

    FAIRY_SPRITES = {
        1: "assets/images/Fairy/Fairy 1.png",
        2: "assets/images/Fairy/Fairy 2.png",
        3: "assets/images/Fairy/Fairy 3.png",
    }

    def __init__(self, x, y, fairy_type=1):
        super().__init__()
        self.fairy_type = fairy_type
        self.scale_factor = 1.5
        self.frame_index = 0
        self.animation_speed = 0.12

        # Charger le spritesheet (horizontal, 8 frames de 32×32)
        self.frames = []
        try:
            path = self.FAIRY_SPRITES.get(fairy_type, self.FAIRY_SPRITES[1])
            sheet = ResourceManager.get_image(path)
            fw = sheet.get_width() // 8
            fh = sheet.get_height()
            for i in range(8):
                frame = sheet.subsurface((i * fw, 0, fw, fh))
                scaled = pygame.transform.scale(frame,
                    (int(fw * self.scale_factor), int(fh * self.scale_factor)))
                self.frames.append(scaled)
        except Exception:
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (100, 255, 100, 200), (16, 16), 12)
            self.frames = [fallback]

        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self.feet = pygame.Rect(0, 0, 16, 16)

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + 8

        # Tracking des joueurs déjà soignés (par index: 0=host, 1=client)
        self.healed_players = set()

        # Dialogue
        self.in_dialogue = False
        self.dialogue_text = None
        self.dialogue_start_time = 0
        self.dialogue_duration = 4000
        self.dialogue_target_player = None

    def can_heal(self, player_index):
        """Vérifie si la fée peut encore soigner ce joueur."""
        return player_index not in self.healed_players

    def interact(self, player, player_index):
        """Interaction avec la fée. Retourne le texte de dialogue."""
        if self.in_dialogue:
            return None

        self.in_dialogue = True
        self.dialogue_start_time = pygame.time.get_ticks()
        self.dialogue_target_player = player_index

        if self.can_heal(player_index):
            self.healed_players.add(player_index)
            player.health = player.max_health
            self.dialogue_text = "Hop ! Tes ecorchures ne sont plus qu'un mauvais souvenir. Essaie de ne pas te briser en mille morceaux avant notre prochaine rencontre !"
        else:
            self.dialogue_text = "Oups ! La source est a sec et mes mains tremblent. Il va falloir faire preuve d'un peu plus de prudence, petit mortel."

        return self.dialogue_text

    def skip_dialogue(self):
        """Skip le dialogue en cours."""
        if self.in_dialogue:
            self.in_dialogue = False
            self.dialogue_text = None
            return True
        return False

    def get_current_dialogue(self):
        """Retourne le texte du dialogue en cours."""
        if self.in_dialogue:
            return self.dialogue_text
        return None

    def update(self, *args):
        # Animation idle en boucle
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.frame_index = 0
        self.image = self.frames[int(self.frame_index)]

        # Fin automatique du dialogue
        if self.in_dialogue:
            if pygame.time.get_ticks() - self.dialogue_start_time >= self.dialogue_duration:
                self.in_dialogue = False
                self.dialogue_text = None


# ==========================================
# MOB 1 : SKELETON
# ==========================================
class Skeleton(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, name="skeleton", base_hp=50, base_dmg=7, base_speed=1.0)
        self.load_dynamic_animation('idle', "assets/images/mob/Skeleton/Skeleton-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/Skeleton/Skeleton-Walk.png")
        self.load_dynamic_animation('attack', "assets/images/mob/Skeleton/Skeleton-Attack01.png")
        self.load_dynamic_animation('death', "assets/images/mob/Skeleton/Skeleton-Death.png")
        
        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

# ==========================================
# MOB 2 : SLIME
# ==========================================
class Slime(Enemy):
    def __init__(self, x, y):
        # PV x0.6, Vitesse x1.4, Dégâts x1
        super().__init__(x, y, name="slime", base_hp=30, base_dmg=7, base_speed=1.4)
        self.load_dynamic_animation('idle', "assets/images/mob/Slime/Slime-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/Slime/Slime-Walk.png")
        self.load_dynamic_animation('attack', "assets/images/mob/Slime/Slime-Attack01.png")
        self.load_dynamic_animation('death', "assets/images/mob/Slime/Slime-Death.png")

        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

# ==========================================
# MOB 3 : ORC RIDER
# ==========================================
class OrcRider(Enemy):
    SHORT_RANGE = 40
    MID_RANGE = 100
    AOE_RADIUS = 80

    def __init__(self, x, y):
        # PV x2
        super().__init__(x, y, name="orc_rider", base_hp=100, base_dmg=7, base_speed=1.0)
        
        # Hitbox plus grande pour le cavalier
        hitbox_size = int(15 * self.scale_factor)
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        self.feet.midbottom = (round(x), round(y))

        self.load_dynamic_animation('idle', "assets/images/mob/Orc_rider/Orc rider-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/Orc_rider/Orc rider-Walk.png")
        self.load_dynamic_animation('attack1', "assets/images/mob/Orc_rider/Orc rider-Attack01.png")
        self.load_dynamic_animation('attack2', "assets/images/mob/Orc_rider/Orc rider-Attack02.png")
        self.load_dynamic_animation('attack3', "assets/images/mob/Orc_rider/Orc rider-Attack03.png")
        self.load_dynamic_animation('death', "assets/images/mob/Orc_rider/Orc rider-Death.png")
        
        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

    def choose_attack(self, distance_to_target, all_players):
        """Choisit l'attaque en fonction de la distance et du nombre de joueurs proches."""
        players_in_range = sum(1 for p in all_players if self.position.distance_to(p.position) <= self.AOE_RADIUS)
        
        if players_in_range > 1:
            return 'attack3' # Balayage de zone
        elif distance_to_target <= self.SHORT_RANGE:
            return 'attack1' # Corps à corps court
        else:
            return 'attack2' # Corps à corps moyen

# ==========================================
# MOB 4 : ELITE ORC
# ==========================================
class EliteOrc(Enemy):
    AOE_RADIUS = 70

    def __init__(self, x, y):
        # PV x4, Dégâts x1.3
        super().__init__(x, y, name="elite_orc", base_hp=200, base_dmg=13, base_speed=1.0)
        self.load_dynamic_animation('idle', "assets/images/mob/Elite_Orc/Elite Orc-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/Elite_Orc/Elite Orc-Walk.png")
        self.load_dynamic_animation('attack1', "assets/images/mob/Elite_Orc/Elite Orc-Attack01.png")
        self.load_dynamic_animation('attack2', "assets/images/mob/Elite_Orc/Elite Orc-Attack02.png")
        self.load_dynamic_animation('attack3', "assets/images/mob/Elite_Orc/Elite Orc-Attack03.png")
        self.load_dynamic_animation('death', "assets/images/mob/Elite_Orc/Elite Orc-Death.png")
        
        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

    def choose_attack(self, all_players):
        players_in_range = sum(1 for p in all_players if self.position.distance_to(p.position) <= self.AOE_RADIUS)
        
        if players_in_range > 1:
            return random.choice(['attack1', 'attack2', 'attack3']) # 33/33/33
        else:
            return random.choice(['attack1', 'attack3']) # 50/50, pas de balayage

# ==========================================
# MOB 5 : GREATSWORD SKELETON
# ==========================================
class GreatswordSkeleton(Enemy):
    def __init__(self, x, y):
        # PV x4
        super().__init__(x, y, name="greatsword_skeleton", base_hp=200, base_dmg=7, base_speed=1.0)
        self.load_dynamic_animation('idle', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Walk.png")
        self.load_dynamic_animation('attack1', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Attack01.png")
        self.load_dynamic_animation('attack2', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Attack02.png")
        self.load_dynamic_animation('attack3', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Attack03.png")
        self.load_dynamic_animation('death', "assets/images/mob/greatsword_skeleton/Greatsword Skeleton-Death.png")
        
        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

    def get_attack_animation(self):
        return random.choice(['attack1', 'attack2', 'attack3'])

    def get_damage_delay(self, anim_name):
        """Dégâts différés selon l'animation d'attaque."""
        if anim_name == 'attack2':
            return 350  # ms — épée qui descend (légèrement avancé)
        if anim_name == 'attack1':
            return 150  # ms — coup rapide, délai très léger
        return 0

# ==========================================
# MOB 6 : SKELETON ARCHER
# ==========================================
class SkeletonArcher(Enemy):
    ARCHER_ATTACK_RANGE = 200  # portée de tir
    ALIGN_TOLERANCE = 8        # tolérance verticale pour considérer qu'on est aligné

    def __init__(self, x, y):
        super().__init__(x, y, name="skeleton_archer", base_hp=50, base_dmg=7, base_speed=1.0)
        self.attack_range = self.ARCHER_ATTACK_RANGE
        self.detection_radius = 250
        self._arrow_fired = False  # True une fois la flèche tirée pendant l'animation
        self.load_dynamic_animation('idle', "assets/images/mob/skeleton_archer/Skeleton Archer-Idle.png")
        self.load_dynamic_animation('walk', "assets/images/mob/skeleton_archer/Skeleton Archer-Walk.png")
        self.load_dynamic_animation('attack', "assets/images/mob/skeleton_archer/Skeleton Archer-Attack.png")
        self.load_dynamic_animation('death', "assets/images/mob/skeleton_archer/Skeleton Archer-Death.png")

        if 'idle' in self.animations['right']:
            self.image = self.animations['right']['idle'][0]

    def update(self, player, walls):
        """Override complet : l'archer s'aligne en Y puis tire de loin."""
        # --- Dégâts différés ---
        if self._pending_damage is not None and not self.is_dead:
            trigger_time, dmg, target = self._pending_damage
            if pygame.time.get_ticks() >= trigger_time:
                target.damage(dmg, source_enemy=self)
                self._pending_damage = None

        if self.is_dead:
            self._pending_damage = None
            self.animate()
            self.rect.size = self.image.get_size()
            self.rect.centerx = self.feet.centerx
            self.rect.bottom = self.feet.bottom + self.empty_space_below
            if pygame.time.get_ticks() - self.death_time > 3000:
                self.kill()
            return

        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.current_velocity = pygame.math.Vector2(0, 0)
                self.animate()
                self.rect.size = self.image.get_size()
                self.rect.centerx = self.feet.centerx
                self.rect.bottom = self.feet.bottom + self.empty_space_below
                return

        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        velocity_x, velocity_y = 0, 0

        if distance < self.detection_radius and not self.is_attacking and player.health > 0:
            dy = target_center.y - my_center.y
            aligned = abs(dy) < self.ALIGN_TOLERANCE

            # Faire face au joueur
            if target_center.x > my_center.x:
                self.facing = "right"
            else:
                self.facing = "left"

            if not aligned:
                # Pas encore aligné → se déplacer uniquement en Y
                velocity_y = self.speed if dy > 0 else -self.speed
                self.position.y += velocity_y
                self.feet.bottom = round(self.position.y)
                for wall in walls:
                    if self.feet.colliderect(wall):
                        if velocity_y > 0:
                            self.feet.bottom = wall.top
                        else:
                            self.feet.top = wall.bottom
                        self.position.y = self.feet.bottom
                        break
            elif distance > self.ARCHER_ATTACK_RANGE * 0.7:
                # Aligné mais trop loin → se rapprocher en X
                dx_dir = 1 if target_center.x > my_center.x else -1
                velocity_x = self.speed * dx_dir
                self.position.x += velocity_x
                self.feet.centerx = round(self.position.x)
                for wall in walls:
                    if self.feet.colliderect(wall):
                        if velocity_x > 0:
                            self.feet.right = wall.left
                        else:
                            self.feet.left = wall.right
                        self.position.x = self.feet.centerx
                        break

        self.current_velocity = pygame.math.Vector2(velocity_x, velocity_y)

        self.animate()
        self.rect.size = self.image.get_size()
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.empty_space_below

        # --- Tir à distance ---
        if (distance < self.ARCHER_ATTACK_RANGE
                and not self.is_attacking
                and player.health > 0
                and abs(target_center.y - my_center.y) < self.ALIGN_TOLERANCE):
            current_time = pygame.time.get_ticks()
            if current_time - self.last_attack_time > 2000:
                self.last_attack_time = current_time
                self.is_attacking = True
                self.frame_index = 0
                self._current_attack_anim = 'attack'
                self._arrow_fired = False  # Flèche pas encore tirée

    def fire_arrow(self, target, group, enemy_projectiles_group):
        """Tire une flèche vers la cible. Appelé par game.py au milieu de l'animation."""
        direction = "right" if target.feet.centerx > self.feet.centerx else "left"
        arrow = Projectile(
            self.feet.centerx,
            self.rect.centery + int(5 * self.scale_factor),
            direction,
            img_path="assets/images/mob/skeleton_archer/Arrow03(32x32).png",
            damage=self.damage_amount
        )
        arrow._is_enemy_projectile = True
        group.add(arrow)
        enemy_projectiles_group.add(arrow)
        self._arrow_fired = True