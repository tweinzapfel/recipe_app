"""
Weekly Meal Planner Module
Handles meal planning, weekly calendar view, and combined shopping lists
"""

import streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from utils import generate_weekly_shopping_list


class MealPlanner:
    """Manages weekly meal planning functionality"""

    MEAL_SLOTS = ["Breakfast", "Lunch", "Dinner", "Snack"]
    SLOT_ICONS = {
        "Breakfast": "\u2600\ufe0f",
        "Lunch": "\u2600\ufe0f",
        "Dinner": "\U0001f31b",
        "Snack": "\U0001f37f",
    }
    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, supabase_client):
        """
        Initialize the meal planner.

        Args:
            supabase_client: Supabase client for database operations (uses anon key with RLS)
        """
        self.supabase_client = supabase_client
        self._initialize_planner_state()

    # ------------------------------------------------------------------
    # Session state
    # ------------------------------------------------------------------
    def _initialize_planner_state(self):
        """Initialize meal planner session state variables"""
        if "meal_planner_week_start" not in st.session_state:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            st.session_state.meal_planner_week_start = monday
        if "meal_planner_shopping_list" not in st.session_state:
            st.session_state.meal_planner_shopping_list = ""

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    def add_meal_to_plan(self, meal_data: Dict[str, Any]) -> bool:
        """Insert a meal plan entry into the database."""
        if not self.supabase_client:
            st.error("Database connection not available")
            return False
        try:
            self.supabase_client.table("meal_plans").insert(meal_data).execute()
            return True
        except Exception as e:
            st.error(f"Error adding meal to plan: {e}")
            return False

    def remove_meal_from_plan(self, meal_plan_id: str) -> bool:
        """Delete a single meal plan entry by its id."""
        if not self.supabase_client:
            st.error("Database connection not available")
            return False
        try:
            self.supabase_client.table("meal_plans").delete().eq("id", meal_plan_id).execute()
            return True
        except Exception as e:
            st.error(f"Error removing meal from plan: {e}")
            return False

    def get_meals_for_week(self, user_id: str, week_start: date) -> Optional[List[Dict]]:
        """Fetch all meal plan entries for *user_id* in the 7-day window starting at *week_start*."""
        if not self.supabase_client:
            return None
        try:
            week_end = week_start + timedelta(days=6)
            response = (
                self.supabase_client.table("meal_plans")
                .select("*, saved_recipes(recipe_content)")
                .eq("user_id", user_id)
                .gte("planned_date", week_start.isoformat())
                .lte("planned_date", week_end.isoformat())
                .order("planned_date")
                .order("meal_slot")
                .execute()
            )
            return response.data
        except Exception as e:
            # If the join fails (FK not detected), fall back to a plain select
            try:
                response = (
                    self.supabase_client.table("meal_plans")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("planned_date", week_start.isoformat())
                    .lte("planned_date", week_end.isoformat())
                    .order("planned_date")
                    .order("meal_slot")
                    .execute()
                )
                return response.data
            except Exception as e2:
                st.error(f"Error loading meal plan: {e2}")
                return None

    def _get_user_saved_recipes(self) -> Optional[List[Dict]]:
        """Fetch id + recipe_name for the current user's saved recipes (for the picker dropdown)."""
        if not self.supabase_client:
            return None
        try:
            response = (
                self.supabase_client.table("saved_recipes")
                .select("id, recipe_name")
                .eq("user_id", st.session_state.user)
                .order("recipe_name")
                .execute()
            )
            return response.data
        except Exception as e:
            st.error(f"Error loading saved recipes: {e}")
            return None

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _organize_meals_into_grid(self, meals: List[Dict], week_start: date) -> Dict:
        """Return ``{date_iso: {slot: [meal, ...]}}`` for the 7-day window."""
        grid: Dict[str, Dict[str, List]] = {}
        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            day_str = day.isoformat()
            grid[day_str] = {slot: [] for slot in self.MEAL_SLOTS}

        if meals:
            for meal in meals:
                day_str = meal.get("planned_date", "")
                slot = meal.get("meal_slot", "")
                if day_str in grid and slot in grid[day_str]:
                    grid[day_str][slot].append(meal)

        return grid

    # ------------------------------------------------------------------
    # Rendering: top-level
    # ------------------------------------------------------------------
    def render_meal_planner_view(self):
        """Top-level entry point called from main.py."""
        st.subheader("📅 Weekly Meal Planner")

        if st.session_state.user is None:
            st.warning("Please log in to use the Meal Planner.")
            return

        # Week navigation
        self._render_week_navigation()

        st.markdown("---")

        # Load data
        week_start = st.session_state.meal_planner_week_start
        meals = self.get_meals_for_week(st.session_state.user, week_start)
        grid = self._organize_meals_into_grid(meals or [], week_start)

        # Calendar grid
        self._render_weekly_calendar(grid, week_start)

        st.markdown("---")

        # Add-meal form
        self._render_add_meal_form(week_start)

        st.markdown("---")

        # Weekly shopping list
        self._render_weekly_shopping_list(meals or [])

    # ------------------------------------------------------------------
    # Rendering: week navigation
    # ------------------------------------------------------------------
    def _render_week_navigation(self):
        week_start = st.session_state.meal_planner_week_start
        week_end = week_start + timedelta(days=6)
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("← Previous Week", use_container_width=True):
                st.session_state.meal_planner_week_start = week_start - timedelta(weeks=1)
                st.session_state.meal_planner_shopping_list = ""
                st.rerun()

        with col2:
            st.markdown(
                f"### Week of {week_start.strftime('%B %d')} – {week_end.strftime('%B %d, %Y')}",
            )
            if week_start != current_monday:
                if st.button("Jump to Current Week", use_container_width=True):
                    st.session_state.meal_planner_week_start = current_monday
                    st.session_state.meal_planner_shopping_list = ""
                    st.rerun()

        with col3:
            if st.button("Next Week →", use_container_width=True):
                st.session_state.meal_planner_week_start = week_start + timedelta(weeks=1)
                st.session_state.meal_planner_shopping_list = ""
                st.rerun()

    # ------------------------------------------------------------------
    # Rendering: 7-day calendar grid
    # ------------------------------------------------------------------
    def _render_weekly_calendar(self, grid: Dict, week_start: date):
        today = date.today()
        cols = st.columns(7)

        for day_offset, col in enumerate(cols):
            day = week_start + timedelta(days=day_offset)
            day_str = day.isoformat()
            day_name = self.DAYS_OF_WEEK[day_offset]
            is_today = day == today

            with col:
                # Day header
                if is_today:
                    st.markdown(f"**:blue[{day_name}]**  \n{day.strftime('%m/%d')}")
                else:
                    st.markdown(f"**{day_name}**  \n{day.strftime('%m/%d')}")

                # Meal slots
                for slot in self.MEAL_SLOTS:
                    meals_in_slot = grid[day_str][slot]
                    icon = self.SLOT_ICONS.get(slot, "🍽️")
                    st.caption(f"{icon} {slot}")

                    if meals_in_slot:
                        for meal in meals_in_slot:
                            st.markdown(f"**{meal['recipe_name']}**")
                            if meal.get("notes"):
                                st.caption(meal["notes"])
                            if st.button("✕", key=f"del_{meal['id']}", help="Remove from plan"):
                                if self.remove_meal_from_plan(meal["id"]):
                                    st.session_state.meal_planner_shopping_list = ""
                                    st.rerun()
                    else:
                        st.caption("—")

                st.markdown("---")

    # ------------------------------------------------------------------
    # Rendering: add-meal form
    # ------------------------------------------------------------------
    def _render_add_meal_form(self, week_start: date):
        st.subheader("Add a Meal")

        # Let user choose between a saved recipe or custom text
        source = st.radio(
            "Meal source",
            options=["Saved recipe", "Custom meal"],
            horizontal=True,
            key="meal_source_radio",
        )

        with st.form("add_meal_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            selected_recipe_id = None
            recipe_name = ""

            if source == "Saved recipe":
                saved_recipes = self._get_user_saved_recipes()
                with col1:
                    if saved_recipes:
                        recipe_options = {r["id"]: r["recipe_name"] for r in saved_recipes}
                        selected_recipe_id = st.selectbox(
                            "Select a recipe",
                            options=list(recipe_options.keys()),
                            format_func=lambda x: recipe_options[x],
                        )
                        recipe_name = recipe_options.get(selected_recipe_id, "")
                    else:
                        st.info("No saved recipes yet — save some first, or use 'Custom meal'.")
            else:
                with col1:
                    recipe_name = st.text_input(
                        "Meal name",
                        placeholder="e.g., Leftover pizza, Eat out",
                    )

            with col2:
                planned_date = st.date_input(
                    "Date",
                    value=week_start,
                    min_value=week_start,
                    max_value=week_start + timedelta(days=6),
                )

            with col3:
                meal_slot = st.selectbox("Meal", self.MEAL_SLOTS)

            notes = st.text_input("Notes (optional)", placeholder="e.g., double the recipe")

            submitted = st.form_submit_button("Add to Plan", use_container_width=True)

            if submitted:
                if not recipe_name:
                    st.warning("Please select a recipe or enter a meal name.")
                else:
                    meal_data: Dict[str, Any] = {
                        "user_id": st.session_state.user,
                        "recipe_name": recipe_name,
                        "planned_date": planned_date.isoformat(),
                        "meal_slot": meal_slot,
                        "notes": notes if notes else None,
                    }
                    if selected_recipe_id:
                        meal_data["recipe_id"] = str(selected_recipe_id)

                    if self.add_meal_to_plan(meal_data):
                        st.success(
                            f"Added '{recipe_name}' to "
                            f"{planned_date.strftime('%A')} {meal_slot}!"
                        )
                        st.session_state.meal_planner_shopping_list = ""
                        st.rerun()

    # ------------------------------------------------------------------
    # Rendering: weekly shopping list
    # ------------------------------------------------------------------
    def _render_weekly_shopping_list(self, meals: List[Dict]):
        st.subheader("🛒 Weekly Shopping List")

        if not meals:
            st.info("Add some meals to your plan to generate a combined shopping list.")
            return

        # Count only meals that have linked recipe content
        recipes_with_content = []
        for meal in meals:
            content = None
            saved = meal.get("saved_recipes")
            if isinstance(saved, dict):
                content = saved.get("recipe_content")
            if content:
                recipes_with_content.append((meal, content))

        total_meals = len(meals)
        with_content = len(recipes_with_content)

        st.write(f"**{total_meals}** meal(s) planned this week ({with_content} with recipe content for the shopping list).")

        if with_content == 0:
            st.info("None of the planned meals have linked recipe content. Add meals from your saved recipes to generate a shopping list.")
            return

        if st.button("Generate Weekly Shopping List", key="weekly_shopping_btn", use_container_width=True):
            recipe_texts = []
            for meal, content in recipes_with_content:
                recipe_texts.append(
                    f"--- {meal['recipe_name']} ({meal['meal_slot']}, {meal['planned_date']}) ---\n{content}"
                )

            combined_text = "\n\n".join(recipe_texts)

            with st.spinner("Generating combined weekly shopping list..."):
                shopping_list = generate_weekly_shopping_list(combined_text)
                st.session_state.meal_planner_shopping_list = shopping_list

        if st.session_state.meal_planner_shopping_list:
            st.markdown(st.session_state.meal_planner_shopping_list)
