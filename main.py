import customtkinter as ctk
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import sys
from CTkMessagebox import CTkMessagebox
import re
import hashlib  # Replace bcrypt with hashlib

# Set dark mode before creating the app
ctk.set_appearance_mode("dark")

class SynchingTeamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'synchingteam_db'
        }
        
        # Validate database connection before proceeding
        if not self.validate_database():
            self.show_error_and_exit("Could not connect to the database. Please check your database configuration and try again.")
            return

        self.title("SynchingTeam")
        self.geometry("900x600")
        self.resizable(False, False)  # Make window non-resizable
        
        # Initialize variables
        self.current_user = None
        self.current_role = None
        
        # Add page management
        self.current_page = None
        self.pages = {}
        self.current_event = None
        
        # Add group management
        self.current_group = None
        
        # Show login screen first
        self.show_login()
    
    def validate_database(self):
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                connection.close()
                return True
            return False
        except Error:
            return False

    def show_error_and_exit(self, message):
        CTkMessagebox(
            title="Error",
            message=message,
            icon="cancel",
            option_1="Exit"
        )
        sys.exit(1)

    def connect_to_database(self):
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Error connecting to MySQL Database: {e}")
            return None

    def show_page(self, page_name, **kwargs):
        # Hide current page if exists
        if self.current_page:
            self.current_page.pack_forget()

        # Create page if it doesn't exist
        if page_name not in self.pages:
            if page_name == "login":
                self.pages[page_name] = LoginPage(self)
            elif page_name == "main":
                self.pages[page_name] = MainPage(self)
            elif page_name == "event_details":
                self.pages[page_name] = EventDetailsPage(self)
            elif page_name == "create_event":
                self.pages[page_name] = CreateEventPage(self)
            elif page_name == "edit_event":
                self.pages[page_name] = EditEventPage(self)
            elif page_name == "delete_event":
                self.pages[page_name] = DeleteEventPage(self)
            elif page_name == "register":
                self.pages[page_name] = RegisterPage(self)
            elif page_name == "create_group":
                self.pages[page_name] = CreateGroupPage(self)
            elif page_name == "no_group":
                self.pages[page_name] = NoGroupPage(self)
            elif page_name == "members":
                self.pages[page_name] = MembersPage(self)

        # Show new page
        self.current_page = self.pages[page_name]
        self.current_page.pack(fill="both", expand=True)
        self.current_page.init_page(**kwargs)

    def show_login(self):
        self.show_page("login")

    def show_main_view(self):
        self.show_page("main")

    def show_event_details(self, event):
        self.current_event = event
        self.show_page("event_details", event=event)

    def login(self, username, password):
        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                # Hash the provided password
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                
                # Get user with matching username and password
                query = """
                    SELECT u.*, g.id as group_id, g.name as group_name 
                    FROM users u 
                    LEFT JOIN group_members gm ON u.id = gm.user_id 
                    LEFT JOIN groups g ON gm.group_id = g.id 
                    WHERE u.username = %s AND u.password = %s
                """
                cursor.execute(query, (username, hashed_password))
                user = cursor.fetchone()
                
                if user:
                    self.current_user = user
                    if user['role'] == 'admin' and not user['group_id']:
                        self.show_create_group()
                    elif not user['group_id']:
                        self.show_no_group_message()
                    else:
                        self.current_group = {
                            'id': user['group_id'],
                            'name': user['group_name']
                        }
                        self.show_main_view()
                else:
                    CTkMessagebox(title="Login Failed", message="Invalid credentials")
            finally:
                cursor.close()
                connection.close()

    def create_event(self):
        self.show_page("create_event")

    def edit_event(self):
        dialog = ctk.CTkInputDialog(
            text="Enter event ID to edit (see event list for IDs):",
            title="Edit Event"
        )
        event_id = dialog.get_input()
        if event_id:
            connection = self.connect_to_database()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT e.*, et.name as type,
                               DATE_FORMAT(e.event_datetime, '%Y-%m-%d') as date
                        FROM events e
                        LEFT JOIN event_types et ON e.event_type_id = et.id
                        WHERE e.id = %s AND e.group_id = %s
                    """, (event_id, self.current_group['id']))
                    event = cursor.fetchone()
                    if event:
                        self.current_event = event
                        self.show_page("edit_event")
                    else:
                        CTkMessagebox(title="Error", message="Event not found", icon="cancel")
                finally:
                    cursor.close()
                    connection.close()

    def delete_event(self):
        dialog = ctk.CTkInputDialog(
            text="Enter event ID to delete:",
            title="Delete Event"
        )
        event_id = dialog.get_input()
        if event_id:
            connection = self.connect_to_database()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT title FROM events 
                        WHERE id = %s AND group_id = %s
                    """, (event_id, self.current_group['id']))
                    event = cursor.fetchone()
                    if event:
                        response = CTkMessagebox(
                            title="Confirm Delete",
                            message=f"Are you sure you want to delete event: {event['title']}?",
                            icon="warning",
                            option_1="No",
                            option_2="Yes"
                        ).get()
                        if response == "Yes":
                            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
                            connection.commit()
                            CTkMessagebox(title="Success", message="Event deleted successfully!", icon="check")
                            self.show_main_view()
                    else:
                        CTkMessagebox(title="Error", message="Event not found", icon="cancel")
                finally:
                    cursor.close()
                    connection.close()

    def update_event(self, event_id, title, date_str, event_type, description):
        try:
            # Validate date format
            event_date = datetime.strptime(date_str, '%Y-%m-%d')
            event_datetime = event_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            CTkMessagebox(title="Error", message="Invalid date format. Use YYYY-MM-DD", icon="cancel")
            return False

        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Get event type id
                cursor.execute("SELECT id FROM event_types WHERE name = %s", (event_type,))
                event_type_id = cursor.fetchone()[0]
                
                query = """
                    UPDATE events 
                    SET title = %s, description = %s, event_datetime = %s, event_type_id = %s
                    WHERE id = %s AND group_id = %s
                """
                cursor.execute(query, (
                    title, description, event_datetime, event_type_id,
                    event_id, self.current_group['id']
                ))
                connection.commit()
                CTkMessagebox(title="Success", message="Event updated successfully!", icon="check")
                return True
            except Error as e:
                CTkMessagebox(title="Error", message=f"Failed to update event: {str(e)}", icon="cancel")
                return False
            finally:
                cursor.close()
                connection.close()
        return False

    def show_register(self):
        self.show_page("register")

    def register_user(self, username, email, password, confirm_password):
        if not username or not email or not password or not confirm_password:
            CTkMessagebox(title="Error", message="All fields are required", icon="cancel")
            return

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            CTkMessagebox(title="Error", message="Please enter a valid email address", icon="cancel")
            return

        if password != confirm_password:
            CTkMessagebox(title="Error", message="Passwords do not match", icon="cancel")
            return

        # Hash password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Determine role based on email domain
        role = 'admin' if email.lower().endswith('@synching-team.com') else 'user'

        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                
                # Check if username or email already exists
                cursor.execute("SELECT username FROM users WHERE username = %s OR email = %s", (username, email))
                if cursor.fetchone():
                    CTkMessagebox(title="Error", message="Username or email already exists", icon="cancel")
                    return

                # Insert new user with hashed password and determined role
                query = "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, email, hashed_password, role))
                connection.commit()
                
                CTkMessagebox(title="Success", message="Registration successful!", icon="check")
                self.show_login()
                
            except Error as e:
                CTkMessagebox(title="Error", message=f"Registration failed: {str(e)}", icon="cancel")
            finally:
                cursor.close()
                connection.close()

    def show_create_group(self):
        self.show_page("create_group")

    def show_no_group_message(self):
        self.show_page("no_group")

    def create_group(self, name, description):
        if not name:
            CTkMessagebox(title="Error", message="Group name cannot be empty", icon="cancel")
            return

        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Create group
                cursor.execute(
                    "INSERT INTO groups (name, description, admin_id) VALUES (%s, %s, %s)",
                    (name, description or None, self.current_user['id'])
                )
                group_id = cursor.lastrowid
                
                # Add admin as member
                cursor.execute(
                    "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                    (group_id, self.current_user['id'])
                )
                connection.commit()
                
                self.current_group = {'id': group_id, 'name': name}
                self.show_main_view()
            finally:
                cursor.close()
                connection.close()

    def add_member(self, identifier):
        if not self.current_group:
            return False
            
        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                # First get user id, role, and check if they're already in any group
                cursor.execute("""
                    SELECT u.id, u.role, u.username,
                           (SELECT COUNT(*) FROM group_members WHERE user_id = u.id) as group_count
                    FROM users u 
                    WHERE u.username = %s OR u.email = %s
                """, (identifier, identifier))
                user = cursor.fetchone()
                
                if not user:
                    return False

                # Check if user is already in any group
                if user['group_count'] > 0:
                    CTkMessagebox(
                        title="Error",
                        message=f"User {user['username']} is already a member of another group",
                        icon="cancel"
                    )
                    return None

                # If user is admin, show warning
                if user['role'] == 'admin':
                    response = CTkMessagebox(
                        title="Warning",
                        message=f"User {user['username']} is an admin. Adding them will give them permission to manage this group. Continue?",
                        icon="warning",
                        option_1="No",
                        option_2="Yes"
                    ).get()
                    
                    if response == "No":
                        return None

                # Add to group if confirmed or not admin
                cursor.execute(
                    "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                    (self.current_group['id'], user['id'])
                )
                connection.commit()
                return user['username']  # Return username for success message
            finally:
                cursor.close()
                connection.close()
        return False

    def remove_member(self, user_id):
        if not self.current_group:
            return False
            
        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Don't allow removing the admin
                if user_id == self.current_user['id']:
                    CTkMessagebox(
                        title="Error",
                        message="You cannot remove yourself as the admin",
                        icon="cancel"
                    )
                    return False

                cursor.execute(
                    "DELETE FROM group_members WHERE group_id = %s AND user_id = %s",
                    (self.current_group['id'], user_id)
                )
                connection.commit()
                return True
            finally:
                cursor.close()
                connection.close()
        return False

    def save_event(self, title, date_str, event_type, description):
        if not title or not date_str:
            CTkMessagebox(title="Error", message="Title and date are required", icon="cancel")
            return False

        try:
            # Validate date format
            event_date = datetime.strptime(date_str, '%Y-%m-%d')
            event_datetime = event_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            CTkMessagebox(title="Error", message="Invalid date format. Use YYYY-MM-DD", icon="cancel")
            return False

        connection = self.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # First get event type id
                cursor.execute("SELECT id FROM event_types WHERE name = %s", (event_type,))
                event_type_id = cursor.fetchone()[0]
                
                # Modified query to not specify id (trigger will handle it)
                query = """
                    INSERT INTO events (group_id, title, description, event_datetime, created_by, event_type_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    self.current_group['id'],
                    title,
                    description,
                    event_datetime,
                    self.current_user['id'],
                    event_type_id
                ))
                connection.commit()
                CTkMessagebox(title="Success", message="Event created successfully!", icon="check")
                return True
            except Error as e:
                CTkMessagebox(title="Error", message=f"Failed to create event: {str(e)}", icon="cancel")
                return False
            finally:
                cursor.close()
                connection.close()
        return False

class BasePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.app = master

    def init_page(self, **kwargs):
        pass

class LoginPage(BasePage):
    def init_page(self, **kwargs):
        # Clear page
        for widget in self.winfo_children():
            widget.destroy()

        # Container frame with reduced top padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(pady=(20, 0))

        ctk.CTkLabel(main_frame, text="Synching-Together Login", font=("Arial", 24)).pack(pady=10)
        
        # Standard width reduced further
        standard_width = 180  # Reduced from 200

        # Entry fields
        username = ctk.CTkEntry(main_frame, 
                              placeholder_text="Username",
                              width=standard_width)
        username.pack(pady=8)
        
        password = ctk.CTkEntry(main_frame, 
                              placeholder_text="Password",
                              show="*",
                              width=standard_width)
        password.pack(pady=8)
        
        # Base button configuration
        base_config = {
            "width": standard_width,
        }
        
        # Login button (solid blue)
        ctk.CTkButton(
            main_frame, 
            text="Login", 
            command=lambda: self.app.login(username.get(), password.get()),
            fg_color="#1F538D",
            hover_color="#164072",
            **base_config
        ).pack(pady=(15, 8))
        
        # Register button (transparent with blue border)
        register_btn = ctk.CTkButton(
            main_frame,
            text="Register",
            command=self.app.show_register,
            fg_color="transparent",
            border_color="#1F538D",
            border_width=2,
            hover_color="#1F538D",
            text_color="#1F538D",
            **base_config
        )
        register_btn.pack(pady=(0, 15))
        
        # Bind hover events to change text color
        register_btn.bind("<Enter>", lambda e: register_btn.configure(text_color="white"))
        register_btn.bind("<Leave>", lambda e: register_btn.configure(text_color="#1F538D"))

class MainPage(BasePage):
    def init_page(self, **kwargs):
        # Clear page
        for widget in self.winfo_children():
            widget.destroy()

        # Create main layout with side panel and content area
        side_panel = ctk.CTkFrame(self, width=200)
        side_panel.pack(side="left", fill="y", padx=10, pady=10)
        side_panel.pack_propagate(False)  # Prevent frame from shrinking

        content_area = ctk.CTkFrame(self)
        content_area.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Side panel content - only username
        ctk.CTkLabel(
            side_panel, 
            text=f"Welcome,\n{self.app.current_user['username']}", 
            font=("Arial", 16)
        ).pack(pady=(20, 10))

        # Standard button width for side panel
        btn_width = 160

        # Admin buttons in side panel
        if self.app.current_user['role'] == "admin":
            ctk.CTkLabel(side_panel, text="Admin Controls:", font=("Arial", 12)).pack(pady=(20, 5))
            
            ctk.CTkButton(
                side_panel,
                text="View Members",
                width=btn_width,
                command=lambda: self.app.show_page("members")
            ).pack(pady=5)
            
            ctk.CTkButton(
                side_panel,
                text="Add Member",
                width=btn_width,
                command=self.show_add_member_dialog
            ).pack(pady=5)
            
            ctk.CTkButton(
                side_panel,
                text="Create Event",
                width=btn_width,
                command=self.app.create_event
            ).pack(pady=5)
            
            ctk.CTkButton(
                side_panel,
                text="Edit Event",
                width=btn_width,
                command=self.app.edit_event
            ).pack(pady=5)
            
            ctk.CTkButton(
                side_panel,
                text="Delete Event",
                width=btn_width,
                command=self.app.delete_event
            ).pack(pady=5)

        # Logout button at bottom of side panel
        ctk.CTkButton(
            side_panel,
            text="Logout",
            width=btn_width,
            command=self.app.show_login
        ).pack(side="bottom", pady=20)

        # Content area header with group name
        content_header = ctk.CTkFrame(content_area)
        content_header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            content_header,
            text=f"Group: {self.app.current_group['name']}",
            font=("Arial", 24)
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            content_header,
            text="Events",
            font=("Arial", 20)
        ).pack(pady=(0, 10))

        # Show events in content area
        self.show_group_events(content_area)

    def show_add_member_dialog(self):
        dialog = ctk.CTkInputDialog(
            text="Enter username or email to add to group:",
            title="Add Member"
        )
        identifier = dialog.get_input()
        if identifier:
            result = self.app.add_member(identifier)
            if isinstance(result, str):  # Success case - returns username
                CTkMessagebox(
                    title="Success",
                    message=f"User {result} added to group successfully!",
                    icon="check"
                )
            elif result is None:  # Already member case
                pass  # Error message already shown by add_member
            else:  # False case - user doesn't exist
                CTkMessagebox(
                    title="Error",
                    message=f"Could not add user. No user found with that username or email.",
                    icon="cancel"
                )

    def show_group_events(self, parent_frame):
        events_frame = ctk.CTkFrame(parent_frame)
        events_frame.pack(pady=10, fill="both", expand=True)
        
        # Fetch events from database
        connection = self.app.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT e.id, e.title, 
                           DATE_FORMAT(e.event_datetime, '%Y-%m-%d') as date,
                           e.description, et.name as type
                    FROM events e
                    LEFT JOIN event_types et ON e.event_type_id = et.id
                    WHERE e.group_id = %s
                    ORDER BY e.event_datetime
                """, (self.app.current_group['id'],))
                
                events = cursor.fetchall()
                
                if not events:
                    ctk.CTkLabel(
                        events_frame,
                        text="No events scheduled",
                        font=("Arial", 14)
                    ).pack(pady=20)
                else:
                    for event in events:
                        event_item = ctk.CTkFrame(events_frame)
                        event_item.pack(pady=5, fill="x", padx=10)
                        
                        # Main label with title and date
                        label = ctk.CTkLabel(
                            event_item, 
                            text=f"{event['title']} ({event['date']})"
                        )
                        label.pack(side="left", padx=10, pady=5)
                        
                        # ID label on the right side
                        id_label = ctk.CTkLabel(
                            event_item,
                            text=f"ID: {event['id']}",
                            text_color="gray"
                        )
                        id_label.pack(side="right", padx=10, pady=5)
                        
                        # Click handler for the entire frame
                        def make_click_handler(evt):
                            return lambda e: self.app.show_event_details(evt)
                        
                        click_handler = make_click_handler(event)
                        event_item.bind("<Button-1>", click_handler)
                        label.bind("<Button-1>", click_handler)
                        id_label.bind("<Button-1>", click_handler)
                
            finally:
                cursor.close()
                connection.close()

class EventDetailsPage(BasePage):
    def init_page(self, **kwargs):
        event = kwargs.get('event')
        
        # Clear page
        for widget in self.winfo_children():
            widget.destroy()

        # Header with back button
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkButton(header, text="← Back", command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Event Details", font=("Arial", 20)).pack(side="left", padx=10)

        # Event details
        details_frame = ctk.CTkFrame(self)
        details_frame.pack(pady=20, padx=20, fill="both", expand=True)

        ctk.CTkLabel(details_frame, text=event['title'], font=("Arial", 24)).pack(pady=10)
        ctk.CTkLabel(details_frame, text=f"Date: {event['date']}").pack(pady=5)
        # Only show type if it exists
        if 'type' in event:
            ctk.CTkLabel(details_frame, text=f"Type: {event['type']}").pack(pady=5)
        ctk.CTkLabel(details_frame, text=f"Description: {event['description']}").pack(pady=5)

class CreateEventPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Header with back button
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkButton(header, text="← Back", command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Create New Event", font=("Arial", 20)).pack(side="left", padx=10)

        # Form fields
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        title = ctk.CTkEntry(form_frame, placeholder_text="Event Title")
        title.pack(pady=10, padx=20, fill="x")
        
        date = ctk.CTkEntry(form_frame, placeholder_text="Date (YYYY-MM-DD)")
        date.pack(pady=10, padx=20, fill="x")
        
        # Get event types from database
        connection = self.app.connect_to_database()
        event_types = ["Brainstorming"]  # Default fallback
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT name FROM event_types ORDER BY id")  # Changed from ORDER BY name
                event_types = [row['name'] for row in cursor.fetchall()]
            finally:
                cursor.close()
                connection.close()
        
        type_var = ctk.StringVar(value=event_types[0])
        type_menu = ctk.CTkOptionMenu(form_frame, 
                                    values=event_types,
                                    variable=type_var)
        type_menu.pack(pady=10, padx=20, fill="x")
        
        description = ctk.CTkTextbox(form_frame, height=100)
        description.pack(pady=10, padx=20, fill="x")
        description.insert("1.0", "Event description...")
        
        def save_event():
            event_saved = self.app.save_event(
                title.get(),
                date.get(),
                type_var.get(),
                description.get("1.0", "end-1c")
            )
            if event_saved:
                self.app.show_main_view()
            
        ctk.CTkButton(form_frame, text="Save Event", command=save_event).pack(pady=20)

class EditEventPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Header with back button
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkButton(header, text="← Back", command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Edit Event", font=("Arial", 20)).pack(side="left", padx=10)

        # Form fields
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        title = ctk.CTkEntry(form_frame, placeholder_text="Event Title")
        title.insert(0, self.app.current_event['title'])
        title.pack(pady=10, padx=20, fill="x")
        
        date = ctk.CTkEntry(form_frame, placeholder_text="Date (YYYY-MM-DD)")
        date.insert(0, self.app.current_event['date'])
        date.pack(pady=10, padx=20, fill="x")
        
        # Get event types from database
        connection = self.app.connect_to_database()
        event_types = ["Brainstorming"]  # Default fallback
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT name FROM event_types ORDER BY id")
                event_types = [row['name'] for row in cursor.fetchall()]
            finally:
                cursor.close()
                connection.close()
                
        type_var = ctk.StringVar(value=self.app.current_event['type'])
        type_menu = ctk.CTkOptionMenu(form_frame, 
                                    values=event_types,
                                    variable=type_var)
        type_menu.pack(pady=10, padx=20, fill="x")
        
        description = ctk.CTkTextbox(form_frame, height=100)
        description.pack(pady=10, padx=20, fill="x")
        description.insert("1.0", self.app.current_event['description'])
        
        def save_changes():
            event_updated = self.app.update_event(
                self.app.current_event['id'],
                title.get(),
                date.get(),
                type_var.get(),
                description.get("1.0", "end-1c")
            )
            if event_updated:
                self.app.show_main_view()
            
        ctk.CTkButton(form_frame, text="Save Changes", command=save_changes).pack(pady=20)

class DeleteEventPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Header with back button
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkButton(header, text="← Back", command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Delete Event", font=("Arial", 20)).pack(side="left", padx=10)

        # Confirmation frame
        confirm_frame = ctk.CTkFrame(self)
        confirm_frame.pack(pady=20, padx=20, fill="both", expand=True)

        ctk.CTkLabel(confirm_frame, 
                    text=f"Are you sure you want to delete the event:\n{self.app.current_event['title']}?",
                    font=("Arial", 16)).pack(pady=20)
        
        buttons_frame = ctk.CTkFrame(confirm_frame)
        buttons_frame.pack(pady=10)
        
        def confirm_delete():
            # Add database integration here
            self.app.show_main_view()
            
        ctk.CTkButton(buttons_frame, text="Cancel", 
                     command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkButton(buttons_frame, text="Delete", 
                     command=confirm_delete).pack(side="left", padx=10)

class RegisterPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Container frame with reduced top padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(pady=(20, 0))

        ctk.CTkLabel(main_frame, text="Create New Account", font=("Arial", 24)).pack(pady=10)
        
        # Standard width reduced further
        standard_width = 180

        # Entry fields
        username = ctk.CTkEntry(main_frame, 
                              placeholder_text="Username",
                              width=standard_width)
        username.pack(pady=8)
        
        email = ctk.CTkEntry(main_frame, 
                           placeholder_text="Email",
                           width=standard_width)
        email.pack(pady=8)
        
        password = ctk.CTkEntry(main_frame, 
                              placeholder_text="Password",
                              show="*",
                              width=standard_width)
        password.pack(pady=8)
        
        confirm_password = ctk.CTkEntry(main_frame, 
                                      placeholder_text="Confirm Password",
                                      show="*",
                                      width=standard_width)
        confirm_password.pack(pady=8)
        
        # Base button configuration
        base_config = {
            "width": standard_width,
        }
        
        # Register button (solid blue)
        ctk.CTkButton(
            main_frame,
            text="Register",
            command=lambda: self.app.register_user(
                username.get(),
                email.get(),
                password.get(),
                confirm_password.get()
            ),
            fg_color="#1F538D",
            hover_color="#164072",
            **base_config
        ).pack(pady=(15, 8))
        
        # Back to Login button (transparent with blue border)
        back_btn = ctk.CTkButton(
            main_frame,
            text="Back to Login",
            command=self.app.show_login,
            fg_color="transparent",
            border_color="#1F538D",
            border_width=2,
            hover_color="#1F538D",
            text_color="#1F538D",
            **base_config
        )
        back_btn.pack(pady=(0, 15))
        
        # Bind hover events to change text color
        back_btn.bind("<Enter>", lambda e: back_btn.configure(text_color="white"))
        back_btn.bind("<Leave>", lambda e: back_btn.configure(text_color="#1F538D"))

class CreateGroupPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Header with title and logout
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkLabel(header, text="Create Your Group", font=("Arial", 24)).pack(side="left", padx=20)
        ctk.CTkButton(
            header,
            text="Logout",
            command=self.app.show_login,
            width=100
        ).pack(side="right", padx=20)

        # Rest of the form
        name = ctk.CTkEntry(self, placeholder_text="Group Name")
        name.pack(pady=10)
        
        description = ctk.CTkTextbox(self, height=100)
        description.pack(pady=10, padx=20, fill="x")
        description.insert("1.0", "")
        
        ctk.CTkButton(
            self,
            text="Create Group",
            command=lambda: self.app.create_group(
                name.get(),
                description.get("1.0", "end-1c")
            )
        ).pack(pady=20)

class NoGroupPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self, 
            text="You are not part of any group.\nPlease ask an admin to add you to a group.",
            font=("Arial", 20)
        ).pack(pady=20)
        
        ctk.CTkButton(
            self,
            text="Logout",
            command=self.app.show_login
        ).pack(pady=20)

class MembersPage(BasePage):
    def init_page(self, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()

        # Header with back button
        header = ctk.CTkFrame(self)
        header.pack(fill="x", pady=10)
        
        ctk.CTkButton(header, text="← Back", command=self.app.show_main_view).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Group Members", font=("Arial", 20)).pack(side="left", padx=10)

        # Members list
        members_frame = ctk.CTkFrame(self)
        members_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Fetch members from database
        connection = self.app.connect_to_database()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT u.id, u.username, u.role, u.email 
                    FROM users u 
                    JOIN group_members gm ON u.id = gm.user_id 
                    WHERE gm.group_id = %s
                    ORDER BY u.username
                """, (self.app.current_group['id'],))
                
                members = cursor.fetchall()
                
                for member in members:
                    member_frame = ctk.CTkFrame(members_frame)
                    member_frame.pack(pady=5, fill="x", padx=10)
                    
                    info_text = f"{member['username']} ({member['role']}) - {member['email']}"
                    ctk.CTkLabel(
                        member_frame,
                        text=info_text
                    ).pack(side="left", padx=10, pady=5)
                    
                    if member['id'] != self.app.current_user['id']:  # Don't show remove button for current user
                        ctk.CTkButton(
                            member_frame,
                            text="Remove",
                            command=lambda m=member: self.remove_member(m),
                            fg_color="red",
                            hover_color="darkred",
                            width=100
                        ).pack(side="right", padx=10, pady=5)
                
            finally:
                cursor.close()
                connection.close()

    def remove_member(self, member):
        if self.app.remove_member(member['id']):
            CTkMessagebox(
                title="Success",
                message=f"Member {member['username']} removed from group",
                icon="check"
            )
            self.app.show_page("members")  # Refresh the page
        else:
            CTkMessagebox(
                title="Error",
                message="Failed to remove member",
                icon="cancel"
            )

if __name__ == "__main__":
    app = SynchingTeamApp()
    app.mainloop()
