#!/usr/bin/env python3
# ~/Documents/display_quotes/display_quote.py 20 Feb at 12:46:35 AM
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import json
import random
import os
import sys
import subprocess
import time
import threading
import cairo

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
QUOTES_FILE = os.path.join(BASE_DIR, "assets", "programming-quotes.json")
SPECIAL_WORKSPACE = "special:scratchpad"
ADDR_FILE = "/tmp/quote_window_addr"

class QuoteOverlay(Gtk.Window):
    def __init__(self):
        super().__init__(title="Quote Display")
        
        # Window properties for overlay
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_resizable(False)
        
        # Make fully transparent
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        
        self.set_app_paintable(True)
        self.connect("draw", self.on_draw)
        
        # Set window size with more space for buttons
        self.set_default_size(700, 250)
        
        # Position in bottom-right corner
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        self.move(screen_width - 750, screen_height - 300)
        
        # Create main box that fills the window
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Create header box for buttons (fixed height)
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.header_box.set_size_request(-1, 70)  # Fixed height for button area
        self.header_box.set_margin_top(10)
        self.header_box.set_margin_end(20)
        
        # Create spacer to push buttons to the right
        self.header_spacer = Gtk.Box()
        self.header_box.pack_start(self.header_spacer, True, True, 0)
        
        # Create button box for top-right corner
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Previous quote button
        self.prev_button = Gtk.Button()
        self.prev_button.set_label("◀")
        self.prev_button.set_name("prev-button")
        self.prev_button.connect("clicked", self.on_prev_clicked)
        self.prev_button.set_tooltip_text("Previous quote")
        self.prev_button.set_sensitive(False)
        self.prev_button.set_can_focus(False)
        self.prev_button.set_halign(Gtk.Align.CENTER)
        self.prev_button.set_valign(Gtk.Align.CENTER)
        
        # Pause/Play button
        self.pause_button = Gtk.Button()
        self.pause_button.set_label("⏸")
        self.pause_button.set_name("pause-button")
        self.pause_button.connect("clicked", self.on_pause_clicked)
        self.pause_button.set_tooltip_text("Pause/Resume auto-rotation")
        self.is_paused = False
        self.pause_button.set_can_focus(False)
        self.pause_button.set_halign(Gtk.Align.CENTER)
        self.pause_button.set_valign(Gtk.Align.CENTER)
        
        # Next quote button
        self.next_button = Gtk.Button()
        self.next_button.set_label("▶")
        self.next_button.set_name("next-button")
        self.next_button.connect("clicked", self.on_next_clicked)
        self.next_button.set_tooltip_text("Next quote")
        self.next_button.set_sensitive(False)
        self.next_button.set_can_focus(False)
        self.next_button.set_halign(Gtk.Align.CENTER)
        self.next_button.set_valign(Gtk.Align.CENTER)
        
        # Copy button
        self.copy_button = Gtk.Button()
        self.copy_button.set_label("📋")
        self.copy_button.set_name("copy-button")
        self.copy_button.connect("clicked", self.on_copy_clicked)
        self.copy_button.set_sensitive(False)
        self.copy_button.set_tooltip_text("Copy quote to clipboard")
        self.copy_button.set_can_focus(False)
        self.copy_button.set_halign(Gtk.Align.CENTER)
        self.copy_button.set_valign(Gtk.Align.CENTER)
        
        # Add buttons to button box
        self.button_box.pack_start(self.prev_button, False, False, 0)
        self.button_box.pack_start(self.pause_button, False, False, 0)
        self.button_box.pack_start(self.next_button, False, False, 0)
        self.button_box.pack_start(self.copy_button, False, False, 0)
        
        # Add button box to header box
        self.header_box.pack_end(self.button_box, False, False, 0)
        
        # Create content box for quote text (centered with margins)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content_box.set_halign(Gtk.Align.CENTER)
        self.content_box.set_valign(Gtk.Align.CENTER)
        self.content_box.set_margin_start(40)  # Left margin
        self.content_box.set_margin_end(40)    # Right margin
        self.content_box.set_margin_top(20)    # Top margin
        self.content_box.set_margin_bottom(20) # Bottom margin
        
        # Quote label with subtle styling
        self.quote_label = Gtk.Label()
        self.quote_label.set_line_wrap(True)
        self.quote_label.set_max_width_chars(70)  # Increased for wider window
        self.quote_label.set_justify(Gtk.Justification.CENTER)
        self.quote_label.set_selectable(False)
        self.quote_label.set_name("quote-label")
        
        # Author label
        self.author_label = Gtk.Label()
        self.author_label.set_justify(Gtk.Justification.CENTER)
        self.author_label.set_name("author-label")
        
        # Add labels to content box
        self.content_box.pack_start(self.quote_label, True, True, 0)
        self.content_box.pack_start(self.author_label, False, False, 0)
        
        # Add header and content to main box
        self.main_box.pack_start(self.header_box, False, False, 0)
        self.main_box.pack_start(self.content_box, True, True, 0)
        
        # Add main box to window
        self.add(self.main_box)
        
        # Apply CSS styling
        self.apply_styling()
        
        # State management
        self.is_visible = False
        self.window_check_active = True
        self.quote_timer_id = None
        self.display_duration = 10  # seconds
        self.monitor_thread = None
        self.current_workspace = None
        self.window_address = None
        
        # Quote management
        self.all_quotes = []
        self.current_quote_index = -1
        self.current_quote = ""
        self.current_author = ""
        
        # Timer tracking
        self.last_quote_change_time = 0
        self.pause_start_time = 0
        
        # Load quotes
        self.load_all_quotes()
        
        # Start monitoring thread
        self.start_workspace_monitor()
        
        # Initially hide the window
        self.hide()
        
        # Connect to map event to get window address
        self.connect("map-event", self.on_window_mapped)
    
    def on_window_mapped(self, widget, event):
        """Get window address after it's mapped"""
        if not self.window_address:
            self.window_address = self.get_window_address()
            if self.window_address:
                print(f"Window address obtained: {self.window_address}")
                # Store the address
                with open(ADDR_FILE, 'w') as f:
                    f.write(self.window_address)
                # Move to special workspace
                self.move_to_special_workspace()
    
    def get_window_address(self):
        """Get the X window ID as hex address for hyprctl"""
        try:
            xid = hex(self.get_window().get_xid())
            return xid
        except Exception as e:
            print(f"Error getting window address: {e}")
            return None
    
    def apply_styling(self):
        css = """
        #quote-label {
            font-family: 'Sans';
            font-size: 24px;
            font-weight: normal;
            font-style: italic;
            color: rgba(255, 255, 255, 0.85);
            padding: 15px;
            background-color: rgba(0, 0, 0, 0.5);
            border-radius: 10px;
            margin: 10px;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        }
        
        #author-label {
            font-family: 'Sans';
            font-size: 20px;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.9);
            padding: 8px 12px;
            background-color: rgba(40, 40, 60, 0.7);
            border-radius: 6px;
            margin-top: 10px;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        }
        
        #prev-button, #pause-button, #next-button, #copy-button {
            font-family: 'Sans';
            font-size: 24px;  /* Larger icon size */
            font-weight: bold;
            color: rgba(255, 255, 255, 0.95);
            border: 2px solid rgba(255, 255, 255, 0.4);
            border-radius: 50%;
            padding: 8px;  /* Uniform padding around icon */
            box-shadow: 0px 3px 10px rgba(0, 0, 0, 0.5);
            transition: all 0.2s ease;
            /* Remove fixed min-width/min-height */
        }
        
        #prev-button, #next-button {
            background-color: rgba(33, 150, 243, 0.85);  /* Blue for navigation */
        }
        
        #pause-button {
            background-color: rgba(255, 193, 7, 0.85);  /* Amber for pause */
        }
        
        #copy-button {
            background-color: rgba(76, 175, 80, 0.85);  /* Green for copy */
        }
        
        #prev-button:hover, #pause-button:hover, #next-button:hover, #copy-button:hover {
            border-color: rgba(255, 255, 255, 0.6);
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.6);
            transform: scale(1.08);
        }
        
        #prev-button:active, #pause-button:active, #next-button:active, #copy-button:active {
            transform: scale(0.95);
        }
        
        #prev-button:disabled, #next-button:disabled {
            background-color: rgba(100, 100, 100, 0.4);
            color: rgba(255, 255, 255, 0.4);
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        #copy-button:disabled {
            background-color: rgba(100, 100, 100, 0.4);
            color: rgba(255, 255, 255, 0.4);
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        window {
            background-color: transparent;
        }
        """
        
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_data(css.encode())
        except Exception as e:
            print(f"CSS loading error: {e}")
            return
        
        # Apply CSS to the screen
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_draw(self, widget, cr):
        # Completely transparent background for the window itself
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False
    
    def load_all_quotes(self):
        """Load all quotes from JSON file"""
        try:
            with open(QUOTES_FILE, 'r') as f:
                self.all_quotes = json.load(f)
                if self.all_quotes:
                    print(f"Loaded {len(self.all_quotes)} quotes")
                else:
                    print("No quotes found in file, using defaults")
                    self.all_quotes = [
                        {"author": "System", "quote": "Add quotes to your JSON file"},
                        {"author": "Unknown", "quote": "The only way to learn a new programming language is by writing programs in it."}
                    ]
        except Exception as e:
            print(f"Error loading quotes: {e}")
            self.all_quotes = [
                {"author": "System", "quote": "Error loading quotes file"},
                {"author": "Unknown", "quote": "The only way to learn a new programming language is by writing programs in it."}
            ]
    
    def show_quote_at_index(self, index):
        """Display quote at specific index"""
        if not self.all_quotes or index < 0 or index >= len(self.all_quotes):
            return False
        
        quote_data = self.all_quotes[index]
        self.current_quote_index = index
        self.current_quote = quote_data["quote"]
        self.current_author = quote_data["author"]
        
        # Update quote change time
        self.last_quote_change_time = time.time()
        
        # Wrap long quotes for display
        quote = self.current_quote
        wrapped_quote = ""
        words = quote.split()
        line = ""
        
        for word in words:
            if len(line + " " + word) > 70:  # Adjusted for wider window
                wrapped_quote += line + "\n"
                line = word
            else:
                line += (" " if line else "") + word
        wrapped_quote += line
        
        self.quote_label.set_text(wrapped_quote)
        self.author_label.set_text(f"— {self.current_author}")
        
        # Update button states
        self.prev_button.set_sensitive(index > 0)
        self.next_button.set_sensitive(index < len(self.all_quotes) - 1)
        self.copy_button.set_sensitive(True)
        
        return True
    
    def show_random_quote(self):
        """Show a random quote"""
        if not self.all_quotes:
            return False
        
        # Get random index different from current if possible
        if len(self.all_quotes) > 1:
            new_index = self.current_quote_index
            while new_index == self.current_quote_index:
                new_index = random.randrange(0, len(self.all_quotes))
        else:
            new_index = 0
        
        return self.show_quote_at_index(new_index)
    
    def show_next_quote(self):
        """Show next quote in sequence"""
        if not self.all_quotes:
            return False
        
        next_index = (self.current_quote_index + 1) % len(self.all_quotes)
        return self.show_quote_at_index(next_index)
    
    def show_prev_quote(self):
        """Show previous quote in sequence"""
        if not self.all_quotes:
            return False
        
        if self.current_quote_index <= 0:
            prev_index = len(self.all_quotes) - 1
        else:
            prev_index = self.current_quote_index - 1
        
        return self.show_quote_at_index(prev_index)
    
    def on_prev_clicked(self, button):
        """Handle previous button click"""
        if self.show_prev_quote():
            self.reset_quote_timer()  # Reset timer when manually changing quote
            print("Showing previous quote")
    
    def on_next_clicked(self, button):
        """Handle next button click"""
        if self.show_next_quote():
            self.reset_quote_timer()  # Reset timer when manually changing quote
            print("Showing next quote")
    
    def on_pause_clicked(self, button):
        """Handle pause/play button click"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            # Pause the quote rotation
            if self.quote_timer_id:
                # Store when we paused
                self.pause_start_time = time.time()
                GLib.source_remove(self.quote_timer_id)
                self.quote_timer_id = None
            
            button.set_label("▶")  # Play symbol
            button.set_tooltip_text("Resume auto-rotation")
            print("Quote rotation paused")
        else:
            # Resume the quote rotation with remaining time
            if self.is_visible and not self.quote_timer_id and self.last_quote_change_time > 0:
                # Calculate how much time has passed since last quote change
                elapsed_since_quote_change = time.time() - self.last_quote_change_time
                
                # Time remaining from original 10 seconds
                remaining_time = max(0.1, self.display_duration - elapsed_since_quote_change)
                
                # Set timer for remaining time
                self.quote_timer_id = GLib.timeout_add(
                    int(remaining_time * 1000),  # Convert to milliseconds
                    self.on_quote_timer_ms
                )
                print(f"Resuming with {remaining_time:.1f} seconds remaining")
            
            button.set_label("⏸")  # Pause symbol
            button.set_tooltip_text("Pause auto-rotation")
            print("Quote rotation resumed")
    
    def reset_quote_timer(self):
        """Reset the 10-second quote timer (used for manual navigation)"""
        # Remove existing timer if it exists
        if self.quote_timer_id:
            GLib.source_remove(self.quote_timer_id)
            self.quote_timer_id = None
        
        # Only restart timer if auto-rotation is not paused
        if self.is_visible and not self.is_paused:
            self.start_quote_timer()
    
    def on_copy_clicked(self, button):
        """Handle copy button click"""
        if not self.current_quote:
            return
        
        # Format quote for clipboard
        full_text = f'"{self.current_quote}"\n\n— {self.current_author}'
        
        try:
            # Copy to clipboard using wl-copy (Wayland)
            subprocess.run(
                ["wl-copy"],
                input=full_text.encode('utf-8'),
                check=True
            )
            
            # Visual feedback on button
            original_label = button.get_label()
            button.set_label("✓")
            
            # Reset button label after 1 second
            GLib.timeout_add(1000, self.reset_button_label, button, original_label)
            
            print(f"Copied quote to clipboard: {self.current_quote[:50]}...")
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to copy to clipboard: {e}")
            button.set_label("✗")
            GLib.timeout_add(2000, self.reset_button_label, button, "📋")
    
    def reset_button_label(self, button, label):
        """Reset button label to original"""
        button.set_label(label)
        return False  # Don't repeat
    
    def start_quote_timer(self):
        """Start timer to change quotes every 10 seconds"""
        if self.quote_timer_id:
            GLib.source_remove(self.quote_timer_id)
        
        # Only start timer if not paused
        if not self.is_paused and self.all_quotes:
            self.quote_timer_id = GLib.timeout_add_seconds(
                self.display_duration,
                self.on_quote_timer
            )
    
    def on_quote_timer(self):
        """Callback for quote timer - shows next quote"""
        if self.is_visible and not self.is_paused and self.all_quotes:
            self.show_next_quote()
            self.start_quote_timer()  # Restart timer for next cycle
            return False  # Return False since we create a new timer
        else:
            return False  # Stop timer
    
    def on_quote_timer_ms(self):
        """Callback for millisecond timer (used when resuming)"""
        if self.is_visible and not self.is_paused and self.all_quotes:
            self.show_next_quote()
            self.start_quote_timer()  # Restart with normal 10-second timer
            return False
        else:
            return False
    
    def get_active_workspace(self):
        """Get the current active workspace"""
        try:
            result = subprocess.run(
                ["hyprctl", "activeworkspace", "-j"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                workspace_info = json.loads(result.stdout)
                return workspace_info["id"]
        except Exception as e:
            print(f"Error getting active workspace: {e}")
        
        return 1  # Default to workspace 1
    
    def move_to_special_workspace(self):
        """Move window to special workspace"""
        if not self.window_address:
            return
        
        try:
            # Move to special workspace and pin it
            subprocess.run(
                ["hyprctl", "dispatch", "movetoworkspacesilent", 
                 f"{SPECIAL_WORKSPACE},address:{self.window_address}"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            # Pin the window (makes it visible on all workspaces)
            subprocess.run(
                ["hyprctl", "dispatch", "pin", f"address:{self.window_address}"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            print(f"Moved window to special workspace and pinned it")
            
        except Exception as e:
            print(f"Error moving window to special workspace: {e}")
    
    def get_windows_on_current_workspace(self):
        """Get all windows on the current workspace"""
        try:
            result = subprocess.run(
                ["hyprctl", "clients", "-j"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                clients = json.loads(result.stdout)
                current_workspace = self.get_active_workspace()
                
                # Count windows on current workspace
                # We need to exclude our own window but include ALL other windows
                
                windows_on_current_workspace = []
                for client in clients:
                    # Check if window is on current workspace and mapped
                    if not (client["workspace"]["id"] == current_workspace and client["mapped"]):
                        continue
                    
                    # Try multiple ways to identify our own window
                    client_class = client.get("class", "")
                    client_title = client.get("title", "")
                    
                    # Exclude our own window by class name and title pattern
                    if client_class == "Quote Display" or "Quote Display" in client_title:
                        continue
                    
                    # Include ALL other windows (floating or tiled)
                    windows_on_current_workspace.append(client)
                
                return len(windows_on_current_workspace) > 0
                
        except Exception as e:
            print(f"Error getting windows on current workspace: {e}")
        
        return True  # Default to True (should hide) on error    

    def workspace_monitor_thread(self):
        """Thread to monitor workspace changes and window state"""
        last_workspace = None
        last_window_state = None
        
        while self.window_check_active:
            current_workspace = self.get_active_workspace()
            windows_exist = self.get_windows_on_current_workspace()
            
            # Check if workspace changed
            workspace_changed = (current_workspace != last_workspace)
            
            # Check if window state changed
            window_state_changed = (windows_exist != last_window_state)
            
            # Update visibility if either changed
            if workspace_changed or window_state_changed:
                # If windows exist, we should hide; if no windows, we should show
                should_show = not windows_exist
                GLib.idle_add(self.update_visibility, should_show)
                
                last_workspace = current_workspace
                last_window_state = windows_exist
            
            time.sleep(0.5)  # Check every 500ms
    
    def start_workspace_monitor(self):
        """Start the workspace monitoring thread"""
        self.monitor_thread = threading.Thread(target=self.workspace_monitor_thread, daemon=True)
        self.monitor_thread.start()
    
    def update_visibility(self, should_show):
        """Update window visibility based on window state in current workspace"""
        if should_show and not self.is_visible:
            # Show first random quote
            if self.show_random_quote():
                # Show the window
                self.show_all()
                self.is_visible = True
                
                # Ensure window is in special workspace and pinned
                if self.window_address:
                    try:
                        # Move to current workspace (from special)
                        current_workspace = self.get_active_workspace()
                        subprocess.run(
                            ["hyprctl", "dispatch", "movetoworkspacesilent", 
                             f"{current_workspace},address:{self.window_address}"],
                            capture_output=True,
                            text=True,
                            timeout=1
                        )
                        # Make sure it's pinned
                        subprocess.run(
                            ["hyprctl", "dispatch", "pin", f"address:{self.window_address}"],
                            capture_output=True,
                            text=True,
                            timeout=1
                        )
                    except Exception as e:
                        print(f"Error moving window to current workspace: {e}")
                
                # Start quote rotation timer
                self.start_quote_timer()
                print(f"Showing quote overlay on workspace {self.get_active_workspace()} (no windows)")
                
        elif not should_show and self.is_visible:
            # Hide the window and move back to special workspace
            if self.quote_timer_id:
                GLib.source_remove(self.quote_timer_id)
                self.quote_timer_id = None
            
            # Move back to special workspace before hiding
            if self.window_address:
                try:
                    subprocess.run(
                        ["hyprctl", "dispatch", "movetoworkspacesilent", 
                         f"{SPECIAL_WORKSPACE},address:{self.window_address}"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                except Exception as e:
                    print(f"Error moving window to special workspace: {e}")
            
            self.hide()
            self.is_visible = False
            print(f"Hiding quote overlay (windows detected on workspace {self.get_active_workspace()})")
    
    def cleanup(self):
        """Clean up resources"""
        self.window_check_active = False
        if self.quote_timer_id:
            GLib.source_remove(self.quote_timer_id)
            self.quote_timer_id = None
        # Remove address file
        try:
            if os.path.exists(ADDR_FILE):
                os.remove(ADDR_FILE)
        except:
            pass

if __name__ == "__main__":
    # Check if required tools are installed
    def check_tool(tool):
        try:
            subprocess.run(["which", tool], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    if not check_tool("wl-copy"):
        print("Warning: wl-copy is not installed. Clipboard functionality will not work.")
        print("Install with: sudo pacman -S wl-clipboard")
    
    # Check if quotes file exists
    if not os.path.exists(QUOTES_FILE):
        print(f"Creating sample quotes file at {QUOTES_FILE}")
        sample_quotes = [
            {
                "author": "Jason Gorman",
                "quote": "Refuctoring - the process of taking a well-designed piece of code and, through a series of small, reversible changes, making it completely unmaintainable by anyone except yourself."
            },
            {
                "author": "E. W. Dijkstra",
                "quote": "If debugging is the process of removing software bugs, then programming must be the process of putting them in."
            },
            {
                "author": "Alan Kay",
                "quote": "The best way to predict the future is to invent it."
            },
            {
                "author": "Linus Torvalds",
                "quote": "Talk is cheap. Show me the code."
            }
        ]
        os.makedirs(os.path.dirname(QUOTES_FILE), exist_ok=True)
        with open(QUOTES_FILE, 'w') as f:
            json.dump(sample_quotes, f, indent=2)
    
    win = QuoteOverlay()
    
    # Handle clean shutdown
    def on_destroy(window):
        window.cleanup()
        Gtk.main_quit()
    
    win.connect("destroy", on_destroy)
    
    # Handle SIGINT for clean shutdown
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    try:
        print("Quote overlay started.")
        print("Window behavior:")
        print("- Window lives in special:scratchpad workspace when hidden")
        print("- Shows only when CURRENT workspace has NO regular windows")
        print("- Hides when CURRENT workspace has ANY regular window")
        print("- Automatically shows/hides when switching workspaces")
        print("Auto-rotation behavior:")
        print("- Timer resets to 10 seconds when using Previous/Next buttons")
        print("- Timer continues from remaining time when resuming from pause")
        print("Button layout: ◀ ⏸ ▶ 📋 (always in top-right corner)")
        print("- ◀ Previous quote (resets timer to 10s)")
        print("- ⏸ Pause/Resume (continues timer when resuming)")
        print("- ▶ Next quote (resets timer to 10s)")
        print("- 📋 Copy to clipboard")
        Gtk.main()
    except KeyboardInterrupt:
        print("\nShutting down quote manager...")
        win.cleanup()
        Gtk.main_quit()
