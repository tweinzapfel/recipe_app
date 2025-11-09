import streamlit as st
from openai import OpenAI
import os
import base64
from PIL import Image
import io
from datetime import datetime, date
from supabase import create_client, Client

# Initialize session state variables at the very beginning
if 'identified_ingredients' not in st.session_state:
    st.session_state.identified_ingredients = ""
if 'cuisine_shopping_list' not in st.session_state:
    st.session_state.cuisine_shopping_list = ""
if 'fridge_shopping_list' not in st.session_state:
    st.session_state.fridge_shopping_list = ""
if 'photo_shopping_list' not in st.session_state:
    st.session_state.photo_shopping_list = ""
if 'cuisine_recipe_content' not in st.session_state:
    st.session_state.cuisine_recipe_content = ""
if 'fridge_recipe_content' not in st.session_state:
    st.session_state.fridge_recipe_content = ""
if 'photo_recipe_content' not in st.session_state:
    st.session_state.photo_recipe_content = ""
if 'uploaded_photos' not in st.session_state:
    st.session_state.uploaded_photos = []
if 'all_identified_ingredients' not in st.session_state:
    st.session_state.all_identified_ingredients = ""
if 'cuisine_recipe_card' not in st.session_state:
    st.session_state.cuisine_recipe_card = ""
if 'fridge_recipe_card' not in st.session_state:
    st.session_state.fridge_recipe_card = ""
if 'photo_recipe_card' not in st.session_state:
    st.session_state.photo_recipe_card = ""
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'show_saved_recipes' not in st.session_state:
    st.session_state.show_saved_recipes = False

# Initialize Supabase clients
# Add your Supabase credentials to Streamlit secrets
# In your secrets.toml file:
# supabase_url = "your-supabase-url"
# supabase_key = "your-supabase-anon-key"
# supabase_service_role_key = "your-supabase-service-role-key"

def get_supabase_client():
    """Get Supabase client for authentication (uses anon key)"""
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_key"]
    )

def get_supabase_admin_client():
    """Get Supabase admin client for database operations (uses service role key)"""
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_service_role_key"]
    )

try:
    supabase: Client = get_supabase_client()
    supabase_admin: Client = get_supabase_admin_client()
except Exception as e:
    st.error(f"Error connecting to Supabase: {e}")
    supabase = None
    supabase_admin = None

headers = {
    "authorization": st.secrets["api_key"],
    "content-type": "application/json"
}

# Set your OpenAI API key (make sure it's in your environment variables or you can paste it here for testing)
client = OpenAI(api_key=st.secrets["api_key"])

# Function to encode image to base64
def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

# Function to get current holiday or special occasion
def get_current_holiday():
    """Determine if there's a current or upcoming holiday/special occasion"""
    today = date.today()
    month = today.month
    day = today.day
    
    # Define holidays and special occasions with date ranges (month, start_day, end_day, name, description)
    holidays = [
        (1, 1, 1, "New Year's Day", "New Year's celebration recipes"),
        (1, 13, 20, "Martin Luther King Jr. Day Weekend", "comfort food and soul food"),
        (2, 1, 14, "Valentine's Day", "romantic dinners and desserts"),
        (2, 15, 28, "Black History Month", "soul food and African-American cuisine"),
        (3, 1, 17, "St. Patrick's Day", "Irish-inspired dishes"),
        (3, 18, 31, "Spring Season", "fresh spring vegetables and lighter dishes"),
        (4, 1, 30, "Easter Season", "spring brunch and Easter dinner recipes"),
        (5, 1, 15, "Cinco de Mayo", "Mexican-inspired celebration food"),
        (5, 20, 31, "Memorial Day Weekend", "BBQ and grilling recipes"),
        (6, 1, 21, "Father's Day", "hearty grilling and favorite comfort foods"),
        (6, 22, 30, "Summer Season", "light summer meals and grilling"),
        (7, 1, 4, "Independence Day", "BBQ, picnic, and patriotic recipes"),
        (7, 5, 31, "Summer Grilling Season", "outdoor cooking and fresh salads"),
        (8, 1, 31, "Late Summer", "fresh produce and outdoor dining"),
        (9, 1, 22, "Labor Day Weekend", "BBQ and end-of-summer gatherings"),
        (9, 23, 30, "Fall Season", "autumn harvest and comfort food"),
        (10, 1, 31, "Halloween & Fall Harvest", "pumpkin, apple, and festive fall recipes"),
        (11, 1, 15, "Thanksgiving Prep", "Thanksgiving sides and preparations"),
        (11, 16, 30, "Thanksgiving", "traditional Thanksgiving feast recipes"),
        (12, 1, 24, "Christmas & Holiday Season", "festive holiday meals and cookies"),
        (12, 25, 31, "Christmas & New Year's", "holiday leftovers and party food"),
    ]
    
    # Check if today falls within any holiday period
    for hol_month, start_day, end_day, holiday_name, description in holidays:
        if month == hol_month and start_day <= day <= end_day:
            return holiday_name, description
    
    # Default seasonal return
    if month in [12, 1, 2]:
        return "Winter Season", "warming winter comfort foods"
    elif month in [3, 4, 5]:
        return "Spring Season", "fresh spring vegetables and lighter dishes"
    elif month in [6, 7, 8]:
        return "Summer Season", "light summer meals and grilling"
    else:
        return "Fall Season", "autumn harvest and comfort food"

# Function to extract clean recipe name from AI response
def extract_recipe_name(recipe_content):
    """Extract just the recipe name from the AI response"""
    lines = recipe_content.split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Clean up the line
        clean_line = line.strip()
        
        # Skip common non-recipe-name patterns
        skip_patterns = [
            'here', 'recipe', 'suggest', 'perfect', 'delicious', 'enjoy',
            'this is', 'try this', 'servings:', 'prep time:', 'cook time:',
            'ingredients:', 'instructions:', 'directions:', '---', '**'
        ]
        
        # Check if line contains skip patterns (case insensitive)
        if any(pattern in clean_line.lower() for pattern in skip_patterns):
            continue
        
        # Remove markdown formatting
        clean_line = clean_line.replace('#', '').replace('*', '').strip()
        
        # If line is reasonable length for a recipe name (5-80 chars) and doesn't start with a number
        if 5 <= len(clean_line) <= 80 and not clean_line[0].isdigit():
            return clean_line
    
    # Fallback: return first non-empty line, cleaned
    for line in lines:
        clean_line = line.strip().replace('#', '').replace('*', '').strip()
        if clean_line and len(clean_line) > 3:
            return clean_line[:80]  # Limit to 80 chars
    
    return "Untitled Recipe"

# Function to generate shopping list from recipe
def generate_shopping_list(recipe_text, available_ingredients=""):
    try:
        prompt = f"""
        Based on this recipe: {recipe_text}
        
        {"And these ingredients I already have: " + available_ingredients if available_ingredients else ""}
        
        Please create a smart shopping list by:
        1. Extracting all ingredients from the recipe with quantities
        2. {"Separating what I already have vs. what I need to buy" if available_ingredients else "Listing all ingredients I need to buy"}
        3. Organizing by grocery store sections (Produce, Meat/Seafood, Dairy, Pantry, etc.)
        4. Including estimated quantities where specified in the recipe
        
        Format as:
        **SHOPPING LIST**
        
        **Produce:**
        - item (quantity)
        
        **Meat/Seafood:**
        - item (quantity)
        
        **Dairy:**
        - item (quantity)
        
        **Pantry/Dry Goods:**
        - item (quantity)
        
        **Other:**
        - item (quantity)
        
        {"**✅ Items you already have:**" + chr(10) + "- (list items from available ingredients that are used in recipe)" if available_ingredients else ""}
        
        Only include items that need to be purchased. Be specific about quantities when mentioned in the recipe.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful shopping assistant who creates organized grocery lists from recipes."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating shopping list: {e}"

# Function to generate print-friendly recipe card
def generate_recipe_card(recipe_text):
    try:
        prompt = f"""
        Based on this recipe: {recipe_text}
        
        Please create a beautifully formatted, print-friendly recipe card with the following structure:
        
        # [Recipe Name]
        
        **Servings:** [number]  |  **Prep Time:** [time]  |  **Cook Time:** [time]  |  **Total Time:** [time]
        
        ---
        
        ## Ingredients
        
        [List all ingredients with quantities, formatted clearly with bullet points using "- "]
        
        ---
        
        ## Instructions
        
        [IMPORTANT: Number the steps sequentially as 1. 2. 3. 4. etc. NOT as 1. 1. 1. 1.]
        [Each step should be clear and concise]
        [Use actual sequential numbers: 1. First step, 2. Second step, 3. Third step, etc.]
        
        ---
        
        ## Tips & Notes
        
        [Any helpful tips, substitutions, or storage information]
        
        ---
        
        **Recipe generated by Dinner Recipe Maker**
        
        Please format this in a clean, organized way that would look great when printed. 
        CRITICAL: Use sequential numbering for instructions (1. 2. 3. 4. etc.), not repeated "1." for every step.
        Use clear markdown formatting with no extra blank lines between list items.
        If prep/cook times aren't specified in the original recipe, estimate reasonable times based on the recipe complexity.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who creates beautifully formatted, print-friendly recipe cards. Always use sequential numbering (1. 2. 3. 4.) for instructions, never repeat '1.' for each step."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating recipe card: {e}"

# Function to create HTML for recipe card popup
def create_recipe_card_html(recipe_card_content):
    """Convert markdown recipe card to HTML for printing"""
    import re
    
    # Split content into lines for processing
    lines = recipe_card_content.split('\n')
    html_lines = []
    in_unordered_list = False
    in_ordered_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines that would create extra spacing
        if not stripped:
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            continue
        
        # Handle headers
        if stripped.startswith('# '):
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            html_lines.append(f'<h1>{stripped[2:]}</h1>')
        elif stripped.startswith('## '):
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        
        # Handle horizontal rules
        elif stripped == '---':
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            html_lines.append('<hr>')
        
        # Handle unordered list items (bullet points)
        elif stripped.startswith('- '):
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if not in_unordered_list:
                html_lines.append('<ul>')
                in_unordered_list = True
            # Convert bold text within list items
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped[2:])
            html_lines.append(f'<li>{item_text}</li>')
        
        # Handle ordered list items (numbered)
        elif re.match(r'^\d+\.\s', stripped):
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if not in_ordered_list:
                html_lines.append('<ol>')
                in_ordered_list = True
            # Extract the text after the number and period
            item_text = re.sub(r'^\d+\.\s+', '', stripped)
            # Convert bold text within list items
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            html_lines.append(f'<li>{item_text}</li>')
        
        # Handle regular text
        else:
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            # Convert bold text
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_lines.append(f'<p>{text}</p>')
    
    # Close any remaining lists
    if in_unordered_list:
        html_lines.append('</ul>')
    if in_ordered_list:
        html_lines.append('</ol>')
    
    html_content = '\n'.join(html_lines)
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Recipe Card</title>
        <style>
            @media print {{
                body {{ margin: 1in; }}
                button {{ display: none; }}
            }}
            body {{
                font-family: 'Georgia', serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                line-height: 1.6;
                color: #333;
            }}
            h1 {{
                color: #2c5530;
                border-bottom: 3px solid #2c5530;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #5a7d5e;
                margin-top: 30px;
                margin-bottom: 15px;
                font-size: 1.4em;
            }}
            hr {{
                border: none;
                border-top: 1px solid #ddd;
                margin: 20px 0;
            }}
            ul {{
                margin-left: 20px;
                margin-bottom: 20px;
                padding-left: 20px;
            }}
            ol {{
                margin-left: 20px;
                margin-bottom: 20px;
                padding-left: 20px;
            }}
            ul li {{
                margin-bottom: 8px;
                list-style-type: disc;
            }}
            ol li {{
                margin-bottom: 10px;
                list-style-type: decimal;
            }}
            strong {{
                color: #2c5530;
            }}
            p {{
                margin: 8px 0;
            }}
            .print-button {{
                background-color: #2c5530;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 20px 0;
                display: block;
            }}
            .print-button:hover {{
                background-color: #1e3d22;
            }}
            @page {{
                margin: 1in;
            }}
        </style>
    </head>
    <body>
        <button class="print-button" onclick="window.print()">🖨️ Print Recipe Card</button>
        {html_content}
        <button class="print-button" onclick="window.print()">🖨️ Print Recipe Card</button>
    </body>
    </html>
    """
    return full_html

# Streamlit UI
st.title("Dinner Recipe Maker")

# Get current holiday/occasion (do this before any conditional logic)
holiday_name, holiday_desc = get_current_holiday()

# User Authentication Section in Sidebar
with st.sidebar:
    st.markdown("## 👤 Account")
    
    if st.session_state.user is None:
        # Show login/signup options
        auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])
        
        with auth_tab1:
            st.subheader("Login")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_btn"):
                if login_email and login_password:
                    try:
                        response = supabase.auth.sign_in_with_password({
                            "email": login_email,
                            "password": login_password
                        })
                        if response.user:
                            st.session_state.user = response.user.id
                            st.session_state.user_email = response.user.email
                            st.session_state.access_token = response.session.access_token
                            st.success(f"Welcome back, {response.user.email}!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")
                else:
                    st.warning("Please enter email and password")
        
        with auth_tab2:
            st.subheader("Create Account")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
            
            if st.button("Sign Up", key="signup_btn"):
                if signup_email and signup_password:
                    if signup_password == signup_password_confirm:
                        try:
                            response = supabase.auth.sign_up({
                                "email": signup_email,
                                "password": signup_password
                            })
                            if response.user:
                                st.success("Account created! Please check your email to verify your account, then log in.")
                        except Exception as e:
                            st.error(f"Sign up failed: {str(e)}")
                    else:
                        st.error("Passwords don't match!")
                else:
                    st.warning("Please fill in all fields")
    else:
        # User is logged in
        st.success(f"Logged in as: {st.session_state.user_email}")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.user_email = None
            st.session_state.show_saved_recipes = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 My Saved Recipes")
        if st.button("View My Saved Recipes", use_container_width=True):
            st.session_state.show_saved_recipes = True
            st.rerun()

# Check if we should show saved recipes view
if st.session_state.show_saved_recipes:
    # SAVED RECIPES VIEW
    st.title("💾 My Saved Recipes")
    
    # Return button
    if st.button("⬅️ Return to Recipe Generator", key="return_btn"):
        st.session_state.show_saved_recipes = False
        st.rerun()
    
    st.markdown("---")
    
    if st.session_state.user is None:
        st.warning("Please log in to view your saved recipes.")
        st.info("👈 Use the sidebar to log in or create an account.")
    else:
        st.write(f"**Logged in as:** {st.session_state.user_email}")
        
        try:
            # Use admin client to fetch recipes (bypasses RLS but filters by user_id)
            response = supabase_admin.table("saved_recipes").select("*").eq("user_id", st.session_state.user).order("created_at", desc=True).execute()
            
            if response.data and len(response.data) > 0:
                st.success(f"You have {len(response.data)} saved recipe(s)")
                
                # Display each saved recipe
                for idx, recipe in enumerate(response.data):
                    # Build metadata display
                    metadata_parts = []
                    if recipe.get('cuisine'):
                        metadata_parts.append(f"🍽️ {recipe['cuisine']}")
                    if recipe.get('occasion'):
                        metadata_parts.append(f"🎉 {recipe['occasion']}")
                    if recipe.get('meal_type'):
                        metadata_parts.append(f"🍴 {recipe['meal_type']}")
                    if recipe.get('complexity'):
                        metadata_parts.append(f"⚡ {recipe['complexity']}")
                    if recipe.get('cooking_method'):
                        metadata_parts.append(f"🔥 {recipe['cooking_method']}")
                    if recipe.get('dietary_tags') and len(recipe['dietary_tags']) > 0:
                        metadata_parts.append(f"✓ {', '.join(recipe['dietary_tags'])}")
                    
                    metadata_display = " | ".join(metadata_parts) if metadata_parts else ""
                    
                    with st.expander(f"📖 {recipe.get('recipe_name', 'Untitled Recipe')} - {recipe.get('created_at', '')[:10]}"):
                        # Display metadata tags
                        if metadata_display:
                            st.markdown(f"**{metadata_display}**")
                            st.markdown("---")
                        
                        st.markdown("### Recipe Details")
                        st.write(recipe.get('recipe_content', 'No content available'))
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Button to delete recipe
                            if st.button(f"🗑️ Delete", key=f"delete_{recipe['id']}"):
                                try:
                                    supabase_admin.table("saved_recipes").delete().eq("id", recipe['id']).execute()
                                    st.success("Recipe deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting recipe: {e}")
                        
                        with col2:
                            # Button to generate recipe card from saved recipe
                            if st.button(f"🖨️ Print Card", key=f"print_{recipe['id']}"):
                                with st.spinner("Creating recipe card..."):
                                    recipe_card = generate_recipe_card(recipe.get('recipe_content', ''))
                                    recipe_html = create_recipe_card_html(recipe_card)
                                    
                                    # Display the print button
                                    st.components.v1.html(
                                        f"""
                                        <button onclick="openRecipeSaved{idx}()" style="
                                            display: inline-block;
                                            padding: 10px 20px;
                                            background-color: #2c5530;
                                            color: white;
                                            border: none;
                                            border-radius: 5px;
                                            font-weight: bold;
                                            cursor: pointer;
                                            font-size: 14px;
                                        ">
                                            🖨️ Open Recipe Card
                                        </button>
                                        
                                        <script>
                                        function openRecipeSaved{idx}() {{
                                            var recipeHTML = `{recipe_html.replace('`', '\\`')}`;
                                            var newWindow = window.open('', '_blank', 'width=900,height=800');
                                            newWindow.document.write(recipeHTML);
                                            newWindow.document.close();
                                        }}
                                        </script>
                                        """,
                                        height=60
                                    )
                
            else:
                st.info("You haven't saved any recipes yet. Generate a recipe and click the 'Save This Recipe' button!")
                
        except Exception as e:
            st.error(f"Error loading saved recipes: {e}")
            st.info("Make sure your Supabase table is set up correctly.")

else:
    # MAIN RECIPE GENERATOR VIEW
    # Get current holiday/occasion
    holiday_name, holiday_desc = get_current_holiday()

# Display holiday banner if applicable
if holiday_name and "Season" not in holiday_name:
    st.info(f"🎉 **{holiday_name}!** Perfect time for {holiday_desc}. Check out our special occasion recipes below!")
elif holiday_name:
    st.success(f"🍂 **{holiday_name}** - Great time for {holiday_desc}")

# Add tabs for different recipe modes
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Recipe by Cuisine", "Recipe by Fridge Items", "Photo Recipe Finder", "🎉 Holiday & Special Occasions", "💾 My Saved Recipes"])

with tab1:
    st.header("Find Recipe by Cuisine & Preferences")
    
    # Cuisine dropdown
    cuisine = st.selectbox(
        "Select a cuisine type:",
        [
        "American",
        "Barbecue",
        "Chinese",
        "French",
        "Greek",
        "Indian",
        "Italian",
        "Japanese",
        "Korean",
        "Latin American",
        "Mediterranean",
        "Mexican",
        "Middle Eastern",
        "Seafood",
        "Southern/Soul Food",
        "Tex-Mex",
        "Thai",
        "Vegan/Vegetarian",
        "Vietnamese",
        "Other"
    ]
    )

    # Meal type and cooking preferences
    col1, col2 = st.columns(2)
    
    with col1:
        meal_type = st.selectbox(
            "What type of meal?",
            ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", "Snack", "Dessert", "Side Dish"]
        )
        
        complexity = st.selectbox(
            "Select cooking complexity:",
            ["Easy", "Medium", "Hard"]
        )
    
    with col2:
        cooking_method = st.selectbox(
            "Preferred cooking method:",
            ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", "Instant Pot/Pressure cooker", 
             "Oven/Baking", "Stovetop", "Grilling", "No-cook/Raw", "Microwave"]
        )
        
        portion_size = st.selectbox(
            "How many servings?",
            ["1 person", "2 people", "3-4 people (family)", "5-6 people", "Large group (8+ people)"]
        )

    # Dietary restrictions
    st.subheader("Dietary Preferences")
    col1, col2 = st.columns(2)
    
    with col1:
        vegetarian = st.checkbox("Vegetarian")
        vegan = st.checkbox("Vegan")
        pescatarian = st.checkbox("Pescatarian")
        gluten_free = st.checkbox("Gluten-free")
        dairy_free = st.checkbox("Dairy-free")
        high_fiber = st.checkbox("High fiber")
    
    with col2:
        keto = st.checkbox("Keto")
        paleo = st.checkbox("Paleo")
        low_carb = st.checkbox("Low-carb")
        low_sodium = st.checkbox("Low-sodium")
        high_protein = st.checkbox("High protein")
    
    # Allergy restrictions
    allergies = st.multiselect(
        "Any food allergies to avoid?",
        ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"]
    )
    
    # Special instructions
    instructions = st.text_input("Any other special instructions or preferences?")

    # Submit button
    if st.button("Suggest Recipe", key="cuisine_recipe"):
        # Build dietary restrictions list
        dietary_restrictions = []
        if vegetarian: dietary_restrictions.append("vegetarian")
        if vegan: dietary_restrictions.append("vegan")
        if pescatarian: dietary_restrictions.append("pescatarian")
        if gluten_free: dietary_restrictions.append("gluten-free")
        if dairy_free: dietary_restrictions.append("dairy-free")
        if keto: dietary_restrictions.append("keto")
        if paleo: dietary_restrictions.append("paleo")
        if low_carb: dietary_restrictions.append("low-carb")
        if low_sodium: dietary_restrictions.append("low-sodium")
        if high_fiber: dietary_restrictions.append("high-fiber")
        if high_protein: dietary_restrictions.append("high-protein")
        
        prompt = f"Suggest a {complexity.lower()} {cuisine.lower()} {meal_type.lower()} recipe for {portion_size}"
        
        if cooking_method != "Any method":
            method_mapping = {
                "One-pot/One-pan": "one-pot or one-pan",
                "Slow cooker": "slow cooker",
                "Air fryer": "air fryer",
                "Instant Pot/Pressure cooker": "Instant Pot or pressure cooker",
                "Oven/Baking": "oven-baked",
                "Stovetop": "stovetop",
                "Grilling": "grilled",
                "No-cook/Raw": "no-cook",
                "Microwave": "microwave"
            }
            prompt += f" using {method_mapping[cooking_method]}"
        
        if dietary_restrictions:
            prompt += f" that is {', '.join(dietary_restrictions)}"
        
        if allergies:
            allergy_list = ', '.join([allergy.lower() for allergy in allergies])
            prompt += f". Avoid these allergens: {allergy_list}"
        
        if instructions:
            prompt += f". Also, consider this: {instructions}"
        prompt += ". Include ingredients and step-by-step instructions."

        # Make request to OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful chef assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            recipe_content = response.choices[0].message.content
            st.session_state.cuisine_recipe_content = recipe_content
            # Clear shopping list when new recipe is generated
            st.session_state.cuisine_shopping_list = ""
        except Exception as e:
            st.error(f"An error occurred: {e}")
    
    # Display recipe if it exists in session state
    if st.session_state.cuisine_recipe_content:
        st.markdown("### Suggested Recipe")
        st.write(st.session_state.cuisine_recipe_content)
        
        # Add shopping list and recipe card generation
        st.markdown("---")
        
        # Show save button prominently if user is logged in
        if st.session_state.user:
            if st.button("💾 Save This Recipe", key="save_cuisine_recipe", use_container_width=True):
                try:
                    # Extract clean recipe name using helper function
                    recipe_name = extract_recipe_name(st.session_state.cuisine_recipe_content)
                    
                    # Build dietary tags array
                    dietary_tags = []
                    if vegetarian: dietary_tags.append("Vegetarian")
                    if vegan: dietary_tags.append("Vegan")
                    if pescatarian: dietary_tags.append("Pescatarian")
                    if gluten_free: dietary_tags.append("Gluten-free")
                    if dairy_free: dietary_tags.append("Dairy-free")
                    if keto: dietary_tags.append("Keto")
                    if paleo: dietary_tags.append("Paleo")
                    if low_carb: dietary_tags.append("Low-carb")
                    if low_sodium: dietary_tags.append("Low-sodium")
                    if high_protein: dietary_tags.append("High Protein")
                    if high_fiber: dietary_tags.append("High Fiber")
                    
                    # Use admin client for database operations (bypasses RLS)
                    data = {
                        "user_id": st.session_state.user,
                        "recipe_name": recipe_name,
                        "recipe_content": st.session_state.cuisine_recipe_content,
                        "recipe_type": "cuisine",
                        "cuisine": cuisine,
                        "meal_type": meal_type,
                        "complexity": complexity,
                        "occasion": None,
                        "cooking_method": cooking_method if cooking_method != "Any method" else None,
                        "dietary_tags": dietary_tags,
                        "created_at": datetime.now().isoformat()
                    }
                    response = supabase_admin.table("saved_recipes").insert(data).execute()
                    st.success("✅ Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                except Exception as e:
                    st.error(f"Error saving recipe: {e}")
            
            st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🛒 Generate Shopping List", key="cuisine_shopping_list_btn"):
                with st.spinner("Creating your shopping list..."):
                    shopping_list = generate_shopping_list(st.session_state.cuisine_recipe_content)
                    st.session_state.cuisine_shopping_list = shopping_list
        
        with col2:
            if st.button("🖨️ Create Recipe Card", key="cuisine_recipe_card_btn"):
                with st.spinner("Creating your recipe card..."):
                    recipe_card = generate_recipe_card(st.session_state.cuisine_recipe_content)
                    st.session_state.cuisine_recipe_card = recipe_card
        
        # Display shopping list if it exists
        if st.session_state.cuisine_shopping_list:
            st.markdown("### 🛒 Smart Shopping List")
            st.write(st.session_state.cuisine_shopping_list)
        
        # Display recipe card if it exists
        if st.session_state.cuisine_recipe_card:
            # Create HTML for the recipe card
            recipe_html = create_recipe_card_html(st.session_state.cuisine_recipe_card)
            
            # Use HTML with onclick to open new window
            st.components.v1.html(
                f"""
                <button onclick="openRecipe()" style="
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #2c5530;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 14px;
                ">
                    🖨️ Open Recipe Card in New Window (Ready to Print)
                </button>
                
                <script>
                function openRecipe() {{
                    var recipeHTML = `{recipe_html.replace('`', '\\`')}`;
                    var newWindow = window.open('', '_blank', 'width=900,height=800');
                    newWindow.document.write(recipeHTML);
                    newWindow.document.close();
                }}
                </script>
                """,
                height=60
            )
    
    else:
        st.info("📝 Create an account and log in to save your favorite recipes!")

with tab2:
    st.header("Find Recipe by What's in Your Fridge")
    
    # Fridge items input
    st.subheader("What ingredients do you have?")
    fridge_items = st.text_area(
        "List the ingredients you have available (separate with commas):",
        placeholder="e.g., chicken, rice, onions, bell peppers, garlic, tomatoes",
        height=100
    )
    
    # Additional preferences for fridge mode
    st.subheader("Preferences")
    # Meal type and cooking preferences for fridge mode
    col1, col2 = st.columns(2)
    
    with col1:
        fridge_meal_type = st.selectbox(
            "What type of meal?",
            ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", "Snack", "Dessert", "Side Dish"],
            key="fridge_meal_type"
        )
        
        fridge_complexity = st.selectbox(
            "Cooking complexity:",
            ["Easy", "Medium", "Hard"],
            key="fridge_complexity"
        )
    
    with col2:
        fridge_cooking_method = st.selectbox(
            "Preferred cooking method:",
            ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", "Instant Pot/Pressure cooker", 
             "Oven/Baking", "Stovetop", "Grilling", "No-cook/Raw", "Microwave"],
            key="fridge_cooking_method"
        )
        
        fridge_portion_size = st.selectbox(
            "How many servings?",
            ["1 person", "2 people", "3-4 people (family)", "5-6 people", "Large group (8+ people)"],
            key="fridge_portion_size"
        )
    # Time and ingredient preferences
    col3, col4 = st.columns(2)
    
    with col3:
        cooking_time = st.selectbox(
            "How much time do you have?",
            ["Quick (under 30 min)", "Medium (30-60 min)", "I have time (60+ min)"]
        )
    
    with col4:
        allow_additional = st.checkbox(
            "Allow recipes that need a few additional common ingredients?",
            value=True,
            help="If checked, recipes may include common pantry items you might not have listed"
        )
    
    # Dietary restrictions for fridge mode
    st.subheader("Dietary Preferences")
    col3, col4 = st.columns(2)
    
    with col3:
        fridge_vegetarian = st.checkbox("Vegetarian", key="fridge_vegetarian")
        fridge_vegan = st.checkbox("Vegan", key="fridge_vegan")
        fridge_pescatarian = st.checkbox("Pescatarian", key="fridge_pescatarian")
        fridge_gluten_free = st.checkbox("Gluten-free", key="fridge_gluten_free")
        fridge_dairy_free = st.checkbox("Dairy-free", key="fridge_dairy_free")
        fridge_high_fiber = st.checkbox("High fiber", key="fridge_high_fiber")
    
    with col4:
        fridge_keto = st.checkbox("Keto", key="fridge_keto")
        fridge_paleo = st.checkbox("Paleo", key="fridge_paleo")
        fridge_low_carb = st.checkbox("Low-carb", key="fridge_low_carb")
        fridge_low_sodium = st.checkbox("Low-sodium", key="fridge_low_sodium")
        fridge_high_protein = st.checkbox("High protein", key="fridge_high_protein")
    
    # Allergy restrictions for fridge mode
    fridge_allergies = st.multiselect(
        "Any food allergies to avoid?",
        ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"],
        key="fridge_allergies"
    )
    
    # Special dietary restrictions or preferences
    fridge_instructions = st.text_input(
        "Any dietary restrictions or special requests?",
        key="fridge_instructions"
    )

    # Submit button for fridge mode
    if st.button("Find Recipe with My Ingredients", key="fridge_recipe"):
        if not fridge_items.strip():
            st.warning("Please enter at least some ingredients from your fridge!")
        else:
            # Build prompt for fridge-based recipe
            time_mapping = {
                "Quick (under 30 min)": "quick and easy, taking less than 30 minutes",
                "Medium (30-60 min)": "moderate cooking time, around 30-60 minutes", 
                "I have time (60+ min)": "can take longer to prepare, 60+ minutes"
            }
            
            # Build dietary restrictions list for fridge mode
            fridge_dietary_restrictions = []
            if fridge_vegetarian: fridge_dietary_restrictions.append("vegetarian")
            if fridge_vegan: fridge_dietary_restrictions.append("vegan")
            if fridge_pescatarian: fridge_dietary_restrictions.append("pescatarian")
            if fridge_gluten_free: fridge_dietary_restrictions.append("gluten-free")
            if fridge_dairy_free: fridge_dietary_restrictions.append("dairy-free")
            if fridge_keto: fridge_dietary_restrictions.append("keto")
            if fridge_paleo: fridge_dietary_restrictions.append("paleo")
            if fridge_low_carb: fridge_dietary_restrictions.append("low-carb")
            if fridge_low_sodium: fridge_dietary_restrictions.append("low-sodium")
            if fridge_high_fiber: fridge_dietary_restrictions.append("high-fiber")
            if fridge_high_protein: fridge_dietary_restrictions.append("high-protein")
            
            prompt = f"I have these ingredients available: {fridge_items}. "
            prompt += f"Please suggest a {fridge_complexity.lower()} {fridge_meal_type.lower()} recipe for {fridge_portion_size} that is {time_mapping[cooking_time]}"
            
            if fridge_cooking_method != "Any method":
                method_mapping = {
                    "One-pot/One-pan": "one-pot or one-pan",
                    "Slow cooker": "slow cooker",
                    "Air fryer": "air fryer",
                    "Instant Pot/Pressure cooker": "Instant Pot or pressure cooker",
                    "Oven/Baking": "oven-baked",
                    "Stovetop": "stovetop",
                    "Grilling": "grilled",
                    "No-cook/Raw": "no-cook",
                    "Microwave": "microwave"
                }
                prompt += f" using {method_mapping[fridge_cooking_method]}"
            
            if fridge_dietary_restrictions:
                prompt += f" and {', '.join(fridge_dietary_restrictions)}"
            
            if fridge_allergies:
                fridge_allergy_list = ', '.join([allergy.lower() for allergy in fridge_allergies])
                prompt += f". Avoid these allergens: {fridge_allergy_list}"
            
            if allow_additional:
                prompt += ". You can suggest recipes that use most of these ingredients and may require a few common pantry staples (like oil, salt, pepper, basic spices) that most people have."
            else:
                prompt += ". Please try to use primarily the ingredients I've listed."
            
            if fridge_instructions:
                prompt += f" Also consider: {fridge_instructions}"
            
            prompt += " Include a complete ingredient list (highlighting what I already have vs. what I might need to get) and step-by-step cooking instructions."

            # Make request to OpenAI
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful chef assistant who specializes in creating recipes based on available ingredients. Always clearly indicate which ingredients the user already has vs. which they might need to purchase."},
                        {"role": "user", "content": prompt}
                    ]
                )
                recipe_content = response.choices[0].message.content
                st.session_state.fridge_recipe_content = recipe_content
                # Clear shopping list when new recipe is generated
                st.session_state.fridge_shopping_list = ""
            except Exception as e:
                st.error(f"An error occurred: {e}")
    
    # Display recipe if it exists in session state
    if st.session_state.fridge_recipe_content:
        st.markdown("### Recipe Based on Your Ingredients")
        st.write(st.session_state.fridge_recipe_content)
        
        # Add shopping list and recipe card generation
        st.markdown("---")
        
        # Show save button prominently if user is logged in
        if st.session_state.user:
            if st.button("💾 Save This Recipe", key="save_fridge_recipe", use_container_width=True):
                try:
                    # Extract clean recipe name using helper function
                    recipe_name = extract_recipe_name(st.session_state.fridge_recipe_content)
                    
                    # Build dietary tags array
                    dietary_tags = []
                    if fridge_vegetarian: dietary_tags.append("Vegetarian")
                    if fridge_vegan: dietary_tags.append("Vegan")
                    if fridge_pescatarian: dietary_tags.append("Pescatarian")
                    if fridge_gluten_free: dietary_tags.append("Gluten-free")
                    if fridge_dairy_free: dietary_tags.append("Dairy-free")
                    if fridge_keto: dietary_tags.append("Keto")
                    if fridge_paleo: dietary_tags.append("Paleo")
                    if fridge_low_carb: dietary_tags.append("Low-carb")
                    if fridge_low_sodium: dietary_tags.append("Low-sodium")
                    if fridge_high_protein: dietary_tags.append("High Protein")
                    if fridge_high_fiber: dietary_tags.append("High Fiber")
                    
                    # Use admin client for database operations (bypasses RLS)
                    data = {
                        "user_id": st.session_state.user,
                        "recipe_name": recipe_name,
                        "recipe_content": st.session_state.fridge_recipe_content,
                        "recipe_type": "fridge",
                        "cuisine": None,
                        "meal_type": fridge_meal_type,
                        "complexity": fridge_complexity,
                        "occasion": None,
                        "cooking_method": fridge_cooking_method if fridge_cooking_method != "Any method" else None,
                        "dietary_tags": dietary_tags,
                        "created_at": datetime.now().isoformat()
                    }
                    response = supabase_admin.table("saved_recipes").insert(data).execute()
                    st.success("✅ Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                except Exception as e:
                    st.error(f"Error saving recipe: {e}")
            
            st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🛒 Generate Shopping List", key="fridge_shopping_list_btn"):
                with st.spinner("Creating your shopping list..."):
                    # Get the current fridge items from the text area
                    current_fridge_items = st.session_state.get('fridge_items_current', fridge_items)
                    shopping_list = generate_shopping_list(st.session_state.fridge_recipe_content, current_fridge_items)
                    st.session_state.fridge_shopping_list = shopping_list
        
        with col2:
            if st.button("🖨️ Create Recipe Card", key="fridge_recipe_card_btn"):
                with st.spinner("Creating your recipe card..."):
                    recipe_card = generate_recipe_card(st.session_state.fridge_recipe_content)
                    st.session_state.fridge_recipe_card = recipe_card
        
        # Display shopping list if it exists
        if st.session_state.fridge_shopping_list:
            st.markdown("### 🛒 Smart Shopping List")
            st.write(st.session_state.fridge_shopping_list)
        
        # Display recipe card if it exists
        if st.session_state.fridge_recipe_card:
            # Create HTML for the recipe card
            recipe_html = create_recipe_card_html(st.session_state.fridge_recipe_card)
            
            # Use HTML with onclick to open new window
            st.components.v1.html(
                f"""
                <button onclick="openRecipeFridge()" style="
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #2c5530;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 14px;
                ">
                    🖨️ Open Recipe Card in New Window (Ready to Print)
                </button>
                
                <script>
                function openRecipeFridge() {{
                    var recipeHTML = `{recipe_html.replace('`', '\\`')}`;
                    var newWindow = window.open('', '_blank', 'width=900,height=800');
                    newWindow.document.write(recipeHTML);
                    newWindow.document.close();
                }}
                </script>
                """,
                height=60
            )

with tab3:
    st.header("Photo Recipe Finder")
    st.write("Take a photo of your fridge, pantry, or ingredients and I'll identify what you have and suggest recipes!")
    
    # Camera input
    camera_photo = st.camera_input("Take a photo of your ingredients")
    
    # Initialize session state for identified ingredients
    if 'identified_ingredients' not in st.session_state:
        st.session_state.identified_ingredients = ""
    
    if camera_photo is not None:
        # Display the photo
        st.image(camera_photo, caption="Your ingredient photo", width=300)
        
        # Button to analyze the photo
        if st.button("🔍 Identify Ingredients in Photo", key="analyze_photo"):
            with st.spinner("Analyzing your photo..."):
                try:
                    # Convert the image to PIL format
                    image = Image.open(camera_photo)
                    
                    # Encode image to base64
                    base64_image = encode_image(image)
                    
                    # Make request to OpenAI Vision API
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Please identify all the food ingredients, items, and products you can see in this image. List them as a comma-separated list. Focus on ingredients that could be used for cooking. Include fresh produce, packaged goods, dairy products, meats, spices, condiments, etc. Be specific about types (e.g., 'red bell peppers' instead of just 'peppers'). Only list food items that are clearly visible and identifiable."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )
                    
                    # Store identified ingredients in session state
                    st.session_state.identified_ingredients = response.choices[0].message.content
                    
                    st.success("✅ Ingredients identified!")
                    
                except Exception as e:
                    st.error(f"Error analyzing image: {e}")
    
    # Display and allow editing of identified ingredients
    if st.session_state.identified_ingredients:
        st.subheader("📝 Identified Ingredients")
        
        # Editable text area with identified ingredients
        photo_ingredients = st.text_area(
            "Review and edit the ingredients I found:",
            value=st.session_state.identified_ingredients,
            height=120,
            help="You can add, remove, or modify any ingredients before generating a recipe"
        )
        
        # Recipe preferences for photo mode
        st.subheader("Recipe Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            photo_meal_type = st.selectbox(
                "What type of meal?",
                ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", "Snack", "Dessert", "Side Dish"],
                key="photo_meal_type"
            )
            
            photo_complexity = st.selectbox(
                "Cooking complexity:",
                ["Easy", "Medium", "Hard"],
                key="photo_complexity"
            )
        
        with col2:
            photo_cooking_method = st.selectbox(
                "Preferred cooking method:",
                ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", "Instant Pot/Pressure cooker", 
                 "Oven/Baking", "Stovetop", "Grilling", "No-cook/Raw", "Microwave"],
                key="photo_cooking_method"
            )
            
            photo_portion_size = st.selectbox(
                "How many servings?",
                ["1 person", "2 people", "3-4 people (family)", "5-6 people", "Large group (8+ people)"],
                key="photo_portion_size"
            )
        
        # Time and additional ingredients
        col3, col4 = st.columns(2)
        
        with col3:
            photo_cooking_time = st.selectbox(
                "How much time do you have?",
                ["Quick (under 30 min)", "Medium (30-60 min)", "I have time (60+ min)"],
                key="photo_cooking_time"
            )
        
        with col4:
            photo_allow_additional = st.checkbox(
                "Allow recipes that need a few additional common ingredients?",
                value=True,
                key="photo_allow_additional",
                help="If checked, recipes may include common pantry items you might not have"
            )
        
        # Dietary restrictions for photo mode
        st.subheader("Dietary Preferences")
        col5, col6 = st.columns(2)
        
        with col5:
            photo_vegetarian = st.checkbox("Vegetarian", key="photo_vegetarian")
            photo_vegan = st.checkbox("Vegan", key="photo_vegan")
            photo_pescatarian = st.checkbox("Pescatarian", key="photo_pescatarian")
            photo_gluten_free = st.checkbox("Gluten-free", key="photo_gluten_free")
            photo_dairy_free = st.checkbox("Dairy-free", key="photo_dairy_free")
            photo_high_fiber = st.checkbox("High fiber", key="photo_high_fiber")
        
        with col6:
            photo_keto = st.checkbox("Keto", key="photo_keto")
            photo_paleo = st.checkbox("Paleo", key="photo_paleo")
            photo_low_carb = st.checkbox("Low-carb", key="photo_low_carb")
            photo_low_sodium = st.checkbox("Low-sodium", key="photo_low_sodium")
            photo_high_protein = st.checkbox("High protein", key="photo_high_protein")
        
        # Allergy restrictions for photo mode
        photo_allergies = st.multiselect(
            "Any food allergies to avoid?",
            ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"],
            key="photo_allergies"
        )
        
        # Special instructions for photo mode
        photo_instructions = st.text_input(
            "Any special instructions or preferences?",
            key="photo_instructions"
        )
        
        # Generate recipe button
        if st.button("🍳 Generate Recipe from Photo", key="photo_recipe"):
            if not photo_ingredients.strip():
                st.warning("Please make sure there are ingredients listed above!")
            else:
                # Build prompt for photo-based recipe
                time_mapping = {
                    "Quick (under 30 min)": "quick and easy, taking less than 30 minutes",
                    "Medium (30-60 min)": "moderate cooking time, around 30-60 minutes", 
                    "I have time (60+ min)": "can take longer to prepare, 60+ minutes"
                }
                
                # Build dietary restrictions list for photo mode
                photo_dietary_restrictions = []
                if photo_vegetarian: photo_dietary_restrictions.append("vegetarian")
                if photo_vegan: photo_dietary_restrictions.append("vegan")
                if photo_pescatarian: photo_dietary_restrictions.append("pescatarian")
                if photo_gluten_free: photo_dietary_restrictions.append("gluten-free")
                if photo_dairy_free: photo_dietary_restrictions.append("dairy-free")
                if photo_keto: photo_dietary_restrictions.append("keto")
                if photo_paleo: photo_dietary_restrictions.append("paleo")
                if photo_low_carb: photo_dietary_restrictions.append("low-carb")
                if photo_low_sodium: photo_dietary_restrictions.append("low-sodium")
                if photo_high_fiber: photo_dietary_restrictions.append("high-fiber")
                if photo_high_protein: photo_dietary_restrictions.append("high-protein")
                
                prompt = f"Based on these ingredients I have from my photo: {photo_ingredients}. "
                prompt += f"Please suggest a {photo_complexity.lower()} {photo_meal_type.lower()} recipe for {photo_portion_size} that is {time_mapping[photo_cooking_time]}"
                
                if photo_cooking_method != "Any method":
                    method_mapping = {
                        "One-pot/One-pan": "one-pot or one-pan",
                        "Slow cooker": "slow cooker",
                        "Air fryer": "air fryer",
                        "Instant Pot/Pressure cooker": "Instant Pot or pressure cooker",
                        "Oven/Baking": "oven-baked",
                        "Stovetop": "stovetop",
                        "Grilling": "grilled",
                        "No-cook/Raw": "no-cook",
                        "Microwave": "microwave"
                    }
                    prompt += f" using {method_mapping[photo_cooking_method]}"
                
                if photo_dietary_restrictions:
                    prompt += f" and {', '.join(photo_dietary_restrictions)}"
                
                if photo_allergies:
                    photo_allergy_list = ', '.join([allergy.lower() for allergy in photo_allergies])
                    prompt += f". Avoid these allergens: {photo_allergy_list}"
                
                if photo_allow_additional:
                    prompt += ". You can suggest recipes that use most of these ingredients and may require a few common pantry staples (like oil, salt, pepper, basic spices) that most people have."
                else:
                    prompt += ". Please try to use primarily the ingredients I've identified from my photo."
                
                if photo_instructions:
                    prompt += f" Also consider: {photo_instructions}"
                
                prompt += " Include a complete ingredient list (highlighting what I already have from the photo vs. what I might need to get) and step-by-step cooking instructions."

                # Make request to OpenAI
                try:
                    with st.spinner("Creating your recipe..."):
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "You are a helpful chef assistant who specializes in creating recipes based on ingredients identified from photos. Always clearly indicate which ingredients the user already has vs. which they might need to purchase."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        recipe_content = response.choices[0].message.content
                        st.session_state.photo_recipe_content = recipe_content
                        # Clear shopping list when new recipe is generated
                        st.session_state.photo_shopping_list = ""
                except Exception as e:
                    st.error(f"An error occurred while generating the recipe: {e}")
        
        # Display recipe if it exists in session state
        if st.session_state.photo_recipe_content:
            st.markdown("### 📸 Recipe Based on Your Photo")
            st.write(st.session_state.photo_recipe_content)
            
            # Add shopping list and recipe card generation
            st.markdown("---")
            
            # Show save button prominently if user is logged in
            if st.session_state.user:
                if st.button("💾 Save This Recipe", key="save_photo_recipe", use_container_width=True):
                    try:
                        # Extract clean recipe name using helper function
                        recipe_name = extract_recipe_name(st.session_state.photo_recipe_content)
                        
                        # Build dietary tags array
                        dietary_tags = []
                        if photo_vegetarian: dietary_tags.append("Vegetarian")
                        if photo_vegan: dietary_tags.append("Vegan")
                        if photo_pescatarian: dietary_tags.append("Pescatarian")
                        if photo_gluten_free: dietary_tags.append("Gluten-free")
                        if photo_dairy_free: dietary_tags.append("Dairy-free")
                        if photo_keto: dietary_tags.append("Keto")
                        if photo_paleo: dietary_tags.append("Paleo")
                        if photo_low_carb: dietary_tags.append("Low-carb")
                        if photo_low_sodium: dietary_tags.append("Low-sodium")
                        if photo_high_protein: dietary_tags.append("High Protein")
                        if photo_high_fiber: dietary_tags.append("High Fiber")
                        
                        # Use admin client for database operations (bypasses RLS)
                        data = {
                            "user_id": st.session_state.user,
                            "recipe_name": recipe_name,
                            "recipe_content": st.session_state.photo_recipe_content,
                            "recipe_type": "photo",
                            "cuisine": None,
                            "meal_type": photo_meal_type,
                            "complexity": photo_complexity,
                            "occasion": None,
                            "cooking_method": photo_cooking_method if photo_cooking_method != "Any method" else None,
                            "dietary_tags": dietary_tags,
                            "created_at": datetime.now().isoformat()
                        }
                        response = supabase_admin.table("saved_recipes").insert(data).execute()
                        st.success("✅ Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                    except Exception as e:
                        st.error(f"Error saving recipe: {e}")
                
                st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🛒 Generate Shopping List", key="photo_shopping_list_btn"):
                    with st.spinner("Creating your shopping list..."):
                        shopping_list = generate_shopping_list(st.session_state.photo_recipe_content, photo_ingredients)
                        st.session_state.photo_shopping_list = shopping_list
            
            with col2:
                if st.button("🖨️ Create Recipe Card", key="photo_recipe_card_btn"):
                    with st.spinner("Creating your recipe card..."):
                        recipe_card = generate_recipe_card(st.session_state.photo_recipe_content)
                        st.session_state.photo_recipe_card = recipe_card
            
            # Display shopping list if it exists
            if st.session_state.photo_shopping_list:
                st.markdown("### 🛒 Smart Shopping List")
                st.write(st.session_state.photo_shopping_list)
            
            # Display recipe card if it exists
            if st.session_state.photo_recipe_card:
                # Create HTML for the recipe card
                recipe_html = create_recipe_card_html(st.session_state.photo_recipe_card)
                
                # Use HTML with onclick to open new window
                st.components.v1.html(
                    f"""
                    <button onclick="openRecipePhoto()" style="
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #2c5530;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-weight: bold;
                        cursor: pointer;
                        font-size: 14px;
                    ">
                        🖨️ Open Recipe Card in New Window (Ready to Print)
                    </button>
                    
                    <script>
                    function openRecipePhoto() {{
                        var recipeHTML = `{recipe_html.replace('`', '\\`')}`;
                        var newWindow = window.open('', '_blank', 'width=900,height=800');
                        newWindow.document.write(recipeHTML);
                        newWindow.document.close();
                    }}
                    </script>
                    """,
                    height=60
                )
    
    else:
        st.info("👆 Take a photo of your ingredients to get started!")
        st.markdown("""
        **Tips for better ingredient identification:**
        - Make sure ingredients are well-lit and clearly visible
        - Try to capture labels on packaged items
        - Spread items out so they're not overlapping
        - Take the photo from a good angle where items are recognizable
        """)

with tab4:
    st.header("🎉 Holiday & Special Occasion Recipes")
    
    # Display current holiday
    st.markdown(f"### Currently: **{holiday_name}**")
    st.write(f"*{holiday_desc.capitalize()}*")
    
    st.markdown("---")
    
    # Holiday selector
    st.subheader("Choose Your Holiday or Occasion")
    
    occasion = st.selectbox(
        "Select a holiday or special occasion:",
        [
            "Current Holiday/Season (Recommended)",
            "New Year's Day",
            "Valentine's Day",
            "St. Patrick's Day",
            "Easter",
            "Cinco de Mayo",
            "Mother's Day",
            "Father's Day",
            "Independence Day (4th of July)",
            "Labor Day",
            "Halloween",
            "Thanksgiving",
            "Christmas",
            "Hanukkah",
            "New Year's Eve",
            "Birthday Party",
            "Baby Shower",
            "Bridal Shower",
            "Wedding Reception",
            "Graduation Party",
            "Game Day/Super Bowl",
            "Picnic",
            "Potluck Dinner"
        ]
    )
    
    # If current holiday is selected, use the detected one
    if occasion == "Current Holiday/Season (Recommended)":
        selected_occasion = holiday_name
    else:
        selected_occasion = occasion
    
    # Recipe type for occasions
    col1, col2 = st.columns(2)
    
    with col1:
        occasion_meal_type = st.selectbox(
            "What type of dish?",
            ["Main Course", "Appetizer/Starter", "Side Dish", "Dessert", "Cocktail/Beverage", "Full Menu"],
            key="occasion_meal_type"
        )
        
        occasion_complexity = st.selectbox(
            "Cooking complexity:",
            ["Easy", "Medium", "Hard", "Show-stopping (Impressive)"],
            key="occasion_complexity"
        )
    
    with col2:
        occasion_serving_style = st.selectbox(
            "Serving style:",
            ["Family-style", "Plated/Individual", "Buffet", "Appetizer bites", "Cocktail party"],
            key="occasion_serving_style"
        )
        
        occasion_portion_size = st.selectbox(
            "How many guests?",
            ["2 people", "4-6 people", "8-10 people", "12-15 people", "Large party (20+ people)"],
            key="occasion_portion_size"
        )
    
    # Special requirements for occasions
    st.subheader("Special Requirements")
    
    col3, col4 = st.columns(2)
    
    with col3:
        make_ahead = st.checkbox("Can be made ahead of time", value=False)
        crowd_pleaser = st.checkbox("Crowd-pleaser (appeals to most tastes)", value=True)
        budget_friendly = st.checkbox("Budget-friendly", value=False)
    
    with col4:
        impressive = st.checkbox("Visually impressive presentation", value=False)
        traditional = st.checkbox("Traditional/Classic recipe", value=False)
        modern_twist = st.checkbox("Modern twist on classic", value=False)
    
    # Dietary restrictions for holiday recipes
    st.subheader("Dietary Preferences")
    col5, col6 = st.columns(2)
    
    with col5:
        occasion_vegetarian = st.checkbox("Vegetarian", key="occasion_vegetarian")
        occasion_vegan = st.checkbox("Vegan", key="occasion_vegan")
        occasion_pescatarian = st.checkbox("Pescatarian", key="occasion_pescatarian")
        occasion_gluten_free = st.checkbox("Gluten-free", key="occasion_gluten_free")
        occasion_dairy_free = st.checkbox("Dairy-free", key="occasion_dairy_free")
        occasion_high_fiber = st.checkbox("High fiber", key="occasion_high_fiber")
    
    with col6:
        occasion_keto = st.checkbox("Keto", key="occasion_keto")
        occasion_paleo = st.checkbox("Paleo", key="occasion_paleo")
        occasion_low_carb = st.checkbox("Low-carb", key="occasion_low_carb")
        occasion_nut_free = st.checkbox("Nut-free", key="occasion_nut_free")
        occasion_high_protein = st.checkbox("High protein", key="occasion_high_protein")
    
    # Additional preferences
    occasion_notes = st.text_area(
        "Any special requests or theme?",
        placeholder="e.g., 'elegant and sophisticated', 'fun for kids', 'Southern-style', 'comfort food'",
        key="occasion_notes"
    )
    
    # Generate holiday recipe
    if st.button("🎉 Get Holiday Recipe Suggestions", key="occasion_recipe_btn"):
        # Build the prompt
        occasion_dietary_restrictions = []
        if occasion_vegetarian: occasion_dietary_restrictions.append("vegetarian")
        if occasion_vegan: occasion_dietary_restrictions.append("vegan")
        if occasion_pescatarian: occasion_dietary_restrictions.append("pescatarian")
        if occasion_gluten_free: occasion_dietary_restrictions.append("gluten-free")
        if occasion_dairy_free: occasion_dietary_restrictions.append("dairy-free")
        if occasion_keto: occasion_dietary_restrictions.append("keto")
        if occasion_paleo: occasion_dietary_restrictions.append("paleo")
        if occasion_low_carb: occasion_dietary_restrictions.append("low-carb")
        if occasion_nut_free: occasion_dietary_restrictions.append("nut-free")
        if occasion_high_fiber: occasion_dietary_restrictions.append("high-fiber")
        if occasion_high_protein: occasion_dietary_restrictions.append("high-protein")
        
        special_reqs = []
        if make_ahead: special_reqs.append("can be made ahead of time")
        if crowd_pleaser: special_reqs.append("crowd-pleaser that appeals to most tastes")
        if budget_friendly: special_reqs.append("budget-friendly")
        if impressive: special_reqs.append("visually impressive presentation")
        if traditional: special_reqs.append("traditional/classic recipe")
        if modern_twist: special_reqs.append("modern twist on a classic")
        
        prompt = f"Suggest a {occasion_complexity.lower()} {occasion_meal_type.lower()} recipe perfect for {selected_occasion} "
        prompt += f"serving {occasion_portion_size} in a {occasion_serving_style.lower()} style. "
        
        if occasion_dietary_restrictions:
            prompt += f"The recipe should be {', '.join(occasion_dietary_restrictions)}. "
        
        if special_reqs:
            prompt += f"Important: The recipe should be {', '.join(special_reqs)}. "
        
        if occasion_notes:
            prompt += f"Additional theme/request: {occasion_notes}. "
        
        prompt += f"Make sure the recipe is festive and appropriate for {selected_occasion}. "
        prompt += "Include a brief introduction explaining why this recipe is perfect for the occasion, "
        prompt += "then provide the full ingredient list and step-by-step instructions. "
        
        if make_ahead:
            prompt += "Include make-ahead instructions and timeline. "
        
        if impressive:
            prompt += "Include plating/presentation suggestions. "
        
        # Make request to OpenAI
        try:
            with st.spinner(f"Creating the perfect recipe for {selected_occasion}..."):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are a helpful chef assistant who specializes in creating festive recipes for holidays and special occasions. You understand the traditions and flavors associated with {selected_occasion}."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.session_state.occasion_recipe_content = response.choices[0].message.content
                # Clear shopping list and recipe card when new recipe is generated
                st.session_state.occasion_shopping_list = ""
                st.session_state.occasion_recipe_card = ""
        except Exception as e:
            st.error(f"An error occurred: {e}")
    
    # Display holiday recipe if it exists
    if 'occasion_recipe_content' not in st.session_state:
        st.session_state.occasion_recipe_content = ""
    if 'occasion_shopping_list' not in st.session_state:
        st.session_state.occasion_shopping_list = ""
    if 'occasion_recipe_card' not in st.session_state:
        st.session_state.occasion_recipe_card = ""
    
    if st.session_state.occasion_recipe_content:
        st.markdown(f"### 🎉 {selected_occasion} Recipe")
        st.write(st.session_state.occasion_recipe_content)
        
        # Add shopping list and recipe card generation
        st.markdown("---")
        
        # Show save button prominently if user is logged in
        if st.session_state.user:
            if st.button("💾 Save This Recipe", key="save_occasion_recipe", use_container_width=True):
                try:
                    # Extract clean recipe name using helper function
                    recipe_name = extract_recipe_name(st.session_state.occasion_recipe_content)
                    
                    # Build dietary tags array
                    dietary_tags = []
                    if occasion_vegetarian: dietary_tags.append("Vegetarian")
                    if occasion_vegan: dietary_tags.append("Vegan")
                    if occasion_pescatarian: dietary_tags.append("Pescatarian")
                    if occasion_gluten_free: dietary_tags.append("Gluten-free")
                    if occasion_dairy_free: dietary_tags.append("Dairy-free")
                    if occasion_keto: dietary_tags.append("Keto")
                    if occasion_paleo: dietary_tags.append("Paleo")
                    if occasion_low_carb: dietary_tags.append("Low-carb")
                    if occasion_nut_free: dietary_tags.append("Nut-free")
                    if occasion_high_protein: dietary_tags.append("High Protein")
                    if occasion_high_fiber: dietary_tags.append("High Fiber")
                    
                    # Use admin client for database operations (bypasses RLS)
                    data = {
                        "user_id": st.session_state.user,
                        "recipe_name": recipe_name,
                        "recipe_content": st.session_state.occasion_recipe_content,
                        "recipe_type": "occasion",
                        "cuisine": None,
                        "meal_type": occasion_meal_type,
                        "complexity": occasion_complexity,
                        "occasion": selected_occasion,
                        "cooking_method": None,
                        "dietary_tags": dietary_tags,
                        "created_at": datetime.now().isoformat()
                    }
                    response = supabase_admin.table("saved_recipes").insert(data).execute()
                    st.success("✅ Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                except Exception as e:
                    st.error(f"Error saving recipe: {e}")
            
            st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🛒 Generate Shopping List", key="occasion_shopping_list_btn"):
                with st.spinner("Creating your shopping list..."):
                    shopping_list = generate_shopping_list(st.session_state.occasion_recipe_content)
                    st.session_state.occasion_shopping_list = shopping_list
        
        with col2:
            if st.button("🖨️ Create Recipe Card", key="occasion_recipe_card_btn"):
                with st.spinner("Creating your recipe card..."):
                    recipe_card = generate_recipe_card(st.session_state.occasion_recipe_content)
                    st.session_state.occasion_recipe_card = recipe_card
        
        # Display shopping list if it exists
        if st.session_state.occasion_shopping_list:
            st.markdown("### 🛒 Smart Shopping List")
            st.write(st.session_state.occasion_shopping_list)
        
        # Display recipe card if it exists
        if st.session_state.occasion_recipe_card:
            # Create HTML for the recipe card
            recipe_html = create_recipe_card_html(st.session_state.occasion_recipe_card)
            
            # Use HTML with onclick to open new window
            st.components.v1.html(
                f"""
                <button onclick="openRecipeOccasion()" style="
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #2c5530;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 14px;
                ">
                    🖨️ Open Recipe Card in New Window (Ready to Print)
                </button>
                
                <script>
                function openRecipeOccasion() {{
                    var recipeHTML = `{recipe_html.replace('`', '\\`')}`;
                    var newWindow = window.open('', '_blank', 'width=900,height=800');
                    newWindow.document.write(recipeHTML);
                    newWindow.document.close();
                }}
                </script>
                """,
                height=60
            )


