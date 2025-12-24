"""
Dinner Recipe Maker - Main Application
A comprehensive recipe generation app with multiple modes and features
"""

import streamlit as st
from datetime import datetime
from PIL import Image
import io

# Import custom modules
from auth import AuthManager
from recipe_generator import RecipeGenerator
from saved_recipes import SavedRecipesManager
from utils import (
    get_current_holiday,
    extract_recipe_name,
    generate_shopping_list,
    generate_recipe_card,
    create_recipe_card_html,
    initialize_session_state
)

# Page configuration
st.set_page_config(
    page_title="Dinner Recipe Maker",
    page_icon="🍴",
    layout="wide"
)

# Initialize session state (your existing initializer)
initialize_session_state()

# Add navigation state (new)
if "page" not in st.session_state:
    st.session_state.page = "Recipe Generator"

# Initialize managers
auth_manager = AuthManager()
recipe_gen = RecipeGenerator()
saved_recipes_manager = SavedRecipesManager(auth_manager.supabase_admin)

# Streamlit UI
st.title("🍴 Dinner Recipe Maker")

# Get current holiday/occasion
holiday_name, holiday_desc = get_current_holiday()

# Sidebar: Auth + Navigation
with st.sidebar:
    auth_manager.render_sidebar()

    st.markdown("---")
    st.markdown("### 🧭 Navigate")

    # Only show "Saved Recipes" if logged in
    nav_options = ["Recipe Generator"]
    if st.session_state.user:
        nav_options.append("Saved Recipes")
    nav_options.append("About")

    # Use a stable key so Streamlit keeps selection nicely
    selected = st.radio(
        label="",
        options=nav_options,
        index=nav_options.index(st.session_state.page) if st.session_state.page in nav_options else 0,
        key="nav_radio"
    )

    # Persist selection to session state
    st.session_state.page = selected

# -------------------------
# PAGE ROUTING
# -------------------------
if st.session_state.page == "Saved Recipes":
    saved_recipes_manager.render_saved_recipes_view()

elif st.session_state.page == "About":
    st.subheader("About Dinner Recipe Maker")
    st.write(
        """
        Generate dinner recipes in a few different ways:
        - Pick a cuisine
        - Use ingredients from your fridge
        - Upload a photo to inspire a recipe
        - Browse holiday and special occasion ideas
        """
    )
    st.info("Tip: Log in to save recipes and build your personal cookbook.")

else:
    # RECIPE GENERATOR PAGE

    # Holiday banner if applicable
    if holiday_name and "Season" not in holiday_name:
        st.info(f"🎉 **{holiday_name}!** Perfect time for {holiday_desc}. Check out our special occasion recipes below!")
    elif holiday_name:
        st.success(f"🍂 **{holiday_name}** - Great time for {holiday_desc}")

    # Tabs for generator modes
    tab1, tab2, tab3, tab4 = st.tabs([
        "🍽️ Recipe by Cuisine",
        "🥘 Recipe by Fridge Items",
        "📸 Photo Recipe Finder",
        "🎉 Holiday & Special Occasions"
    ])

    with tab1:
        recipe_gen.render_cuisine_tab(saved_recipes_manager)

    with tab2:
        recipe_gen.render_fridge_tab(saved_recipes_manager)

    with tab3:
        recipe_gen.render_photo_tab(saved_recipes_manager)

    with tab4:
        recipe_gen.render_holiday_tab(saved_recipes_manager, holiday_name, holiday_desc)
