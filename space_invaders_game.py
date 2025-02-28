import sys
import subprocess
import os

# Check and install pygame if needed before importing it
def check_pygame_installed():
    try:
        import pygame
        return True
    except ImportError:
        print("Pygame is not installed. Attempting to install it automatically...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
            print("Pygame successfully installed!")
            return True
        except Exception as e:
            print(f"Failed to install pygame: {e}")
            print("Please install pygame manually with:")
            print("  pip install pygame")
            
            # On Windows, keep the window open
            if os.name == 'nt':
                input("\nPress Enter to exit...")
            return False

# Try to install pygame if needed before proceeding
if not check_pygame_installed():
    sys.exit(1)

# Now that we know pygame is available, import it and other modules
import pygame
import random
import math
from space_invaders_classes import *

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)

# Screen dimensions
BREDDE = 800
HOYDE = 600
skjerm = pygame.display.set_mode((BREDDE, HOYDE))
pygame.display.set_caption("Space Invaders")

# Game state variables
VANSKELIGHETSGRAD = 1  # 1=Easy, 2=Medium, 3=Hard, 4=Impossible
VIS_MENY = True  # Show menu at startup
FULLSKJERM = False  # Start in windowed mode
LEVEL = 1  # Starting level for level-based mode
LEVEL_MODE = False  # Whether level-based mode is active

# Current game state
class Spilltilstand:
    MENY = 0
    SPILLER = 1
    GAME_OVER = 2
    LEVEL_COMPLETE = 3
    LEVEL_SELECT = 4
    QUIT_CONFIRM = 5
    HELP = 6  # New state for help screen
    SETTINGS = 7  # New state for settings screen

spilltilstand = Spilltilstand.MENY

# Variables for level selection menu
current_level_page = 0
levels_per_page = 9
max_level_pages = 5  # This allows selecting up to level 45

# Load configuration and high scores
game_config = load_config()
high_scores = load_high_scores()

# Initialize settings from config file or use defaults if not present
sound_volume = game_config.get("sound_volume", 0.5)  # Default sound volume (50%)
music_volume = game_config.get("music_volume", 0.07)  # Default music volume (7%)
fullscreen_enabled = game_config.get("fullscreen_enabled", False)  # Default fullscreen setting
mouse_control = game_config.get("mouse_control", False)  # Default for mouse control - ensure this is loaded

# Load images from assets folder
assets_folder = os.path.join(os.path.dirname(__file__), 'assets')
spiller_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller.png')).convert_alpha()
spiller2_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller2.png')).convert_alpha()
spiller3_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller3.png')).convert_alpha()
spiller4_bilde = pygame.image.load(os.path.join(assets_folder, 'spiller4.png')).convert_alpha()
fiende_bilde = pygame.image.load(os.path.join(assets_folder, 'fiende.png')).convert_alpha()
sterk_fiende_bilde = pygame.image.load(os.path.join(assets_folder, 'sterk_fiende.png')).convert_alpha()
liv_bilde = pygame.image.load(os.path.join(assets_folder, 'liv.png')).convert_alpha()  # Load the life image

# Load background image for main menu
try:
    bakgrunn_bilde = pygame.image.load(os.path.join(assets_folder, 'background.jpg')).convert()
    # Scale the background to fit the screen
    bakgrunn_bilde = pygame.transform.scale(bakgrunn_bilde, (BREDDE, HOYDE))
except Exception as e:
    print(f"Could not load background image: {e}")
    bakgrunn_bilde = None  # Set to None if loading fails

# Load sounds
try:
    skyte_lyd = pygame.mixer.Sound(os.path.join(assets_folder, 'thock.wav'))
    eksplosjon_lyd = pygame.mixer.Sound(os.path.join(assets_folder, 'eksplosjon.wav'))
    theme_song = pygame.mixer.Sound(os.path.join(assets_folder, 'theme_song.wav'))
    liv_lyd = pygame.mixer.Sound(os.path.join(assets_folder, 'life.wav'))  # Load the life pickup soundife pickup sound
except Exception as e:
    print(f"Could not load sound effects: {e}")
    # Fallback to generated sounds
    skyte_lyd = lag_skyte_lyd()
    eksplosjon_lyd = lag_eksplosjon_lyd()
    theme_song = pygame.mixer.Sound(bytearray([127] * 4000))
    liv_lyd = lag_bonus_lyd()  # Fallback for life sound

# Adjust volume based on saved settings
skyte_lyd.set_volume(sound_volume * 0.8)
eksplosjon_lyd.set_volume(sound_volume * 1.2)
liv_lyd.set_volume(sound_volume)
# Generate bonus sound if not already defined
bonus_lyd = lag_bonus_lyd()
bonus_lyd.set_volume(sound_volume)
theme_song.set_volume(music_volume)

# Apply fullscreen setting if enabled in config
if fullscreen_enabled:
    skjerm = pygame.display.set_mode((BREDDE, HOYDE), pygame.FULLSCREEN)
else:
    skjerm = pygame.display.set_mode((BREDDE, HOYDE))

# Sprite groups
alle_sprites = pygame.sprite.Group()
fiende_gruppe = pygame.sprite.Group()
skudd_gruppe = pygame.sprite.Group()
bonus_gruppe = pygame.sprite.Group()
fiende_prosjektil_gruppe = pygame.sprite.Group()
star_gruppe = pygame.sprite.Group()

# Create stars for background
create_stars(star_gruppe, 100)

# Create player
spiller = Spiller(spiller_bilde)
alle_sprites.add(spiller)

# Start background music - plays in a loop
try:
    theme_song.play(loops=-1)
except Exception as e:
    print(f"Could not play background music: {e}")

# Score and multiplier system
poeng = 0
score_multiplier = 1.0
consecutive_hits = 0
aktive_skudd = []

# Load better font
try:
    # Try to load a sci-fi font, otherwise use system font
    font_path = os.path.join(assets_folder, 'nasalization-rg.ttf')
    if (os.path.exists(font_path)):
        game_font_small = pygame.font.Font(font_path, 18)
        game_font_medium = pygame.font.Font(font_path, 24)
        game_font_large = pygame.font.Font(font_path, 36)
        game_font_xlarge = pygame.font.Font(font_path, 48)  # Extra large font for title
    else:
        # Fallback to another sci-fi-like font if available
        available_fonts = pygame.font.get_fonts()
        if 'courier' in available_fonts:
            game_font_small = pygame.font.SysFont('courier', 18)
            game_font_medium = pygame.font.SysFont('courier', 24)
            game_font_large = pygame.font.SysFont('courier', 36)
        else:
            # Fallback to standard font
            game_font_small = pygame.font.SysFont('arial', 18)
            game_font_medium = pygame.font.SysFont('arial', 24)
            game_font_large = pygame.font.SysFont('arial', 36)
        game_font_xlarge = pygame.font.SysFont('arial', 48)  # Extra large font for fallback
    # Define menu fonts - these are needed for the menu UI
    meny_font = game_font_medium  # For menu headers and options
    info_font = game_font_small   # For smaller informational text
except Exception as e:
    print(f"Could not load font: {e}")
    game_font_small = pygame.font.SysFont('arial', 18)
    game_font_medium = pygame.font.SysFont('arial', 24)
    game_font_large = pygame.font.SysFont('arial', 36)
    game_font_xlarge = pygame.font.SysFont('arial', 48)
    # Set the menu fonts even when using fallback
    meny_font = game_font_medium
    info_font = game_font_small

# Clock
klokke = pygame.time.Clock()

# Bonus timer
bonus_timer = pygame.time.get_ticks()
bonus_forsinkelse = 15000  # 15 seconds

# Check for level completion
def check_level_complete(LEVEL, poeng, LEVEL_MODE, VANSKELIGHETSGRAD, high_scores):
    if LEVEL_MODE:
        level_reqs = set_level_requirements(LEVEL)
        if poeng >= level_reqs["target_score"]:
            check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE)
            
            new_level = LEVEL + 1
            
            # Update max reached level
            game_config = load_config()
            weapon_unlocked = False
            
            if new_level > game_config["max_level_reached"]:
                game_config["max_level_reached"] = new_level
                
                # Check for new skins based on level
                if new_level == 5 and "level5_skin" not in game_config["unlocked_skins"]:
                    game_config["unlocked_skins"].append("level5_skin")
                
                # Check for special milestones
                # Only set weapon_unlocked to True if the shotgun is being unlocked for the first time
                if new_level == 6 and not game_config.get("shotgun_unlocked", False):
                    weapon_unlocked = True
                    game_config["shotgun_unlocked"] = True
                
                # Save the config to file
                save_config(game_config)
                
                # Update the running game's config reference to match the changes
                globals()["game_config"] = game_config
            
            return True, new_level, weapon_unlocked
    
    return False, LEVEL, False

# Game loop
spillkjorer = True

# Flag to show shotgun unlock notification
show_shotgun_unlock = False

# Settings variables
sound_volume = 0.5  # Default sound volume (50%)
music_volume = 0.07  # Default music volume (7%)
fullscreen_enabled = False  # Default fullscreen setting

# Game state variables for Help screen pagination
help_current_page = 0
help_max_pages = 2  # Two pages: game modes and controls (including mouse controls)

# Variables for help screen scrolling
help_scroll_y = 0  # Vertical scroll position
help_scroll_speed = 20  # Pixels to scroll per key press
help_content_height = 800  # Will be calculated based on actual content

while spillkjorer:
    # Maintain correct FPS
    klokke.tick(60)
    
    # Events
    for hendelse in pygame.event.get():
        if hendelse.type == pygame.QUIT:
            spillkjorer = False
        # Move the mouse button handling inside the event loop
        elif hendelse.type == pygame.MOUSEBUTTONDOWN:
            # Mouse control actions - only work if mouse_control is enabled and in gameplay
            if mouse_control and spilltilstand == Spilltilstand.SPILLER:
                if hendelse.button == 1:  # Left mouse button
                    # Fire laser
                    spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "normal")
                elif hendelse.button == 3:  # Right mouse button
                    # If shotgun is unlocked, fire shotgun
                    if game_config["max_level_reached"] > 5:
                        spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "shotgun")
                elif hendelse.button == 2:  # Middle mouse button
                    # If whip is unlocked and charged, use it
                    if game_config["max_level_reached"] >= 10 and spiller.whip_charge >= spiller.whip_charge_threshold:
                        spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "electric whip")
        elif hendelse.type == pygame.KEYDOWN:
            # Toggle fullscreen with F key
            if hendelse.key == pygame.K_f:
                FULLSKJERM = not FULLSKJERM
                if FULLSKJERM:
                    skjerm = pygame.display.set_mode((BREDDE, HOYDE), pygame.FULLSCREEN)
                else:
                    skjerm = pygame.display.set_mode((BREDDE, HOYDE))
                
                # Save fullscreen setting to config
                game_config["fullscreen_enabled"] = fullscreen_enabled
                save_config(game_config)
            
            # In menu state
            if spilltilstand == Spilltilstand.MENY:
                if hendelse.key == pygame.K_1:
                    VANSKELIGHETSGRAD = 1
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                    # Reset score and multiplier
                    poeng = 0
                    score_multiplier = 1.0
                    consecutive_hits = 0
                    spiller.liv = 3
                elif hendelse.key == pygame.K_2:
                    VANSKELIGHETSGRAD = 2
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                    # Reset score and multiplier
                    poeng = 0
                    score_multiplier = 1.0
                    consecutive_hits = 0
                    spiller.liv = 3
                elif hendelse.key == pygame.K_3:
                    VANSKELIGHETSGRAD = 3
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                    # Reset score and multiplier
                    poeng = 0
                    score_multiplier = 1.0
                    consecutive_hits = 0
                    spiller.liv = 3
                elif hendelse.key == pygame.K_4 and game_config["unlock_impossible"]:
                    VANSKELIGHETSGRAD = 4
                    LEVEL_MODE = False
                    spilltilstand = Spilltilstand.SPILLER
                    VIS_MENY = False
                    opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                    # Reset score and multiplier
                    poeng = 0
                    score_multiplier = 1.0
                    consecutive_hits = 0
                    spiller.liv = 3
                elif hendelse.key == pygame.K_l:  # Level mode now goes to level selection
                    LEVEL_MODE = True
                    current_level_page = 0  # Reset to first page
                    spilltilstand = Spilltilstand.LEVEL_SELECT
                elif hendelse.key == pygame.K_h:
                    spilltilstand = Spilltilstand.HELP
                elif hendelse.key == pygame.K_i:  # New handler for settings screen
                    spilltilstand = Spilltilstand.SETTINGS
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
                        opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                        # Reset score and multiplier
                        poeng = 0
                        score_multiplier = 1.0
                        consecutive_hits = 0
                        spiller.liv = 3
            # During game
            elif spilltilstand == Spilltilstand.SPILLER:
                # Shoot with Space, W or up arrow
                if hendelse.key == pygame.K_SPACE or hendelse.key == pygame.K_w or hendelse.key == pygame.K_UP:
                    spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe)
                # Add escape key to bring up quit confirmation
                elif hendelse.key == pygame.K_ESCAPE:
                    spilltilstand = Spilltilstand.QUIT_CONFIRM
                # Weapon switching with number keys - with immediate whip firing for key 3
                elif hendelse.key == pygame.K_1:
                    spiller.switch_weapon('normal', game_config["max_level_reached"])
                elif hendelse.key == pygame.K_2:
                    spiller.switch_weapon('shotgun', game_config["max_level_reached"])
                elif hendelse.key == pygame.K_3:
                    # For whip, only fire if charged - don't switch to whip permanently
                    if game_config["max_level_reached"] >= 10 and spiller.whip_charge >= spiller.whip_charge_threshold:
                        # Store current weapon to return to after whip use
                        previous_weapon = spiller.current_weapon
                        
                        # Create whip animation
                        whip = ElectricWhip(spiller.rect.midtop, BREDDE, HOYDE)
                        alle_sprites.add(whip)
                        
                        # Play whip sound
                        skyte_lyd.play(maxtime=0, fade_ms=0)
                        
                        # Reset charge
                        spiller.whip_charge = 0
                        
                        # We don't keep the whip selected, immediately revert to previous weapon
                        spiller.current_weapon = previous_weapon
            # Add handling for quit confirmation
            elif spilltilstand == Spilltilstand.QUIT_CONFIRM:
                if hendelse.key == pygame.K_j or hendelse.key == pygame.K_y:  # Y or J for Yes
                    # Check for high score before exiting
                    check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE)
                    # Return to menu
                    spilltilstand = Spilltilstand.MENY
                    VIS_MENY = True
                elif hendelse.key == pygame.K_n or hendelse.key == pygame.K_ESCAPE:  # N or ESC to cancel
                    # Return to game
                    spilltilstand = Spilltilstand.SPILLER
            # Game over
            elif spilltilstand == Spilltilstand.GAME_OVER:
                if hendelse.key == pygame.K_RETURN:
                    # Go back to the menu to select difficulty again
                    spilltilstand = Spilltilstand.MENY
                    VIS_MENY = True
            # Level completed
            elif spilltilstand == Spilltilstand.LEVEL_COMPLETE:
                if hendelse.key == pygame.K_RETURN:
                    # Start next level
                    spilltilstand = Spilltilstand.SPILLER
                    opprett_fiender(LEVEL_MODE, LEVEL, VANSKELIGHETSGRAD, fiende_bilde, sterk_fiende_bilde, alle_sprites, fiende_gruppe)
                    # Reset score for new level
                    poeng = 0
                    score_multiplier = 1.0
                    consecutive_hits = 0
                    spiller.liv = 3
            elif spilltilstand == Spilltilstand.HELP:
                if hendelse.key == pygame.K_ESCAPE or hendelse.key == pygame.K_h:  # Allow both ESC and H to exit
                    spilltilstand = Spilltilstand.MENY
                    help_scroll_y = 0  # Reset scroll position when leaving help
                elif hendelse.key == pygame.K_DOWN:
                    # Scroll down
                    help_scroll_y = min(help_scroll_y + help_scroll_speed, max(0, help_content_height - (help_box_height - 100)))
                elif hendelse.key == pygame.K_UP:
                    # Scroll up
                    help_scroll_y = max(0, help_scroll_y - help_scroll_speed)
            # Settings panel
            elif spilltilstand == Spilltilstand.SETTINGS:
                if hendelse.key == pygame.K_ESCAPE or hendelse.key == pygame.K_i:  # ESC or I to exit settings
                    spilltilstand = Spilltilstand.MENY
                    
                # Volume controls
                elif hendelse.key == pygame.K_1:  # Decrease sound volume
                    sound_volume = max(0.0, sound_volume - 0.1)
                    skyte_lyd.set_volume(sound_volume * 0.8)  # 80% of master volume
                    eksplosjon_lyd.set_volume(sound_volume * 1.2)  # 120% of master volume
                    liv_lyd.set_volume(sound_volume)
                    bonus_lyd.set_volume(sound_volume)
                    
                    # Save sound volume to config
                    game_config["sound_volume"] = sound_volume
                    save_config(game_config)
                    
                elif hendelse.key == pygame.K_2:  # Increase sound volume
                    sound_volume = min(1.0, sound_volume + 0.1)
                    skyte_lyd.set_volume(sound_volume * 0.8)
                    eksplosjon_lyd.set_volume(sound_volume * 1.2)
                    liv_lyd.set_volume(sound_volume)
                    bonus_lyd.set_volume(sound_volume)
                    
                    # Save sound volume to config
                    game_config["sound_volume"] = sound_volume
                    save_config(game_config)
                    
                elif hendelse.key == pygame.K_3:  # Decrease music volume
                    music_volume = max(0.0, music_volume - 0.01)
                    theme_song.set_volume(music_volume)
                    
                    # Save music volume to config
                    game_config["music_volume"] = music_volume
                    save_config(game_config)
                    
                elif hendelse.key == pygame.K_4:  # Increase music volume
                    music_volume = min(0.2, music_volume + 0.01)
                    theme_song.set_volume(music_volume)
                    
                    # Save music volume to config
                    game_config["music_volume"] = music_volume
                    save_config(game_config)
                    
                elif hendelse.key == pygame.K_5:  # Toggle mouse control - now using key 5
                    mouse_control = not mouse_control
                    
                    # Save mouse control setting to config
                    game_config["mouse_control"] = mouse_control
                    save_config(game_config)
    
    # Update
    star_gruppe.update()  # Update stars first
    
    if spilltilstand == Spilltilstand.SPILLER:
        # Update player with current score and skin images - PASS mouse_control PARAMETER
        spiller_bilder = (spiller_bilde, spiller2_bilde, spiller3_bilde, spiller4_bilde)
        spiller.update(poeng, spiller_bilder, mouse_control)  # Add mouse_control parameter here!
        
        # Remove the code checking for weapon_upgraded since we're now using shotgun_unlocked instead
        
        # Update enemies
        for enemy in fiende_gruppe:
            if VANSKELIGHETSGRAD == 4:
                enemy.update(VANSKELIGHETSGRAD, alle_sprites, fiende_prosjektil_gruppe)
            else:
                enemy.update()
        
        # Update shots and explosions
        for shot in skudd_gruppe:
            shot.update(lambda: globals().update(zip(['score_multiplier', 'consecutive_hits'], reset_multiplier())))
        
        # Update other sprites with special handling for ElectricWhip
        for sprite in alle_sprites:
            if sprite not in skudd_gruppe and sprite not in fiende_gruppe and sprite is not spiller:
                if isinstance(sprite, ElectricWhip):
                    # Pass fiende_gruppe for collision detection - call correctly with 4 arguments
                    sprite.update(fiende_gruppe, alle_sprites, eksplosjon_lyd, score_multiplier)
                    
                    # Process damage and scoring for hit enemies
                    for fiende in sprite.enemies_hit:
                        if fiende in fiende_gruppe:  # Make sure enemy still exists
                            # Increase score multiplier for every hit
                            score_multiplier, consecutive_hits = increase_multiplier(score_multiplier, consecutive_hits)
                            point_gain = int(fiende.point_value * score_multiplier)
                            poeng += point_gain
                            
                            # Create explosion at enemy position
                            eksplosjon = Eksplosjon(fiende.rect.center)
                            alle_sprites.add(eksplosjon)
                            
                            # Determine enemy type before removal
                            is_strong_enemy = isinstance(fiende, SterkFiende)
                            
                            # Remove the enemy
                            fiende.kill()
                            
                            # Create a replacement enemy based on original type
                            if is_strong_enemy:
                                ny_fiende = SterkFiende(sterk_fiende_bilde, VANSKELIGHETSGRAD)
                            else:
                                ny_fiende = Fiende(fiende_bilde, VANSKELIGHETSGRAD)
                                
                            alle_sprites.add(ny_fiende)
                            fiende_gruppe.add(ny_fiende)
                else:
                    sprite.update()
        
        # Get current high score
        current_high_score = get_current_high_score(VANSKELIGHETSGRAD, LEVEL, LEVEL_MODE, high_scores)
        
        # Check for collisions between shots and enemies
        treff = pygame.sprite.groupcollide(skudd_gruppe, fiende_gruppe, True, False)
        processed_enemies = set()
        for skudd, fiender in treff.items():
            skudd.truffet_fiende = True
            if isinstance(skudd, ExplosiveShot):
                points, enemy_type = skudd.explode(alle_sprites, fiende_gruppe, poeng, score_multiplier, eksplosjon_lyd)
                poeng += points
                continue
            for fiende in fiender:
                if fiende in processed_enemies:
                    continue
                processed_enemies.add(fiende)
                fiende.treff += 1
                if fiende.treff >= fiende.max_treff:
                    score_multiplier, consecutive_hits = increase_multiplier(score_multiplier, consecutive_hits)
                    point_gain = int(fiende.point_value * score_multiplier)
                    poeng += point_gain
                    # Increase electric whip charge with earned points
                    spiller.whip_charge = min(spiller.whip_charge + point_gain, spiller.whip_charge_threshold)
                    if not isinstance(skudd, ExplosiveShot):
                        eksplosjon = Eksplosjon(fiende.rect.center)
                        alle_sprites.add(eksplosjon)
                        eksplosjon_lyd.play(maxtime=0, fade_ms=0)
                    fiende.kill()
                    # For strong enemies, do not spawn a replacement; for others, always spawn normal enemy
                    if isinstance(fiende, SterkFiende):
                        ny_fiende = Fiende(fiende_bilde, VANSKELIGHETSGRAD)
                    else:
                        ny_fiende = Fiende(fiende_bilde, VANSKELIGHETSGRAD)
                    alle_sprites.add(ny_fiende)
                    fiende_gruppe.add(ny_fiende)
        
        # In Impossible mode, check for collisions between player and enemy projectiles
        if VANSKELIGHETSGRAD == 4:
            treff_prosjektil = pygame.sprite.spritecollide(spiller, fiende_prosjektil_gruppe, True)
            for hit in treff_prosjektil:
                spiller.liv -= 1
                if spiller.liv <= 0:
                    spilltilstand = Spilltilstand.GAME_OVER
                    check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE)
        
        # Check if enemies have reached the bottom
        for fiende in fiende_gruppe:
            if fiende.rect.top > HOYDE:
                fiende.rect.x = random.randrange(BREDDE - fiende.rect.width)
                fiende.rect.y = random.randrange(-100, -40)
                
                # Adjust speed based on difficulty
                if VANSKELIGHETSGRAD == 1:
                    fiende.hastighet = random.randrange(1, 2)
                elif VANSKELIGHETSGRAD == 2:
                    fiende.hastighet = random.randrange(1, 3)
                else:  # Level 3 or higher
                    fiende.hastighet = random.randrange(1, 4)
                spiller.liv -= 1
                if spiller.liv <= 0:
                    spilltilstand = Spilltilstand.GAME_OVER
                    check_and_update_highscore(poeng, VANSKELIGHETSGRAD, high_scores, LEVEL, LEVEL_MODE)
        
        # Generate bonus
        naa = pygame.time.get_ticks()
        if naa - bonus_timer > bonus_forsinkelse:
            bonus_timer = naa
            bonus = Kraftbonus(liv_bilde)  # Pass the life image to the Kraftbonus constructor
            alle_sprites.add(bonus)
            bonus_gruppe.add(bonus)
        
        # Check for collisions between player and bonus
        treff_bonus = pygame.sprite.spritecollide(spiller, bonus_gruppe, True)
        for hit in treff_bonus:
            liv_lyd.play(maxtime=0, fade_ms=0)  # Play the life sound instead of bonus sound
            spiller.liv += 1
            # Visual effect when bonus is collected
            for i in range(10):
                vinkel = random.uniform(0, 2 * math.pi)
                hastighet = random.uniform(1, 3)
                partikkel = Partikkel(hit.rect.center, vinkel, hastighet)
                alle_sprites.add(partikkel)
        
        # Check for level completion
        level_complete, new_level, shotgun_unlocked = check_level_complete(LEVEL, poeng, LEVEL_MODE, VANSKELIGHETSGRAD, high_scores)
        if level_complete:
            LEVEL = new_level
            spilltilstand = Spilltilstand.LEVEL_COMPLETE
            
            # If shotgun was unlocked, set flag to show notification
            if shotgun_unlocked:
                show_shotgun_unlock = True
    
    # Handle mouse events when mouse control is enabled
    elif mouse_control and spilltilstand == Spilltilstand.SPILLER:
        if hendelse.type == pygame.MOUSEBUTTONDOWN:
            if hendelse.button == 1:  # Left mouse button
                # Fire laser
                spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "normal")
            elif hendelse.button == 3:  # Right mouse button
                # If shotgun is unlocked, fire shotgun
                if game_config["max_level_reached"] > 5:
                    spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "shotgun")
            elif hendelse.button == 2:  # Middle mouse button
                # If whip is unlocked and charged, use it
                if game_config["max_level_reached"] >= 10 and spiller.whip_charge >= spiller.whip_charge_threshold:
                    spiller.skyt(alle_sprites, skudd_gruppe, aktive_skudd, skyte_lyd, VANSKELIGHETSGRAD, fiende_gruppe, "electric whip")

    # Draw / render
    if spilltilstand == Spilltilstand.MENY and bakgrunn_bilde is not None:
        # Use background image for main menu
        skjerm.blit(bakgrunn_bilde, (0, 0))
    else:
        # Use black background for other game states
        skjerm.fill(SVART)
    
    # Show stars (only when not in main menu)
    if spilltilstand != Spilltilstand.MENY:
        star_gruppe.draw(skjerm)
    
    # Show menu to choose difficulty
    if spilltilstand == Spilltilstand.MENY:
        # Use a larger title font positioned higher up
        tittel_font = game_font_xlarge
        
        # Title - positioned higher
        tittel = tittel_font.render("SPACE INVADERS", True, HVIT)
        skjerm.blit(tittel, (BREDDE//2 - tittel.get_width()//2, 35))  # Moved from 50 to 35
        
        # Define colors - use whiter/brighter text for better contrast
        option_color = (240, 240, 240)  # Whiter text for options
        info_color = (220, 220, 220)    # Brighter gray for info text
        header_color = (250, 250, 250)  # Almost pure white for headers
        
        # Pastel colors for game modes
        pastel_colors = {
            "easy": (180, 230, 220),    # Soft mint
            "medium": (230, 220, 180),  # Soft yellow
            "hard": (230, 180, 180),    # Soft pink
            "impossible": (180, 180, 230), # Soft blue
            "level": (210, 180, 230)    # Soft purple
        }
        
        # Menu panels
        left_panel_width = BREDDE * 0.5
        left_center = left_panel_width // 2
        right_center = left_panel_width + (BREDDE - left_panel_width) // 2
        
        # Add headers for both sections
        modes_title = game_font_medium.render("GAME MODES", True, header_color)
        skjerm.blit(modes_title, (left_center - modes_title.get_width()//2, 120))
        
        scores_title = game_font_medium.render("HIGH SCORES", True, header_color)
        skjerm.blit(scores_title, (right_center - scores_title.get_width()//2, 120))
        
        # Create grid for game modes - smaller boxes since descriptions are removed
        grid_top = 165
        grid_row_height = 70  # Reduced from 100
        grid_col_width = left_panel_width * 0.45
        grid_margin = 10
        grid_padding = 10
        
        # Draw the game modes box background - ADJUST HEIGHT AND WIDTH
        modes_box_width = left_panel_width * 0.98  # Increased from 0.95 to 0.98 for more width
        modes_box_height = grid_row_height * 3.6  # Reduced from 3.8 to 3.6 for less height
        modes_box_x = left_center - modes_box_width // 2
        modes_box_y = grid_top - grid_margin
        pygame.draw.rect(skjerm, (40, 40, 50), (modes_box_x, modes_box_y, modes_box_width, modes_box_height))
        pygame.draw.rect(skjerm, (60, 60, 70), (modes_box_x, modes_box_y, modes_box_width, modes_box_height), 2)
        
        # Calculate positions for grid cells
        cell_positions = [
            # Row 1
            (left_center - grid_col_width - grid_margin//2, grid_top),  # Cell 1 (Top left)
            (left_center + grid_margin//2, grid_top),                   # Cell 2 (Top right)
            # Row 2
            (left_center - grid_col_width - grid_margin//2, grid_top + grid_row_height),  # Cell 3 (Middle left)
            (left_center + grid_margin//2, grid_top + grid_row_height),                   # Cell 4 (Middle right)
            # Row 3 (spans both columns)
            (left_center - grid_col_width * 0.5, grid_top + grid_row_height * 2)          # Cell 5 (Bottom)
        ]
        
        # Mode 1: Easy (Top left) - Only show name and key
        easy_color = pastel_colors["easy"]
        pygame.draw.rect(skjerm, (40, 60, 50), (cell_positions[0][0], cell_positions[0][1], grid_col_width, grid_row_height - grid_margin))
        pygame.draw.rect(skjerm, easy_color, (cell_positions[0][0], cell_positions[0][1], grid_col_width, grid_row_height - grid_margin), 2)
        
        valg1_text = "Lett [1]"
        valg1 = meny_font.render(valg1_text, True, easy_color)  # Use easy_color instead of option_color
        skjerm.blit(valg1, (cell_positions[0][0] + grid_col_width//2 - valg1.get_width()//2, 
                           cell_positions[0][1] + (grid_row_height - grid_margin)//2 - valg1.get_height()//2))
        
        # Mode 2: Medium (Top right) - Only show name and key
        medium_color = pastel_colors["medium"]
        pygame.draw.rect(skjerm, (60, 50, 40), (cell_positions[1][0], cell_positions[1][1], grid_col_width, grid_row_height - grid_margin))
        pygame.draw.rect(skjerm, medium_color, (cell_positions[1][0], cell_positions[1][1], grid_col_width, grid_row_height - grid_margin), 2)
        
        valg2_text = "Middels [2]"
        valg2 = meny_font.render(valg2_text, True, medium_color)  # Use medium_color instead of option_color
        skjerm.blit(valg2, (cell_positions[1][0] + grid_col_width//2 - valg2.get_width()//2, 
                           cell_positions[1][1] + (grid_row_height - grid_margin)//2 - valg2.get_height()//2))
        
        # Mode 3: Hard (Middle left) - Only show name and key
        hard_color = pastel_colors["hard"]
        pygame.draw.rect(skjerm, (60, 40, 40), (cell_positions[2][0], cell_positions[2][1], grid_col_width, grid_row_height - grid_margin))
        pygame.draw.rect(skjerm, hard_color, (cell_positions[2][0], cell_positions[2][1], grid_col_width, grid_row_height - grid_margin), 2)
        
        valg3_text = "Vanskelig [3]"
        valg3 = meny_font.render(valg3_text, True, hard_color)  # Use hard_color instead of option_color
        skjerm.blit(valg3, (cell_positions[2][0] + grid_col_width//2 - valg3.get_width()//2, 
                           cell_positions[2][1] + (grid_row_height - grid_margin)//2 - valg3.get_height()//2))
        
        # Mode 4: Impossible (Middle right) - Always show but gray out if not unlocked
        impossible_color = pastel_colors["impossible"] if game_config["unlock_impossible"] else (120, 120, 120)
        pygame.draw.rect(skjerm, (40, 40, 60), (cell_positions[3][0], cell_positions[3][1], grid_col_width, grid_row_height - grid_margin))
        pygame.draw.rect(skjerm, impossible_color, (cell_positions[3][0], cell_positions[3][1], grid_col_width, grid_row_height - grid_margin), 2)
        
        valg4_text = "Umulig [4]"
        if not game_config["unlock_impossible"]:
            valg4_text = "Umulig [Låst]"
        
        valg4 = meny_font.render(valg4_text, True, impossible_color)
        skjerm.blit(valg4, (cell_positions[3][0] + grid_col_width//2 - valg4.get_width()//2, 
                           cell_positions[3][1] + (grid_row_height - grid_margin)//2 - valg4.get_height()//2))
        
        # Level Mode (Bottom row spanning both columns) - Keep description
        level_color = pastel_colors["level"]
        level_cell_width = grid_col_width * 2 + grid_margin
        # Center the level mode box properly
        level_cell_x = left_center - level_cell_width//2
        
        # Reset to a more reasonable height for the button itself
        level_cell_height = (grid_row_height - grid_margin) * 1.6  # Back to previous height
        
        pygame.draw.rect(skjerm, (50, 40, 60), (level_cell_x, cell_positions[4][1], level_cell_width, level_cell_height))
        pygame.draw.rect(skjerm, level_color, (level_cell_x, cell_positions[4][1], level_cell_width, level_cell_height), 2)
        
        level_mode_text = "Level Mode [L]"
        level_mode_valg = meny_font.render(level_mode_text, True, level_color)  # Use level_color instead of option_color
        skjerm.blit(level_mode_valg, (left_center - level_mode_valg.get_width()//2, 
                                     cell_positions[4][1] + 15))
        
        # Keep the description for Level Mode only
        if game_config["max_level_reached"] > 1:
            level_continue_text = f"(Fortsett fra level {game_config['max_level_reached']})"
            level_continue = info_font.render(level_continue_text, True, level_color)
            skjerm.blit(level_continue, (left_center - level_continue.get_width()//2, 
                                        cell_positions[4][1] + 45))  # Fixed position with more space
        
        # High scores section - MATCH POSITION AND SIZE WITH GAME MODES BOX
        hs_box_width = modes_box_width * 0.95  # Keep the 0.95 width
        hs_box_height = modes_box_height  # Keep the same height as modes box
        hs_box_x = right_center - hs_box_width // 2
        hs_box_y = grid_top - grid_margin  # Set to the exact same y-position as modes box
        
        pygame.draw.rect(skjerm, (40, 40, 50), (hs_box_x, hs_box_y, hs_box_width, hs_box_height))
        pygame.draw.rect(skjerm, (60, 60, 70), (hs_box_x, hs_box_y, hs_box_width, hs_box_height), 2)
        
        # Remove the inner title and start scores higher in the box
        # Calculate even spacing for 4 scores across the entire box height
        score_spacing = hs_box_height // 5  # Divide by 5 for 4 scores with some margin
        hs_y = hs_box_y + score_spacing // 2 + 10  # Start with a bit of padding from the top
        
        for diff, name in [(1, "Lett"), (2, "Middels"), (3, "Vanskelig"), (4, "Umulig")]:
            diff_key = {1: "easy", 2: "medium", 3: "hard", 4: "impossible"}[diff]
            score = high_scores.get(diff_key, 0)
            
            # Use matching pastel colors for high scores
            color = pastel_colors[diff_key]
            
            # Keep using meny_font for larger scores
            score_text = meny_font.render(f"{name}: {score}", True, color)
            skjerm.blit(score_text, (right_center - score_text.get_width()//2, hs_y))
            hs_y += score_spacing  # Use calculated spacing
        
        # Bottom panel - weapon display in a horizontal row
        weapons_title = game_font_medium.render("VÅPEN", True, header_color)
        weapons_y = HOYDE - 150  # Increased from 130 to 150 for more space
        skjerm.blit(weapons_title, (BREDDE//2 - weapons_title.get_width()//2, weapons_y))
        
        # Create weapon display panels - now in horizontal row
        weapon_panel_width = 180  # A bit smaller than before
        weapon_panel_height = 45
        weapon_spacing = 20
        weapons_count = 3
        total_width = weapons_count * weapon_panel_width + (weapons_count-1) * weapon_spacing
        weapons_start_x = (BREDDE - total_width) // 2
        
        # Standard laser weapon (always unlocked) - match with easy color
        laser_panel_x = weapons_start_x
        laser_panel_y = weapons_y + 35
        
        laser_bg_color = (40, 60, 50)
        laser_border_color = pastel_colors["easy"]
        laser_text_color = pastel_colors["easy"]
        
        # Draw laser weapon panel
        pygame.draw.rect(skjerm, laser_bg_color, (laser_panel_x, laser_panel_y, weapon_panel_width, weapon_panel_height))
        pygame.draw.rect(skjerm, laser_border_color, (laser_panel_x, laser_panel_y, weapon_panel_width, weapon_panel_height), 2)
        
        # Laser weapon name and key binding - new format
        laser_name = info_font.render("Laser [1]", True, laser_text_color)
        skjerm.blit(laser_name, (laser_panel_x + weapon_panel_width//2 - laser_name.get_width()//2, 
                                laser_panel_y + weapon_panel_height//2 - laser_name.get_height()//2))
        
        # Shotgun weapon - match with medium color
        shotgun_panel_x = laser_panel_x + weapon_panel_width + weapon_spacing
        shotgun_panel_y = laser_panel_y
        
        shotgun_unlocked = game_config["max_level_reached"] > 5
        
        if shotgun_unlocked:
            shotgun_bg_color = (60, 50, 40)
            shotgun_border_color = pastel_colors["medium"]
            shotgun_text_color = pastel_colors["medium"]
            shotgun_text = "Hagle [2]"
        else:
            shotgun_bg_color = (50, 50, 50)
            shotgun_border_color = (120, 120, 120)
            shotgun_text_color = (150, 150, 150)
            shotgun_text = "Hagle [Lvl 5+]"
        
        # Draw shotgun weapon panel
        pygame.draw.rect(skjerm, shotgun_bg_color, (shotgun_panel_x, shotgun_panel_y, weapon_panel_width, weapon_panel_height))
        pygame.draw.rect(skjerm, shotgun_border_color, (shotgun_panel_x, shotgun_panel_y, weapon_panel_width, weapon_panel_height), 2)
        
        shotgun_name = info_font.render(shotgun_text, True, shotgun_text_color)
        skjerm.blit(shotgun_name, (shotgun_panel_x + weapon_panel_width//2 - shotgun_name.get_width()//2, 
                                  shotgun_panel_y + weapon_panel_height//2 - shotgun_name.get_height()//2))
        
        # Electric whip weapon - match with hard color
        whip_panel_x = shotgun_panel_x + weapon_panel_width + weapon_spacing
        whip_panel_y = laser_panel_y
        
        whip_unlocked = game_config["max_level_reached"] >= 10
        
        if whip_unlocked:
            whip_bg_color = (60, 40, 40)
            whip_border_color = pastel_colors["hard"]
            whip_text_color = pastel_colors["hard"]
            whip_text = "Pisk [3]"
        else:
            whip_bg_color = (50, 50, 50)
            whip_border_color = (120, 120, 120)
            whip_text_color = (150, 150, 150)
            whip_text = "Pisk [Lvl 10+]"
        
        # Draw whip weapon panel
        pygame.draw.rect(skjerm, whip_bg_color, (whip_panel_x, whip_panel_y, weapon_panel_width, weapon_panel_height))
        pygame.draw.rect(skjerm, whip_border_color, (whip_panel_x, whip_panel_y, weapon_panel_width, weapon_panel_height), 2)
        
        whip_name = info_font.render(whip_text, True, whip_text_color)
        skjerm.blit(whip_name, (whip_panel_x + weapon_panel_width//2 - whip_name.get_width()//2, 
                               whip_panel_y + weapon_panel_height//2 - whip_name.get_height()//2))
        
        # Add both copyright and help text at the bottom
        copyright_font = pygame.font.SysFont('arial', 14)
        copyright_text = "kkarlsen_06 2025 All Rights Reserved"
        copyright = copyright_font.render(copyright_text, True, (150, 150, 150))
        
        help_text = "Help [H]"
        help = copyright_font.render(help_text, True, (200, 200, 200))
        
        settings_text = "Settings [I]"
        settings = copyright_font.render(settings_text, True, (200, 200, 200))
        
        # Position help text and settings text with more space between elements
        skjerm.blit(copyright, (100, HOYDE - 25))
        skjerm.blit(help, (BREDDE - 250, HOYDE - 25))
        skjerm.blit(settings, (BREDDE - 120, HOYDE - 25))

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
        
        # Add weapon unlock indicators somewhere in the UI
        weapon_info_y = info_box_y + info_box_height + 20
        
        if game_config["max_level_reached"] > 5:
            shotgun_text = game_font_small.render("Hagle (våpen) låst opp! Bruk tast 2", True, (255, 165, 0))
            skjerm.blit(shotgun_text, (grid_x_start + 20, weapon_info_y))
            weapon_info_y += 30
        
        if game_config["max_level_reached"] >= 10:
            whip_text = game_font_small.render("Elektrisk pisk (våpen) låst opp! Bruk tast 3", True, (0, 200, 255))
            skjerm.blit(whip_text, (grid_x_start + 20, weapon_info_y))

    elif spilltilstand == Spilltilstand.HELP:
        # Use black background
        skjerm.fill(SVART)
        
        # Show stars in background
        star_gruppe.draw(skjerm)
        
        # Help screen title
        help_title = game_font_large.render("SPILLMODUSER - HJELP", True, HVIT)
        skjerm.blit(help_title, (BREDDE//2 - help_title.get_width()//2, 50))
        
        # Create a semi-transparent background for content
        help_box_width = BREDDE * 0.8
        help_box_height = HOYDE * 0.8
        help_box_x = BREDDE//2 - help_box_width//2
        help_box_y = 100
        
        # Draw box
        pygame.draw.rect(skjerm, (40, 40, 50, 180), (help_box_x, help_box_y, help_box_width, help_box_height))
        pygame.draw.rect(skjerm, HVIT, (help_box_x, help_box_y, help_box_width, help_box_height), 2)
        
        # Create a clipping rect for the content area
        content_rect = pygame.Rect(help_box_x + 20, help_box_y + 20, help_box_width - 40, help_box_height - 50)
        
        # Create a surface for drawing all content
        content_surface = pygame.Surface((content_rect.width, 1500), pygame.SRCALPHA)
        content_surface.fill((0, 0, 0, 0))  # Transparent background
        
        # Now draw all the help content onto the content_surface
        content_y = 0  # Starting position in the virtual content
        line_spacing = 30  # Spacing between lines
        section_spacing = 50  # Spacing between sections
        
        # Game Modes Section
        page_title = game_font_medium.render("Spillmoduser", True, (200, 200, 255))
        content_surface.blit(page_title, (content_rect.width//2 - page_title.get_width()//2, content_y))
        content_y += 40
        
        # Easy mode
        easy_title = game_font_medium.render("Lett [1]", True, pastel_colors["easy"])
        content_surface.blit(easy_title, (20, content_y))
        content_y += 30
        easy_desc = game_font_small.render("Sakte fiender, siktelinje som hjelper med sikting", True, HVIT)
        content_surface.blit(easy_desc, (20, content_y))
        content_y += line_spacing
        
        # Medium mode
        medium_title = game_font_medium.render("Middels [2]", True, pastel_colors["medium"])
        content_surface.blit(medium_title, (20, content_y))
        content_y += 30
        medium_desc = game_font_small.render("Medium hastighet på fiender, siktelinje tilgjengelig", True, HVIT)
        content_surface.blit(medium_desc, (20, content_y))
        content_y += line_spacing
        
        # Hard mode
        hard_title = game_font_medium.render("Vanskelig [3]", True, pastel_colors["hard"])
        content_surface.blit(hard_title, (20, content_y))
        content_y += 30
        hard_desc = game_font_small.render("Raske fiender, ingen siktelinje for å hjelpe med sikting", True, HVIT)
        content_surface.blit(hard_desc, (20, content_y))
        content_y += line_spacing
        
        # Impossible mode
        imp_title = game_font_medium.render("Umulig [4]", True, pastel_colors["impossible"])
        content_surface.blit(imp_title, (20, content_y))
        content_y += 30
        imp_desc = game_font_small.render("Fiender skyter tilbake! Ekstrem vanskelighetsgrad", True, HVIT)
        content_surface.blit(imp_desc, (20, content_y))
        content_y += line_spacing
        
        # Level mode
        level_title = game_font_medium.render("Level Mode [L]", True, pastel_colors["level"])
        content_surface.blit(level_title, (20, content_y))
        content_y += 30
        level_desc = game_font_small.render("Spill nivåer i rekkefølge. Nye våpen låses opp ved fremgang.", True, HVIT)
        content_surface.blit(level_desc, (20, content_y))
        content_y += section_spacing
        
        # Controls Section - Keyboard
        keyboard_title = game_font_medium.render("Tastatur Kontroller", True, (220, 220, 150))
        content_surface.blit(keyboard_title, (20, content_y))
        content_y += 40
        
        # Movement controls
        move_desc = game_font_small.render("Bevegelse: Piltaster eller A/D", True, HVIT)
        content_surface.blit(move_desc, (40, content_y))
        content_y += line_spacing
        
        # Shooting controls
        shoot_desc = game_font_small.render("Skyt: Mellomrom, W eller Pil opp", True, HVIT)
        content_surface.blit(shoot_desc, (40, content_y))
        content_y += line_spacing
        
        # Weapon switching
        weapons_desc = game_font_small.render("Bytt våpen: 1, 2, 3 (hvis tilgjengelig)", True, HVIT)
        content_surface.blit(weapons_desc, (40, content_y))
        content_y += line_spacing
        
        # Pause/menu
        pause_desc = game_font_small.render("Pause/meny: ESC", True, HVIT)
        content_surface.blit(pause_desc, (40, content_y))
        content_y += line_spacing
        
        # Fullscreen toggle
        full_desc = game_font_small.render("Fullskjerm: F", True, HVIT)
        content_surface.blit(full_desc, (40, content_y))
        content_y += section_spacing
        
        # Controls Section - Mouse
        mouse_title = game_font_medium.render("Musisk bevegelse", True, (150, 220, 150))
        content_surface.blit(mouse_title, (20, content_y))
        content_y += 40
        
        # Mouse movement
        mouse_move_desc = game_font_small.render("Bevegelse: Flytt musen horisontalt", True, HVIT)
        content_surface.blit(mouse_move_desc, (40, content_y))
        content_y += line_spacing
        
        # Mouse shooting options
        mouse_desc_1 = game_font_small.render("Venstre-klikk: Laser", True, HVIT)
        content_surface.blit(mouse_desc_1, (40, content_y))
        content_y += line_spacing
        
        mouse_desc_2 = game_font_small.render("Høyre-klikk: Hagle (om tilgjengelig)", True, HVIT)
        content_surface.blit(mouse_desc_2, (40, content_y))
        content_y += line_spacing
        
        mouse_desc_3 = game_font_small.render("Midtklikk: El-pisk (om ladet)", True, HVIT)
        content_surface.blit(mouse_desc_3, (40, content_y))
        content_y += section_spacing
        
        # How to enable mouse control
        enable_heading = game_font_medium.render("Aktivere musisk bevegelse", True, (200, 200, 200))
        content_surface.blit(enable_heading, (20, content_y))
        content_y += 40
        
        enable_desc = game_font_small.render("Gå til innstillinger [I] fra hovedmenyen og velg [5] Bytt", True, (200, 200, 200))
        content_surface.blit(enable_desc, (40, content_y))
        content_y += section_spacing
        
        # Weapons information
        weapons_info_title = game_font_medium.render("Våpeninformasjon", True, (220, 180, 180))
        content_surface.blit(weapons_info_title, (20, content_y))
        content_y += 40
        
        # Laser weapon
        laser_info = game_font_small.render("Laser: Standard våpen, presist og raskt", True, HVIT)
        content_surface.blit(laser_info, (40, content_y))
        content_y += line_spacing
        
        # Shotgun weapon
        shotgun_info = game_font_small.render("Hagle: Bred spredning, kort rekkevidde, låses opp i level 5+", True, HVIT)
        content_surface.blit(shotgun_info, (40, content_y))
        content_y += line_spacing
        
        # Electric whip weapon
        whip_info = game_font_small.render("Elektrisk pisk: Kraftig våpen med stor rekkevidde, låses opp i level 10+", True, HVIT)
        content_surface.blit(whip_info, (40, content_y))
        content_y += line_spacing
        
        # How to use whip
        whip_usage = game_font_small.render("Pisken lades opp når du skyter fiender. Bruk når fulladet for best effekt.", True, HVIT)
        content_surface.blit(whip_usage, (40, content_y))
        content_y += section_spacing
        
        # Store the actual content height for scrolling limits
        help_content_height = content_y
        
        # Draw the visible portion of the content
        skjerm.blit(content_surface, content_rect, 
                  (0, help_scroll_y, content_rect.width, content_rect.height))
        
        # Draw scroll indicators if needed
        if help_scroll_y > 0:
            # Up arrow indicator
            pygame.draw.polygon(skjerm, (200, 200, 200), 
                            [(help_box_x + help_box_width//2, help_box_y + 10),
                             (help_box_x + help_box_width//2 - 15, help_box_y + 25),
                             (help_box_x + help_box_width//2 + 15, help_box_y + 25)])
        
        if help_scroll_y < help_content_height - content_rect.height:
            # Down arrow indicator
            pygame.draw.polygon(skjerm, (200, 200, 200), 
                            [(help_box_x + help_box_width//2, help_box_y + help_box_height - 10),
                             (help_box_x + help_box_width//2 - 15, help_box_y + help_box_height - 25),
                             (help_box_x + help_box_width//2 + 15, help_box_y + help_box_height - 25)])
        
        # Back instruction - at the bottom
        back_text = game_font_small.render("Trykk ESC eller H for å gå tilbake", True, (200, 200, 200))
        skjerm.blit(back_text, (BREDDE//2 - back_text.get_width()//2, help_box_y + help_box_height + 10))
        
        # Remove the "Bruk piltastene..." navigation text

    elif spilltilstand == Spilltilstand.LEVEL_COMPLETE:
        # Draw a semi-transparent overlay for level complete
        overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Black with transparency
        skjerm.blit(overlay, (0, 0))
        
        # Create a dialog box
        dialog_width = 400
        dialog_height = 200
        dialog_x = BREDDE//2 - dialog_width//2
        dialog_y = HOYDE//2 - dialog_height//2
        
        # Draw dialog box
        pygame.draw.rect(skjerm, (50, 90, 60), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(skjerm, GRONN, (dialog_x, dialog_y, dialog_width, dialog_height), 2)
        
        # Level complete title
        level_title = game_font_large.render("LEVEL FULLFØRT!", True, GRONN)
        skjerm.blit(level_title, (BREDDE//2 - level_title.get_width()//2, dialog_y + 30))
        
        # Next level message
        if LEVEL > 1:
            next_level = game_font_medium.render(f"Level {LEVEL-1} fullført! Neste: Level {LEVEL}", True, HVIT)
            skjerm.blit(next_level, (BREDDE//2 - next_level.get_width()//2, dialog_y + 80))
        else:
            next_level = game_font_medium.render(f"Du går nå til Level {LEVEL}", True, HVIT)
            skjerm.blit(next_level, (BREDDE//2 - next_level.get_width()//2, dialog_y + 80))
            
        # If shotgun was unlocked, show special message
        if show_shotgun_unlock:
            shotgun_msg = game_font_medium.render("HAGLE VÅPEN LÅST OPP!", True, (255, 165, 0))
            skjerm.blit(shotgun_msg, (BREDDE//2 - shotgun_msg.get_width()//2, dialog_y + 120))
            
        # Press enter to continue
        continue_text = game_font_small.render("Trykk ENTER for å fortsette", True, HVIT)
        skjerm.blit(continue_text, (BREDDE//2 - continue_text.get_width()//2, dialog_y + 160))

    elif spilltilstand == Spilltilstand.SETTINGS:
        # Use black background
        skjerm.fill(SVART)
        
        # Show stars in background
        star_gruppe.draw(skjerm)
        
        # Settings screen title
        settings_title = game_font_large.render("INNSTILLINGER", True, HVIT)
        skjerm.blit(settings_title, (BREDDE//2 - settings_title.get_width()//2, 30))
        
        # Create a semi-transparent background for content - INCREASE HEIGHT
        settings_box_width = BREDDE * 0.7
        settings_box_height = HOYDE * 0.75  # Increased from 0.7 to have more space
        settings_box_x = BREDDE//2 - settings_box_width//2
        settings_box_y = 80
        
        # Draw box
        pygame.draw.rect(skjerm, (40, 40, 50, 200), (settings_box_x, settings_box_y, settings_box_width, settings_box_height))
        pygame.draw.rect(skjerm, (100, 100, 150), (settings_box_x, settings_box_y, settings_box_width, settings_box_height), 2)
        
        # Settings content
        y_pos = settings_box_y + 30
        line_spacing = 120
        
        # Sound effects volume
        sound_title = game_font_medium.render("Lydeffekter", True, (150, 220, 220))
        skjerm.blit(sound_title, (settings_box_x + 50, y_pos))
        
        # Draw volume bar
        bar_width = int(settings_box_width * 0.6)
        bar_height = 20
        bar_x = settings_box_x + 50
        bar_y = y_pos + 35
        
        # Background bar
        pygame.draw.rect(skjerm, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        # Fill bar based on volume
        fill_width = int(bar_width * sound_volume)
        pygame.draw.rect(skjerm, (100, 200, 200), (bar_x, bar_y, fill_width, bar_height))
        # Border
        pygame.draw.rect(skjerm, HVIT, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Volume percentage
        vol_text = game_font_small.render(f"{int(sound_volume * 100)}%", True, HVIT)
        skjerm.blit(vol_text, (bar_x + bar_width + 20, bar_y))
        
        # Controls
        controls_text = game_font_small.render("[1] Senk   [2] Øk", True, HVIT)
        skjerm.blit(controls_text, (bar_x, bar_y + bar_height + 10))
        
        # Music volume
        y_pos += line_spacing
        music_title = game_font_medium.render("Musikk", True, (220, 150, 220))
        skjerm.blit(music_title, (settings_box_x + 50, y_pos))
        
        # Draw volume bar
        bar_y = y_pos + 35
        
        # Background bar
        pygame.draw.rect(skjerm, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        # Fill bar based on volume (scale up for better visibility since music_volume max is 0.2)
        fill_width = int(bar_width * (music_volume / 0.2))
        pygame.draw.rect(skjerm, (200, 100, 200), (bar_x, bar_y, fill_width, bar_height))
        # Border
        pygame.draw.rect(skjerm, HVIT, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Volume percentage (scale to 100%)
        vol_text = game_font_small.render(f"{int((music_volume / 0.2) * 100)}%", True, HVIT)
        skjerm.blit(vol_text, (bar_x + bar_width + 20, bar_y))
        
        # Controls
        controls_text = game_font_small.render("[3] Senk   [4] Øk", True, HVIT)
        skjerm.blit(controls_text, (bar_x, bar_y + bar_height + 10))
        
        # Mouse control toggle - moved up to replace fullscreen toggle
        y_pos += line_spacing
        mouse_title = game_font_medium.render("Musisk bevegelse", True, (150, 220, 150))
        skjerm.blit(mouse_title, (settings_box_x + 50, y_pos))
        
        # Draw toggle indicator
        toggle_width = 60
        toggle_height = 30
        toggle_x = bar_x
        toggle_y = y_pos + 35
        
        # Background
        pygame.draw.rect(skjerm, (80, 80, 80), (toggle_x, toggle_y, toggle_width, toggle_height))
        # Fill based on state
        if mouse_control:
            pygame.draw.rect(skjerm, (150, 200, 100), (toggle_x + toggle_width//2, toggle_y, toggle_width//2, toggle_height))
        else:
            pygame.draw.rect(skjerm, (200, 100, 100), (toggle_x, toggle_y, toggle_width//2, toggle_height))
        # Border
        pygame.draw.rect(skjerm, HVIT, (toggle_x, toggle_y, toggle_width, toggle_height), 2)
        
        # Toggle state text
        mouse_state_text = "PÅ" if mouse_control else "AV"
        mouse_state_color = (150, 200, 100) if mouse_control else (200, 100, 100)
        mouse_toggle_text = game_font_small.render(mouse_state_text, True, mouse_state_color)
        skjerm.blit(mouse_toggle_text, (toggle_x + toggle_width + 20, toggle_y + 5))
        
        # Controls
        mouse_controls_text = game_font_small.render("[5] Bytt", True, HVIT)
        skjerm.blit(mouse_controls_text, (toggle_x, toggle_y + toggle_height + 10))
        
        # Note about controls - simplified reference to Help screen
        help_note = game_font_small.render("Se Hjelp [H] for kontroll-informasjon", True, (200, 200, 200))
        skjerm.blit(help_note, (settings_box_x + 50, toggle_y + toggle_height + 40))
        
        # Back instruction - Position at very bottom of the box
        back_text = game_font_medium.render("Trykk ESC eller I for å gå tilbake", True, (200, 200, 200))
        back_y_position = settings_box_y + settings_box_height - 50  # Position 50px from the bottom edge
        skjerm.blit(back_text, (BREDDE//2 - back_text.get_width()//2, back_y_position))

    elif spilltilstand == Spilltilstand.GAME_OVER:
        # Draw a semi-transparent overlay for game over
        overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Black with transparency
        skjerm.blit(overlay, (0, 0))
        
        # Create a dialog box
        dialog_width = 400
        dialog_height = 200
        dialog_x = BREDDE//2 - dialog_width//2
        dialog_y = HOYDE//2 - dialog_height//2
        
        # Draw dialog box
        pygame.draw.rect(skjerm, (90, 50, 50), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(skjerm, ROD, (dialog_x, dialog_y, dialog_width, dialog_height), 2)
        
        # Game Over title
        game_over_title = game_font_large.render("GAME OVER!", True, ROD)
        skjerm.blit(game_over_title, (BREDDE//2 - game_over_title.get_width()//2, dialog_y + 30))
        
        # Final score
        score_text = game_font_medium.render(f"Din poengsum: {poeng}", True, HVIT)
        skjerm.blit(score_text, (BREDDE//2 - score_text.get_width()//2, dialog_y + 80))
        
        # High score message if a new high score was achieved
        current_high_score = get_current_high_score(VANSKELIGHETSGRAD, LEVEL, LEVEL_MODE, high_scores)
        if poeng > current_high_score:
            high_score_msg = game_font_small.render("Ny highscore!", True, (255, 215, 0))
            skjerm.blit(high_score_msg, (BREDDE//2 - high_score_msg.get_width()//2, dialog_y + 120))
        
        # Press enter to continue
        continue_text = game_font_small.render("Trykk ENTER for å gå til hovedmenyen", True, HVIT)
        skjerm.blit(continue_text, (BREDDE//2 - continue_text.get_width()//2, dialog_y + 160))
    
    elif spilltilstand == Spilltilstand.QUIT_CONFIRM:
        # Draw a semi-transparent overlay for quit confirmation
        overlay = pygame.Surface((BREDDE, HOYDE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Black with transparency
        skjerm.blit(overlay, (0, 0))
        
        # Create a dialog box
        dialog_width = 400
        dialog_height = 180
        dialog_x = BREDDE//2 - dialog_width//2
        dialog_y = HOYDE//2 - dialog_height//2
        
        # Draw dialog box
        pygame.draw.rect(skjerm, (60, 60, 70), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(skjerm, (120, 120, 140), (dialog_x, dialog_y, dialog_width, dialog_height), 2)
        
        # Quit confirmation title
        quit_title = game_font_medium.render("Vil du avslutte spillet?", True, HVIT)
        skjerm.blit(quit_title, (BREDDE//2 - quit_title.get_width()//2, dialog_y + 30))
        
        # Options
        yes_option = game_font_small.render("Ja [J/Y] - Tilbake til hovedmeny", True, HVIT)
        skjerm.blit(yes_option, (BREDDE//2 - yes_option.get_width()//2, dialog_y + 80))
        
        no_option = game_font_small.render("Nei [N/ESC] - Fortsett spill", True, HVIT)
        skjerm.blit(no_option, (BREDDE//2 - no_option.get_width()//2, dialog_y + 120))
    else:
        # Draw aim line for the player at level 1 and 2
        if not spilltilstand == Spilltilstand.GAME_OVER and VANSKELIGHETSGRAD < 3:
            # Create a semi-transparent surface for aim line
            siktelinje = pygame.Surface((2, HOYDE), pygame.SRCALPHA)
            siktelinje.fill((0, 0, 255, 30))  # Blue color with 30/255 alpha (almost transparent)
            
            # Draw dotted lines on the surface
            for y in range(0, HOYDE, 10):
                if y % 20 == 0:  # Alternates between visible and invisible to create dotted effect
                    pygame.draw.line(siktelinje, (0, 0, 255, 80), (0, y), (2, y+8), 2)
            
            # Place aim line on the screen, centered with the player
            skjerm.blit(siktelinje, (spiller.rect.centerx - 1, 0))
        
        alle_sprites.draw(skjerm)
        
        # Show points and high score
        high_score = get_current_high_score(VANSKELIGHETSGRAD, LEVEL, LEVEL_MODE, high_scores)
        poeng_tekst = game_font_small.render(f"Poeng: {poeng}", True, HVIT)
        if not LEVEL_MODE:  # Only show high score in regular mode
            high_score_tekst = game_font_small.render(f"High Score: {high_score}", True, (255, 215, 0))  # Gold color for high score
            skjerm.blit(high_score_tekst, (BREDDE - high_score_tekst.get_width() - 10, 10))

        skjerm.blit(poeng_tekst, (10, 10))
        
        # Show lives
        liv_tekst = game_font_small.render(f"Liv: {spiller.liv}", True, HVIT)
        skjerm.blit(liv_tekst, (10, 40))
        
        # Show difficulty level
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
        
        # Show level progress (only in level mode)
        if LEVEL_MODE and spilltilstand == Spilltilstand.SPILLER:
            draw_level_progress(skjerm, poeng, LEVEL, game_font_small)
        
        # Show multiplier - moved from center to right side with better visibility
        if spilltilstand == Spilltilstand.SPILLER:
            # Show multiplier with more prominent positioning and better visibility
            if score_multiplier > 1.0:
                multiplier_text = game_font_medium.render(f"x{score_multiplier:.1f}", True, (255, 215, 0))  # Brighter gold color
                skjerm.blit(multiplier_text, (BREDDE - multiplier_text.get_width() - 10, 40))  # Position at top-right
            
            # Show enemy point values - restore this functionality
            try:
                # Pass additional parameters to control enemy display
                draw_enemy_points(skjerm, fiende_bilde, sterk_fiende_bilde, score_multiplier, game_font_small, 
                                VANSKELIGHETSGRAD, LEVEL_MODE, LEVEL)
            except Exception as e:
                print(f"Failed to draw enemy points: {e}")
            
            # Show currently selected weapon - with consistent styling matching the main menu
            # Now stacked vertically instead of horizontally
            # Remove the condition that was hiding weapons in-game
            # if game_config["max_level_reached"] > 5:  # This condition was making weapons not show
            
            # Set up panel dimensions - smaller than menu but same style
            weapon_panel_width = 130  # Slightly wider than before
            weapon_panel_height = 35
            weapon_spacing = 10  # Vertical spacing between panels
            
            # Position in top-right corner with some padding
            weapons_start_x = BREDDE - weapon_panel_width - 10
            weapons_start_y = 120  # Start below the multiplier display
            
            # Define weapon types and their properties
            weapon_types = [
                {
                    "name": "Laser",
                    "key": "1",
                    "type": "normal",
                    "bg_color": (40, 60, 50),
                    "border_color": pastel_colors["easy"],
                    "text_color": pastel_colors["easy"],
                    "unlocked": True
                },
                {
                    "name": "Hagle",
                    "key": "2", 
                    "type": "shotgun",
                    "bg_color": (60, 50, 40) if game_config["max_level_reached"] > 5 else (50, 50, 50),
                    "border_color": pastel_colors["medium"] if game_config["max_level_reached"] > 5 else (120, 120, 120),
                    "text_color": pastel_colors["medium"] if game_config["max_level_reached"] > 5 else (150, 150, 150),
                    "unlocked": game_config["max_level_reached"] > 5,
                    "locked_text": "Hagle [Lvl 5+]"
                },
                {
                    "name": "Pisk",
                    "key": "3",
                    "type": "electric whip",
                    "bg_color": (60, 40, 40) if game_config["max_level_reached"] >= 10 else (50, 50, 50),
                    "border_color": pastel_colors["hard"] if game_config["max_level_reached"] >= 10 else (120, 120, 120),
                    "text_color": pastel_colors["hard"] if game_config["max_level_reached"] >= 10 else (150, 150, 150),
                    "unlocked": game_config["max_level_reached"] >= 10,
                    "charged": spiller.whip_charge >= spiller.whip_charge_threshold,
                    "locked_text": "Pisk [Lvl 10+]"
                }
            ]
            
            for i, weapon in enumerate(weapon_types):
                # Always display all weapons, don't skip any
                
                is_selected = False
                if weapon["type"] == "electric whip":
                    is_selected = weapon.get("charged", False) and weapon["unlocked"]
                else:
                    is_selected = (spiller.current_weapon == weapon["type"])
                panel_y = weapons_start_y + i * (weapon_panel_height + weapon_spacing)
                
                # Draw the weapon panel background
                pygame.draw.rect(skjerm, weapon["bg_color"], 
                                (weapons_start_x, panel_y, weapon_panel_width, weapon_panel_height))
                
                # Only show charge meter if the whip is unlocked
                if weapon["type"] == "electric whip" and weapon["unlocked"]:
                    # Draw charging progress
                    charge_ratio = spiller.whip_charge / spiller.whip_charge_threshold
                    fill_width = int(weapon_panel_width * min(max(charge_ratio, 0), 1))
                    if spiller.whip_charge >= spiller.whip_charge_threshold:
                        # Create pulsing effect when fully charged
                        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2
                        factor = 1.0 + 0.5 * pulse
                        fill_color = (min(255, int(ROD[0] * factor)),
                                    min(255, int(ROD[1] * factor)),
                                    min(255, int(ROD[2] * factor)))
                        # Draw a glowing border in sync with the pulse
                        glow = (min(255, int(ROD[0] * (1.0+0.7*pulse))),
                               min(255, int(ROD[1] * (1.0+0.7*pulse))),
                               min(255, int(ROD[2] * (1.0+0.7*pulse))))
                        pygame.draw.rect(skjerm, glow, (weapons_start_x-2, panel_y-2, weapon_panel_width+4, weapon_panel_height+4), 2)
                    else:
                        fill_color = ROD
                    pygame.draw.rect(skjerm, fill_color, (weapons_start_x, panel_y, fill_width, weapon_panel_height))
                
                # Draw panel border
                pygame.draw.rect(skjerm, weapon["border_color"],
                                (weapons_start_x, panel_y, weapon_panel_width, weapon_panel_height),
                                3 if is_selected else 1)
                    
                # Draw weapon text centered - use locked text if not unlocked
                if weapon["unlocked"]:
                    weapon_text = f"{weapon['name']} [{weapon['key']}]"
                else:
                    weapon_text = weapon.get("locked_text", f"{weapon['name']} [Låst]")
                
                text_render = info_font.render(weapon_text, True,
                                            HVIT if is_selected else weapon["text_color"])
                skjerm.blit(text_render, (weapons_start_x + weapon_panel_width//2 - text_render.get_width()//2,
                                        panel_y + weapon_panel_height//2 - text_render.get_height()//2))

    # Fix in-game weapons display in mouse mode - only show electric whip (pisk)
    if spilltilstand == Spilltilstand.SPILLER:
        # ...existing code...
        
        # Process whip hits - FORBEDRET VERSJON FOR FIENDE HÅNDTERING
        whip_found = False
        
        for sprite in list(alle_sprites):
            if isinstance(sprite, ElectricWhip):
                whip_found = True
                # Pass fiende_gruppe for collision detection - call correctly with 4 arguments
                sprite.update(fiende_gruppe, alle_sprites, eksplosjon_lyd, score_multiplier)
                
                # Process damage and scoring for hit enemies
                for fiende in list(sprite.enemies_hit):  # Bruk liste for å unngå "set changed during iteration"
                    # Make sure enemy still exists in the game
                    if fiende in fiende_gruppe:
                        # Increase score multiplier for every hit
                        score_multiplier, consecutive_hits = increase_multiplier(score_multiplier, consecutive_hits)
                        point_gain = int(fiende.point_value * score_multiplier)
                        poeng += point_gain
                        
                        # Create explosion at enemy position
                        eksplosjon = Eksplosjon(fiende.rect.center)
                        alle_sprites.add(eksplosjon)
                        
                        # Determine enemy type before removal
                        is_strong_enemy = isinstance(fiende, SterkFiende)
                        fiende_pos = fiende.rect.center  # Husk posisjonen
                        
                        # Remove the enemy - remove from both groups
                        fiende.kill()
                        
                        # Create a replacement enemy based on original type
                        if is_strong_enemy:
                            ny_fiende = SterkFiende(sterk_fiende_bilde, VANSKELIGHETSGRAD)
                        else:
                            ny_fiende = Fiende(fiende_bilde, VANSKELIGHETSGRAD)
                        
                        # Add the new enemy to both sprite groups
                        alle_sprites.add(ny_fiende)
                        fiende_gruppe.add(ny_fiende)
                
                # Fjern referanse til fiender som er borte - unngå duplikat håndtering
                sprite.enemies_hit.clear()

    # Update the screen
    pygame.display.flip()

# End the game
pygame.mixer.stop()  # Stop all music and sound effects before exiting
pygame.quit()
sys.exit()