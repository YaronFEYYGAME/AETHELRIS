"""
Définitions des classes de personnages jouables.
Chaque personnage a ses propres sprites, animations, attaques et compétences.
"""

# Configuration de chaque classe de personnage
# Toutes les sprites sont en 100x100 pixels
CHARACTER_DEFS = {
    'soldier': {
        'name': 'Soldier',
        'scale_factor': 1.5,
        'empty_space_below': 43,
        'animations': {
            'idle':          ('assets/images/Soldier-Idle.png', 6),
            'walk':          ('assets/images/Soldier-Walk.png', 8),
            'death':         ('assets/images/Soldier-Death.png', 4),
            'attack_melee':  ('assets/images/Soldier-Attack01.png', 6),
            'attack_ranged': ('assets/images/Soldier-Attack03.png', 9),
        },
        'has_melee': True,
        'has_ranged': True,
        'current_weapon': 'melee',
        'arrows': 15,
        'melee_damage': 10,
        'ranged_damage': 10.5,
        'attack_cooldown_melee': 600,
        'attack_cooldown_ranged': 800,
        'ranged_fire_frame': 6,
        'abilities': {},
        'icons': {
            'slot1': 'assets/images/sword_icon.png',
            'slot2': 'assets/images/arc_icon.png',
        },
        'projectile_img': 'assets/images/Arrow01(32x32).png',
    },

    'swordsman': {
        'name': 'Swordsman',
        'scale_factor': 1.5,
        'empty_space_below': 43,
        'animations': {
            'idle':          ('assets/images/Swordsman-Idle.png', 6),
            'walk':          ('assets/images/Swordsman-Walk.png', 8),
            'death':         ('assets/images/Swordsman-Death.png', 4),
            'attack_melee':  ('assets/images/Swordsman-Attack01.png', 7),
            'skill1':        ('assets/images/Swordsman-Attack02.png', 15),
            'skill2':        ('assets/images/Swordsman-Attack3.png', 12),
        },
        'has_melee': True,
        'has_ranged': False,
        'current_weapon': 'melee',
        'arrows': 0,
        'melee_damage': 12,
        'ranged_damage': 0,
        'attack_cooldown_melee': 500,
        'attack_cooldown_ranged': 0,
        'ranged_fire_frame': -1,
        'abilities': {
            'skill1': {
                'cooldown': 3000,     # 3 secondes
                'damage': 8,          # par salve
                'hits': 3,            # 3 salves
                'hit_frames': [4, 8, 12],  # frames qui infligent des dégâts
                'range': 80,
                'anim': 'skill1',
            },
            'skill2': {
                'cooldown': 8000,     # 8 secondes
                'damage': 6,          # par salve
                'hits': 5,            # 5 salves rapides
                'hit_frames': [2, 4, 6, 8, 10],
                'range': 80,
                'anim': 'skill2',
            },
        },
        'icons': {
            'slot1': 'assets/images/sword2_icon.png',
            'slot2': 'assets/images/sword2_icon.png',
        },
        'projectile_img': None,
    },

    'archer': {
        'name': 'Archer',
        'scale_factor': 1.5,
        'empty_space_below': 43,
        'animations': {
            'idle':          ('assets/images/Archer-Idle.png', 6),
            'walk':          ('assets/images/Archer-Walk.png', 8),
            'death':         ('assets/images/Archer-Death.png', 4),
            'attack_ranged': ('assets/images/Archer-Attack01.png', 9),
            'skill1':        ('assets/images/Archer-Attack02.png', 12),
        },
        'has_melee': False,
        'has_ranged': True,
        'current_weapon': 'ranged',
        'arrows': 15,
        'melee_damage': 0,
        'ranged_damage': 10.5,
        'attack_cooldown_melee': 0,
        'attack_cooldown_ranged': 700,
        'ranged_fire_frame': 6,
        'arrow_regen_time': 10000,  # 10 secondes pour regagner 10 flèches
        'arrow_regen_amount': 10,
        'abilities': {
            'skill1': {
                'cooldown': 6000,     # 6 secondes
                'damage': 31.5,       # 3x dégâts d'une flèche normale
                'anim': 'skill1',
                'projectile_img': 'assets/images/Arrow02(32x32).png',
                'fire_frame': 8,
                'type': 'projectile',
                'piercing': True,     # traverse les ennemis
            },
        },
        'icons': {
            'slot1': 'assets/images/arc_icon.png',
            'slot2': 'assets/images/golden_arrow_icon.png',
        },
        'projectile_img': 'assets/images/Arrow01(32x32).png',
    },

    'wizard': {
        'name': 'Wizard',
        'scale_factor': 1.5,
        'empty_space_below': 43,
        'animations': {
            'idle':          ('assets/images/Wizard-Idle.png', 6),
            'walk':          ('assets/images/Wizard-Walk.png', 8),
            'death':         ('assets/images/Wizard-DEATH.png', 4),
            'skill1':        ('assets/images/Wizard-Attack02.png', 6),
            'skill2':        ('assets/images/Wizard-Attack01.png', 6),
        },
        'has_melee': False,
        'has_ranged': False,
        'current_weapon': 'skill1',
        'arrows': 0,
        'melee_damage': 0,
        'ranged_damage': 0,
        'attack_cooldown_melee': 0,
        'attack_cooldown_ranged': 0,
        'ranged_fire_frame': -1,
        'abilities': {
            'skill1': {
                'cooldown': 1500,     # 1.5 secondes
                'damage': 12,
                'anim': 'skill1',
                'projectile_img': 'assets/images/Wizard-Attack02_Effect.png',
                'fire_frame': 3,
                'type': 'projectile',
                'effect_frames': 7,
            },
            'skill2': {
                'cooldown': 5000,     # 5 secondes
                'damage': 25,
                'anim': 'skill2',
                'effect_img': 'assets/images/Wizard-Attack01_Effect.png',
                'fire_frame': 3,
                'type': 'homing',
                'effect_frames': 10,
                'explosion_radius': 60,
                'detect_range': 200,
                'render_scale': 0.6,  # effet visuel réduit pour le wizard
                'paralyze': 3000,  # paralysie 3s (1.5s sur les boss)
            },
        },
        'icons': {
            'slot1': 'assets/images/fireball_icon.png',
            'slot2': 'assets/images/cristal_icon.png',
        },
        'projectile_img': None,
    },

    'priest': {
        'name': 'Priest',
        'scale_factor': 1.5,
        'empty_space_below': 43,
        'animations': {
            'idle':          ('assets/images/Priest-Idle.png', 6),
            'walk':          ('assets/images/Priest-Walk.png', 8),
            'death':         ('assets/images/Priest-Death.png', 4),
            'skill1':        ('assets/images/Priest-Attack.png', 9),
            'skill2':        ('assets/images/Priest-Heal.png', 6),
        },
        'has_melee': False,
        'has_ranged': False,
        'current_weapon': 'skill1',
        'arrows': 0,
        'melee_damage': 0,
        'ranged_damage': 0,
        'attack_cooldown_melee': 0,
        'attack_cooldown_ranged': 0,
        'ranged_fire_frame': -1,
        'abilities': {
            'skill1': {
                'cooldown': 1500,     # 1.5 secondes
                'damage': 20,
                'anim': 'skill1',
                'effect_img': 'assets/images/Priest-Attack_effect.png',
                'fire_frame': 5,
                'type': 'homing',
                'effect_frames': 5,
                'explosion_radius': 60,
                'detect_range': 200,
            },
            'skill2': {
                'cooldown': 16000,    # 16 secondes
                'heal_amount': 0.30,  # 30% PV max du joueur ciblé
                'anim': 'skill2',
                'effect_img': 'assets/images/Priest-Heal_Effect.png',
                'fire_frame': 3,
                'type': 'heal',
                'heal_range': 120,    # distance max pour soigner
                'effect_frames': 4,
            },
        },
        'icons': {
            'slot1': 'assets/images/explosion_icon.png',
            'slot2': 'assets/images/heal_icon.png',
        },
        'projectile_img': None,
    },
}


def get_character_def(char_type):
    """Retourne la définition d'un personnage par son type."""
    return CHARACTER_DEFS.get(char_type, CHARACTER_DEFS['soldier'])


def get_all_character_types():
    """Retourne la liste de tous les types de personnages disponibles."""
    return list(CHARACTER_DEFS.keys())
