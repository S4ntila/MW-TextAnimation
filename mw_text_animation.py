import pygame
import pygame.freetype
import pygame.mixer
import sys
import os
import time
import random
import string
from PIL import Image, ImageSequence
import imageio
import numpy as np
from pygame.locals import *

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

# Constants
WIDTH, HEIGHT = 800, 450
BLUE_BG = (0, 0, 0)  # Changed to black background
TEXT_COLOR = (245, 255, 245)  # Changed to #f5fff5 (light green/white)
GLOW_COLOR = (51, 227, 44)  # Added glow color #33e32c (medium green)
FONT_SIZE = 40
FPS = 60
ANIMATION_SPEED = 10  # Reduced from 10 to make it slower
FADE_SPEED = 4  # Alpha change per frame (increased from 3)
DISAPPEAR_SPEED = 4  # Frames between character disappearance (higher = slower)
CHAR_CYCLE_SPEED = 5  # Increased from 3 to make cycling slower
GLOW_RADIUS = 5  # How many pixels the glow extends
GLOW_INTENSITY = 2  # How many layers of glow to render

# Set up the display window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Modern Warfare Text Animation")
clock = pygame.time.Clock()

# Load the font
try:
    font_path = "BankGothicMediumBT.ttf"
    font = pygame.font.Font(font_path, FONT_SIZE)
    print(f"Loaded font: {font_path}")
except:
    print("Could not load the custom font. Using default font instead.")
    font = pygame.font.SysFont("arial", FONT_SIZE)

# Load the sound effect
try:
    decoding_sound = pygame.mixer.Sound("Decoding Sound.wav")
    print("Loaded sound effect: Decoding Sound.wav")
    # Set the volume to avoid being too loud
    decoding_sound.set_volume(0.3)
except:
    print("Could not load the sound effect. Sound will be disabled.")
    decoding_sound = None

# Character pool for randomization - reduced to fewer characters
CHAR_POOL = string.ascii_uppercase + string.digits + '!@#$%^&*()[]{}|'

class TextAnimation:
    def __init__(self, text, screen_width, screen_height):
        self.original_text = text
        self.visible_text = ""
        self.char_index = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.alpha = 0  # Transparency value (0-255)
        self.state = "fade_in"  # States: fade_in, type, hold, disappear, done
        self.timer = 0
        self.frames = []  # To store frames for export
        self.recording = False
        self.export_type = None  # 'gif' or 'video'
        # For random disappearing letters
        self.visible_chars = []
        self.disappear_timer = 0
        # For character cycling effect
        self.current_cycling_char = 0
        self.cycling_chars = []  # Stores random characters for each position
        self.cycle_counters = []  # Counts frames for each position's cycling
        self.chars_locked = []  # Which characters are locked in (finished cycling)
        # For sound effects
        self.sound_channel = None
        self.sound_playing = False
        self.last_sound_time = 0
        
    def start_recording(self, export_type):
        self.recording = True
        self.export_type = export_type
        self.frames = []
        
    def stop_recording(self):
        self.recording = False
        export_type = self.export_type
        self.export_type = None
        return self.frames, export_type
        
    def reset(self):
        self.visible_text = ""
        self.char_index = 0
        self.alpha = 0
        self.state = "fade_in"
        self.timer = 0
        self.visible_chars = []
        self.disappear_timer = 0
        self.current_cycling_char = 0
        self.cycling_chars = []
        self.cycle_counters = []
        self.chars_locked = []
        self.sound_playing = False
        self.last_sound_time = 0
        
    def update(self):
        if self.state == "fade_in":
            self.alpha += FADE_SPEED
            if self.alpha >= 255:
                self.alpha = 255
                self.state = "type"
                # Initialize arrays for character cycling
                self.cycling_chars = [random.choice(CHAR_POOL) for _ in range(len(self.original_text))]
                self.cycle_counters = [0 for _ in range(len(self.original_text))]
                self.chars_locked = [False for _ in range(len(self.original_text))]
                # Initialize sound channel
                if decoding_sound:
                    self.sound_channel = pygame.mixer.Channel(0)
                
        elif self.state == "type":
            self.timer += 1
            
            # Play decoding sound continuously during typing
            if decoding_sound and not self.sound_playing:
                self.sound_channel.play(decoding_sound, loops=-1)  # Loop continuously
                self.sound_playing = True
            
            # Update character cycling
            for i in range(self.char_index + 1):
                if i < len(self.original_text) and not self.chars_locked[i]:
                    self.cycle_counters[i] += 1
                    
                    # If we've cycled enough, lock in the real character
                    if self.cycle_counters[i] >= CHAR_CYCLE_SPEED * (random.randint(1, 5)):
                        self.chars_locked[i] = True
                    else:
                        # Otherwise show a random character
                        self.cycling_chars[i] = random.choice(CHAR_POOL)
                        
            # Add character at a controlled rate
            if self.timer % (FPS // ANIMATION_SPEED) == 0:
                if self.char_index < len(self.original_text):
                    self.char_index += 1
            
            # Check if all characters are locked in up to the current index
            if self.char_index >= len(self.original_text) and all(self.chars_locked[:len(self.original_text)]):
                self.state = "hold"
                self.timer = pygame.time.get_ticks()
                # Initialize the visible characters array for disappearance
                self.visible_chars = [True] * len(self.original_text)
                # Let sound finish naturally instead of fading out
                if decoding_sound and self.sound_playing:
                    # Stop looping but allow current playback to finish
                    self.sound_channel.stop()
                    # Play the sound one last time without looping
                    self.sound_channel.play(decoding_sound)
                    self.sound_playing = False
                
        elif self.state == "hold":
            # Hold the full text for a moment
            if pygame.time.get_ticks() - self.timer > 2000:  # 2 seconds
                self.state = "disappear"
                self.disappear_timer = 0
                
        elif self.state == "disappear":
            # Random character disappearance
            self.disappear_timer += 1
            
            if self.disappear_timer >= DISAPPEAR_SPEED:
                self.disappear_timer = 0
                
                # Count remaining visible characters
                remaining = sum(self.visible_chars)
                
                if remaining > 0:
                    # Select a random visible character to disappear
                    while True:
                        idx = random.randint(0, len(self.original_text) - 1)
                        if self.visible_chars[idx]:
                            self.visible_chars[idx] = False
                            break
                else:
                    self.state = "done"
                
    def render(self, surface):
        # First render the full text to calculate positions
        full_text_surface = font.render(self.original_text, True, TEXT_COLOR)
        full_text_rect = full_text_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        
        if self.state == "fade_in":
            # Don't show anything during fade-in
            pass
            
        elif self.state == "type":
            # Only render the individual characters using the same approach for all states
            self.render_individual_chars(surface, full_text_rect)
            
        elif self.state == "hold":
            # Also render each character individually for consistent spacing
            self.render_individual_chars(surface, full_text_rect)
            
        elif self.state == "disappear":
            # Render only visible characters using the same method
            self.render_individual_chars(surface, full_text_rect, disappear_mode=True)
        
        # Store frame if recording
        if self.recording:
            self.frames.append(pygame.surfarray.array3d(surface))
    
    def render_individual_chars(self, surface, full_text_rect, disappear_mode=False):
        # Calculate the starting x position to center the entire text
        start_x = full_text_rect.left
        
        # Keep track of the x position as we place each character
        current_x = start_x
        
        for i, char in enumerate(self.original_text):
            # Skip rendering based on animation state and character visibility
            if disappear_mode and not self.visible_chars[i]:
                continue
                
            if not disappear_mode and i > self.char_index:
                continue
                
            # Determine which character to display
            display_char = char
            if not disappear_mode and i <= self.char_index and not self.chars_locked[i]:
                display_char = self.cycling_chars[i]
            
            # Get real position
            if i == 0:
                # First character starts at the beginning of the text rect
                pos_x = current_x
            else:
                # Measure the width of all text up to this character
                prev_text = self.original_text[:i]
                prev_width = font.size(prev_text)[0]
                pos_x = start_x + prev_width
                current_x = pos_x
            
            # Center vertically
            pos_y = full_text_rect.centery - font.size(display_char)[1] / 2
            
            # Render glow effect first (multiple layers with decreasing alpha)
            for glow_size in range(GLOW_RADIUS, 0, -1):
                for j in range(GLOW_INTENSITY):
                    # Calculate alpha for this glow layer
                    glow_alpha = 40 - (glow_size * 10) - (j * 5)
                    glow_alpha = max(5, min(glow_alpha, 60))  # Clamp between 5-60
                    
                    # Create slightly larger font for the glow
                    glow_size_px = glow_size + (j * 0.5)
                    glow_font = pygame.font.Font(font_path if 'font_path' in globals() else None, 
                                               int(FONT_SIZE + glow_size_px * 2))
                    
                    # Render glow character
                    glow_surface = glow_font.render(display_char, True, GLOW_COLOR)
                    glow_surface.set_alpha(glow_alpha)
                    
                    # Position adjustments for the larger glow
                    glow_x = pos_x - glow_size_px
                    glow_y = pos_y - glow_size_px
                    
                    # Render glow
                    surface.blit(glow_surface, (glow_x, glow_y))
            
            # Render the character
            char_surface = font.render(display_char, True, TEXT_COLOR)
            surface.blit(char_surface, (pos_x, pos_y))

    def is_done(self):
        return self.state == "done"

def save_to_gif(frames, filename="animation.gif", fps=30):
    # Convert frames to PIL Images and save as GIF
    pil_frames = [Image.fromarray(frame.transpose(1, 0, 2)) for frame in frames]
    pil_frames[0].save(
        filename,
        save_all=True,
        append_images=pil_frames[1:],
        optimize=False,
        duration=int(1000/fps),
        loop=0
    )
    print(f"Animation saved as {filename}")

def save_to_video(frames, filename="animation.mp4", fps=30):
    # Save frames as MP4 using imageio
    frames_rgb = [frame.transpose(1, 0, 2) for frame in frames]
    imageio.mimsave(filename, frames_rgb, fps=fps)
    print(f"Animation saved as {filename}")

def main():
    text_input = ""
    animation = None
    input_active = True
    
    while True:
        screen.fill(BLUE_BG)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
                
            if input_active:
                if event.type == KEYDOWN:
                    if event.key == K_RETURN:
                        if text_input:
                            animation = TextAnimation(text_input, WIDTH, HEIGHT)
                            input_active = False
                    elif event.key == K_BACKSPACE:
                        text_input = text_input[:-1]
                    else:
                        text_input += event.unicode
            else:
                if event.type == KEYDOWN:
                    if event.key == K_r and animation.is_done():
                        # Reset animation
                        animation.reset()
                    elif event.key == K_n and animation.is_done():
                        # New text
                        text_input = ""
                        input_active = True
                    elif event.key == K_g and animation.is_done():
                        # Export as GIF
                        animation.reset()
                        animation.start_recording('gif')
                    elif event.key == K_v and animation.is_done():
                        # Export as video
                        animation.reset()
                        animation.start_recording('video')
        
        if input_active:
            # Show text input screen
            prompt_surface = font.render("Enter text for animation:", True, TEXT_COLOR)
            prompt_rect = prompt_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            screen.blit(prompt_surface, prompt_rect)
            
            input_surface = font.render(text_input, True, TEXT_COLOR)
            input_rect = input_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(input_surface, input_rect)
            
            # Display an underscore cursor
            cursor_surface = font.render("_", True, TEXT_COLOR)
            cursor_rect = cursor_surface.get_rect(midleft=(input_rect.right, input_rect.centery))
            if pygame.time.get_ticks() % 1000 < 500:  # Blinking cursor
                screen.blit(cursor_surface, cursor_rect)
                
            # Show instructions
            instr = font.render("Press Enter to start animation", True, TEXT_COLOR)
            instr_rect = instr.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
            screen.blit(instr, instr_rect)
            
        elif animation:
            animation.update()
            animation.render(screen)
            
            if animation.is_done():
                if animation.recording:
                    frames, export_type = animation.stop_recording()
                    if export_type == 'gif':
                        save_to_gif(frames)
                    elif export_type == 'video':
                        save_to_video(frames)
                    
                # Show controls when animation is done
                controls = [
                    "R - Replay animation",
                    "N - New text",
                    "G - Export as GIF",
                    "V - Export as MP4 video"
                ]
                
                for i, text in enumerate(controls):
                    ctrl_surf = font.render(text, True, TEXT_COLOR)
                    ctrl_rect = ctrl_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100 + i * 30))
                    screen.blit(ctrl_surf, ctrl_rect)
        
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main() 