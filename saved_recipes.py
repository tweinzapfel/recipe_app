"""
Saved Recipes Manager Module
Handles saving, loading, and displaying saved recipes with advanced filtering and sorting
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from utils import generate_recipe_card, create_recipe_card_html, extract_recipe_name, generate_shopping_list

class SavedRecipesManager:
    """Manages saved recipes functionality"""
    
    def __init__(self, supabase_admin):
        """
        Initialize the saved recipes manager
        
        Args:
            supabase_admin: Supabase admin client for database operations
        """
        self.supabase_admin = supabase_admin
        self._initialize_filter_state()
    
    def _initialize_filter_state(self):
        """Initialize filter state variables"""
        if 'recipe_filters' not in st.session_state:
            st.session_state.recipe_filters = {
                'search_query': '',
                'selected_cuisines': [],
                'selected_meal_types': [],
                'selected_complexity': [],
                'selected_dietary': [],
                'selected_cooking_methods': [],
                'sort_by': 'Date (Newest First)'
            }
    
    def save_recipe(self, recipe_data: Dict[str, Any]) -> bool:
        """
        Save a recipe to the database
        
        Args:
            recipe_data: Dictionary containing recipe information
            
        Returns:
            bool: True if save successful, False otherwise
        """
        if not self.supabase_admin:
            st.error("Database connection not available")
            return False
        
        try:
            # Add created_at timestamp if not present
            if 'created_at' not in recipe_data:
                recipe_data['created_at'] = datetime.now().isoformat()
            
            response = self.supabase_admin.table("saved_recipes").insert(recipe_data).execute()
            return True
        except Exception as e:
            st.error(f"Error saving recipe: {e}")
            return False
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """
        Delete a recipe from the database
        
        Args:
            recipe_id: The ID of the recipe to delete
            
        Returns:
            bool: True if delete successful, False otherwise
        """
        if not self.supabase_admin:
            st.error("Database connection not available")
            return False
        
        try:
            self.supabase_admin.table("saved_recipes").delete().eq("id", recipe_id).execute()
            return True
        except Exception as e:
            st.error(f"Error deleting recipe: {e}")
            return False
    
    def get_user_recipes(self, user_id: str) -> Optional[List[Dict]]:
        """
        Get all recipes for a specific user
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of recipe dictionaries or None if error
        """
        if not self.supabase_admin:
            return None
        
        try:
            response = self.supabase_admin.table("saved_recipes").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            st.error(f"Error loading recipes: {e}")
            return None
    
    def get_unique_values(self, recipes: List[Dict]) -> Dict[str, List]:
        """
        Extract unique values for filters from recipes
        
        Args:
            recipes: List of recipe dictionaries
            
        Returns:
            Dictionary containing unique values for each filter category
        """
        unique_values = {
            'cuisines': set(),
            'meal_types': set(),
            'complexity': set(),
            'dietary_tags': set(),
            'cooking_methods': set(),
            'occasions': set()
        }
        
        for recipe in recipes:
            if recipe.get('cuisine'):
                unique_values['cuisines'].add(recipe['cuisine'])
            if recipe.get('meal_type'):
                unique_values['meal_types'].add(recipe['meal_type'])
            if recipe.get('complexity'):
                unique_values['complexity'].add(recipe['complexity'])
            if recipe.get('cooking_method'):
                unique_values['cooking_methods'].add(recipe['cooking_method'])
            if recipe.get('occasion'):
                unique_values['occasions'].add(recipe['occasion'])
            if recipe.get('dietary_tags'):
                for tag in recipe['dietary_tags']:
                    unique_values['dietary_tags'].add(tag)
        
        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in unique_values.items()}
    
    def filter_recipes(self, recipes: List[Dict]) -> List[Dict]:
        """
        Filter recipes based on selected criteria
        
        Args:
            recipes: List of all recipes
            
        Returns:
            Filtered list of recipes
        """
        filtered = recipes
        
        # Search filter (searches in recipe name and content)
        search_query = st.session_state.recipe_filters['search_query'].lower()
        if search_query:
            filtered = [r for r in filtered if 
                       search_query in r.get('recipe_name', '').lower() or 
                       search_query in r.get('recipe_content', '').lower()]
        
        # Cuisine filter
        if st.session_state.recipe_filters['selected_cuisines']:
            filtered = [r for r in filtered if 
                       r.get('cuisine') in st.session_state.recipe_filters['selected_cuisines']]
        
        # Meal type filter
        if st.session_state.recipe_filters['selected_meal_types']:
            filtered = [r for r in filtered if 
                       r.get('meal_type') in st.session_state.recipe_filters['selected_meal_types']]
        
        # Complexity filter
        if st.session_state.recipe_filters['selected_complexity']:
            filtered = [r for r in filtered if 
                       r.get('complexity') in st.session_state.recipe_filters['selected_complexity']]
        
        # Dietary tags filter
        if st.session_state.recipe_filters['selected_dietary']:
            filtered = [r for r in filtered if 
                       r.get('dietary_tags') and 
                       any(tag in r['dietary_tags'] for tag in st.session_state.recipe_filters['selected_dietary'])]
        
        # Cooking method filter
        if st.session_state.recipe_filters['selected_cooking_methods']:
            filtered = [r for r in filtered if 
                       r.get('cooking_method') in st.session_state.recipe_filters['selected_cooking_methods']]
        
        return filtered
    
    def sort_recipes(self, recipes: List[Dict]) -> List[Dict]:
        """
        Sort recipes based on selected criteria
        
        Args:
            recipes: List of recipes to sort
            
        Returns:
            Sorted list of recipes
        """
        sort_option = st.session_state.recipe_filters['sort_by']
        
        if sort_option == 'Date (Newest First)':
            return sorted(recipes, key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_option == 'Date (Oldest First)':
            return sorted(recipes, key=lambda x: x.get('created_at', ''))
        elif sort_option == 'Name (A-Z)':
            return sorted(recipes, key=lambda x: x.get('recipe_name', '').lower())
        elif sort_option == 'Name (Z-A)':
            return sorted(recipes, key=lambda x: x.get('recipe_name', '').lower(), reverse=True)
        elif sort_option == 'Cuisine':
            return sorted(recipes, key=lambda x: (x.get('cuisine', 'zzz'), x.get('recipe_name', '')))
        elif sort_option == 'Meal Type':
            return sorted(recipes, key=lambda x: (x.get('meal_type', 'zzz'), x.get('recipe_name', '')))
        elif sort_option == 'Complexity':
            complexity_order = {'Easy': 1, 'Medium': 2, 'Hard': 3, 'Show-stopping (Impressive)': 4}
            return sorted(recipes, key=lambda x: (complexity_order.get(x.get('complexity', ''), 5), x.get('recipe_name', '')))
        
        return recipes
    
    def render_filter_sidebar(self, unique_values: Dict[str, List]):
        """
        Render the filter sidebar
        
        Args:
            unique_values: Dictionary of unique values for each filter category
        """
        with st.sidebar:
            st.markdown("### 🔍 Filter & Sort Recipes")
            
            # Search bar
            st.session_state.recipe_filters['search_query'] = st.text_input(
                "Search recipes",
                value=st.session_state.recipe_filters['search_query'],
                placeholder="Search by name or ingredients..."
            )
            
            # Sort dropdown
            st.session_state.recipe_filters['sort_by'] = st.selectbox(
                "Sort by",
                ['Date (Newest First)', 'Date (Oldest First)', 
                 'Name (A-Z)', 'Name (Z-A)', 'Cuisine', 
                 'Meal Type', 'Complexity']
            )
            
            st.markdown("---")
            
            # Filter sections
            with st.expander("🍽️ Cuisine", expanded=False):
                if unique_values['cuisines']:
                    st.session_state.recipe_filters['selected_cuisines'] = st.multiselect(
                        "Select cuisines",
                        unique_values['cuisines'],
                        default=st.session_state.recipe_filters['selected_cuisines'],
                        label_visibility="collapsed"
                    )
            
            with st.expander("🍴 Meal Type", expanded=False):
                if unique_values['meal_types']:
                    st.session_state.recipe_filters['selected_meal_types'] = st.multiselect(
                        "Select meal types",
                        unique_values['meal_types'],
                        default=st.session_state.recipe_filters['selected_meal_types'],
                        label_visibility="collapsed"
                    )
            
            with st.expander("⚡ Complexity", expanded=False):
                if unique_values['complexity']:
                    st.session_state.recipe_filters['selected_complexity'] = st.multiselect(
                        "Select complexity",
                        unique_values['complexity'],
                        default=st.session_state.recipe_filters['selected_complexity'],
                        label_visibility="collapsed"
                    )
            
            with st.expander("🥗 Dietary Tags", expanded=False):
                if unique_values['dietary_tags']:
                    st.session_state.recipe_filters['selected_dietary'] = st.multiselect(
                        "Select dietary tags",
                        unique_values['dietary_tags'],
                        default=st.session_state.recipe_filters['selected_dietary'],
                        label_visibility="collapsed"
                    )
            
            with st.expander("🔥 Cooking Method", expanded=False):
                if unique_values['cooking_methods']:
                    st.session_state.recipe_filters['selected_cooking_methods'] = st.multiselect(
                        "Select cooking methods",
                        unique_values['cooking_methods'],
                        default=st.session_state.recipe_filters['selected_cooking_methods'],
                        label_visibility="collapsed"
                    )
            
            # Clear filters button
            if st.button("🔄 Clear All Filters", use_container_width=True):
                st.session_state.recipe_filters = {
                    'search_query': '',
                    'selected_cuisines': [],
                    'selected_meal_types': [],
                    'selected_complexity': [],
                    'selected_dietary': [],
                    'selected_cooking_methods': [],
                    'sort_by': 'Date (Newest First)'
                }
                st.rerun()
    
    def render_recipe_stats(self, all_recipes: List[Dict], filtered_recipes: List[Dict]):
        """
        Render recipe statistics
        
        Args:
            all_recipes: All user recipes
            filtered_recipes: Filtered recipes
        """
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Recipes", len(all_recipes))
        
        with col2:
            st.metric("Showing", len(filtered_recipes))
        
        with col3:
            # Count recipes by type
            recipe_types = {}
            for r in all_recipes:
                r_type = r.get('recipe_type', 'Unknown')
                recipe_types[r_type] = recipe_types.get(r_type, 0) + 1
            most_common = max(recipe_types.items(), key=lambda x: x[1])[0] if recipe_types else "N/A"
            st.metric("Most Common Type", most_common.title())
        
        with col4:
            # Count unique cuisines
            unique_cuisines = len(set(r.get('cuisine', '') for r in all_recipes if r.get('cuisine')))
            st.metric("Cuisines Tried", unique_cuisines)
    
    def render_save_button(self, recipe_content: str, recipe_type: str, 
                          recipe_metadata: Dict[str, Any], button_key: str) -> bool:
        """
        Render a save recipe button and handle saving
        
        Args:
            recipe_content: The recipe text content
            recipe_type: Type of recipe (cuisine, fridge, photo, occasion)
            recipe_metadata: Additional metadata about the recipe
            button_key: Unique key for the button
            
        Returns:
            bool: True if recipe was saved
        """
        if st.session_state.user and recipe_content:
            if st.button("ðŸ’¾ Save This Recipe", key=button_key, use_container_width=True):
                try:
                    recipe_name = extract_recipe_name(recipe_content)
                    
                    data = {
                        "user_id": st.session_state.user,
                        "recipe_name": recipe_name,
                        "recipe_content": recipe_content,
                        "recipe_type": recipe_type,
                        **recipe_metadata
                    }
                    
                    if self.save_recipe(data):
                        st.success("âœ… Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                        return True
                except Exception as e:
                    st.error(f"Error saving recipe: {e}")
        elif not st.session_state.user:
            st.info("ðŸ“ Create an account and log in to save your favorite recipes!")
        
        return False
    
    def render_saved_recipes_view(self):
        """Render the saved recipes view"""
        st.title("ðŸ’¾ My Saved Recipes")
        
        # Return button
        if st.button("â¬…ï¸ Return to Recipe Generator", key="return_btn"):
            st.session_state.show_saved_recipes = False
            st.rerun()
        
        st.markdown("---")
        
        if st.session_state.user is None:
            st.warning("Please log in to view your saved recipes.")
            st.info("ðŸ‘ˆ Use the sidebar to log in or create an account.")
            return
        
        st.write(f"**Logged in as:** {st.session_state.user_email}")
        
        recipes = self.get_user_recipes(st.session_state.user)
        
        if not recipes:
            st.info("You haven't saved any recipes yet. Generate a recipe and click the 'Save This Recipe' button!")
            return
        
        st.success(f"You have {len(recipes)} saved recipe(s)")
        
        # Display each saved recipe
        for idx, recipe in enumerate(recipes):
            self._render_recipe_card(recipe, idx)
    
    def _render_recipe_card(self, recipe: Dict[str, Any], idx: int):
        """
        Render a single recipe card in the saved recipes view
        
        Args:
            recipe: Recipe data dictionary
            idx: Index for unique keys
        """
        # Build metadata display
        metadata_parts = []
        if recipe.get('cuisine'):
            metadata_parts.append(f"ðŸ½ï¸ {recipe['cuisine']}")
        if recipe.get('occasion'):
            metadata_parts.append(f"ðŸŽ‰ {recipe['occasion']}")
        if recipe.get('meal_type'):
            metadata_parts.append(f"ðŸ´ {recipe['meal_type']}")
        if recipe.get('complexity'):
            metadata_parts.append(f"âš¡ {recipe['complexity']}")
        if recipe.get('cooking_method'):
            metadata_parts.append(f"ðŸ”¥ {recipe['cooking_method']}")
        if recipe.get('dietary_tags') and len(recipe['dietary_tags']) > 0:
            metadata_parts.append(f"âœ“ {', '.join(recipe['dietary_tags'])}")
        
        metadata_display = " | ".join(metadata_parts) if metadata_parts else ""
        
        with st.expander(f"ðŸ“– {recipe.get('recipe_name', 'Untitled Recipe')} - {recipe.get('created_at', '')[:10]}"):
            # Display metadata tags
            if metadata_display:
                st.markdown(f"**{metadata_display}**")
                st.markdown("---")
            
            st.markdown("### Recipe Details")
            st.write(recipe.get('recipe_content', 'No content available'))
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Button to delete recipe
                if st.button(f"ðŸ—‘ï¸ Delete", key=f"delete_{recipe['id']}"):
                    if self.delete_recipe(recipe['id']):
                        st.success("Recipe deleted!")
                        st.rerun()
            
            with col2:
                # Button to generate recipe card from saved recipe
                if st.button(f"ðŸ–¨ï¸ Print Card", key=f"print_{recipe['id']}"):
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
                                ðŸ–¨ï¸ Open Recipe Card
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
        
        with col3:
            # Shopping list button
            if st.button(f"🛒 Shopping List", key=f"shop_{recipe['id']}_{idx}"):
                with st.spinner("Generating shopping list..."):
                    shopping_list = generate_shopping_list(recipe.get('recipe_content', ''))
                    st.markdown("### 🛒 Shopping List")
                    st.write(shopping_list)
