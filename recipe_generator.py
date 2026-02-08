"""
Recipe Generator Module
Handles all recipe generation functionality for different modes
"""

import streamlit as st
from openai import OpenAI
import base64
from PIL import Image
import io
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from utils import (
    get_openai_client,
    generate_shopping_list,
    generate_recipe_card,
    create_recipe_card_html,
    extract_recipe_name
)

class RecipeGenerator:
    """Handles recipe generation for all modes"""
    
    def __init__(self):
        """Initialize the recipe generator"""
        self.client = get_openai_client()
    
    def encode_image(self, image) -> str:
        """
        Encode image to base64
        
        Args:
            image: PIL Image object
            
        Returns:
            str: Base64 encoded image
        """
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    def generate_recipe(self, prompt: str, system_message: str = "You are a helpful chef assistant.") -> str:
        """
        Generate a recipe using OpenAI
        
        Args:
            prompt: The recipe generation prompt
            system_message: System message for the AI
            
        Returns:
            str: Generated recipe content
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return ""
    
    def build_dietary_restrictions(self, checkbox_states: Dict[str, bool]) -> List[str]:
        """
        Build a list of dietary restrictions from checkbox states
        
        Args:
            checkbox_states: Dictionary of dietary restriction checkboxes
            
        Returns:
            List of dietary restriction strings
        """
        restrictions = []
        mapping = {
            'vegetarian': 'vegetarian',
            'vegan': 'vegan',
            'pescatarian': 'pescatarian',
            'gluten_free': 'gluten-free',
            'dairy_free': 'dairy-free',
            'keto': 'keto',
            'paleo': 'paleo',
            'low_carb': 'low-carb',
            'low_sodium': 'low-sodium',
            'high_fiber': 'high-fiber',
            'high_protein': 'high-protein'
        }
        
        for key, label in mapping.items():
            if checkbox_states.get(key, False):
                restrictions.append(label)
        
        return restrictions
    
    def build_dietary_tags(self, checkbox_states: Dict[str, bool]) -> List[str]:
        """
        Build a list of dietary tags for saving
        
        Args:
            checkbox_states: Dictionary of dietary restriction checkboxes
            
        Returns:
            List of dietary tag strings
        """
        tags = []
        mapping = {
            'vegetarian': 'Vegetarian',
            'vegan': 'Vegan',
            'pescatarian': 'Pescatarian',
            'gluten_free': 'Gluten-free',
            'dairy_free': 'Dairy-free',
            'keto': 'Keto',
            'paleo': 'Paleo',
            'low_carb': 'Low-carb',
            'low_sodium': 'Low-sodium',
            'high_fiber': 'High Fiber',
            'high_protein': 'High Protein',
            'nut_free': 'Nut-free'
        }
        
        for key, label in mapping.items():
            if checkbox_states.get(key, False):
                tags.append(label)
        
        return tags
    
    def render_recipe_output(self, recipe_content: str, recipe_type: str, 
                           shopping_list_key: str, recipe_card_key: str,
                           available_ingredients: str = ""):
        """
        Render recipe output with shopping list and recipe card buttons
        
        Args:
            recipe_content: The generated recipe content
            recipe_type: Type of recipe for session state keys
            shopping_list_key: Button key for shopping list
            recipe_card_key: Button key for recipe card
            available_ingredients: Optional ingredients user already has
        """
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🛒 Generate Shopping List", key=shopping_list_key):
                with st.spinner("Creating your shopping list..."):
                    shopping_list = generate_shopping_list(recipe_content, available_ingredients)
                    st.session_state[f"{recipe_type}_shopping_list"] = shopping_list
        
        with col2:
            if st.button("🖨️ Create Recipe Card", key=recipe_card_key):
                with st.spinner("Creating your recipe card..."):
                    recipe_card = generate_recipe_card(recipe_content)
                    st.session_state[f"{recipe_type}_recipe_card"] = recipe_card
        
        # Display shopping list if it exists
        if st.session_state.get(f"{recipe_type}_shopping_list"):
            st.markdown("### 🛒 Smart Shopping List")
            st.write(st.session_state[f"{recipe_type}_shopping_list"])
        
        # Display recipe card if it exists
        if st.session_state.get(f"{recipe_type}_recipe_card"):
            recipe_html = create_recipe_card_html(st.session_state[f"{recipe_type}_recipe_card"])

            # Unique function name for each recipe type
            func_name = f"openRecipe{recipe_type.capitalize()}"

            # Base64-encode HTML to prevent XSS from AI-generated content
            encoded_html = base64.b64encode(recipe_html.encode('utf-8')).decode('ascii')

            st.components.v1.html(
                f"""
                <button onclick="{func_name}()" style="
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
                function {func_name}() {{
                    var encoded = "{encoded_html}";
                    var recipeHTML = decodeURIComponent(escape(atob(encoded)));
                    var newWindow = window.open('', '_blank', 'width=900,height=800');
                    newWindow.document.write(recipeHTML);
                    newWindow.document.close();
                }}
                </script>
                """,
                height=60
            )
    
    def render_cuisine_tab(self, saved_recipes_manager):
        """Render the cuisine-based recipe generation tab"""
        st.header("Find Recipe by Cuisine & Preferences")
        
        # Cuisine dropdown
        cuisine = st.selectbox(
            "Select a cuisine type:",
            ["American", "Barbecue", "Chinese", "French", "Greek", "Indian", 
             "Italian", "Japanese", "Korean", "Latin American", "Mediterranean",
             "Mexican", "Middle Eastern", "Seafood", "Southern/Soul Food",
             "Tex-Mex", "Thai", "Vegan/Vegetarian", "Vietnamese", "Other"]
        )

        # Meal type and cooking preferences
        col1, col2 = st.columns(2)
        
        with col1:
            meal_type = st.selectbox(
                "What type of meal?",
                ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", 
                 "Snack", "Dessert", "Side Dish"]
            )
            
            complexity = st.selectbox(
                "Select cooking complexity:",
                ["Easy", "Medium", "Hard"]
            )
        
        with col2:
            cooking_method = st.selectbox(
                "Preferred cooking method:",
                ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", 
                 "Instant Pot/Pressure cooker", "Oven/Baking", "Stovetop", 
                 "Grilling", "No-cook/Raw", "Microwave"]
            )
            
            portion_size = st.selectbox(
                "How many servings?",
                ["1 person", "2 people", "3-4 people (family)", 
                 "5-6 people", "Large group (8+ people)"]
            )

        # Dietary restrictions
        st.subheader("Dietary Preferences")
        col3, col4 = st.columns(2)
        
        dietary_checkboxes = {}
        with col3:
            dietary_checkboxes['vegetarian'] = st.checkbox("Vegetarian")
            dietary_checkboxes['vegan'] = st.checkbox("Vegan")
            dietary_checkboxes['pescatarian'] = st.checkbox("Pescatarian")
            dietary_checkboxes['gluten_free'] = st.checkbox("Gluten-free")
            dietary_checkboxes['dairy_free'] = st.checkbox("Dairy-free")
            dietary_checkboxes['high_fiber'] = st.checkbox("High fiber")
        
        with col4:
            dietary_checkboxes['keto'] = st.checkbox("Keto")
            dietary_checkboxes['paleo'] = st.checkbox("Paleo")
            dietary_checkboxes['low_carb'] = st.checkbox("Low-carb")
            dietary_checkboxes['low_sodium'] = st.checkbox("Low-sodium")
            dietary_checkboxes['high_protein'] = st.checkbox("High protein")
        
        # Allergy restrictions
        allergies = st.multiselect(
            "Any food allergies to avoid?",
            ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"]
        )
        
        # Special instructions
        instructions = st.text_input("Any other special instructions or preferences?")

        # Submit button
        if st.button("Suggest Recipe", key="cuisine_recipe"):
            dietary_restrictions = self.build_dietary_restrictions(dietary_checkboxes)
            
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

            recipe_content = self.generate_recipe(prompt)
            if recipe_content:
                st.session_state.cuisine_recipe_content = recipe_content
                st.session_state.cuisine_shopping_list = ""
        
        # Display recipe if it exists
        if st.session_state.cuisine_recipe_content:
            st.markdown("### Suggested Recipe")
            st.write(st.session_state.cuisine_recipe_content)
            
            st.markdown("---")
            
            # Save button
            if st.session_state.user:
                dietary_tags = self.build_dietary_tags(dietary_checkboxes)
                
                metadata = {
                    "cuisine": cuisine,
                    "meal_type": meal_type,
                    "complexity": complexity,
                    "occasion": None,
                    "cooking_method": cooking_method if cooking_method != "Any method" else None,
                    "dietary_tags": dietary_tags
                }
                
                saved_recipes_manager.render_save_button(
                    st.session_state.cuisine_recipe_content,
                    "cuisine",
                    metadata,
                    "save_cuisine_recipe"
                )
                st.markdown("---")
            
            # Shopping list and recipe card buttons
            self.render_recipe_output(
                st.session_state.cuisine_recipe_content,
                "cuisine",
                "cuisine_shopping_list_btn",
                "cuisine_recipe_card_btn"
            )
    
    def render_fridge_tab(self, saved_recipes_manager):
        """Render the fridge-based recipe generation tab"""
        st.header("Find Recipe by What's in Your Fridge")
        
        # Fridge items input
        st.subheader("What ingredients do you have?")
        fridge_items = st.text_area(
            "List the ingredients you have available (separate with commas):",
            placeholder="e.g., chicken, rice, onions, bell peppers, garlic, tomatoes",
            height=100
        )
        
        # Additional preferences
        st.subheader("Preferences")
        col1, col2 = st.columns(2)
        
        with col1:
            fridge_meal_type = st.selectbox(
                "What type of meal?",
                ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", 
                 "Snack", "Dessert", "Side Dish"],
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
                ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", 
                 "Instant Pot/Pressure cooker", "Oven/Baking", "Stovetop", 
                 "Grilling", "No-cook/Raw", "Microwave"],
                key="fridge_cooking_method"
            )
            
            fridge_portion_size = st.selectbox(
                "How many servings?",
                ["1 person", "2 people", "3-4 people (family)", 
                 "5-6 people", "Large group (8+ people)"],
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
        
        # Dietary restrictions
        st.subheader("Dietary Preferences")
        col5, col6 = st.columns(2)
        
        fridge_dietary_checkboxes = {}
        with col5:
            fridge_dietary_checkboxes['vegetarian'] = st.checkbox("Vegetarian", key="fridge_vegetarian")
            fridge_dietary_checkboxes['vegan'] = st.checkbox("Vegan", key="fridge_vegan")
            fridge_dietary_checkboxes['pescatarian'] = st.checkbox("Pescatarian", key="fridge_pescatarian")
            fridge_dietary_checkboxes['gluten_free'] = st.checkbox("Gluten-free", key="fridge_gluten_free")
            fridge_dietary_checkboxes['dairy_free'] = st.checkbox("Dairy-free", key="fridge_dairy_free")
            fridge_dietary_checkboxes['high_fiber'] = st.checkbox("High fiber", key="fridge_high_fiber")
        
        with col6:
            fridge_dietary_checkboxes['keto'] = st.checkbox("Keto", key="fridge_keto")
            fridge_dietary_checkboxes['paleo'] = st.checkbox("Paleo", key="fridge_paleo")
            fridge_dietary_checkboxes['low_carb'] = st.checkbox("Low-carb", key="fridge_low_carb")
            fridge_dietary_checkboxes['low_sodium'] = st.checkbox("Low-sodium", key="fridge_low_sodium")
            fridge_dietary_checkboxes['high_protein'] = st.checkbox("High protein", key="fridge_high_protein")
        
        # Allergy restrictions
        fridge_allergies = st.multiselect(
            "Any food allergies to avoid?",
            ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"],
            key="fridge_allergies"
        )
        
        fridge_instructions = st.text_input(
            "Any dietary restrictions or special requests?",
            key="fridge_instructions"
        )

        # Submit button
        if st.button("Find Recipe with My Ingredients", key="fridge_recipe"):
            if not fridge_items.strip():
                st.warning("Please enter at least some ingredients from your fridge!")
            else:
                time_mapping = {
                    "Quick (under 30 min)": "quick and easy, taking less than 30 minutes",
                    "Medium (30-60 min)": "moderate cooking time, around 30-60 minutes", 
                    "I have time (60+ min)": "can take longer to prepare, 60+ minutes"
                }
                
                fridge_dietary_restrictions = self.build_dietary_restrictions(fridge_dietary_checkboxes)
                
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

                system_msg = "You are a helpful chef assistant who specializes in creating recipes based on available ingredients. Always clearly indicate which ingredients the user already has vs. which they might need to purchase."
                recipe_content = self.generate_recipe(prompt, system_msg)
                
                if recipe_content:
                    st.session_state.fridge_recipe_content = recipe_content
                    st.session_state.fridge_shopping_list = ""
                    # Store the fridge items for shopping list generation
                    st.session_state.fridge_items_current = fridge_items
        
        # Display recipe if it exists
        if st.session_state.fridge_recipe_content:
            st.markdown("### Recipe Based on Your Ingredients")
            st.write(st.session_state.fridge_recipe_content)
            
            st.markdown("---")
            
            # Save button
            if st.session_state.user:
                dietary_tags = self.build_dietary_tags(fridge_dietary_checkboxes)
                
                metadata = {
                    "cuisine": None,
                    "meal_type": fridge_meal_type,
                    "complexity": fridge_complexity,
                    "occasion": None,
                    "cooking_method": fridge_cooking_method if fridge_cooking_method != "Any method" else None,
                    "dietary_tags": dietary_tags
                }
                
                saved_recipes_manager.render_save_button(
                    st.session_state.fridge_recipe_content,
                    "fridge",
                    metadata,
                    "save_fridge_recipe"
                )
                st.markdown("---")
            
            # Shopping list and recipe card buttons with available ingredients
            available_ingredients = st.session_state.get('fridge_items_current', fridge_items)
            self.render_recipe_output(
                st.session_state.fridge_recipe_content,
                "fridge",
                "fridge_shopping_list_btn",
                "fridge_recipe_card_btn",
                available_ingredients
            )
    
    def render_photo_tab(self, saved_recipes_manager):
        """Render the photo-based recipe generation tab"""
        st.header("Photo Recipe Finder")
        st.write("Take a photo of your fridge, pantry, or ingredients and I'll identify what you have and suggest recipes!")
        
        # Camera input
        camera_photo = st.camera_input("Take a photo of your ingredients")
        
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
                        base64_image = self.encode_image(image)
                        
                        # Make request to OpenAI Vision API
                        response = self.client.chat.completions.create(
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
                    ["Dinner", "Lunch", "Breakfast/Brunch", "Appetizer", 
                     "Snack", "Dessert", "Side Dish"],
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
                    ["Any method", "One-pot/One-pan", "Slow cooker", "Air fryer", 
                     "Instant Pot/Pressure cooker", "Oven/Baking", "Stovetop", 
                     "Grilling", "No-cook/Raw", "Microwave"],
                    key="photo_cooking_method"
                )
                
                photo_portion_size = st.selectbox(
                    "How many servings?",
                    ["1 person", "2 people", "3-4 people (family)", 
                     "5-6 people", "Large group (8+ people)"],
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
            
            photo_dietary_checkboxes = {}
            with col5:
                photo_dietary_checkboxes['vegetarian'] = st.checkbox("Vegetarian", key="photo_vegetarian")
                photo_dietary_checkboxes['vegan'] = st.checkbox("Vegan", key="photo_vegan")
                photo_dietary_checkboxes['pescatarian'] = st.checkbox("Pescatarian", key="photo_pescatarian")
                photo_dietary_checkboxes['gluten_free'] = st.checkbox("Gluten-free", key="photo_gluten_free")
                photo_dietary_checkboxes['dairy_free'] = st.checkbox("Dairy-free", key="photo_dairy_free")
                photo_dietary_checkboxes['high_fiber'] = st.checkbox("High fiber", key="photo_high_fiber")
            
            with col6:
                photo_dietary_checkboxes['keto'] = st.checkbox("Keto", key="photo_keto")
                photo_dietary_checkboxes['paleo'] = st.checkbox("Paleo", key="photo_paleo")
                photo_dietary_checkboxes['low_carb'] = st.checkbox("Low-carb", key="photo_low_carb")
                photo_dietary_checkboxes['low_sodium'] = st.checkbox("Low-sodium", key="photo_low_sodium")
                photo_dietary_checkboxes['high_protein'] = st.checkbox("High protein", key="photo_high_protein")
            
            # Allergy restrictions
            photo_allergies = st.multiselect(
                "Any food allergies to avoid?",
                ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Other"],
                key="photo_allergies"
            )
            
            photo_instructions = st.text_input(
                "Any special instructions or preferences?",
                key="photo_instructions"
            )
            
            # Generate recipe button
            if st.button("🍳 Generate Recipe from Photo", key="photo_recipe"):
                if not photo_ingredients.strip():
                    st.warning("Please make sure there are ingredients listed above!")
                else:
                    time_mapping = {
                        "Quick (under 30 min)": "quick and easy, taking less than 30 minutes",
                        "Medium (30-60 min)": "moderate cooking time, around 30-60 minutes", 
                        "I have time (60+ min)": "can take longer to prepare, 60+ minutes"
                    }
                    
                    photo_dietary_restrictions = self.build_dietary_restrictions(photo_dietary_checkboxes)
                    
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

                    system_msg = "You are a helpful chef assistant who specializes in creating recipes based on ingredients identified from photos. Always clearly indicate which ingredients the user already has vs. which they might need to purchase."
                    
                    with st.spinner("Creating your recipe..."):
                        recipe_content = self.generate_recipe(prompt, system_msg)
                        
                        if recipe_content:
                            st.session_state.photo_recipe_content = recipe_content
                            st.session_state.photo_shopping_list = ""
                            # Store the photo ingredients for shopping list generation
                            st.session_state.photo_ingredients_current = photo_ingredients
            
            # Display recipe if it exists
            if st.session_state.photo_recipe_content:
                st.markdown("### 📸 Recipe Based on Your Photo")
                st.write(st.session_state.photo_recipe_content)
                
                st.markdown("---")
                
                # Save button
                if st.session_state.user:
                    dietary_tags = self.build_dietary_tags(photo_dietary_checkboxes)
                    
                    metadata = {
                        "cuisine": None,
                        "meal_type": photo_meal_type,
                        "complexity": photo_complexity,
                        "occasion": None,
                        "cooking_method": photo_cooking_method if photo_cooking_method != "Any method" else None,
                        "dietary_tags": dietary_tags
                    }
                    
                    saved_recipes_manager.render_save_button(
                        st.session_state.photo_recipe_content,
                        "photo",
                        metadata,
                        "save_photo_recipe"
                    )
                    st.markdown("---")
                
                # Shopping list and recipe card buttons with photo ingredients
                available_ingredients = st.session_state.get('photo_ingredients_current', photo_ingredients)
                self.render_recipe_output(
                    st.session_state.photo_recipe_content,
                    "photo",
                    "photo_shopping_list_btn",
                    "photo_recipe_card_btn",
                    available_ingredients
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
    
    def render_holiday_tab(self, saved_recipes_manager, holiday_name: str, holiday_desc: str):
        """Render the holiday/occasion recipe generation tab"""
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
                "New Year's Day", "Valentine's Day", "St. Patrick's Day",
                "Easter", "Cinco de Mayo", "Mother's Day", "Father's Day",
                "Independence Day (4th of July)", "Labor Day", "Halloween",
                "Thanksgiving", "Christmas", "Hanukkah", "New Year's Eve",
                "Birthday Party", "Baby Shower", "Bridal Shower",
                "Wedding Reception", "Graduation Party", "Game Day/Super Bowl",
                "Picnic", "Potluck Dinner"
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
                ["Main Course", "Appetizer/Starter", "Side Dish", "Dessert", 
                 "Cocktail/Beverage", "Full Menu"],
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
                ["Family-style", "Plated/Individual", "Buffet", 
                 "Appetizer bites", "Cocktail party"],
                key="occasion_serving_style"
            )
            
            occasion_portion_size = st.selectbox(
                "How many guests?",
                ["2 people", "4-6 people", "8-10 people", 
                 "12-15 people", "Large party (20+ people)"],
                key="occasion_portion_size"
            )
        
        # Special requirements
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
        
        # Dietary restrictions
        st.subheader("Dietary Preferences")
        col5, col6 = st.columns(2)
        
        occasion_dietary_checkboxes = {}
        with col5:
            occasion_dietary_checkboxes['vegetarian'] = st.checkbox("Vegetarian", key="occasion_vegetarian")
            occasion_dietary_checkboxes['vegan'] = st.checkbox("Vegan", key="occasion_vegan")
            occasion_dietary_checkboxes['pescatarian'] = st.checkbox("Pescatarian", key="occasion_pescatarian")
            occasion_dietary_checkboxes['gluten_free'] = st.checkbox("Gluten-free", key="occasion_gluten_free")
            occasion_dietary_checkboxes['dairy_free'] = st.checkbox("Dairy-free", key="occasion_dairy_free")
            occasion_dietary_checkboxes['high_fiber'] = st.checkbox("High fiber", key="occasion_high_fiber")
        
        with col6:
            occasion_dietary_checkboxes['keto'] = st.checkbox("Keto", key="occasion_keto")
            occasion_dietary_checkboxes['paleo'] = st.checkbox("Paleo", key="occasion_paleo")
            occasion_dietary_checkboxes['low_carb'] = st.checkbox("Low-carb", key="occasion_low_carb")
            occasion_dietary_checkboxes['nut_free'] = st.checkbox("Nut-free", key="occasion_nut_free")
            occasion_dietary_checkboxes['high_protein'] = st.checkbox("High protein", key="occasion_high_protein")
        
        # Additional preferences
        occasion_notes = st.text_area(
            "Any special requests or theme?",
            placeholder="e.g., 'elegant and sophisticated', 'fun for kids', 'Southern-style', 'comfort food'",
            key="occasion_notes"
        )
        
        # Generate holiday recipe
        if st.button("🎉 Get Holiday Recipe Suggestions", key="occasion_recipe_btn"):
            occasion_dietary_restrictions = self.build_dietary_restrictions(occasion_dietary_checkboxes)
            
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
            
            system_msg = f"You are a helpful chef assistant who specializes in creating festive recipes for holidays and special occasions. You understand the traditions and flavors associated with {selected_occasion}."
            
            with st.spinner(f"Creating the perfect recipe for {selected_occasion}..."):
                recipe_content = self.generate_recipe(prompt, system_msg)
                
                if recipe_content:
                    st.session_state.occasion_recipe_content = recipe_content
                    st.session_state.occasion_shopping_list = ""
                    st.session_state.occasion_recipe_card = ""
        
        # Display recipe if it exists
        if st.session_state.occasion_recipe_content:
            st.markdown(f"### 🎉 {selected_occasion} Recipe")
            st.write(st.session_state.occasion_recipe_content)
            
            st.markdown("---")
            
            # Save button
            if st.session_state.user:
                dietary_tags = self.build_dietary_tags(occasion_dietary_checkboxes)
                
                metadata = {
                    "cuisine": None,
                    "meal_type": occasion_meal_type,
                    "complexity": occasion_complexity,
                    "occasion": selected_occasion,
                    "cooking_method": None,
                    "dietary_tags": dietary_tags
                }
                
                saved_recipes_manager.render_save_button(
                    st.session_state.occasion_recipe_content,
                    "occasion",
                    metadata,
                    "save_occasion_recipe"
                )
                st.markdown("---")
            
            # Shopping list and recipe card buttons
            self.render_recipe_output(
                st.session_state.occasion_recipe_content,
                "occasion",
                "occasion_shopping_list_btn",
                "occasion_recipe_card_btn"
            )
