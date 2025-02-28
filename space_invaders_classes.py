import pygame
import random
import math
import os
import json
import sys

# Initialize pygame if not already initialized
if not pygame.get_init():
    pygame.init()
    
# Initialize mixer if not already initialized
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)

# Screen dimensions
BREDDE = 800
HOYDE = 600

# Colors
SVART = (0, 0, 0)
HVIT = (255, 255, 255)
ROD = (255, 23, 68)
GRONN = (0, 255, 255)
BLA = (0, 123, 255)
GUL = (255, 165, 0)

# Game states
class Spilltilstand:
    MENY = 0
    SPILLER = 1
    GAME_OVER = 2
    LEVEL_COMPLETE = 3
    LEVEL_SELECT = 4
    QUIT_CONFIRM = 5  # State for quit confirmation

# Configuration file paths
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'game_config.json')
HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), 'high_scores.json')

# Default configuration
default_config = {
    "unlock_impossible": False,
    "unlocked_skins": ["default"],
    "active_skin": "default",
    "max_level_reached": 1,
    "shotgun_unlocked": False,
    "sound_volume": 0.5,
    "music_volume": 0.07,
    "fullscreen_enabled": False,
    "mouse_control": False  # New default setting for mouse control
}

# Default high scores
default_high_scores = {
    "easy": 0,
    "medium": 0,
    "hard": 0,
    "impossible": 0,
    "level_mode": {}  # For level-specific high scores
}

# Load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_config.copy()
    else:
        # Create default configuration if file doesn't exist
        save_config(default_config)
        return default_config.copy()

# Load high scores
def load_high_scores():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_high_scores.copy()
    else:
        # Create default high scores if file doesn't exist
        save_high_scores(default_high_scores)
        return default_high_scores.copy()

# Save configuration
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Save high scores
def save_high_scores(scores):
    with open(HIGH_SCORE_FILE, 'w') as f:
        json.dump(scores, f, indent=4)

# Functions to generate sounds if files don't exist
def lag_eksplosjon_lyd():
    buffer = bytearray()
    # Low frequency sound with noise
    for i in range(12000):
        amplitude = max(0, 1 - i/10000)
        verdi = int(127 + amplitude * 127 * random.uniform(-1, 1))
        buffer.append(verdi)
    return pygame.mixer.Sound(buffer)

def lag_bonus_lyd():
    buffer = bytearray()
    # Ascending tone
    for i in range(8000):
        frekvens = 300 + i/20
        verdi = int(127 + 127 * 0.8 * math.sin(frekvens * i/1000))
        buffer.append(verdi)
    return pygame.mixer.Sound(buffer)

def lag_skyte_lyd():
    buffer = bytearray()
    # Sound that sounds like "thock"
    for i in range(4000):
        verdi = int(127 + 127 * max(0, 1 - i/1000) * (0.8 if i % 8 < 4 else -0.8))
        buffer.append(verdi)
    return pygame.mixer.Sound(buffer)

# Star class for background effect
class Star(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Different sizes for stars to simulate depth
        size = random.randint(1, 3)
        self.image = pygame.Surface((size, size))
        self.image.fill(HVIT)
        self.rect = self.image.get_rect()
        
        # Random position
        self.rect.x = random.randrange(BREDDE)
        self.rect.y = random.randrange(HOYDE)
        
        # Different speeds for parallax effect
        self.speed = random.uniform(1, 5)
        
    def update(self):
        # Move stars down to create illusion of forward movement
        self.rect.y += self.speed
        
        # Reset position if star goes off screen
        if self.rect.top > HOYDE:
            self.rect.y = -self.rect.height
            self.rect.x = random.randrange(BREDDE)

# Player class
class Spiller(pygame.sprite.Sprite):
    def __init__(self, spiller_bilde):
        super().__init__()
        self.base_bilde = spiller_bilde
        self.image = pygame.transform.scale(self.base_bilde, (50, 40))
        self.rect = self.image.get_rect()
        self.rect.centerx = BREDDE // 2
        self.rect.bottom = HOYDE - 10
        self.hastighet = 8
        self.liv = 3
        # Add variables for shot cooldown
        self.siste_skudd = 0
        self.skudd_cooldown = 150  # 150 milliseconds between shots
        # Skin variables
        self.score_for_check = 0
        # Weapon variables
        self.current_weapon = 'normal'  # 'normal', 'shotgun' or 'electric whip'
        # New electric whip attributes with reduced threshold for faster charging:
        self.whip_charge = 0
        self.whip_charge_threshold = 1000  # Reduced from 2000 to 1000 for twice as fast charging
        # Add mouse control variable
        self.target_x = self.rect.centerx  # Target position for smooth mouse movement
        self.mouse_speed_factor = 0.5  # More moderate speed factor for smoother tracking
        
    def update(self, poeng, spiller_bilder, mouse_control=False):
        # Handle keyboard controls when mouse control is disabled
        if not mouse_control:
            taster = pygame.key.get_pressed()
            # Move left with either left arrow or A
            if taster[pygame.K_LEFT] or taster[pygame.K_a]:
                self.rect.x -= self.hastighet
                # Pac-Man-like wrap-around when player goes off left edge
                if self.rect.right < 0:
                    self.rect.left = BREDDE
            # Move right with either right arrow or D
            if taster[pygame.K_RIGHT] or taster[pygame.K_d]:
                self.rect.x += self.hastighet
                # Pac-Man-like wrap-around when player goes off right edge
                if self.rect.left > BREDDE:
                    self.rect.right = 0
        else:
            # Mouse control - more direct but still smooth tracking with bounded movement
            mouse_x, _ = pygame.mouse.get_pos()
            
            # Set target position to mouse x-coordinate
            # Ensure the target is within valid bounds for the rocket (half width from each edge)
            half_width = self.rect.width // 2
            self.target_x = max(half_width, min(mouse_x, BREDDE - half_width))
            
            # Calculate distance to move (the error between current and target position)
            dx = self.target_x - self.rect.centerx
            
            # Move toward target position with fixed speed if far enough
            if abs(dx) > 2:  # Only move if we're at least 2 pixels away from target
                # Cap max movement speed to hastighet * 2 for more control
                max_move = self.hastighet * 2
                
                # Move faster when far from target, slower when closer
                # This gives a "weighted average" kind of movement that's quick but still smooth
                move_amount = min(max_move, abs(dx) * self.mouse_speed_factor)
                
                # Ensure we move at least 1 pixel if we're moving at all
                if move_amount < 1:
                    move_amount = 1
                    
                # Apply direction
                if dx > 0:
                    self.rect.x += move_amount
                else:
                    self.rect.x -= move_amount
            
            # Ensure rocket stays on screen by clamping position
            # This is a safeguard in case other logic fails
            if self.rect.left < 0:
                self.rect.left = 0
            elif self.rect.right > BREDDE:
                self.rect.right = BREDDE
        
        # Check if we should upgrade skin based on score
        if poeng != self.score_for_check:
            self.score_for_check = poeng
            self.update_skin(poeng, spiller_bilder)
    
    def update_skin(self, poeng, spiller_bilder):
        # Change skin based on points - now every 500 points
        spiller_bilde, spiller2_bilde, spiller3_bilde, spiller4_bilde = spiller_bilder
        
        if poeng >= 1500:
            self.base_bilde = spiller4_bilde
        elif poeng >= 1000:
            self.base_bilde = spiller3_bilde
        elif poeng >= 500:
            self.base_bilde = spiller2_bilde
        else:
            self.base_bilde = spiller_bilde
        
        # Update the image but keep the size
        self.image = pygame.transform.scale(self.base_bilde, (50, 40))
        
        return False

    def skyt(self, alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe=None, weapon_override=None):
        naa = pygame.time.get_ticks()
        
        # Use specified weapon if override is provided
        current_weapon = weapon_override if weapon_override is not None else self.current_weapon
        
        # Electric whip branch
        if current_weapon == 'electric whip':
            if self.whip_charge >= self.whip_charge_threshold and fiende_gruppe:
                # Create whip animation
                whip = ElectricWhip(self.rect.midtop, BREDDE, HOYDE)
                alle_sprites.add(whip)
                
                # Play whip sound
                skyte_lyd.play(maxtime=0, fade_ms=0)
                
                # Reset charge
                self.whip_charge = 0
            # Do not create shot objects for electric whip
            return
            
        if naa - self.siste_skudd > self.skudd_cooldown:
            self.siste_skudd = naa
            if current_weapon == 'shotgun':
                # Fire 7 pellets with wider angles
                for angle in [-45, -30, -15, 0, 15, 30, 45]:
                    skudd = ShotgunShot(self.rect.centerx, self.rect.top, angle)
                    skudd.hastighet = -20 if VANSKELIGHETSGRAD == 1 else -8
                    alle_sprites.add(skudd)
                    skudd_gruppe.add(skudd)
                    if angle == 0:
                        aktive_skudd.append(skudd)
            else:
                # Normal single shot
                skudd = Skudd(self.rect.centerx, self.rect.top)
                skudd.hastighet = -30 if VANSKELIGHETSGRAD == 1 else -10
                alle_sprites.add(skudd)
                skudd_gruppe.add(skudd)
                aktive_skudd.append(skudd)
            skyte_lyd.play(maxtime=0, fade_ms=0)

    def switch_weapon(self, weapon_name, max_level_reached):
        """Switch to the specified weapon if it's available based on max level reached"""
        if weapon_name == 'normal':
            self.current_weapon = weapon_name
            return True
        elif weapon_name == 'shotgun' and max_level_reached > 5:
            self.current_weapon = weapon_name
            return True
        elif weapon_name == 'electric whip' and max_level_reached >= 10:
            self.current_weapon = weapon_name
            return True
        return False

# Shot class
class Skudd(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 15))
        self.image.fill(GRONN)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.hastighet = -10
        self.truffet_fiende = False  # For multiplier tracking

    def update(self, reset_multiplier_func=None):
        self.rect.y += self.hastighet
        # Remove shot if it goes off screen
        if self.rect.bottom < 0:
            # Only reset multiplier for non-shotgun shots
            if not self.truffet_fiende and reset_multiplier_func and not isinstance(self, ShotgunShot):
                reset_multiplier_func()
            self.kill()

# ExplosiveShot class that inherits from Skudd
class ExplosiveShot(Skudd):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.image.fill(ROD)  # Red color instead of green
        self.image = pygame.Surface((7, 18))  # Slightly larger
        self.image.fill((255, 100, 100))  # Reddish color
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.explosion_radius = 80  # Radius of explosion effect
    
    def explode(self, alle_sprites, fiende_gruppe, poeng, score_multiplier, eksplosjon_lyd):
        # Create explosion effect at current position
        explosion = ExplosiveEffect(self.rect.center, self.explosion_radius)
        alle_sprites.add(explosion)
        
        # Play explosion sound
        eksplosjon_lyd.play(maxtime=0, fade_ms=0)
        
        # Track how many points were earned for return value
        total_points_earned = 0
        
        # Damage all enemies within explosion radius
        for fiende in fiende_gruppe:
            # Calculate distance between explosion center and enemy center
            distance = math.sqrt(
                (fiende.rect.centerx - self.rect.centerx) ** 2 +
                (fiende.rect.centery - self.rect.centery) ** 2
            )
            
            # If enemy is within radius, damage it
            if distance <= self.explosion_radius:
                # Kill regular enemies immediately, damage strong enemies
                if isinstance(fiende, SterkFiende):
                    fiende.treff += 1
                    if fiende.treff >= fiende.max_treff:
                        # Calculate points based on multiplier
                        point_gain = int(fiende.point_value * score_multiplier)
                        total_points_earned += point_gain
                        fiende.kill()
                        
                        # Return enemy type for respawning in main script
                        return total_points_earned, "SterkFiende"
                else:
                    # Regular enemy - kill immediately
                    point_gain = int(fiende.point_value * score_multiplier)
                    total_points_earned += point_gain
                    fiende.kill()
                    
                    # Return enemy type for respawning in main script
                    return total_points_earned, "Fiende"
        
        return total_points_earned, None
    
    def update(self, reset_multiplier_func=None):
        self.rect.y += self.hastighet
        # When reaching top of screen or if killed by collision, explode
        if self.rect.bottom < 0:
            # Signal to main script that explosion should occur
            self.truffet_fiende = True  # Prevent multiplier reset
            self.kill()
            return True  # Signal to explode
        return False

# ShotgunShot class that inherits from Skudd
class ShotgunShot(Skudd):
    def __init__(self, x, y, angle=0):
        super().__init__(x, y)
        self.image.fill((255, 100, 0))  # Orange color for shotgun pellets
        self.image = pygame.Surface((4, 10))  # Smaller than normal shot
        self.image.fill((255, 165, 0))  # Orange color
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.angle = math.radians(angle)  # Convert angle to radians
        self.range = 200   # Extended range from 150 to 200
        self.distance_traveled = 0
        self.horizontal_speed = math.sin(self.angle) * 5  # Increased multiplier for more spread
        
    def update(self, reset_multiplier_func=None):
        # Update position with both vertical and horizontal components
        self.rect.y += self.hastighet
        self.rect.x += self.horizontal_speed
        
        # Track distance traveled
        self.distance_traveled += abs(self.hastighet)
        
        # Remove shot if it goes off screen or exceeds range
        if self.rect.bottom < 0 or self.rect.left > BREDDE or self.rect.right < 0 or self.distance_traveled > self.range:
            # If shot goes off screen without hitting, reset multiplier
            if not self.truffet_fiende and reset_multiplier_func:
                reset_multiplier_func()
            self.kill()

# Explosive effect animation
class ExplosiveEffect(pygame.sprite.Sprite):
    def __init__(self, center, radius):
        super().__init__()
        self.radius = radius
        self.center = center
        self.image = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.frame = 0
        self.max_frames = 10
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 40  # Milliseconds between frames
        self.draw_frame()
        
    def draw_frame(self):
        # Clear the image
        self.image.fill((0, 0, 0, 0))
        
        # Calculate the current explosion size
        progress = self.frame / self.max_frames
        current_radius = int(self.radius * (1 - progress/2))  # Shrink slightly over time
        
        # Draw an expanding/contracting circular explosion
        if self.frame < self.max_frames // 2:
            # Expanding phase - red to orange
            color_r = min(255, 180 + self.frame * 15)
            color_g = min(255, self.frame * 25)
            color_b = 0
            alpha = 200
        else:
            # Contracting phase - orange to yellow to transparent
            color_r = min(255, 255)
            color_g = min(255, 100 + self.frame * 15)
            color_b = min(255, (self.frame - self.max_frames//2) * 40)
            alpha = max(0, 200 - (self.frame - self.max_frames//2) * 40)
        
        # Draw with glow effect (multiple circles with decreasing opacity)
        for i in range(3):
            r_offset = current_radius - i * 10
            if r_offset > 0:
                pygame.draw.circle(
                    self.image, 
                    (color_r, color_g, color_b, alpha//(i+1)), 
                    (self.radius, self.radius), 
                    r_offset
                )
    
    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.frame += 1
            if self.frame >= self.max_frames:
                self.kill()
            else:
                self.draw_frame()

# Notification class for weapon upgrade
class WeaponUpgradeNotification(pygame.sprite.Sprite):
    def __init__(self, game_font_medium, game_font_small):
        super().__init__()
        self.image = pygame.Surface((500, 60), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(BREDDE//2, HOYDE//2 - 50))
        self.timer = 180  # Show for 3 seconds (60 fps * 3)
        self.draw_notification(game_font_medium, game_font_small)
    
    def draw_notification(self, game_font_medium, game_font_small):
        # Background with transparency
        pygame.draw.rect(self.image, (0, 0, 0, 180), (0, 0, 500, 60))
        pygame.draw.rect(self.image, (255, 0, 0), (0, 0, 500, 60), 2)
        
        # Get text with game_font_medium
        title_text = game_font_medium.render("VÅPEN OPPGRADERT!", True, (255, 50, 50))
        desc_text = game_font_small.render("Du har låst opp eksplosivt laser (1200+ poeng)", True, HVIT)
        
        # Center the text
        self.image.blit(title_text, (250 - title_text.get_width()//2, 5))
        self.image.blit(desc_text, (250 - desc_text.get_width()//2, 35))
    
    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()

# Notification class for weapon unlock
class WeaponUnlockNotification(pygame.sprite.Sprite):
    def __init__(self, game_font_medium, game_font_small):
        super().__init__()
        self.image = pygame.Surface((500, 80), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(BREDDE//2, HOYDE//2 - 50))
        self.timer = 180  # Show for 3 seconds (60 fps * 3)
        self.draw_notification(game_font_medium, game_font_small)
    
    def draw_notification(self, game_font_medium, game_font_small):
        # Background with transparency
        pygame.draw.rect(self.image, (0, 0, 0, 180), (0, 0, 500, 80))
        pygame.draw.rect(self.image, (255, 165, 0), (0, 0, 500, 80), 2)  # Orange border
        
        # Get text with game_font_medium
        title_text = game_font_medium.render("NYTT VÅPEN LÅST OPP!", True, (255, 165, 0))  # Orange text
        desc_text = game_font_small.render("Du har låst opp hagle (trykk 2 for å bruke)", True, HVIT)
        tip_text = game_font_small.render("Bred spredning, kort rekkevidde", True, HVIT)
        
        # Center the text
        self.image.blit(title_text, (250 - title_text.get_width()//2, 5))
        self.image.blit(desc_text, (250 - desc_text.get_width()//2, 35))
        self.image.blit(tip_text, (250 - tip_text.get_width()//2, 55))
    
    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()

# Enemy projectile for Impossible mode
class FiendeProsjektil(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((6, 15))
        self.image.fill(GUL)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.top = y
        self.hastighet = 7  # Slightly slower than player shots

    def update(self):
        self.rect.y += self.hastighet
        # Remove projectile if it goes off screen
        if self.rect.top > HOYDE:
            self.kill()

# Enemy class
class Fiende(pygame.sprite.Sprite):
    def __init__(self, fiende_bilde, VANSKELIGHETSGRAD):
        super().__init__()
        # Random size between 70% and 120% of original size
        self.scale_factor = random.uniform(0.7, 1.2)
        size = int(40 * self.scale_factor)
        
        # Original image for rotation
        self.original_image = pygame.transform.scale(fiende_bilde, (size, size))
        
        # Random rotation
        self.angle = 0
        self.rotation_speed = random.uniform(-2, 2)  # Degrees per frame
        self.image = self.original_image.copy()
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        
        # Adjust speed based on difficulty
        if VANSKELIGHETSGRAD == 1:
            self.hastighet = random.randrange(1, 2)
        elif VANSKELIGHETSGRAD == 2:
            self.hastighet = random.randrange(1, 3)
        else:  # Level 3 or higher
            self.hastighet = random.randrange(1, 4)
            
        self.treff = 0  # Always 0 for regular enemies
        self.max_treff = 1  # Regular enemies need 1 hit
        
        # In Impossible mode, enemies can shoot back with low probability
        self.last_shot = pygame.time.get_ticks()
        self.shot_delay = random.randint(3000, 8000)  # 3-8 seconds between shots
        
        # Point value
        self.point_value = 10

    def update(self, VANSKELIGHETSGRAD=None, alle_sprites=None, fiende_prosjektil_gruppe=None):
        # Move the enemy
        self.rect.y += self.hastighet
        
        # Update rotation
        self.angle += self.rotation_speed
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        
        # In Impossible mode, let enemies shoot
        if VANSKELIGHETSGRAD == 4:
            now = pygame.time.get_ticks()
            if now - self.last_shot > self.shot_delay and random.random() < 0.01:  # 1% chance per frame
                self.last_shot = now
                self.shoot(alle_sprites, fiende_prosjektil_gruppe)
    
    def shoot(self, alle_sprites, fiende_prosjektil_gruppe):
        if self.rect.bottom > 0:  # Only shoot if the enemy is visible
            prosjektil = FiendeProsjektil(self.rect.centerx, self.rect.bottom)
            alle_sprites.add(prosjektil)
            fiende_prosjektil_gruppe.add(prosjektil)

# Class for stronger enemies (level 3)
class SterkFiende(Fiende):
    def __init__(self, sterk_fiende_bilde, VANSKELIGHETSGRAD):
        super().__init__(sterk_fiende_bilde, VANSKELIGHETSGRAD)
        # Random size between 80% and 130% of original size
        self.scale_factor = random.uniform(0.8, 1.3)
        size = int(50 * self.scale_factor)
        
        # Original image for rotation
        self.original_image = pygame.transform.scale(sterk_fiende_bilde, (size, size))
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        
        # Make strong enemies faster in Hard mode
        if VANSKELIGHETSGRAD == 3:
            self.hastighet = random.randrange(2, 4)  # Faster in Hard mode
        elif VANSKELIGHETSGRAD == 4:
            self.hastighet = random.randrange(2, 5)  # Even faster in Impossible mode
        else:
            self.hastighet = random.randrange(1, 3)
            
        self.treff = 0  # Number of hits needed to destroy (2 for stronger enemies)
        self.max_treff = 2
        self.point_value = 25  # 25 points for strong enemies
        self.rotation_speed = 0  # Make strong enemies static in rotation

    def update(self, VANSKELIGHETSGRAD=None, alle_sprites=None, fiende_prosjektil_gruppe=None):
        self.rect.y += self.hastighet
        # Skip rotating: self.angle remains unchanged
        # ...existing shooting code...
        if VANSKELIGHETSGRAD == 4:
            now = pygame.time.get_ticks()
            # Increase shoot frequency: lower delay uniformly and raise probability to 10% # Increased chance per frame
            if now - self.last_shot > self.shot_delay and random.random() < 0.1:
                self.last_shot = now
                self.shoot(alle_sprites, fiende_prosjektil_gruppe)

# Explosion class
class Eksplosjon(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        pygame.draw.circle(self.image, (255, 165, 0), (25, 25), 25)  # Orange circle
        self.image.set_colorkey(SVART)
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.frame = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 50

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.frame += 1
            if self.frame == 6:
                self.kill()
            else:
                center = self.rect.center
                self.image = pygame.Surface((50 - self.frame * 8, 50 - self.frame * 8))
                pygame.draw.circle(self.image, (255, 165, 0), 
                                  (int((50 - self.frame * 8)/2), int((50 - self.frame * 8)/2)), 
                                  int((50 - self.frame * 8)/2))
                self.image.set_colorkey(SVART)
                self.rect = self.image.get_rect()
                self.rect.center = center

# Particle class for visual effects
class Partikkel(pygame.sprite.Sprite):
    def __init__(self, pos, vinkel, hastighet):
        super().__init__()
        self.image = pygame.Surface((4, 4))
        self.image.fill(BLA)
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.x = pos[0]
        self.y = pos[1]
        self.hastighet_x = math.cos(vinkel) * hastighet
        self.hastighet_y = math.sin(vinkel) * hastighet
        self.levetid = 30
        
    def update(self):
        self.x += self.hastighet_x
        self.y += self.hastighet_y
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)
        self.levetid -= 1
        if self.levetid <= 0:
            self.kill()

# Power bonus class
class Kraftbonus(pygame.sprite.Sprite):
    def __init__(self, liv_bilde=None):
        super().__init__()
        if liv_bilde:
            # Use the provided life image and scale it appropriately
            size = 30
            self.image = pygame.transform.scale(liv_bilde, (size, size))
        else:
            # Fallback to the blue circle if no image is provided
            self.image = pygame.Surface((30, 30))
            pygame.draw.circle(self.image, BLA, (15, 15), 15)
            self.image.set_colorkey(SVART)
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        self.hastighet = 3

    def update(self):
        self.rect.y += self.hastighet
        # If bonus reaches bottom, remove it
        if self.rect.top > HOYDE:
            self.kill()

# Multiplier functions
def reset_multiplier():
    # Return base values instead of modifying globals
    return 1.0, 0

def increase_multiplier(score_multiplier, consecutive_hits):
    consecutive_hits += 1
    # Increase multiplier by 0.1 for each hit, max 5.0
    new_multiplier = min(5.0, 1.0 + (consecutive_hits * 0.1))
    return new_multiplier, consecutive_hits

# Create stars for background
def create_stars(star_gruppe, count=100):
    for i in range(count):
        star = Star()
        star_gruppe.add(star)

# Set requirements for each level
def set_level_requirements(level):
    """Set enemies and goals for selected level (easier settings)"""
    if level == 1:
        return {"target_score": 100, "fiende_count": 3, "sterk_fiende_count": 0}
    elif level == 2:
        return {"target_score": 150, "fiende_count": 4, "sterk_fiende_count": 0}
    elif level == 3:
        return {"target_score": 200, "fiende_count": 4, "sterk_fiende_count": 1}
    elif level == 4:
        return {"target_score": 250, "fiende_count": 5, "sterk_fiende_count": 1}
    elif level == 5:
        return {"target_score": 300, "fiende_count": 5, "sterk_fiende_count": 1}
    elif level <= 10:
        base_score = 300
        return {
            "target_score": base_score + (level - 5) * 30,
            "fiende_count": 5 + (level - 5) // 2,
            "sterk_fiende_count": 1
        }
    elif level <= 20:
        base_score = 450
        return {
            "target_score": base_score + (level - 10) * 30,
            "fiende_count": 6,
            "sterk_fiende_count": 1
        }
    else:
        base_score = 750
        return {
            "target_score": base_score + (level - 20) * 30,
            "fiende_count": min(8, 6 + (level - 20) // 10),
            "sterk_fiende_count": 1
        }

# UI helper functions
def draw_level_progress(skjerm, poeng, LEVEL, game_font_small):
    level_reqs = set_level_requirements(LEVEL)
    progress_text = game_font_small.render(f"Progress: {poeng}/{level_reqs['target_score']}", True, HVIT)
    skjerm.blit(progress_text, (BREDDE//2 - progress_text.get_width()//2, 10))

def draw_multiplier(skjerm, score_multiplier, game_font_small):
    multiplier_text = game_font_small.render(f"Multiplier: x{score_multiplier:.1f}", True, (255, 165, 0))
    skjerm.blit(multiplier_text, (BREDDE//2 - multiplier_text.get_width()//2, 40))

def draw_enemy_points(skjerm, fiende_bilde, sterk_fiende_bilde, score_multiplier, game_font_small, VANSKELIGHETSGRAD, LEVEL_MODE=False, LEVEL=1):
    try:
        # Create small icons and show current point values
        normal_icon_size = 25
        # Use safe scaling with error handling
        try:
            normal_icon = pygame.transform.scale(fiende_bilde, (normal_icon_size, normal_icon_size))
            skjerm.blit(normal_icon, (10, 100))
        except:
            # If image scaling fails, use a simple rectangle instead
            normal_icon = pygame.Surface((normal_icon_size, normal_icon_size))
            normal_icon.fill(GRONN)
            skjerm.blit(normal_icon, (10, 100))
            
        normal_points = int(10 * score_multiplier)
        normal_text = game_font_small.render(f"{normal_points} poeng", True, HVIT)
        skjerm.blit(normal_text, (40, 110))
        
        # Only show strong enemy points for Hard/Impossible mode or in Level Mode with sufficient level
        if VANSKELIGHETSGRAD >= 3 or (LEVEL_MODE and LEVEL >= 3):
            strong_icon_size = 30
            try:
                strong_icon = pygame.transform.scale(sterk_fiende_bilde, (strong_icon_size, strong_icon_size))
                skjerm.blit(strong_icon, (10, 130))
            except:
                strong_icon = pygame.Surface((strong_icon_size, strong_icon_size))
                strong_icon.fill(ROD)
                skjerm.blit(strong_icon, (10, 130))
                
            strong_points = int(25 * score_multiplier)
            strong_text = game_font_small.render(f"{strong_points} poeng", True, HVIT)
            skjerm.blit(strong_text, (45, 140))
    except Exception as e:
        print(f"Error in draw_enemy_points: {e}")

# Check and save highscores
def check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE):
    updated = False
    
    # Map difficulty level to keys in config
    diff_map = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}
    
    if LEVEL_MODE:
        # For level mode, save high score for each level
        level_key = f"level_{LEVEL}"
        if level_key not in high_scores["level_mode"] or poeng > high_scores["level_mode"][level_key]:
            high_scores["level_mode"][level_key] = poeng
            updated = True
    else:
        # For normal mode
        current_diff = diff_map.get(VANSKELIGHETSGRAD)
        
        if current_diff and poeng > high_scores.get(current_diff, 0):
            high_scores[current_diff] = poeng
            updated = True
            
            # Check for unlock of impossible mode
            if current_diff == "hard" and poeng >= 1000:
                game_config = load_config()
                game_config["unlock_impossible"] = True
                save_config(game_config)
    
    # Save updated high scores
    if updated:
        save_high_scores(high_scores)
        return True
    
    return False

# Get current high score
def get_current_high_score(VANSKELIGHETSGRAD, LEVEL, LEVEL_MODE, high_scores):
    if LEVEL_MODE:
        level_key = f"level_{LEVEL}"
        return high_scores["level_mode"].get(level_key, 0)
    else:
        diff_map = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}
        current_diff = diff_map.get(VANSKELIGHETSGRAD)
        return high_scores.get(current_diff, 0)

# Check for level completion in level-mode
def check_level_complete(LEVEL, poeng, LEVEL_MODE, VANSKELIGHETSGRAD, high_scores):
    if LEVEL_MODE:
        level_reqs = set_level_requirements(LEVEL)
        if poeng >= level_reqs["target_score"]:
            # Check for high score before level change
            check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE)
            
            # Level completed
            new_level = LEVEL + 1
            
            # Update max reached level
            game_config = load_config()
            if new_level > game_config["max_level_reached"]:
                game_config["max_level_reached"] = new_level
                save_config(game_config)
                
                # Check for new skins based on level
                if new_level == 5 and "level5_skin" not in game_config["unlocked_skins"]:
                    game_config["unlocked_skins"].append("level5_skin")
                    save_config(game_config)
                
                # Check for shotgun unlock at level 5
                if new_level > 5 and not game_config.get("shotgun_unlocked", False):
                    game_config["shotgun_unlocked"] = True
                    save_config(game_config)
                    return True, new_level, True  # Return that shotgun was unlocked
            
            return True, new_level, False
    
    return False, LEVEL, False

# Function to create enemies based on difficulty
def opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe):
    # Clear any existing enemies
    for sprite in fiende_gruppe:
        sprite.kill()
    
    # Create new enemies
    if LEVEL_MODE:
        level_reqs = set_level_requirements(LEVEL)
        antall_fiender = level_reqs["fiende_count"]
        antall_sterke = level_reqs["sterk_fiende_count"]
    else:
        if VANSKELIGHETSGRAD == 1:
            antall_fiender = 3
            antall_sterke = 0  # Easy: No strong enemies
        elif VANSKELIGHETSGRAD == 2:
            antall_fiender = 4
            antall_sterke = 1  # Medium: Some strong enemies
        elif VANSKELIGHETSGRAD == 3:
            antall_fiender = 4
            antall_sterke = 3  # Hard: More strong enemies and they're faster
        else:  # VANSKELIGHETSGRAD == 4 (Impossible)
            antall_fiender = 5
            antall_sterke = 5  # Impossible: Many strong enemies and they shoot
            
    for i in range(antall_fiender):
        enemy = Fiende(fiende_bilde, VANSKELIGHETSGRAD)
        alle_sprites.add(enemy)
        fiende_gruppe.add(enemy)
    for i in range(antall_sterke):
        strong_enemy = SterkFiende(sterk_fiende_bilde, VANSKELIGHETSGRAD)
        alle_sprites.add(strong_enemy)
        fiende_gruppe.add(strong_enemy)
    return antall_fiender + antall_sterke

# Electric Whip animation class
class ElectricWhip(pygame.sprite.Sprite):
    def __init__(self, player_pos, screen_width, screen_height):
        super().__init__()
        self.center_pos = player_pos
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.length = screen_width * 1.5  # Make it long enough to reach all corners
        self.angle = 0  # Start at 0 degrees (pointing left) instead of 90
        self.angular_speed = 6  # Degrees per frame - reduced from 15 to 6 for smoother sweep
        self.done = False
        self.enemies_hit = set()  # Track enemies already hit
        
        # Create the initial image (a horizontal line pointing left)
        self.image = pygame.Surface((self.length, self.length), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.center = player_pos
        self.update_image()
    
    def update_image(self):
        # Clear the image
        self.image.fill((0, 0, 0, 0))
        
        # Calculate end point of line based on current angle
        angle_rad = math.radians(self.angle)
        end_x = self.length // 2
        end_y = self.length // 2
        
        # Calculate start point (center of image)
        start_x = self.length // 2
        start_y = self.length // 2
        
        # Calculate endpoint based on angle
        dx = math.cos(angle_rad) * self.length // 2
        dy = -math.sin(angle_rad) * self.length // 2  # Negative because pygame's y-axis is flipped
        
        # Draw the main laser line - make it thicker
        pygame.draw.line(self.image, (0, 200, 255, 255), (start_x, start_y), 
                        (start_x + dx, start_y + dy), 5)  # Increased thickness from 3 to 5
        
        # Add some glow effect with additional lines - make them thicker
        pygame.draw.line(self.image, (100, 220, 255, 180), (start_x, start_y), 
                        (start_x + dx, start_y + dy), 8)  # Increased thickness and opacity
        pygame.draw.line(self.image, (180, 230, 255, 100), (start_x, start_y), 
                        (start_x + dx, start_y + dy), 12)  # Increased thickness and opacity
        
        # Add more electricity particles along the line
        for i in range(20):  # Increased from 10 to 20 particles
            dist = random.random()
            particle_x = start_x + dx * dist
            particle_y = start_y + dy * dist
            
            # Random offset perpendicular to line
            perp_angle = angle_rad + math.pi/2
            offset = random.uniform(-10, 10)  # Increased offset range from -8,8 to -10,10
            particle_x += math.cos(perp_angle) * offset
            particle_y -= math.sin(perp_angle) * offset
            
            size = random.randint(2, 6)  # Increased max size from 4 to 6
            alpha = random.randint(150, 255)  # Increased opacity range
            pygame.draw.circle(self.image, (150, 220, 255, alpha), 
                              (int(particle_x), int(particle_y)), size)
    
    def update(self, fiende_gruppe=None, alle_sprites=None, eksplosjon_lyd=None, score_multiplier=1.0):
        # Update angle by moving from 0 to 180 degrees (left to right sweep)
        self.angle += self.angular_speed
        
        if self.angle >= 180:  # End when pointing right instead of -90
            self.kill()
            self.done = True
            return
            
        # Update image with new angle
        self.update_image()
        
        # Check for collisions with enemies
        if fiende_gruppe and alle_sprites:
            for fiende in list(fiende_gruppe):
                # Skip if already hit
                if fiende in self.enemies_hit:
                    continue
                    
                # Check if the enemy is hit by the whip
                fiende_center = fiende.rect.center
                whip_center = self.rect.center
                
                # Create a vector from whip origin to enemy center
                dx = fiende_center[0] - whip_center[0]
                dy = fiende_center[1] - whip_center[1]
                
                # Convert to polar coordinates
                distance = math.sqrt(dx*dx + dy*dy)
                angle_to_enemy = math.degrees(math.atan2(-dy, dx))  # Negative dy because y increases downward
                
                # Normalize angle_to_enemy to be in the range [0, 360)
                while angle_to_enemy < 0:
                    angle_to_enemy += 360
                while angle_to_enemy >= 360:
                    angle_to_enemy -= 360
                
                # If enemy is within whip length and the angle is close to the whip's angle
                # (giving the whip some thickness in the angular dimension)
                angle_diff = abs((self.angle - angle_to_enemy) % 360)
                if angle_diff > 180: 
                    angle_diff = 360 - angle_diff
                    
                if distance <= self.length and angle_diff < 15:  # 15 degrees of angular thickness
                    # Mark as hit
                    self.enemies_hit.add(fiende)
                    
                    # Create explosion
                    if alle_sprites:
                        eks = Eksplosjon(fiende.rect.center)
                        alle_sprites.add(eks)
                    
                    # Add some electrical particles
                    for _ in range(10):
                        vinkel = random.uniform(0, 2 * math.pi)
                        hastighet = random.uniform(2, 5)
                        partikkel = ElectricalParticle(fiende.rect.center, vinkel, hastighet)
                        if alle_sprites:
                            alle_sprites.add(partikkel)
                        
                    # Play sound
                    if eksplosjon_lyd:
                        eksplosjon_lyd.play(maxtime=0, fade_ms=0)

# Electrical particle for whip effect
class ElectricalParticle(Partikkel):
    def __init__(self, pos, vinkel, hastighet):
        super().__init__(pos, vinkel, hastighet)
        # Override base particle color with electric blue
        self.image.fill((100, 200, 255))
        # Shorter lifespan
        self.levetid = 15
        
    def update(self):
        super().update()
        # Add flickering effect
        if random.random() < 0.5:
            self.image.fill((200, 230, 255))  # Brighter color
        else:
            self.image.fill((80, 150, 255))  # Darker color