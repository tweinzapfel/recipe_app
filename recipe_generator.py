"""
Recipe Generator Module
Handles all recipe generation functionality for different modes
"""

import streamlit as st
import base64
import random
from PIL import Image
import io
from typing import Dict, Any, List
from utils import (
    get_openai_client,
    generate_shopping_list,
    generate_recipe_card,
    create_recipe_card_html,
    extract_recipe_name,
    generate_nutritional_info,
    generate_substitutions,
    scale_recipe
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
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return ""

    def _append_preferences_to_prompt(self, prompt: str) -> str:
        """
        Append sidebar preferences (servings, time, dietary, allergies,
        spice, budget, leftovers) to any recipe prompt.
        """
        servings = st.session_state.get('pref_servings', 4)
        time_limit = st.session_state.get('pref_time_limit', 30)
        dietary = st.session_state.get('pref_dietary', [])
        allergies = st.session_state.get('pref_allergies', [])
        spice = st.session_state.get('pref_spice_level', 'Medium')
        budget = st.session_state.get('pref_budget', 'Medium')
        leftovers = st.session_state.get('pref_include_leftovers', False)

        prompt += f" The recipe should serve {servings} and take no more than {time_limit} minutes."

        if dietary:
            prompt += f" It must be {', '.join(d.lower() for d in dietary)}."

        if allergies:
            prompt += f" Avoid these allergens: {', '.join(a.lower() for a in allergies)}."

        prompt += f" Target a {spice.lower()} spice level."
        prompt += f" Keep ingredients within a {budget.lower()} budget."

        if leftovers:
            prompt += " The recipe should be leftover-friendly and reheat well."

        return prompt

    def _get_dietary_tags(self) -> List[str]:
        """Return the current sidebar dietary tags for saving to the database."""
        return list(st.session_state.get('pref_dietary', []))

    def generate_surprise_prompt(self) -> str:
        """Build a randomized recipe prompt using sidebar preferences."""
        cuisines = [
            "American", "Chinese", "French", "Greek", "Indian", "Italian",
            "Japanese", "Korean", "Mediterranean", "Mexican", "Thai",
            "Vietnamese", "Middle Eastern", "Southern/Soul Food"
        ]
        styles = [
            "comfort food", "light and healthy", "quick weeknight",
            "impressive date night", "family-friendly", "adventurous and bold",
            "rustic and hearty", "elegant and refined"
        ]
        cuisine = random.choice(cuisines)
        style = random.choice(styles)

        prompt = f"Surprise me with an amazing {cuisine} dinner recipe! Make it {style}."
        prompt = self._append_preferences_to_prompt(prompt)
        prompt += " Include ingredients and step-by-step instructions."
        return prompt

    def render_recipe_output(self, recipe_content: str, recipe_type: str,
                           shopping_list_key: str, recipe_card_key: str,
                           available_ingredients: str = ""):
        """
        Render recipe output with shopping list and recipe card buttons.
        Uses st.download_button for the recipe card to avoid popup-blocker issues.
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

        # Display recipe card download if it exists
        if st.session_state.get(f"{recipe_type}_recipe_card"):
            recipe_html = create_recipe_card_html(st.session_state[f"{recipe_type}_recipe_card"])
            st.download_button(
                label="🖨️ Download Recipe Card (Open in Browser to Print)",
                data=recipe_html,
                file_name=f"{recipe_type}_recipe_card.html",
                mime="text/html",
                key=f"{recipe_type}_download_card"
            )

        # --- Recipe Tools ---
        with st.expander("🔧 Recipe Tools", expanded=False):
            tool_col1, tool_col2 = st.columns(2)

            with tool_col1:
                # Nutrition info
                if st.button("📊 Get Nutrition Info", key=f"{recipe_type}_nutrition_btn"):
                    with st.spinner("Estimating nutrition..."):
                        info = generate_nutritional_info(recipe_content)
                        st.session_state[f"{recipe_type}_nutrition"] = info

                # Scale recipe
                target = st.number_input(
                    "Scale to servings:",
                    min_value=1, max_value=20,
                    value=st.session_state.get('pref_servings', 4),
                    key=f"{recipe_type}_scale_input"
                )
                if st.button("⚖️ Scale Recipe", key=f"{recipe_type}_scale_btn"):
                    with st.spinner("Scaling recipe..."):
                        scaled = scale_recipe(recipe_content, target)
                        st.session_state[f"{recipe_type}_scaled"] = scaled

            with tool_col2:
                # Ingredient substitutions
                sub_ingredient = st.text_input(
                    "Ingredient to substitute:",
                    placeholder="e.g., butter, flour, eggs",
                    key=f"{recipe_type}_sub_input"
                )
                if st.button("🔄 Find Substitutes", key=f"{recipe_type}_sub_btn"):
                    if sub_ingredient.strip():
                        with st.spinner("Finding substitutes..."):
                            subs = generate_substitutions(recipe_content, sub_ingredient)
                            st.session_state[f"{recipe_type}_substitutions"] = subs
                    else:
                        st.warning("Enter an ingredient to find substitutes for.")

            # Display nutrition info
            if st.session_state.get(f"{recipe_type}_nutrition"):
                st.markdown("---")
                st.markdown("### 📊 Nutritional Estimates")
                st.write(st.session_state[f"{recipe_type}_nutrition"])

            # Display scaled recipe
            if st.session_state.get(f"{recipe_type}_scaled"):
                st.markdown("---")
                st.markdown("### ⚖️ Scaled Recipe")
                st.write(st.session_state[f"{recipe_type}_scaled"])

            # Display substitutions
            if st.session_state.get(f"{recipe_type}_substitutions"):
                st.markdown("---")
                st.markdown("### 🔄 Ingredient Substitutions")
                st.write(st.session_state[f"{recipe_type}_substitutions"])

        # --- Copy to clipboard ---
        if not st.session_state.get('user'):
            st.info("Not logged in? Copy your recipe below so you don't lose it!")
        with st.expander("📋 Copy Recipe Text"):
            st.code(recipe_content, language=None)

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

        # Special instructions
        instructions = st.text_input("Any other special instructions or preferences?")

        # Submit button
        if st.button("Suggest Recipe", key="cuisine_recipe"):
            prompt = f"Suggest a {complexity.lower()} {cuisine.lower()} {meal_type.lower()} recipe"

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

            if instructions:
                prompt += f". Also, consider this: {instructions}"

            prompt = self._append_preferences_to_prompt(prompt)
            prompt += " Include ingredients and step-by-step instructions."

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
                metadata = {
                    "cuisine": cuisine,
                    "meal_type": meal_type,
                    "complexity": complexity,
                    "occasion": None,
                    "cooking_method": cooking_method if cooking_method != "Any method" else None,
                    "dietary_tags": self._get_dietary_tags()
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

            allow_additional = st.checkbox(
                "Allow recipes that need a few additional common ingredients?",
                value=True,
                help="If checked, recipes may include common pantry items you might not have listed"
            )

        fridge_instructions = st.text_input(
            "Any other special instructions or preferences?",
            key="fridge_instructions"
        )

        # Submit button
        if st.button("Find Recipe with My Ingredients", key="fridge_recipe"):
            if not fridge_items.strip():
                st.warning("Please enter at least some ingredients from your fridge!")
            else:
                prompt = f"I have these ingredients available: {fridge_items}. "
                prompt += f"Please suggest a {fridge_complexity.lower()} {fridge_meal_type.lower()} recipe"

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

                if allow_additional:
                    prompt += ". You can suggest recipes that use most of these ingredients and may require a few common pantry staples (like oil, salt, pepper, basic spices) that most people have."
                else:
                    prompt += ". Please try to use primarily the ingredients I've listed."

                if fridge_instructions:
                    prompt += f" Also consider: {fridge_instructions}"

                prompt = self._append_preferences_to_prompt(prompt)
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
                metadata = {
                    "cuisine": None,
                    "meal_type": fridge_meal_type,
                    "complexity": fridge_complexity,
                    "occasion": None,
                    "cooking_method": fridge_cooking_method if fridge_cooking_method != "Any method" else None,
                    "dietary_tags": self._get_dietary_tags()
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
        st.write("Take a photo or upload an image of your fridge, pantry, or ingredients and I'll identify what you have and suggest recipes!")

        # Photo input: camera or file upload
        input_method = st.radio(
            "How would you like to provide your photo?",
            ["Take a photo", "Upload a file"],
            horizontal=True,
            key="photo_input_method"
        )

        photo = None
        if input_method == "Take a photo":
            photo = st.camera_input("Take a photo of your ingredients")
        else:
            photo = st.file_uploader(
                "Upload a photo of your ingredients",
                type=["jpg", "jpeg", "png", "webp"],
                key="photo_file_upload"
            )

        if photo is not None:
            # Display the photo
            st.image(photo, caption="Your ingredient photo", width=300)

            # Button to analyze the photo
            if st.button("🔍 Identify Ingredients in Photo", key="analyze_photo"):
                with st.spinner("Analyzing your photo..."):
                    try:
                        # Convert the image to PIL format
                        image = Image.open(photo)

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
                        st.success("Ingredients identified!")

                    except Exception as e:
                        st.error(f"Error analyzing image: {e}")

        # Display and allow editing of identified ingredients
        if st.session_state.identified_ingredients:
            st.subheader("Identified Ingredients")

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

                photo_allow_additional = st.checkbox(
                    "Allow recipes that need a few additional common ingredients?",
                    value=True,
                    key="photo_allow_additional",
                    help="If checked, recipes may include common pantry items you might not have"
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
                    prompt = f"Based on these ingredients I have from my photo: {photo_ingredients}. "
                    prompt += f"Please suggest a {photo_complexity.lower()} {photo_meal_type.lower()} recipe"

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

                    if photo_allow_additional:
                        prompt += ". You can suggest recipes that use most of these ingredients and may require a few common pantry staples (like oil, salt, pepper, basic spices) that most people have."
                    else:
                        prompt += ". Please try to use primarily the ingredients I've identified from my photo."

                    if photo_instructions:
                        prompt += f" Also consider: {photo_instructions}"

                    prompt = self._append_preferences_to_prompt(prompt)
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
                st.markdown("### Recipe Based on Your Photo")
                st.write(st.session_state.photo_recipe_content)

                st.markdown("---")

                # Save button
                if st.session_state.user:
                    metadata = {
                        "cuisine": None,
                        "meal_type": photo_meal_type,
                        "complexity": photo_complexity,
                        "occasion": None,
                        "cooking_method": photo_cooking_method if photo_cooking_method != "Any method" else None,
                        "dietary_tags": self._get_dietary_tags()
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
            st.info("Take a photo or upload an image of your ingredients to get started!")
            st.markdown("""
            **Tips for better ingredient identification:**
            - Make sure ingredients are well-lit and clearly visible
            - Try to capture labels on packaged items
            - Spread items out so they're not overlapping
            - Take the photo from a good angle where items are recognizable
            """)

    def render_holiday_tab(self, saved_recipes_manager, holiday_name: str, holiday_desc: str):
        """Render the holiday/occasion recipe generation tab"""
        st.header("Holiday & Special Occasion Recipes")

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

        # Additional preferences
        occasion_notes = st.text_area(
            "Any special requests or theme?",
            placeholder="e.g., 'elegant and sophisticated', 'fun for kids', 'Southern-style', 'comfort food'",
            key="occasion_notes"
        )

        # Generate holiday recipe
        if st.button("Get Holiday Recipe Suggestions", key="occasion_recipe_btn"):
            special_reqs = []
            if make_ahead: special_reqs.append("can be made ahead of time")
            if crowd_pleaser: special_reqs.append("crowd-pleaser that appeals to most tastes")
            if budget_friendly: special_reqs.append("budget-friendly")
            if impressive: special_reqs.append("visually impressive presentation")
            if traditional: special_reqs.append("traditional/classic recipe")
            if modern_twist: special_reqs.append("modern twist on a classic")

            prompt = f"Suggest a {occasion_complexity.lower()} {occasion_meal_type.lower()} recipe perfect for {selected_occasion} "
            prompt += f"in a {occasion_serving_style.lower()} style. "

            if special_reqs:
                prompt += f"Important: The recipe should be {', '.join(special_reqs)}. "

            if occasion_notes:
                prompt += f"Additional theme/request: {occasion_notes}. "

            prompt += f"Make sure the recipe is festive and appropriate for {selected_occasion}. "

            prompt = self._append_preferences_to_prompt(prompt)

            prompt += " Include a brief introduction explaining why this recipe is perfect for the occasion, "
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
            st.markdown(f"### {selected_occasion} Recipe")
            st.write(st.session_state.occasion_recipe_content)

            st.markdown("---")

            # Save button
            if st.session_state.user:
                metadata = {
                    "cuisine": None,
                    "meal_type": occasion_meal_type,
                    "complexity": occasion_complexity,
                    "occasion": selected_occasion,
                    "cooking_method": None,
                    "dietary_tags": self._get_dietary_tags()
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
