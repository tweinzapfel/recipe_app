"""
Dinner Recipe Maker - Main Application
A comprehensive recipe generation app with multiple modes and features
"""

import streamlit as st

# Import custom modules
from auth import AuthManager
from recipe_generator import RecipeGenerator
from saved_recipes import SavedRecipesManager
from meal_planner import MealPlanner
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

initialize_session_state()

# -------------------------
# NEW: Preference defaults
# -------------------------
def initialize_preferences():
    defaults = {
        "pref_servings": 4,
        "pref_time_limit": 30,          # minutes
        "pref_dietary": [],             # multi-select
        "pref_spice_level": "Medium",   # Low/Medium/Hot
        "pref_budget": "Medium",        # Low/Medium/High
        "pref_include_leftovers": False,
        "pref_allergies": [],
        "dark_mode": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

initialize_preferences()

# Dark mode CSS
if st.session_state.get('dark_mode', False):
    st.markdown("""
    <style>
        :root { color-scheme: dark; }
        .stApp, [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #fafafa; }
        [data-testid="stSidebar"] > div { background-color: #262730; }
        [data-testid="stHeader"] { background-color: rgba(14, 17, 23, 0.8); }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea { background-color: #262730; color: #fafafa; }
        .stSelectbox > div > div, .stMultiSelect > div > div { background-color: #262730; }
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
        .stExpander { border-color: #555; }
    </style>
    """, unsafe_allow_html=True)

# Navigation state
if "page" not in st.session_state:
    st.session_state.page = "Recipe Generator"

# Initialize managers
auth_manager = AuthManager()
recipe_gen = RecipeGenerator()
saved_recipes_manager = SavedRecipesManager(auth_manager.supabase)
meal_planner = MealPlanner(auth_manager.supabase)

# Streamlit UI
st.title("🍴 Dinner Recipe Maker")

# Get current holiday/occasion
holiday_name, holiday_desc = get_current_holiday()

# -------------------------
# Sidebar: Auth + Nav + Preferences
# -------------------------
with st.sidebar:
    auth_manager.render_sidebar()

    st.markdown("---")
    st.markdown("### 🧭 Navigate")

    nav_options = ["Recipe Generator"]
    if st.session_state.user:
        nav_options.append("Saved Recipes")
        nav_options.append("Meal Planner")
    nav_options.append("About")

    selected = st.radio(
        label="",
        options=nav_options,
        index=nav_options.index(st.session_state.page) if st.session_state.page in nav_options else 0,
        key="nav_radio"
    )
    st.session_state.page = selected

    # NEW: Global preferences (available to all tabs)
    st.markdown("---")
    st.markdown("### ⚙️ Preferences")

    with st.expander("Recipe preferences", expanded=True):
        st.slider(
            "Servings",
            min_value=1,
            max_value=10,
            value=st.session_state.pref_servings,
            key="pref_servings"
        )

        st.select_slider(
            "Time limit",
            options=[15, 30, 45, 60, 90],
            value=st.session_state.pref_time_limit,
            key="pref_time_limit",
            help="Target max time to cook."
        )

        st.multiselect(
            "Dietary",
            options=[
                "Vegetarian",
                "Vegan",
                "Gluten-free",
                "Dairy-free",
                "Low carb",
                "Keto",
                "Pescatarian",
                "Nut-free",
                "Paleo",
                "Low-sodium",
                "High-fiber",
                "High-protein"
            ],
            default=st.session_state.pref_dietary,
            key="pref_dietary"
        )

        st.multiselect(
            "Allergies",
            options=[
                "Nuts", "Shellfish", "Eggs", "Soy",
                "Fish", "Sesame", "Other"
            ],
            default=st.session_state.pref_allergies,
            key="pref_allergies"
        )

        st.radio(
            "Spice level",
            options=["Low", "Medium", "Hot"],
            index=["Low", "Medium", "Hot"].index(st.session_state.pref_spice_level),
            key="pref_spice_level",
            horizontal=True
        )

        st.radio(
            "Budget",
            options=["Low", "Medium", "High"],
            index=["Low", "Medium", "High"].index(st.session_state.pref_budget),
            key="pref_budget",
            horizontal=True,
            help="Rough ingredient cost preference."
        )

        st.toggle(
            "Prefer leftover-friendly recipes",
            value=st.session_state.pref_include_leftovers,
            key="pref_include_leftovers"
        )

    st.markdown("---")
    st.toggle(
        "🌙 Dark mode",
        value=st.session_state.dark_mode,
        key="dark_mode"
    )

    # Optional: Quick "reset preferences"
    if st.button("Reset preferences", use_container_width=True):
        for k in [
            "pref_servings",
            "pref_time_limit",
            "pref_dietary",
            "pref_spice_level",
            "pref_budget",
            "pref_include_leftovers",
            "pref_allergies",
            "dark_mode"
        ]:
            if k in st.session_state:
                del st.session_state[k]
        initialize_preferences()
        st.rerun()

# -------------------------
# PAGE ROUTING
# -------------------------
if st.session_state.page == "Saved Recipes":
    saved_recipes_manager.render_saved_recipes_view()

elif st.session_state.page == "Meal Planner":
    meal_planner.render_meal_planner_view()

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

    # Surprise Me button
    if st.button("🎲 Surprise Me!", use_container_width=True,
                 help="Generate a random recipe based on your preferences"):
        surprise_prompt = recipe_gen.generate_surprise_prompt()
        with st.spinner("Cooking up something special..."):
            content = recipe_gen.generate_recipe(surprise_prompt)
            if content:
                st.session_state.surprise_recipe_content = content
                st.session_state.surprise_shopping_list = ""
                st.session_state.surprise_recipe_card = ""

    if st.session_state.get('surprise_recipe_content'):
        st.markdown("### 🎲 Surprise Recipe!")
        st.write(st.session_state.surprise_recipe_content)
        st.markdown("---")
        if st.session_state.user:
            saved_recipes_manager.render_save_button(
                st.session_state.surprise_recipe_content,
                "surprise",
                {"cuisine": None, "meal_type": "Dinner", "complexity": None,
                 "occasion": None, "cooking_method": None,
                 "dietary_tags": recipe_gen._get_dietary_tags()},
                "save_surprise_recipe"
            )
        recipe_gen.render_recipe_output(
            st.session_state.surprise_recipe_content,
            "surprise",
            "surprise_shopping_list_btn",
            "surprise_recipe_card_btn"
        )
        st.markdown("---")

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
