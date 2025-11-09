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

# Initialize session state
initialize_session_state()

# Initialize managers
auth_manager = AuthManager()
recipe_gen = RecipeGenerator()
saved_recipes_manager = SavedRecipesManager(auth_manager.supabase_admin)

# Streamlit UI
st.title("🍴 Dinner Recipe Maker")

# Get current holiday/occasion
holiday_name, holiday_desc = get_current_holiday()

# User Authentication Section in Sidebar
with st.sidebar:
    auth_manager.render_sidebar()
    
    # Show saved recipes button if logged in
    if st.session_state.user:
        st.markdown("---")
        st.markdown("### 📚 My Saved Recipes")
        if st.button("View My Saved Recipes", use_container_width=True):
            st.session_state.show_saved_recipes = True
            st.rerun()

# Check if we should show saved recipes view
if st.session_state.show_saved_recipes:
    saved_recipes_manager.render_saved_recipes_view()
else:
    # MAIN RECIPE GENERATOR VIEW
    # Display holiday banner if applicable
    if holiday_name and "Season" not in holiday_name:
        st.info(f"🎉 **{holiday_name}!** Perfect time for {holiday_desc}. Check out our special occasion recipes below!")
    elif holiday_name:
        st.success(f"🍂 **{holiday_name}** - Great time for {holiday_desc}")

    # Add tabs for different recipe modes
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
