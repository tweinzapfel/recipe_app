"""
Saved Recipes Manager Module
Handles saving, loading, and displaying saved recipes with advanced filtering and sorting
"""

import re
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from utils import generate_recipe_card, create_recipe_card_html, extract_recipe_name, generate_shopping_list

class SavedRecipesManager:
    """Manages saved recipes functionality"""
    
    def __init__(self, supabase_client):
        """
        Initialize the saved recipes manager
        
        Args:
            supabase_client: Supabase client for database operations (uses anon key with RLS)
        """
        self.supabase_client = supabase_client
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
        if 'confirm_delete_id' not in st.session_state:
            st.session_state.confirm_delete_id = None
    
    def save_recipe(self, recipe_data: Dict[str, Any]) -> bool:
        """
        Save a recipe to the database
        
        Args:
            recipe_data: Dictionary containing recipe information
            
        Returns:
            bool: True if save successful, False otherwise
        """
        if not self.supabase_client:
            st.error("Database connection not available")
            return False
        
        try:
            # Add created_at timestamp if not present
            if 'created_at' not in recipe_data:
                recipe_data['created_at'] = datetime.now().isoformat()
            
            response = self.supabase_client.table("saved_recipes").insert(recipe_data).execute()
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
        if not self.supabase_client:
            st.error("Database connection not available")
            return False
        
        try:
            self.supabase_client.table("saved_recipes").delete().eq("id", recipe_id).execute()
            return True
        except Exception as e:
            st.error(f"Error deleting recipe: {e}")
            return False
    
    def update_recipe(self, recipe_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update fields on a saved recipe.

        Args:
            recipe_id: The recipe ID
            updates: Dictionary of column->value pairs to update

        Returns:
            bool: True if update succeeded
        """
        if not self.supabase_client:
            st.error("Database connection not available")
            return False
        try:
            self.supabase_client.table("saved_recipes").update(updates).eq("id", recipe_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating recipe: {e}")
            return False

    def toggle_favorite(self, recipe_id: str, current_value: bool) -> bool:
        """Toggle the is_favorite flag on a saved recipe."""
        return self.update_recipe(recipe_id, {"is_favorite": not current_value})

    def get_user_recipes(self, user_id: str) -> Optional[List[Dict]]:
        """
        Get all recipes for a specific user
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of recipe dictionaries or None if error
        """
        if not self.supabase_client:
            return None
        
        try:
            response = self.supabase_client.table("saved_recipes").select("*").eq(
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

        # Favorites-only filter
        if st.session_state.recipe_filters.get('favorites_only', False):
            filtered = [r for r in filtered if r.get('is_favorite')]

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
        elif sort_option == 'Rating (Highest First)':
            return sorted(recipes, key=lambda x: x.get('rating') or 0, reverse=True)
        elif sort_option == 'Favorites First':
            return sorted(recipes, key=lambda x: (0 if x.get('is_favorite') else 1, x.get('recipe_name', '')))

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
                 'Meal Type', 'Complexity',
                 'Rating (Highest First)', 'Favorites First']
            )

            # Favorites-only toggle
            st.session_state.recipe_filters['favorites_only'] = st.checkbox(
                "Show favorites only",
                value=st.session_state.recipe_filters.get('favorites_only', False)
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
        Render recipe statistics in a compact single line.

        Args:
            all_recipes: All user recipes
            filtered_recipes: Filtered recipes
        """
        # Count recipes by type
        recipe_types: Dict[str, int] = {}
        for r in all_recipes:
            r_type = r.get('recipe_type', 'Unknown')
            recipe_types[r_type] = recipe_types.get(r_type, 0) + 1
        most_common = max(recipe_types.items(), key=lambda x: x[1])[0].title() if recipe_types else "N/A"

        unique_cuisines = len(set(r.get('cuisine', '') for r in all_recipes if r.get('cuisine')))

        showing_text = f"**{len(filtered_recipes)}** of **{len(all_recipes)}** recipes"
        if len(filtered_recipes) != len(all_recipes):
            showing_text += " (filtered)"

        st.caption(
            f"{showing_text}  ·  Most common: {most_common}  ·  {unique_cuisines} cuisine(s) tried"
        )
    
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
            if st.button("💾 Save This Recipe", key=button_key, use_container_width=True):
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
                        st.success("✅ Recipe saved successfully! View it in the 'My Saved Recipes' tab.")
                        return True
                except Exception as e:
                    st.error(f"Error saving recipe: {e}")
        elif not st.session_state.user:
            st.info("🔐 Create an account and log in to save your favorite recipes!")
        
        return False
    
    def render_saved_recipes_view(self):
        """Render the saved recipes view with filtering and sorting"""
        st.title("💾 My Saved Recipes")
        
        # Return button
        if st.button("⬅️ Return to Recipe Generator", key="return_btn"):
            st.session_state.show_saved_recipes = False
            st.rerun()
        
        st.markdown("---")
        
        if st.session_state.user is None:
            st.warning("Please log in to view your saved recipes.")
            st.info("👈 Use the sidebar to log in or create an account.")
            return
        
        # Load all recipes
        all_recipes = self.get_user_recipes(st.session_state.user)
        
        if not all_recipes:
            st.info("You haven't saved any recipes yet. Generate a recipe and click the 'Save This Recipe' button!")
            return
        
        # Get unique values for filters
        unique_values = self.get_unique_values(all_recipes)
        
        # Render filter sidebar
        self.render_filter_sidebar(unique_values)
        
        # Apply filters
        filtered_recipes = self.filter_recipes(all_recipes)
        
        # Apply sorting
        filtered_recipes = self.sort_recipes(filtered_recipes)
        
        # Display view options and statistics on one line
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📖 Your Recipe Collection")
        with col2:
            view_mode = st.selectbox(
                "View mode",
                ["Compact", "Expanded"],
                label_visibility="collapsed"
            )

        # Compact stats line
        self.render_recipe_stats(all_recipes, filtered_recipes)

        # Check if any recipes match filters
        if not filtered_recipes:
            st.warning("No recipes match your current filters. Try adjusting or clearing filters.")
            return
        
        # Active filters display
        active_filters = []
        if st.session_state.recipe_filters['search_query']:
            active_filters.append(f"Search: '{st.session_state.recipe_filters['search_query']}'")
        if st.session_state.recipe_filters['selected_cuisines']:
            active_filters.append(f"Cuisines: {', '.join(st.session_state.recipe_filters['selected_cuisines'])}")
        if st.session_state.recipe_filters['selected_meal_types']:
            active_filters.append(f"Meal Types: {', '.join(st.session_state.recipe_filters['selected_meal_types'])}")
        if st.session_state.recipe_filters['selected_complexity']:
            active_filters.append(f"Complexity: {', '.join(st.session_state.recipe_filters['selected_complexity'])}")
        if st.session_state.recipe_filters['selected_dietary']:
            active_filters.append(f"Dietary: {', '.join(st.session_state.recipe_filters['selected_dietary'])}")
        if st.session_state.recipe_filters['selected_cooking_methods']:
            active_filters.append(f"Methods: {', '.join(st.session_state.recipe_filters['selected_cooking_methods'])}")
        
        if active_filters:
            st.info(f"**Active filters:** {' | '.join(active_filters)}")
        
        # Display recipes based on view mode
        if view_mode == "Compact":
            self._render_compact_view(filtered_recipes)
        else:
            self._render_expanded_view(filtered_recipes)
    
    @staticmethod
    def _clean_display_name(name: str, max_len: int = 55) -> str:
        """Clean up a recipe name for display, fixing legacy bad extractions."""
        if not name:
            return "Untitled Recipe"

        # Strip markdown formatting
        clean = name.replace('#', '').replace('*', '').strip().rstrip(':').strip()

        # If name looks like conversational AI text, try to extract the real name
        ai_patterns = [
            r"(?:how about|let'?s make|let'?s try|try making|here'?s|here is)\s+(?:a\s+|some\s+)?(?:delicious\s+|classic\s+|homemade\s+|amazing\s+)?(.+?)(?:\?|!|\.|,|this\s)",
            r"(?:recipe for|make|making)\s+(?:a\s+|some\s+)?(?:delicious\s+|classic\s+)?(.+?)(?:\?|!|\.|,|this\s)",
        ]
        lower = clean.lower()
        if any(p in lower for p in ['sure!', 'how about', 'let\'s', 'here\'s', 'try making', 'here is']):
            for pattern in ai_patterns:
                match = re.search(pattern, clean, re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip().rstrip('.,!? ')
                    if len(extracted) >= 3:
                        clean = extracted
                        break

        # Skip generic headers
        if clean.lower() in ('introduction', 'overview', 'recipe', 'description'):
            return "Untitled Recipe"

        # Truncate with ellipsis if needed
        if len(clean) > max_len:
            clean = clean[:max_len].rsplit(' ', 1)[0] + "..."

        return clean if clean else "Untitled Recipe"

    def _render_compact_view(self, recipes: List[Dict]):
        """
        Render recipes in a compact accordion view — one row per recipe.

        Args:
            recipes: List of filtered and sorted recipes
        """
        for idx, recipe in enumerate(recipes):
            recipe_name = recipe.get('recipe_name', 'Untitled Recipe')
            display_name = self._clean_display_name(recipe_name)
            is_fav = recipe.get('is_favorite', False)

            # Build a rich expander label with key info at a glance
            fav_marker = "♥ " if is_fav else ""
            rating = recipe.get('rating')
            stars = f"  {'⭐' * rating}" if rating else ""

            tags = []
            if recipe.get('cuisine'):
                tags.append(recipe['cuisine'])
            if recipe.get('meal_type'):
                tags.append(recipe['meal_type'])
            tag_str = f"  —  {' · '.join(tags)}" if tags else ""

            date_str = recipe.get('created_at', '')[:10] if recipe.get('created_at') else ''
            date_part = f"  ·  📅 {date_str}" if date_str else ""

            label = f"{fav_marker}{display_name}{stars}{tag_str}{date_part}"

            with st.expander(label, expanded=False):
                self._render_full_recipe_content(recipe, idx)
    
    @staticmethod
    def _get_recipe_preview(content: str, max_lines: int = 3) -> str:
        """Extract a short preview from recipe content, skipping headers/metadata."""
        if not content:
            return ""
        skip_prefixes = ('#', '**', '---', 'servings', 'prep time', 'cook time', 'total time')
        preview_lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if any(lower.startswith(p) for p in skip_prefixes):
                continue
            # Skip list items that look like ingredients
            if stripped.startswith('-') or stripped.startswith('•'):
                continue
            preview_lines.append(stripped)
            if len(preview_lines) >= max_lines:
                break
        preview = ' '.join(preview_lines)
        if len(preview) > 180:
            preview = preview[:180].rsplit(' ', 1)[0] + "..."
        return preview

    def _render_expanded_view(self, recipes: List[Dict]):
        """
        Render recipes in an expanded card-grid view.

        Args:
            recipes: List of filtered and sorted recipes
        """
        # Inject card accent CSS once
        meal_type_colors = {
            'Dinner': '#6366f1',           # indigo
            'Lunch': '#f59e0b',            # amber
            'Breakfast/Brunch': '#f97316', # orange
            'Appetizer': '#8b5cf6',        # violet
            'Snack': '#10b981',            # emerald
            'Dessert': '#ec4899',          # pink
            'Side Dish': '#14b8a6',        # teal
            'Main Course': '#6366f1',      # indigo
        }

        cols_per_row = 2
        for i in range(0, len(recipes), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(recipes):
                    with col:
                        self._render_recipe_card(recipes[i + j], i + j, meal_type_colors)

    def _render_recipe_card(self, recipe: Dict[str, Any], idx: int, meal_type_colors: Dict[str, str]):
        """
        Render a single recipe card with border, accent, and preview.

        Args:
            recipe: Recipe data dictionary
            idx: Index for unique keys
            meal_type_colors: Mapping of meal type to accent color hex
        """
        meal_icons = {
            'Dinner': '🌆', 'Lunch': '☀️', 'Breakfast/Brunch': '🌅',
            'Appetizer': '🥨', 'Snack': '🍿', 'Dessert': '🍰',
            'Side Dish': '🥗', 'Main Course': '🍽️',
        }
        meal_type = recipe.get('meal_type', '')
        meal_icon = meal_icons.get(meal_type, '🍽️')
        accent = meal_type_colors.get(meal_type, '#64748b')
        display_name = self._clean_display_name(recipe.get('recipe_name', 'Untitled Recipe'))
        is_fav = recipe.get('is_favorite', False)

        with st.container(border=True):
            # Colored accent bar via small HTML div
            st.markdown(
                f'<div style="height:4px;border-radius:2px;background:{accent};margin-bottom:0.5rem"></div>',
                unsafe_allow_html=True,
            )

            # Title row
            title_col, fav_col = st.columns([5, 1])
            with title_col:
                st.markdown(f"#### {meal_icon} {display_name}")
            with fav_col:
                if st.button("♥" if is_fav else "♡", key=f"fav_card_{recipe['id']}_{idx}", help="Toggle favorite"):
                    self.toggle_favorite(recipe['id'], is_fav)
                    st.rerun()

            # Metadata line
            meta_parts = []
            if recipe.get('cuisine'):
                meta_parts.append(f"**{recipe['cuisine']}**")
            if recipe.get('complexity'):
                meta_parts.append(f"*{recipe['complexity']}*")
            rating = recipe.get('rating')
            if rating:
                meta_parts.append("⭐" * rating)
            if meta_parts:
                st.markdown("&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts), unsafe_allow_html=True)

            # Dietary tags
            if recipe.get('dietary_tags') and len(recipe['dietary_tags']) > 0:
                tag_string = " ".join([f"`{tag}`" for tag in recipe['dietary_tags']])
                st.markdown(tag_string)

            # Brief recipe preview
            preview = self._get_recipe_preview(recipe.get('recipe_content', ''))
            if preview:
                st.caption(preview)

            # Date
            date_str = recipe.get('created_at', '')[:10] if recipe.get('created_at') else 'N/A'
            st.caption(f"📅 {date_str}")

            # Full recipe in expander
            with st.expander("View Full Recipe", expanded=False):
                self._render_full_recipe_content(recipe, idx)
    
    def _render_full_recipe_content(self, recipe: Dict[str, Any], idx: int):
        """
        Render the full recipe content with actions
        
        Args:
            recipe: Recipe data dictionary
            idx: Index for unique keys
        """
        # Editable recipe title
        current_name = recipe.get('recipe_name', 'Untitled Recipe')
        name_col, save_col = st.columns([4, 1])
        with name_col:
            new_name = st.text_input(
                "Recipe title",
                value=current_name,
                key=f"title_{recipe['id']}_{idx}",
                label_visibility="collapsed",
                placeholder="Recipe title",
            )
        with save_col:
            if new_name != current_name:
                if st.button("✏️ Rename", key=f"rename_{recipe['id']}_{idx}"):
                    if new_name.strip():
                        if self.update_recipe(recipe['id'], {'recipe_name': new_name.strip()}):
                            st.success("Title updated!")
                            st.rerun()
                    else:
                        st.warning("Title cannot be empty.")

        # Full metadata display
        st.markdown("**Recipe Details:**")
        metadata_cols = st.columns(3)
        
        with metadata_cols[0]:
            if recipe.get('recipe_type'):
                st.caption(f"Type: {recipe['recipe_type'].title()}")
            if recipe.get('cuisine'):
                st.caption(f"Cuisine: {recipe['cuisine']}")
        
        with metadata_cols[1]:
            if recipe.get('meal_type'):
                st.caption(f"Meal: {recipe['meal_type']}")
            if recipe.get('complexity'):
                st.caption(f"Difficulty: {recipe['complexity']}")
        
        with metadata_cols[2]:
            if recipe.get('cooking_method'):
                st.caption(f"Method: {recipe['cooking_method']}")
            if recipe.get('occasion'):
                st.caption(f"Occasion: {recipe['occasion']}")
        
        st.markdown("---")
        
        # Recipe content
        st.markdown("### Instructions")
        st.write(recipe.get('recipe_content', 'No content available'))
        
        st.markdown("---")
        
        # Action buttons - 3 columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Delete button with confirmation
            if st.session_state.confirm_delete_id == recipe['id']:
                st.warning("Are you sure?")
                if st.button("Yes, delete", key=f"confirm_full_del_{recipe['id']}_{idx}"):
                    if self.delete_recipe(recipe['id']):
                        st.session_state.confirm_delete_id = None
                        st.rerun()
                if st.button("Cancel", key=f"cancel_full_del_{recipe['id']}_{idx}"):
                    st.session_state.confirm_delete_id = None
                    st.rerun()
            else:
                if st.button(f"🗑️ Delete Recipe", key=f"delete_{recipe['id']}_{idx}"):
                    st.session_state.confirm_delete_id = recipe['id']
                    st.rerun()
        
        with col2:
            # Print card button
            if st.button(f"🖨️ Print Card", key=f"print_{recipe['id']}_{idx}"):
                with st.spinner("Creating recipe card..."):
                    recipe_card = generate_recipe_card(recipe.get('recipe_content', ''))
                    recipe_html = create_recipe_card_html(recipe_card)
                    st.session_state[f"saved_recipe_card_{recipe['id']}"] = recipe_html

            # Show download button if card was generated
            card_html = st.session_state.get(f"saved_recipe_card_{recipe['id']}")
            if card_html:
                st.download_button(
                    label="🖨️ Download Recipe Card (Open in Browser to Print)",
                    data=card_html,
                    file_name=f"{recipe.get('recipe_name', 'recipe')}_card.html",
                    mime="text/html",
                    key=f"download_card_{recipe['id']}_{idx}"
                )
        
        with col3:
            # Shopping list button
            if st.button(f"🛒 Shopping List", key=f"shop_{recipe['id']}_{idx}"):
                with st.spinner("Generating shopping list..."):
                    shopping_list = generate_shopping_list(recipe.get('recipe_content', ''))
                    st.markdown("### 🛒 Shopping List")
                    st.write(shopping_list)

        st.markdown("---")

        # --- Rating & Notes ---
        rate_col, fav_col = st.columns([3, 1])

        with rate_col:
            current_rating = recipe.get('rating') or 0
            new_rating = st.radio(
                "Rate this recipe",
                options=[0, 1, 2, 3, 4, 5],
                index=current_rating,
                format_func=lambda x: "No rating" if x == 0 else "⭐" * x,
                horizontal=True,
                key=f"rating_{recipe['id']}_{idx}"
            )

        with fav_col:
            is_fav = recipe.get('is_favorite', False)
            fav_label = "♥ Favorited" if is_fav else "♡ Favorite"
            if st.button(fav_label, key=f"fav_full_{recipe['id']}_{idx}", use_container_width=True):
                self.toggle_favorite(recipe['id'], is_fav)
                st.rerun()

        current_notes = recipe.get('user_notes') or ""
        new_notes = st.text_area(
            "Your notes",
            value=current_notes,
            placeholder="e.g., 'Kids loved it!', 'Use less salt next time'",
            key=f"notes_{recipe['id']}_{idx}"
        )

        # Save rating & notes if changed
        changes = {}
        if new_rating != current_rating:
            changes['rating'] = new_rating if new_rating > 0 else None
        if new_notes != current_notes:
            changes['user_notes'] = new_notes if new_notes else None
        if changes:
            if st.button("💾 Save Rating & Notes", key=f"save_meta_{recipe['id']}_{idx}"):
                if self.update_recipe(recipe['id'], changes):
                    st.success("Saved!")
                    st.rerun()

        # --- Copy recipe ---
        with st.expander("📋 Copy Recipe Text"):
            st.code(recipe.get('recipe_content', ''), language=None)
