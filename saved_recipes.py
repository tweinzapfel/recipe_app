"""
Saved Recipes Manager Module
Handles saving, loading, and displaying saved recipes
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List
from utils import generate_recipe_card, create_recipe_card_html, extract_recipe_name

class SavedRecipesManager:
    """Manages saved recipes functionality"""
    
    def __init__(self, supabase_admin):
        """
        Initialize the saved recipes manager
        
        Args:
            supabase_admin: Supabase admin client for database operations
        """
        self.supabase_admin = supabase_admin
    
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
            st.info("📝 Create an account and log in to save your favorite recipes!")
        
        return False
    
    def render_saved_recipes_view(self):
        """Render the saved recipes view"""
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
                    if self.delete_recipe(recipe['id']):
                        st.success("Recipe deleted!")
                        st.rerun()
            
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
