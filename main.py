import tkinter as tk
from tkinter import filedialog, ttk
import cv2
import os
import PIL.Image, PIL.ImageTk

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")
        self.video_source = None
        self.video_capture = None
        self.current_frame = None
        self.frame_index = 0
        self.total_frames = 0
        self.output_dir = None
        
        # Autoplay variables
        self.is_playing = False
        self.play_speed = 100  # milliseconds between frames (10 fps)

        # Create frame2 first, so it gets priority
        self.frame2 = tk.Frame(root, height=120)
        self.frame2.pack_propagate(False)  # Prevent frame2 from resizing to fit its children
        self.frame2.pack(side=tk.BOTTOM, fill=tk.X, expand=False)   # This frame does NOT expand

        # Then create frame1, which will take remaining space
        self.canvas_width = 1000
        self.canvas_height = 700
        self.frame1 = tk.Frame(root, width=self.canvas_width, height=self.canvas_height)
        self.frame1.pack_propagate(False)
        self.frame1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # This frame expands

        # Add a divider between frame1 and frame2
        self.divider = ttk.Separator(root, orient='horizontal')
        self.divider.pack(fill=tk.X, before=self.frame2)

        self.canvas = tk.Canvas(self.frame1, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create message box container frame inside frame2
        self.message_frame = tk.Frame(self.frame2)
        self.message_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # File info message box (left side)
        self.info_label = tk.Label(self.message_frame, text="No file loaded", fg="blue", font=("Arial", 12))
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Transient message box (right side)
        self.message_label = tk.Label(self.message_frame, text="", fg="red", font=("Arial", 12), width=500)
        self.message_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        # Button styles
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 11, 'bold'))
        style.map('TButton', 
            background=[('active', "#a0b1c5")],
            foreground=[('active', 'black')])  # Changed to black text on hover
        
        # Create button frame with nice padding
        self.button_frame = tk.Frame(self.frame2, pady=10)
        self.button_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Buttons in frame2 with improved styling
        self.btn_open = ttk.Button(
            self.button_frame, 
            text="Open Video File",
            command=self.open_video,
            style='TButton',
            padding=(15, 8)
        )
        self.btn_open.pack(side=tk.LEFT, padx=20, pady=5)

        # Add Save Frame button
        self.btn_save = ttk.Button(
            self.button_frame, 
            text="Save Frame",
            command=lambda: self.save_frame(),
            style='TButton',
            padding=(15, 8)
        )
        self.btn_save.pack(side=tk.LEFT, padx=20, pady=5)
        
        # Add Play/Pause button
        self.btn_play = ttk.Button(
            self.button_frame, 
            text="Play",
            command=self.toggle_play,
            style='TButton',
            padding=(15, 8)
        )
        self.btn_play.pack(side=tk.LEFT, padx=20, pady=5)
        
        # Add Keymap button
        self.btn_keymap = ttk.Button(
            self.button_frame, 
            text="Show Keymap",
            command=self.show_keymap_dialog,
            style='TButton',
            padding=(15, 8)
        )
        self.btn_keymap.pack(side=tk.LEFT, padx=20, pady=5)


        # Initialization flag
        self.initialized = False

        # Track previous window size
        self.previous_width = self.frame1.winfo_width() + self.frame2.winfo_width()
        self.previous_height = self.frame1.winfo_height() + self.frame2.winfo_height()

        # Bind keys
        self.root.bind("<Left>", self.prev_frame)
        self.root.bind("<Right>", self.next_frame)
        self.root.bind("<Shift-Left>", self.skip_back)
        self.root.bind("<Shift-Right>", self.skip_forward)
        self.root.bind("s", self.save_frame)
        self.root.bind("q", lambda e: self.quit_app())
        self.root.bind("o", lambda e: self.open_video())
        self.root.bind("<space>", lambda e: self.toggle_play())

        # Bind window resize event
        self.root.bind("<Configure>", self.on_resize)

        # Set initialized flag to True after setup
        self.root.after(100, self.set_initialized)
        
        # Display keymaps initially
        self.show_keymaps()

    def set_initialized(self):
        self.initialized = True

    def on_resize(self, event):
        if not self.initialized:
            return

        current_width = self.frame1.winfo_width()
        # Calculate the height available for frame1 (total window height minus frame2 height)
        available_height = self.root.winfo_height() - self.frame2.winfo_height()
        current_height = min(self.frame1.winfo_height(), available_height)

        # Check if the size has changed
        if current_width != self.previous_width or current_height != self.previous_height:
            self.previous_width = current_width
            self.previous_height = current_height

            # Update frame1 dimensions
            self.frame1_width = current_width
            self.frame1_height = current_height
            self.frame1.config(width=self.frame1_width, height=self.frame1_height)
            # update canvas dimensions to be the same as frame1
            self.canvas.config(width=self.frame1_width, height=self.frame1_height)

            # Redraw the current frame to fit the new size
            if self.current_frame is not None:
                self.show_frame()
            else:
                self.show_keymaps()

    def get_keymap_text(self):
        """Return the standardized keymap text used in multiple places"""
        return """
← (Left Arrow): Previous frame
→ (Right Arrow): Next frame
Shift + ← : Skip back 10 frames
Shift + → : Skip forward 10 frames
Space: Play/Pause
s: Save current frame
o: Open video file
q: Quit application
        """

    def show_keymaps(self):
        """Display keyboard shortcuts on the canvas when no video is loaded"""
        self.canvas.delete("all")
        
        # Use the explicit canvas dimensions during initialization
        if not self.initialized:
            canvas_width = self.canvas_width
            canvas_height = self.canvas_height
        else:
            # After initialization, use the actual widget dimensions
            canvas_width = max(self.canvas.winfo_width(), self.frame1.winfo_width())
            canvas_height = max(self.canvas.winfo_height(), self.frame1.winfo_height())
        
        # First create the title with bold font
        self.canvas.create_text(
            canvas_width // 2, 
            (canvas_height // 2) - 100,
            text="Keyboard Shortcuts:",
            font=("Arial", 16, "bold"),
            justify=tk.LEFT
        )
        
        # Then create the shortcuts list with regular font
        self.canvas.create_text(
            canvas_width // 2, 
            (canvas_height // 2) + 20,
            text=self.get_keymap_text(),
            font=("Arial", 14),
            justify=tk.LEFT
        )

    def truncate_filename(self, filename, max_length=40):
        """Truncate long filenames with '...' in the middle"""
        if len(filename) <= max_length:
            return filename
        
        # Keep first and last parts, with "..." in the middle
        first_part = filename[:max_length//2-1]
        last_part = filename[-(max_length//2-1):]
        return f"{first_part}...{last_part}"

    def update_info_label(self):
        """Update the info label with current file and frame information"""
        if self.video_source:
            filename = os.path.basename(self.video_source)
            # Truncate filename if it's too long
            truncated_filename = self.truncate_filename(filename)
            self.info_label.config(text=f"File: {truncated_filename} | Frame: {self.frame_index}/{self.total_frames-1}")
        else:
            self.info_label.config(text="No file loaded")

    def open_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file_path:
            # Stop playback if active
            if self.is_playing:
                self.toggle_play()
                
            self.video_source = file_path
            self.video_capture = cv2.VideoCapture(file_path)
            self.frame_index = 0
            self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self.output_dir = os.path.splitext(os.path.basename(file_path))[0]
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            self.show_frame()
            self.update_info_label()

    def show_frame(self):
        if self.video_capture and self.video_capture.isOpened():
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame
                self.canvas.delete("all")  # Clear canvas

                # Get the aspect ratio of the video
                video_height, video_width, _ = frame.shape
                aspect_ratio = video_width / video_height

                # Calculate new dimensions while maintaining aspect ratio
                if self.frame1_width / self.frame1_height > aspect_ratio:
                    # Fit to height
                    new_height = self.frame1_height
                    new_width = int(new_height * aspect_ratio)
                else:
                    # Fit to width
                    new_width = self.frame1_width
                    new_height = int(new_width / aspect_ratio)

                # Resize the frame to fit the canvas while maintaining aspect ratio
                frame = cv2.resize(frame, (new_width, new_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Center the frame on the canvas
                x_offset = (self.frame1_width - new_width) // 2
                y_offset = (self.frame1_height - new_height) // 2

                # Display the frame on the canvas
                img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
                self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=img)
                self.canvas.image = img
                
                # Update info label
                self.update_info_label()

    def show_message(self, message):
        """Display a message in the message box."""
        self.message_label.config(text=message)
        self.root.after(3000, lambda: self.message_label.config(text=""))  # Clear message after 3 seconds

    def prev_frame(self, event=None):
        if self.is_playing:
            self.toggle_play()  # Stop playback when manually navigating
            
        if self.video_capture and self.frame_index > 0:
            self.frame_index -= 1
            self.show_frame()
        else:
            self.show_message("Already at first frame")

    def next_frame(self, event=None):
        if self.is_playing:
            self.toggle_play()  # Stop playback when manually navigating
            
        if self.video_capture and self.frame_index < self.total_frames - 1:
            self.frame_index += 1
            self.show_frame()
        else:
            self.show_message("Already at last frame")
            
    def skip_frames(self, count):
        """Skip forward or backward by specified number of frames
        Positive count = forward, negative count = backward
        """
        if self.is_playing:
            self.toggle_play()  # Stop playback when manually navigating
            
        if not self.video_capture:
            return
            
        # Calculate new position with bounds checking
        if count > 0:
            new_position = min(self.total_frames - 1, self.frame_index + count)
            message = f"Skipped forward {count} frames"
            error_message = "Already at last frame"
        else:
            new_position = max(0, self.frame_index + count)  # count is negative
            message = f"Skipped back {abs(count)} frames"
            error_message = "Already at first frame"
        
        # If position didn't change, we're at a boundary
        if new_position == self.frame_index:
            self.show_message(error_message)
            return
            
        self.frame_index = new_position
        self.show_frame()
        self.show_message(message)

    def skip_back(self, event=None):
        """Skip back 10 frames"""
        self.skip_frames(-10)
        
    def skip_forward(self, event=None):
        """Skip forward 10 frames"""
        self.skip_frames(10)

    def toggle_play(self, event=None):
        """Toggle between play and pause states"""
        if not self.video_capture:
            self.show_message("No video loaded")
            return
            
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.btn_play.config(text="Pause")
            self.play_video()
            self.show_message("Playback started")
        else:
            self.btn_play.config(text="Play")
            self.show_message("Playback paused")
    
    def play_video(self):
        """Play the video by advancing frames at regular intervals"""
        if not self.is_playing:
            return

        if self.video_capture and self.frame_index < self.total_frames - 1:
            self.frame_index += 1
            self.show_frame()
            self.root.after(self.play_speed, self.play_video)
        else:
            # We've reached the end of the video - reset to beginning
            self.is_playing = False
            self.frame_index = 0
            # self.show_frame()
            self.show_message("End of video reached")
            self.btn_play.config(text="Play")

    def save_frame(self, event=None):
        if self.current_frame is not None:
            filename = os.path.join(self.output_dir, f"frame_{self.frame_index}.png")
            cv2.imwrite(filename, self.current_frame)
            self.show_message(f"Frame saved to {filename}")
            print(f"Frame saved to {filename}")

    def quit_app(self):
        if self.video_capture:
            self.video_capture.release()
        self.root.destroy()

    def show_keymap_dialog(self):
        """Show keymap in a dialog window"""
        keymap_window = tk.Toplevel(self.root)
        keymap_window.title("Keyboard Shortcuts")
        keymap_window.geometry("400x300")
        keymap_window.resizable(False, False)
        
        # Make the window modal
        keymap_window.transient(self.root)
        keymap_window.grab_set()
        
        # Create a frame for the content
        frame = tk.Frame(keymap_window, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add title with bold font
        title_label = tk.Label(
            frame,
            text="Keyboard Shortcuts",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Add keymap text
        label = tk.Label(
            frame,
            text=self.get_keymap_text(),
            font=("Arial", 12),
            justify=tk.LEFT
        )
        label.pack(pady=10)
        
        # Add OK button to close the dialog
        ok_button = ttk.Button(
            frame,
            text="OK",
            command=keymap_window.destroy,
            style='TButton',
            padding=(15, 8)
        )
        ok_button.pack(pady=10)
        
        # Center the window on the parent
        keymap_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - keymap_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - keymap_window.winfo_height()) // 2
        keymap_window.geometry(f"+{x}+{y}")
        
        # Wait for this window to be closed before returning to the main window
        self.root.wait_window(keymap_window)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()