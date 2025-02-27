import pygame
import random
import sys
import math
import os
import json

# Initialiserer pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)

# Skjermstørrelse
BREDDE = 800
HOYDE = 600
skjerm = pygame.display.set_mode((BREDDE, HOYDE))
pygame.display.set_caption("Space Indavers")

# Farger
SVART = (0, 0, 0)
HVIT = (255, 255, 255)
ROD = (255, 0, 0)
GRONN = (0, 255, 0)
BLA = (0, 0, 255)
GUL = (255, 255, 0)

# Starklasse for bakgrunnseffekt
class Star(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Ulike størrelser for stjerner for å simulere dybde
        size = random.randint(1, 3)
        self.image = pygame.Surface((size, size))
        self.image.fill(HVIT)
        self.rect = self.image.get_rect()
        
        # Tilfeldig posisjon
        self.rect.x = random.randrange(BREDDE)
        self.rect.y = random.randrange(HOYDE)
        
        # Ulike hastigheter for parallax-effekt
        self.speed = random.uniform(1, 5)
        
    def update(self):
        # Flytt stjerner nedover for å skape illusjonen av bevegelse fremover
        self.rect.y += self.speed
        
        # Resett posisjon hvis stjernen går ut av skjermen
        if self.rect.top > HOYDE:
            self.rect.y = -self.rect.height
            self.rect.x = random.randrange(BREDDE)

# Globale variabler
VANSKELIGHETSGRAD = 1  # 1=Lett, 2=Middels, 3=Vanskelig, 4=Umulig
VIS_MENY = True  # Viser menyen ved oppstart
FULLSKJERM = False  # Starter i vindusmodus
LEVEL = 1  # Startlevel for nivå-basert modus
LEVEL_MODE = False  # Om nivå-basert modus er aktiv

# Spilltilstander
class Spilltilstand:
    MENY = 0
    SPILLER = 1
    GAME_OVER = 2
    LEVEL_COMPLETE = 3
    LEVEL_SELECT = 4
    QUIT_CONFIRM = 5  # New state for quit confirmation

spilltilstand = Spilltilstand.MENY

# Variables for level selection menu
current_level_page = 0
levels_per_page = 9
max_level_pages = 5  # This allows selecting up to level 45

# Konfigurasjon og progresjon
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'game_config.json')
HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), 'high_scores.json')

# Standard konfigurasjon
default_config = {
    "unlock_impossible": False,
    "unlocked_skins": ["default"],
    "active_skin": "default",
    "max_level_reached": 1
}

# Standard high scores
default_high_scores = {
    "easy": 0,
    "medium": 0,
    "hard": 0,
    "impossible": 0,
    "level_mode": {}  # For level-specific high scores
}

# Last inn eller opprett konfigfil
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_config.copy()
    else:
        # Opprett standard konfigurasjon hvis filen ikke eksisterer
        save_config(default_config)
        return default_config.copy()

# Last inn eller opprett high score fil
def load_high_scores():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_high_scores.copy()
    else:
        # Opprett standard high scores hvis filen ikke eksisterer
        save_high_scores(default_high_scores)
        return default_high_scores.copy()

# Lagre konfigurasjon
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Lagre high scores
def save_high_scores(scores):
    with open(HIGH_SCORE_FILE, 'w') as f:
        json.dump(scores, f, indent=4)

# Last inn konfigurasjonen og high scores
game_config = load_config()
high_scores = load_high_scores()

# Last inn bilder fra assets-mappen
assets_folder = os.path.join(os.path.dirname(__file__), 'assets')
spiller_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller.png')).convert_alpha()
spiller2_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller2.png')).convert_alpha()
spiller3_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller3.png')).convert_alpha()
spiller4_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller4.png')).convert_alpha()  # Add new skin
fiende_bilde = pygame.image.load(os.path.join(assets_folder, 'fiende.png')).convert_alpha()
sterk_fiende_bilde = pygame.image.load(os.path.join(assets_folder, 'sterk_fiende.png')).convert_alpha()

# Last inn lyder
try:
    skyte_lyd = pygame.mixer.Sound(os.path.join(assets_folder, 'thock.wav'))
except:
    # Fallback til generert lyd hvis filen ikke finnes
    def lag_skyte_lyd():
        buffer = bytearray()
        # Lyd som høres ut som "thock"
        for i in range(4000):
            verdi = int(127 + 127 * max(0, 1 - i/1000) * (0.8 if i % 8 < 4 else -0.8))
            buffer.append(verdi)
        return pygame.mixer.Sound(buffer)
    skyte_lyd = lag_skyte_lyd()

# Spiller klasse
class Spiller(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.base_bilde = spiller_bilde
        self.image = pygame.transform.scale(self.base_bilde, (50, 40))
        self.rect = self.image.get_rect()
        self.rect.centerx = BREDDE // 2
        self.rect.bottom = HOYDE - 10
        self.hastighet = 8
        self.liv = 3
        # Legg til variabler for skudd-cooldown
        self.siste_skudd = 0
        self.skudd_cooldown = 150  # 150 millisekunder mellom hvert skudd
        # Skin variabler
        self.score_for_check = 0
        # Explosive weapon upgrade
        self.explosive_weapon = False
        
    def update(self):
        taster = pygame.key.get_pressed()
        # Beveg til venstre med enten venstre piltast eller A
        if taster[pygame.K_LEFT] or taster[pygame.K_a]:
            self.rect.x -= self.hastighet
            # Pac-Man-lignende wrap-around når spilleren går utenfor venstre kant
            if self.rect.right < 0:
                self.rect.left = BREDDE
        # Beveg til høyre med enten høyre piltast eller D
        if taster[pygame.K_RIGHT] or taster[pygame.K_d]:
            self.rect.x += self.hastighet
            # Pac-Man-lignende wrap-around når spilleren går utenfor høyre kant
            if self.rect.left > BREDDE:
                self.rect.right = 0
        
        # Sjekk om vi skal oppgradere skin basert på score
        global poeng
        if poeng != self.score_for_check:
            self.score_for_check = poeng
            self.update_skin()
    
    def update_skin(self):
        # Bytte skin basert på poeng - now every 500 points
        if poeng >= 1500:
            self.base_bilde = spiller4_bilde
        elif poeng >= 1000:
            self.base_bilde = spiller3_bilde
        elif poeng >= 500:
            self.base_bilde = spiller2_bilde
        else:
            self.base_bilde = spiller_bilde
        
        # Check for explosive weapon upgrade at 1200 points
        if poeng >= 1200 and not self.explosive_weapon:
            self.explosive_weapon = True
            # Create a temporary notification
            notification = WeaponUpgradeNotification()
            alle_sprites.add(notification)
        
        # Oppdater bildet men behold størrelsen
        self.image = pygame.transform.scale(self.base_bilde, (50, 40))

    def skyt(self):
        global poeng, score_multiplier, consecutive_hits
        naa = pygame.time.get_ticks()
        # Sjekk om nok tid har gått siden siste skudd
        if naa - self.siste_skudd > self.skudd_cooldown:
            self.siste_skudd = naa
            
            # Create either a regular shot or explosive shot based on weapon upgrade
            if self.explosive_weapon:
                skudd = ExplosiveShot(self.rect.centerx, self.rect.top)
            else:
                skudd = Skudd(self.rect.centerx, self.rect.top)
            
            # Juster skuddets hastighet basert på vanskelighetsgrad
            if VANSKELIGHETSGRAD == 1:
                skudd.hastighet = -30  # Raskere på lett nivå
            else:
                skudd.hastighet = -10
                
            alle_sprites.add(skudd)
            skudd_gruppe.add(skudd)
            
            # Spill av skuddlyd
            skyte_lyd.play(maxtime=0, fade_ms=0)
            
            # Legg til skuddet i liste over aktive skudd for multiplier tracking
            aktive_skudd.append(skudd)

# Skudd klasse
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

    def update(self):
        self.rect.y += self.hastighet
        # Fjern skuddet hvis det går ut av skjermen
        if self.rect.bottom < 0:
            # Hvis skuddet går ut av skjermen uten å treffe, reset multiplier
            if not self.truffet_fiende:
                reset_multiplier()
            self.kill()

# New ExplosiveShot class that inherits from Skudd
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
    
    def explode(self):
        # Declare global variables at the beginning of the function
        global poeng, score_multiplier
        
        # Create explosion effect at current position
        explosion = ExplosiveEffect(self.rect.center, self.explosion_radius)
        alle_sprites.add(explosion)
        
        # Play explosion sound
        eksplosjon_lyd.play(maxtime=0, fade_ms=0)
        
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
                        poeng += point_gain
                        fiende.kill()
                        
                        # Spawn new enemy
                        ny_fiende = SterkFiende() if random.random() < 0.3 else Fiende()
                        alle_sprites.add(ny_fiende)
                        fiende_gruppe.add(ny_fiende)
                else:
                    # Regular enemy - kill immediately
                    point_gain = int(fiende.point_value * score_multiplier)
                    poeng += point_gain
                    fiende.kill()
                    
                    # Spawn new enemy
                    ny_fiende = Fiende()
                    alle_sprites.add(ny_fiende)
                    fiende_gruppe.add(ny_fiende)
    
    def update(self):
        self.rect.y += self.hastighet
        # When reaching top of screen or if killed by collision, explode
        if self.rect.bottom < 0:
            self.explode()
            self.kill()

# New explosive effect animation
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
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((400, 60), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(BREDDE//2, HOYDE//2 - 50))
        self.timer = 180  # Show for 3 seconds (60 fps * 3)
        self.draw_notification()
    
    def draw_notification(self):
        # Background with transparency
        pygame.draw.rect(self.image, (0, 0, 0, 180), (0, 0, 400, 60))
        pygame.draw.rect(self.image, (255, 0, 0), (0, 0, 400, 60), 2)
        
        # Get text with game_font_medium
        title_text = game_font_medium.render("VÅPEN OPPGRADERT!", True, (255, 50, 50))
        desc_text = game_font_small.render("Du har låst opp eksplosivt laser (1200+ poeng)", True, HVIT)
        
        # Center the text
        self.image.blit(title_text, (200 - title_text.get_width()//2, 5))
        self.image.blit(desc_text, (200 - desc_text.get_width()//2, 35))
    
    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()

# Fiende prosjektil for Impossible mode
class FiendeProsjektil(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((6, 15))
        self.image.fill(GUL)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.top = y
        self.hastighet = 7  # Litt saktere enn spiller skudd

    def update(self):
        self.rect.y += self.hastighet
        # Fjern prosjektilet hvis det går ut av skjermen
        if self.rect.top > HOYDE:
            self.kill()

# Fiende klasse
class Fiende(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Tilfeldig størrelse mellom 70% og 120% av original størrelse
        self.scale_factor = random.uniform(0.7, 1.2)
        size = int(40 * self.scale_factor)
        
        # Original bilde for rotasjon
        self.original_image = pygame.transform.scale(fiende_bilde, (size, size))
        
        # Tilfeldig rotasjon
        self.angle = 0
        self.rotation_speed = random.uniform(-2, 2)  # Grader per frame
        self.image = self.original_image.copy()
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        
        # Juster hastighet basert på vanskelighetsgrad
        if VANSKELIGHETSGRAD == 1:
            self.hastighet = random.randrange(1, 2)
        elif VANSKELIGHETSGRAD == 2:
            self.hastighet = random.randrange(1, 3)
        else:  # Nivå 3 eller høyere
            self.hastighet = random.randrange(1, 4)
            
        self.treff = 0  # Alltid 0 for vanlige fiender
        self.max_treff = 1  # Vanlige fiender trenger 1 treff
        
        # I Impossible mode, fiender kan skyte tilbake med lav sannsynlighet
        self.last_shot = pygame.time.get_ticks()
        self.shot_delay = random.randint(3000, 8000)  # 3-8 sekunder mellom skudd
        
        # Poeng verdi
        self.point_value = 10

    def update(self):
        # Beveg fienden
        self.rect.y += self.hastighet
        
        # Oppdater rotasjon
        self.angle += self.rotation_speed
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        
        # I Impossible mode, la fiender skyte
        if VANSKELIGHETSGRAD == 4:
            now = pygame.time.get_ticks()
            if now - self.last_shot > self.shot_delay and random.random() < 0.01:  # 1% sjanse per frame
                self.last_shot = now
                self.shoot()
    
    def shoot(self):
        if VANSKELIGHETSGRAD == 4 and self.rect.bottom > 0:  # Bare skyt hvis fienden er synlig
            prosjektil = FiendeProsjektil(self.rect.centerx, self.rect.bottom)
            alle_sprites.add(prosjektil)
            fiende_prosjektil_gruppe.add(prosjektil)

# Klasse for sterkere fiender (nivå 3)
class SterkFiende(Fiende):
    def __init__(self):
        super().__init__()
        # Tilfeldig størrelse mellom 80% og 130% av original størrelse
        self.scale_factor = random.uniform(0.8, 1.3)
        size = int(50 * self.scale_factor)
        
        # Original bilde for rotasjon
        self.original_image = pygame.transform.scale(sterk_fiende_bilde, (size, size))
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        self.hastighet = random.randrange(1, 3)
        self.treff = 0  # Antall treff som trengs for å ødelegge (2 for sterkere fiender)
        self.max_treff = 2
        self.point_value = 25  # 25 poeng for sterke fiender

# Eksplosjon klasse
class Eksplosjon(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        pygame.draw.circle(self.image, (255, 165, 0), (25, 25), 25)  # Oransje sirkel
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

# Partikkel klasse for visuelle effekter
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

# Kraftbonus klasse
class Kraftbonus(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((30, 30))
        pygame.draw.circle(self.image, BLA, (15, 15), 15)
        self.image.set_colorkey(SVART)
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(BREDDE - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        self.hastighet = 3

    def update(self):
        self.rect.y += self.hastighet
        # Hvis bonusen når bunnen, fjern den
        if self.rect.top > HOYDE:
            self.kill()

def lag_eksplosjon_lyd():
    buffer = bytearray()
    # Lavfrekvens lyd med støy
    for i in range(12000):
        amplitude = max(0, 1 - i/10000)
        verdi = int(127 + amplitude * 127 * random.uniform(-1, 1))
        buffer.append(verdi)
    return pygame.mixer.Sound(buffer)

def lag_bonus_lyd():
    buffer = bytearray()
    # Oppadgående tone
    for i in range(8000):
        frekvens = 300 + i/20
        verdi = int(127 + 127 * 0.8 * math.sin(frekvens * i/1000))
        buffer.append(verdi)
    return pygame.mixer.Sound(buffer)

# Generer lydene
eksplosjon_lyd = lag_eksplosjon_lyd()
bonus_lyd = lag_bonus_lyd()

# Juster volum
skyte_lyd.set_volume(0.4)
eksplosjon_lyd.set_volume(0.6)
bonus_lyd.set_volume(0.5)

# Grupper av sprites
alle_sprites = pygame.sprite.Group()
fiende_gruppe = pygame.sprite.Group()
skudd_gruppe = pygame.sprite.Group()
bonus_gruppe = pygame.sprite.Group()
fiende_prosjektil_gruppe = pygame.sprite.Group()  # For fiende-prosjektiler i Impossible mode
star_gruppe = pygame.sprite.Group()  # Ny gruppe for stjerner i bakgrunnen

# Opprett stjerner for bakgrunnen
def create_stars(count=100):
    for i in range(count):
        star = Star()
        star_gruppe.add(star)

create_stars()

# Lag spilleren
spiller = Spiller()
alle_sprites.add(spiller)

# Poeng og multiplier system
poeng = 0
score_multiplier = 1.0
consecutive_hits = 0
aktive_skudd = []

def reset_multiplier():
    global score_multiplier, consecutive_hits
    score_multiplier = 1.0
    consecutive_hits = 0

def increase_multiplier():
    global score_multiplier, consecutive_hits
    consecutive_hits += 1
    # Øk multiplier med 0.1 for hvert treff, maks 5.0
    score_multiplier = min(5.0, 1.0 + (consecutive_hits * 0.1))

# Last inn bedre font
try:
    # Prøv å laste inn en sci-fi font, ellers bruk system font
    font_path = os.path.join(assets_folder, 'nasalization-rg.ttf')
    if os.path.exists(font_path):
        game_font_small = pygame.font.Font(font_path, 18)  # Reduced from 24
        game_font_medium = pygame.font.Font(font_path, 24)  # Reduced from 36
        game_font_large = pygame.font.Font(font_path, 36)  # Reduced from 48
    else:
        # Fallback til en annen sci-fi-lignende font hvis tilgjengelig
        available_fonts = pygame.font.get_fonts()
        if 'courier' in available_fonts:
            game_font_small = pygame.font.SysFont('courier', 18)  # Reduced from 24
            game_font_medium = pygame.font.SysFont('courier', 24)  # Reduced from 36
            game_font_large = pygame.font.SysFont('courier', 36)  # Reduced from 48
        else:
            # Fallback til standard font
            game_font_small = pygame.font.SysFont('arial', 18)  # Reduced from 24
            game_font_medium = pygame.font.SysFont('arial', 24)  # Reduced from 36
            game_font_large = pygame.font.SysFont('arial', 36)  # Reduced from 48
except Exception as e:
    print(f"Kunne ikke laste inn font: {e}")
    game_font_small = pygame.font.SysFont('arial', 18)  # Reduced from 24
    game_font_medium = pygame.font.SysFont('arial', 24)  # Reduced from 36
    game_font_large = pygame.font.SysFont('arial', 36)  # Reduced from 48

# Klokke
klokke = pygame.time.Clock()

# Bonus timer
bonus_timer = pygame.time.get_ticks()
bonus_forsinkelse = 15000  # 15 sekunder

# Level-basert system
def set_level_requirements(level):
    """Sett fiender og mål for valgt nivå"""
    if level == 1:
        return {"target_score": 150, "fiende_count": 4, "sterk_fiende_count": 0}
    elif level == 2:
        return {"target_score": 200, "fiende_count": 5, "sterk_fiende_count": 0}
    elif level == 3:
        return {"target_score": 250, "fiende_count": 5, "sterk_fiende_count": 1}
    elif level == 4:
        return {"target_score": 300, "fiende_count": 6, "sterk_fiende_count": 1}
    elif level == 5:
        return {"target_score": 350, "fiende_count": 6, "sterk_fiende_count": 2}
    elif level <= 10:
        # Levels 6-10: Smooth progression
        base_score = 350
        score_increment = 50
        return {
            "target_score": base_score + (level - 5) * score_increment,
            "fiende_count": 6 + (level - 5) // 2,
            "sterk_fiende_count": 2
        }
    elif level <= 20:
        # Levels 11-20: Slightly harder but still manageable
        base_score = 600
        score_increment = 50
        return {
            "target_score": base_score + (level - 10) * score_increment,
            "fiende_count": 8,
            "sterk_fiende_count": min(3, 2 + (level - 10) // 5)
        }
    else:
        # Levels 21+: Cap the difficulty to keep it fair
        base_score = 1100
        score_increment = 50
        return {
            "target_score": base_score + (level - 20) * score_increment,
            "fiende_count": min(10, 8 + (level - 20) // 10),
            "sterk_fiende_count": min(4, 3 + (level - 20) // 10)
        }

# Funksjon for å opprette fiender basert på vanskelighetsgrad
def opprett_fiender(level_mode=False):
    # Tøm sprite grupper
    for sprite in fiende_gruppe:
        sprite.kill()
    for sprite in skudd_gruppe:
        sprite.kill()
    for sprite in bonus_gruppe:
        sprite.kill()
    for sprite in fiende_prosjektil_gruppe:
        sprite.kill()
    
    # Opprett nye fiender
    if level_mode:
        level_reqs = set_level_requirements(LEVEL)
        antall_fiender = level_reqs["fiende_count"]
        antall_sterke = level_reqs["sterk_fiende_count"]
    else:
        antall_fiender = 4
        antall_sterke = 0 if VANSKELIGHETSGRAD < 3 else 1
    
    for i in range(antall_fiender):
        fiende = Fiende()
        alle_sprites.add(fiende)
        fiende_gruppe.add(fiende)
    
    # Legg til sterke fiender
    for i in range(antall_sterke):
        sterk_fiende = SterkFiende()
        alle_sprites.add(sterk_fiende)
        fiende_gruppe.add(sterk_fiende)
    
    # Tilbakestill poeng og liv
    global poeng, score_multiplier, consecutive_hits
    poeng = 0  # Alltid start på 0 poeng for hvert level/nytt spill
    score_multiplier = 1.0
    consecutive_hits = 0
    spiller.liv = 3

# Sjekk og lagre highscores
def check_and_update_highscore():
    global poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE
    
    updated = False
    
    # Map av vanskelighetsgrad til nøkler i config
    diff_map = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}
    
    if LEVEL_MODE:
        # For level mode, lagre high score for hvert level
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
            
            # Sjekk for unlock av impossible mode
            if current_diff == "hard" and poeng >= 1000:
                game_config["unlock_impossible"] = True
                save_config(game_config)
    
    # Lagre oppdatert high scores
    if updated:
        save_high_scores(high_scores)
        return True
    
    return False

# Hent gjeldende high score
def get_current_high_score():
    global VANSKELIGHETSGRAD, LEVEL, LEVEL_MODE, high_scores
    
    if LEVEL_MODE:
        level_key = f"level_{LEVEL}"
        return high_scores["level_mode"].get(level_key, 0)
    else:
        diff_map = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}
        current_diff = diff_map.get(VANSKELIGHETSGRAD)
        return high_scores.get(current_diff, 0)

# Sjekk for level completion i level-mode
def check_level_complete():
    global LEVEL, poeng, game_config
    
    if LEVEL_MODE:
        level_reqs = set_level_requirements(LEVEL)
        if poeng >= level_reqs["target_score"]:
            # Sjekk for high score før level endring
            check_and_update_highscore()
            
            # Level fullført
            LEVEL += 1
            
            # Oppdater maks oppnådd level
            if LEVEL > game_config["max_level_reached"]:
                game_config["max_level_reached"] = LEVEL
                save_config(game_config)
                
                # Sjekk for nye skins basert på level
                if LEVEL == 5 and "level5_skin" not in game_config["unlocked_skins"]:
                    game_config["unlocked_skins"].append("level5_skin")
                    save_config(game_config)
            
            return True
    
    return False

# UI hjelpefunksjoner
def draw_level_progress():
    if LEVEL_MODE:
        level_reqs = set_level_requirements(LEVEL)
        progress_text = game_font_small.render(f"Progress: {poeng}/{level_reqs['target_score']}", True, HVIT)
        skjerm.blit(progress_text, (BREDDE//2 - progress_text.get_width()//2, 10))

def draw_multiplier():
    # Move multiplier to middle top instead of right top to avoid overlap with high score
    multiplier_text = game_font_small.render(f"Multiplier: x{score_multiplier:.1f}", True, (255, 165, 0))
    skjerm.blit(multiplier_text, (BREDDE//2 - multiplier_text.get_width()//2, 40))

def draw_enemy_points():
    try:
        # Lag små ikoner og vis nåværende poengsummer
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
        
        # Only show strong enemy points in levels/difficulties where they appear
        if (LEVEL_MODE and LEVEL >= 2) or (not LEVEL_MODE and VANSKELIGHETSGRAD >= 3):
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

# Spill-løkke
spillkjorer = True

while spillkjorer:
    # Hold riktig FPS
    klokke.tick(60)
    
    # Hendelser
    for hendelse in pygame.event.get():
        if hendelse.type == pygame.QUIT:
            spillkjorer = False
        elif hendelse.type == pygame.KEYDOWN:
            # Veksle fullskjerm med F-tasten
            if hendelse.key == pygame.K_f:
                FULLSKJERM = not FULLSKJERM
                if FULLSKJERM:
                    skjerm = pygame.display.set_mode((BREDDE, HOYDE), pygame.FULLSCREEN)
                else:
                    skjerm = pygame.display.set_mode((BREDDE, HOYDE))
            
            # I menytilstand
            if spilltilstand == Spilltilstand.MENY:
                if hendelse.key == pygame.K_1:
                    VANSKELIGHETSGRAD = 1
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender()
                elif hendelse.key == pygame.K_2:
                    VANSKELIGHETSGRAD = 2
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender()
                elif hendelse.key == pygame.K_3:
                    VANSKELIGHETSGRAD = 3
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender()
                elif hendelse.key == pygame.K_4 and game_config["unlock_impossible"]:
                    VANSKELIGHETSGRAD = 4
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender()
                elif hendelse.key == pygame.K_l:  # Level mode now goes to level selection
                    LEVEL_MODE = True
                    current_level_page = 0  # Reset to first page
                    spilltilstand = Spilltilstand.LEVEL_SELECT
            # Level selection menu
            elif spilltilstand == Spilltilstand.LEVEL_SELECT:
                # Navigate pages
                if hendelse.key == pygame.K_RIGHT or hendelse.key == pygame.K_n:
                    current_level_page = min(current_level_page + 1, max_level_pages - 1)
                elif hendelse.key == pygame.K_LEFT or hendelse.key == pygame.K_p:
                    current_level_page = max(current_level_page - 1, 0)
                elif hendelse.key == pygame.K_ESCAPE:
                    spilltilstand = Spilltilstand.MENY  # Go back to main menu
                # Select level with number keys
                elif hendelse.key >= pygame.K_1 and hendelse.key <= pygame.K_9:
                    selected_level = (current_level_page * levels_per_page) + (hendelse.key - pygame.K_0)
                    max_allowed_level = game_config["max_level_reached"]
                    
                    if selected_level <= max_allowed_level:
                        LEVEL = selected_level
                        VANSKELIGHETSGRAD = 2  # Standard difficulty for level mode
                        spilltilstand = Spilltilstand.SPILLER
                        VIS_MENY = False
                        opprett_fiender(True)
            # Under spill
            elif spilltilstand == Spilltilstand.SPILLER:
                # Skyt med Space, W eller pil opp
                if hendelse.key == pygame.K_SPACE or hendelse.key == pygame.K_w or hendelse.key == pygame.K_UP:
                    spiller.skyt()
                # Add escape key to bring up quit confirmation
                elif hendelse.key == pygame.K_ESCAPE:
                    spilltilstand = Spilltilstand.QUIT_CONFIRM
            # Add handling for quit confirmation
            elif spilltilstand == Spilltilstand.QUIT_CONFIRM:
                if hendelse.key == pygame.K_j or hendelse.key == pygame.K_y:  # Y or J for Yes
                    # Check for high score before exiting
                    check_and_update_highscore()
                    # Return to menu
                    spilltilstand = Spilltilstand.MENY
                    VIS_MENY = True
                elif hendelse.key == pygame.K_n or hendelse.key == pygame.K_ESCAPE:  # N or ESC to cancel
                    # Return to game
                    spilltilstand = Spilltilstand.SPILLER
            # Game over
            elif spilltilstand == Spilltilstand.GAME_OVER:
                if hendelse.key == pygame.K_RETURN:
                    # Gå tilbake til menyen for å velge vanskelighetsgrad igjen
                    spilltilstand = Spilltilstand.MENY
                    VIS_MENY = True
            # Level fullført
            elif spilltilstand == Spilltilstand.LEVEL_COMPLETE:
                if hendelse.key == pygame.K_RETURN:
                    # Start neste level
                    spilltilstand = Spilltilstand.SPILLER
                    opprett_fiender(True)
                    
    # Oppdater
    star_gruppe.update()  # Oppdater stjernene først
    
    if spilltilstand == Spilltilstand.SPILLER:
        alle_sprites.update()
        
        # Hent gjeldende high score
        current_high_score = get_current_high_score()
        
        # Sjekk for kollisjoner mellom skudd og fiender
        treff = pygame.sprite.groupcollide(skudd_gruppe, fiende_gruppe, True, False)
        for skudd, fiender in treff.items():
            # Merk skuddet som truffet for multiplier beregning
            skudd.truffet_fiende = True
            
            # Handle explosive shots specially
            if isinstance(skudd, ExplosiveShot):
                skudd.explode()  # This will handle the explosion effect and damage nearby enemies
            
            # Process each hit enemy
            for fiende in fiender:
                fiende.treff += 1
                # If the enemy has reached max hits, remove it
                if fiende.treff >= fiende.max_treff:
                    # Increase multiplier when we hit an enemy
                    increase_multiplier()
                    
                    # Calculate points based on multiplier
                    point_gain = int(fiende.point_value * score_multiplier)
                    poeng += point_gain
                    
                    # Only create explosion for regular shots or if not hit by explosive shot
                    if not isinstance(skudd, ExplosiveShot):
                        eksplosjon = Eksplosjon(fiende.rect.center)
                        alle_sprites.add(eksplosjon)
                        eksplosjon_lyd.play(maxtime=0, fade_ms=0)
                    
                    # Remove the enemy
                    fiende.kill()
                    
                    # Create a new enemy based on difficulty
                    if (VANSKELIGHETSGRAD >= 3 and random.random() < 0.3) or (LEVEL_MODE and random.random() < 0.2 * LEVEL):
                        ny_fiende = SterkFiende()
                    else:
                        ny_fiende = Fiende()
                    alle_sprites.add(ny_fiende)
                    fiende_gruppe.add(ny_fiende)
                else:
                    # Visual feedback for hit without destroying the enemy
                    # Only needed for regular shots since explosive shots handle their own effects
                    if not isinstance(skudd, ExplosiveShot):
                        fiende.image.fill(SVART)
                        pygame.draw.circle(fiende.image, (255, 255, 0), (25, 25), 25)  # Yellow flash for hit
                        fiende.image.set_colorkey(SVART)
                        
                        # After a short time, change back to original color
                        pygame.time.delay(20)
                        fiende.image.fill(SVART)
                        pygame.draw.circle(fiende.image, (255, 165, 0), (25, 25), 25)
                        fiende.image.set_colorkey(SVART)
        
        # I Impossible mode, sjekk for kollisjoner mellom spiller og fiende prosjektiler
        if VANSKELIGHETSGRAD == 4:
            treff_prosjektil = pygame.sprite.spritecollide(spiller, fiende_prosjektil_gruppe, True)
            for hit in treff_prosjektil:
                spiller.liv -= 1
                if spiller.liv <= 0:
                    spilltilstand = Spilltilstand.GAME_OVER
                    check_and_update_highscore()
        
        # Sjekk om fiender har nådd bunnen
        for fiende in fiende_gruppe:
            if fiende.rect.top > HOYDE:
                fiende.rect.x = random.randrange(BREDDE - fiende.rect.width)
                fiende.rect.y = random.randrange(-100, -40)
                
                # Juster hastighet basert på vanskelighetsgrad
                if VANSKELIGHETSGRAD == 1:
                    fiende.hastighet = random.randrange(1, 2)
                elif VANSKELIGHETSGRAD == 2:
                    fiende.hastighet = random.randrange(1, 3)
                else:  # Nivå 3
                    fiende.hastighet = random.randrange(1, 3)  # Gjør kometene saktere
                spiller.liv -= 1
                if spiller.liv <= 0:
                    spilltilstand = Spilltilstand.GAME_OVER
                    check_and_update_highscore()
        
        # Generer bonus
        naa = pygame.time.get_ticks()
        if naa - bonus_timer > bonus_forsinkelse:
            bonus_timer = naa
            bonus = Kraftbonus()
            alle_sprites.add(bonus)
            bonus_gruppe.add(bonus)
        
        # Sjekk for kollisjoner mellom spiller og bonus
        treff_bonus = pygame.sprite.spritecollide(spiller, bonus_gruppe, True)
        for hit in treff_bonus:
            bonus_lyd.play(maxtime=0, fade_ms=0)
            spiller.liv += 1
            # Visuell effekt når bonus samles inn
            for i in range(10):
                vinkel = random.uniform(0, 2 * math.pi)
                hastighet = random.uniform(1, 3)
                partikkel = Partikkel(hit.rect.center, vinkel, hastighet)
                alle_sprites.add(partikkel)
        
        # Sjekk for level completion
        if check_level_complete():
            spilltilstand = Spilltilstand.LEVEL_COMPLETE
    
    # Tegn / render
    skjerm.fill(SVART)
    
    # Vis stjernene (før alt annet for å være i bakgrunnen)
    star_gruppe.draw(skjerm)
    
    # Vis menyen for å velge vanskelighetsgrad
    if spilltilstand == Spilltilstand.MENY:
        # Use a smaller title font
        tittel_font = game_font_large
        meny_font = game_font_medium
        info_font = game_font_small
        
        # Title - positioned higher
        tittel = tittel_font.render("SPACE INVADERS", True, HVIT)
        skjerm.blit(tittel, (BREDDE//2 - tittel.get_width()//2, 50))
        
        # Create a menu panel on the left side
        menu_panel_width = BREDDE * 0.65  # Left 65% of screen for menu
        
        # Menu items with more consistent spacing
        y_start = 120
        line_spacing = 35
        
        # Calculate menu center point with a safe margin
        menu_center = int(menu_panel_width * 0.4)  # Adjusted from BREDDE//4 to ensure text fits
        
        valg1 = meny_font.render("1 - Lett", True, GRONN)
        skjerm.blit(valg1, (menu_center - valg1.get_width()//2, y_start))
        
        # For info text that might be too long, check against available width
        valg1_info_text = "(Sakte fiender, siktelinje)"
        valg1_info = info_font.render(valg1_info_text, True, GRONN)
        if valg1_info.get_width() > menu_panel_width * 0.8:  # If text is too wide
            # Split into multiple lines or use truncated text
            valg1_info = info_font.render(valg1_info_text[:20] + "...", True, GRONN)
        skjerm.blit(valg1_info, (menu_center - valg1_info.get_width()//2, y_start + 25))
        
        valg2 = meny_font.render("2 - Middels", True, (255, 255, 0))
        skjerm.blit(valg2, (menu_center - valg2.get_width()//2, y_start + line_spacing * 2))
        
        valg2_info_text = "(Medium fiender, siktelinje)"
        valg2_info = info_font.render(valg2_info_text, True, (255, 255, 0))
        if valg2_info.get_width() > menu_panel_width * 0.8:
            valg2_info = info_font.render(valg2_info_text[:20] + "...", True, (255, 255, 0))
        skjerm.blit(valg2_info, (menu_center - valg2_info.get_width()//2, y_start + line_spacing * 2 + 25))
        
        valg3 = meny_font.render("3 - Vanskelig", True, ROD)
        skjerm.blit(valg3, (menu_center - valg3.get_width()//2, y_start + line_spacing * 4))
        
        # This line is particularly long and might cause clipping
        valg3_info_text = "(Raske fiender, sterke fiender, ingen siktelinje)"
        valg3_info_long = info_font.render(valg3_info_text, True, ROD)
        
        # If the text is too long, split it into two lines
        if valg3_info_long.get_width() > menu_panel_width * 0.8:
            valg3_info_line1 = info_font.render("(Raske fiender,", True, ROD)
            valg3_info_line2 = info_font.render("sterke fiender, ingen siktelinje)", True, ROD)
            skjerm.blit(valg3_info_line1, (menu_center - valg3_info_line1.get_width()//2, y_start + line_spacing * 4 + 25))
            skjerm.blit(valg3_info_line2, (menu_center - valg3_info_line2.get_width()//2, y_start + line_spacing * 4 + 45))
        else:
            skjerm.blit(valg3_info_long, (menu_center - valg3_info_long.get_width()//2, y_start + line_spacing * 4 + 25))
        
        if game_config["unlock_impossible"]:
            valg4 = meny_font.render("4 - Umulig", True, (255, 0, 255))
            skjerm.blit(valg4, (menu_center - valg4.get_width()//2, y_start + line_spacing * 6))
            
            valg4_info_text = "(Fiender skyter tilbake)"
            valg4_info = info_font.render(valg4_info_text, True, (255, 0, 255))
            skjerm.blit(valg4_info, (menu_center - valg4_info.get_width()//2, y_start + line_spacing * 6 + 25))
        
        # Adjust y-position if valg3 has two lines
        level_y_pos = y_start + line_spacing * 8
        if valg3_info_long.get_width() > menu_panel_width * 0.8:
            level_y_pos += 20  # Add extra space for the two-line description
            
        level_mode_valg = meny_font.render("L - Level Mode", True, BLA)
        skjerm.blit(level_mode_valg, (menu_center - level_mode_valg.get_width()//2, level_y_pos))
        
        # Add info about continuing from previous level
        if game_config["max_level_reached"] > 1:
            level_continue = info_font.render(f"(Fortsett fra level {game_config['max_level_reached']})", True, BLA)
            skjerm.blit(level_continue, (menu_center - level_continue.get_width()//2, level_y_pos + 25))
        
        # Draw a vertical separator line
        pygame.draw.line(skjerm, HVIT, (menu_panel_width, 100), (menu_panel_width, HOYDE - 100), 2)
        
        # High scores section - moved to right panel
        hs_title = game_font_medium.render("HIGH SCORES", True, HVIT)
        hs_x = menu_panel_width + (BREDDE - menu_panel_width) // 2
        skjerm.blit(hs_title, (hs_x - hs_title.get_width()//2, 120))
        
        y_pos = 170
        for diff, name in [(1, "Lett"), (2, "Middels"), (3, "Vanskelig"), (4, "Umulig")]:
            diff_key = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}[diff]
            score = high_scores.get(diff_key, 0)
            color = {1: GRONN, 2: (255, 255, 0), 3: ROD, 4: (255, 0, 255)}[diff]
            score_text = info_font.render(f"{name}: {score}", True, color)
            skjerm.blit(score_text, (hs_x - score_text.get_width()//2, y_pos))
            y_pos += 30
        
        # Add instructions at the bottom
        instr = info_font.render("Bruk tallene 1-3 eller L for å velge spillmodus", True, HVIT)
        skjerm.blit(instr, (BREDDE//2 - instr.get_width()//2, HOYDE - 50))

    elif spilltilstand == Spilltilstand.LEVEL_SELECT:
        # Title
        tittel = game_font_large.render("VELG LEVEL", True, HVIT)
        skjerm.blit(tittel, (BREDDE//2 - tittel.get_width()//2, 50))
        
        # Draw level grid - position it more to the left side
        level_side = 80  # Size of each level box
        margin = 20
        
        # Move grid to the left by setting x_start at 25% of screen width instead of center
        grid_x_start = int(BREDDE * 0.25) - ((3 * level_side + 2 * margin) // 2)
        grid_y_start = 150
        
        # Make color info box wider - calculate its width (at least double the grid width)
        info_box_width = min(BREDDE - 40, (3 * level_side + 2 * margin) * 2)
        
        # Page indicator - moved to align with the grid
        page_text = game_font_medium.render(f"Side {current_level_page + 1}/{max_level_pages}", True, HVIT)
        skjerm.blit(page_text, (grid_x_start + (3 * level_side + 2 * margin)//2 - page_text.get_width()//2, 110))
        
        # Navigation area on the right side
        nav_area_x = grid_x_start + 3 * level_side + 2 * margin + 40
        nav_area_width = BREDDE - nav_area_x - 20
        nav_area_height = 3 * level_side + 2 * margin
        
        # Draw navigation panel
        pygame.draw.rect(skjerm, (50, 50, 70), (nav_area_x, grid_y_start, nav_area_width, nav_area_height))
        pygame.draw.rect(skjerm, HVIT, (nav_area_x, grid_y_start, nav_area_width, nav_area_height), 2)
        
        # Navigation title
        nav_title = game_font_medium.render("Navigasjon", True, HVIT)
        skjerm.blit(nav_title, (nav_area_x + nav_area_width//2 - nav_title.get_width()//2, grid_y_start + 20))
        
        # Navigation hints - distributed vertically in the panel
        nav_text1 = game_font_small.render("Piltaster høyre/venstre", True, HVIT)
        nav_text2 = game_font_small.render("eller N/P for å bla", True, HVIT)
        nav_text3 = game_font_small.render("ESC for å gå tilbake", True, HVIT)
        nav_text4 = game_font_small.render("Tall 1-9 for å velge level", True, HVIT)
        
        # Position navigation hints with even spacing
        nav_spacing = (nav_area_height - 80) // 4
        skjerm.blit(nav_text1, (nav_area_x + 20, grid_y_start + 60))
        skjerm.blit(nav_text2, (nav_area_x + 20, grid_y_start + 60 + nav_spacing))
        skjerm.blit(nav_text3, (nav_area_x + 20, grid_y_start + 60 + nav_spacing * 2))
        skjerm.blit(nav_text4, (nav_area_x + 20, grid_y_start + 60 + nav_spacing * 3))
        
        # Draw level boxes
        for row in range(3):
            for col in range(3):
                level_num = (current_level_page * levels_per_page) + (row * 3 + col + 1)
                x = grid_x_start + col * (level_side + margin)
                y = grid_y_start + row * (level_side + margin)
                
                # Determine level status and color
                if level_num <= game_config["max_level_reached"]:
                    # Level is unlocked
                    # A level is considered completed only if the player has reached a level beyond it
                    if level_num < game_config["max_level_reached"]:
                        # Level is completed (player has progressed past this level)
                        box_color = GRONN  # Completed level
                        text_color = HVIT
                    else:
                        # Current level - unlocked but not completed yet
                        box_color = (100, 100, 255)  # Light blue for unlocked
                        text_color = HVIT
                else:
                    # Level is locked
                    box_color = (100, 100, 100)  # Gray for locked
                    text_color = (200, 200, 200)
                
                # Draw box
                pygame.draw.rect(skjerm, box_color, (x, y, level_side, level_side))
                pygame.draw.rect(skjerm, HVIT, (x, y, level_side, level_side), 2)  # Border
                
                # Draw level number
                num_text = game_font_medium.render(str(level_num), True, text_color)
                skjerm.blit(num_text, (x + level_side//2 - num_text.get_width()//2, 
                                      y + level_side//2 - num_text.get_height()//2))
        
        # Level info box - position below the level grid with increased width
        info_box_y = grid_y_start + 3 * (level_side + margin) + 10
        info_box_height = 100
        
        # Draw the info box with increased width
        pygame.draw.rect(skjerm, (50, 50, 70), (grid_x_start, info_box_y, 
                                              info_box_width, info_box_height))
        pygame.draw.rect(skjerm, HVIT, (grid_x_start, info_box_y, 
                                      info_box_width, info_box_height), 2)
        
        info_title = game_font_medium.render("Fargekoder:", True, HVIT)
        skjerm.blit(info_title, (grid_x_start + 20, info_box_y + 15))
        
        # Calculate available width and spacing for horizontal layout - now with more space
        legend_spacing_x = info_box_width // 3  # Divide available space into 3 equal parts
        box_size = 25
        
        # Calculate center positions for each color explanation
        center1_x = grid_x_start + (legend_spacing_x // 2)
        center2_x = grid_x_start + legend_spacing_x + (legend_spacing_x // 2)
        center3_x = grid_x_start + 2 * legend_spacing_x + (legend_spacing_x // 2)
        
        # Position for all color boxes (same Y position)
        legend_y = info_box_y + 45
        
        # Green - completed (first position)
        pygame.draw.rect(skjerm, GRONN, (center1_x - box_size//2, legend_y, box_size, box_size))
        completed_text = game_font_small.render("Fullført nivå", True, HVIT)
        skjerm.blit(completed_text, (center1_x - completed_text.get_width()//2, legend_y + box_size + 5))
        
        # Blue - available (second position)
        pygame.draw.rect(skjerm, (100, 100, 255), (center2_x - box_size//2, legend_y, box_size, box_size))
        unlocked_text = game_font_small.render("Tilgjengelig nivå", True, HVIT)
        skjerm.blit(unlocked_text, (center2_x - unlocked_text.get_width()//2, legend_y + box_size + 5))
        
        # Gray - locked (third position)
        pygame.draw.rect(skjerm, (100, 100, 100), (center3_x - box_size//2, legend_y, box_size, box_size))
        locked_text = game_font_small.render("Låst nivå", True, HVIT)
        skjerm.blit(locked_text, (center3_x - locked_text.get_width()//2, legend_y + box_size + 5))

    else:
        # Tegn siktelinje for spilleren på nivå 1 og 2
        if not spilltilstand == Spilltilstand.GAME_OVER and VANSKELIGHETSGRAD < 3:
            # Lag en semi-transparent overflate for siktelinjen
            siktelinje = pygame.Surface((2, HOYDE), pygame.SRCALPHA)
            siktelinje.fill((0, 0, 255, 30))  # Blå farge med 30/255 alpha (nesten gjennomsiktig)
            
            # Tegn stiplede linjer på overflaten
            for y in range(0, HOYDE, 10):
                if y % 20 == 0:  # Alternerer mellom synlig og usynlig for å skape stiplet effekt
                    pygame.draw.line(siktelinje, (0, 0, 255, 80), (0, y), (2, y+8), 2)
            
            # Plasser siktelinjen på skjermen, sentrert med spilleren
            skjerm.blit(siktelinje, (spiller.rect.centerx - 1, 0))
        
        alle_sprites.draw(skjerm)
        
        # Vis poeng og high score
        high_score = get_current_high_score()
        poeng_tekst = game_font_small.render(f"Poeng: {poeng}", True, HVIT)
        if not LEVEL_MODE:  # Only show high score in regular mode
            high_score_tekst = game_font_small.render(f"High Score: {high_score}", True, (255, 215, 0))  # Gull-farge for high score
            skjerm.blit(high_score_tekst, (BREDDE - high_score_tekst.get_width() - 10, 10))

        skjerm.blit(poeng_tekst, (10, 10))
        
        # Vis liv
        liv_tekst = game_font_small.render(f"Liv: {spiller.liv}", True, HVIT)
        skjerm.blit(liv_tekst, (10, 40))
        
        # Vis vanskelighetsgrad
        if LEVEL_MODE:
            # In level mode, show the current level instead of difficulty
            level_tekst = game_font_small.render(f"Level: {LEVEL}", True, BLA)
            skjerm.blit(level_tekst, (10, 70))
        else:
            # In regular mode, show difficulty
            if VANSKELIGHETSGRAD == 1:
                vanskelig_tekst = game_font_small.render("Nivå: Lett", True, GRONN)
            elif VANSKELIGHETSGRAD == 2:
                vanskelig_tekst = game_font_small.render("Nivå: Middels", True, (255, 255, 0))
            elif VANSKELIGHETSGRAD == 3:
                vanskelig_tekst = game_font_small.render("Nivå: Vanskelig", True, ROD)
            else:
                vanskelig_tekst = game_font_small.render("Nivå: Umulig", True, (255, 0, 255))
            skjerm.blit(vanskelig_tekst, (10, 70))
        
        # Vis level progress (kun i level mode)
        if LEVEL_MODE and spilltilstand == Spilltilstand.SPILLER:
            draw_level_progress()
        
        # Vis multiplier - now handled by the draw_multiplier function
        if spilltilstand == Spilltilstand.SPILLER:
            draw_multiplier()
        
        # Vis fiendepoengsummer - wrap this in a try/except to prevent crashes
        if spilltilstand == Spilltilstand.SPILLER:
            try:
                draw_enemy_points()
            except Exception as e:
                print(f"Failed to draw enemy points: {e}")
        
        # Vis informasjon om nivået
        if spilltilstand == Spilltilstand.SPILLER:
            if VANSKELIGHETSGRAD == 1:
                hjelp_tekst = game_font_small.render("F = Fullskjerm", True, HVIT)
                skjerm.blit(hjelp_tekst, (BREDDE - hjelp_tekst.get_width() - 10, 40))
                
        # Vis "Game Over" melding with improved spacing
        if spilltilstand == Spilltilstand.GAME_OVER:
            # Create a semi-transparent overlay for better text readability
            overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))  # Black with 50% transparency
            skjerm.blit(overlay, (0, 0))
            
            # Title with more space
            over_font = game_font_large
            over_tekst = over_font.render("GAME OVER", True, ROD)
            skjerm.blit(over_tekst, (BREDDE//2 - over_tekst.get_width()//2, HOYDE//2 - 100))
            
            # Score text with more spacing
            score_tekst = game_font_medium.render(f"Din poengsum: {poeng}", True, HVIT)
            skjerm.blit(score_tekst, (BREDDE//2 - score_tekst.get_width()//2, HOYDE//2 - 20))
            
            # Vis om det ble ny high score
            current_high_score = get_current_high_score()
            if poeng >= current_high_score:
                nytt_hs_tekst = game_font_medium.render("NY HIGH SCORE!", True, (255, 215, 0))
                skjerm.blit(nytt_hs_tekst, (BREDDE//2 - nytt_hs_tekst.get_width()//2, HOYDE//2 + 20))
            
            # Instructions with better positioning
            restart_font = game_font_medium
            restart_tekst = restart_font.render("Trykk ENTER for å gå til menyen", True, HVIT)
            skjerm.blit(restart_tekst, (BREDDE//2 - restart_tekst.get_width()//2, HOYDE//2 + 80))
        
        # Vis "Level Complete" melding - also improve spacing
        if spilltilstand == Spilltilstand.LEVEL_COMPLETE:
            # Add semi-transparent overlay
            overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))  # Black with 50% transparency
            skjerm.blit(overlay, (0, 0))
            
            level_font = game_font_large
            level_tekst = level_font.render(f"LEVEL {LEVEL-1} FULLFØRT", True, GRONN)
            skjerm.blit(level_tekst, (BREDDE//2 - level_tekst.get_width()//2, HOYDE//2 - 80))
            
            # Vis poengsum for nivået
            score_tekst = game_font_medium.render(f"Din poengsum: {poeng}", True, HVIT)
            skjerm.blit(score_tekst, (BREDDE//2 - score_tekst.get_width()//2, HOYDE//2 - 20))
            
            # Get the requirements for the next level
            next_level_reqs = set_level_requirements(LEVEL)
            next_target_score = next_level_reqs["target_score"]
            
            # Display the target score for the next level
            target_text = game_font_medium.render(f"Neste mål: {next_target_score} poeng", True, (255, 255, 100))
            skjerm.blit(target_text, (BREDDE//2 - target_text.get_width()//2, HOYDE//2 + 20))
            
            next_level_font = game_font_medium
            next_level_tekst = next_level_font.render("Trykk ENTER for neste level", True, HVIT)
            skjerm.blit(next_level_tekst, (BREDDE//2 - next_level_tekst.get_width()//2, HOYDE//2 + 60))
        
        # Add quit confirmation screen to the rendering section where other game states are handled
        elif spilltilstand == Spilltilstand.QUIT_CONFIRM:
            # Continue drawing the game in the background
            # ...reuse existing drawing code for gameplay...
            
            # Draw a semi-transparent overlay
            overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))  # Black with transparency
            skjerm.blit(overlay, (0, 0))
            
            # Create a dialog box
            dialog_width = 400
            dialog_height = 200
            dialog_x = BREDDE//2 - dialog_width//2
            dialog_y = HOYDE//2 - dialog_height//2
            
            # Draw dialog box
            pygame.draw.rect(skjerm, (60, 60, 80), (dialog_x, dialog_y, dialog_width, dialog_height))
            pygame.draw.rect(skjerm, HVIT, (dialog_x, dialog_y, dialog_width, dialog_height), 2)
            
            # Dialog title
            quit_title = game_font_medium.render("Avslutt spill?", True, HVIT)
            skjerm.blit(quit_title, (BREDDE//2 - quit_title.get_width()//2, dialog_y + 30))
            
            # Current score
            score_text = game_font_small.render(f"Din nåværende poengsum: {poeng}", True, HVIT)
            skjerm.blit(score_text, (BREDDE//2 - score_text.get_width()//2, dialog_y + 70))
            
            # Check if current score is a high score
            current_high_score = get_current_high_score()
            if poeng > current_high_score:
                highscore_text = game_font_small.render("Dette vil bli en ny rekord!", True, (255, 215, 0))
                skjerm.blit(highscore_text, (BREDDE//2 - highscore_text.get_width()//2, dialog_y + 100))
            
            # Options
            options_text = game_font_small.render("Trykk J for ja, N for nei", True, HVIT)
            skjerm.blit(options_text, (BREDDE//2 - options_text.get_width()//2, dialog_y + 140))
    
    # Oppdater skjermen
    pygame.display.flip()

# Avslutt spillet
pygame.quit()
sys.exit()
