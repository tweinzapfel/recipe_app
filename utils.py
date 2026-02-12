"""
Utility Functions Module
Contains helper functions for the recipe app
"""

import streamlit as st
from datetime import date
from openai import OpenAI
import re
from typing import Tuple, Optional

@st.cache_resource
def get_openai_client():
    """Get OpenAI client with API key from secrets (cached across reruns)"""
    return OpenAI(api_key=st.secrets["api_key"])

def initialize_session_state():
    """Initialize all session state variables"""
    default_states = {
        'identified_ingredients': "",
        'cuisine_shopping_list': "",
        'fridge_shopping_list': "",
        'photo_shopping_list': "",
        'cuisine_recipe_content': "",
        'fridge_recipe_content': "",
        'photo_recipe_content': "",
        'uploaded_photos': [],
        'all_identified_ingredients': "",
        'cuisine_recipe_card': "",
        'fridge_recipe_card': "",
        'photo_recipe_card': "",
        'user': None,
        'user_email': None,
        'access_token': None,
        'refresh_token': None,
        'show_saved_recipes': False,
        'occasion_recipe_content': "",
        'occasion_shopping_list': "",
        'occasion_recipe_card': "",
        'surprise_recipe_content': "",
        'surprise_shopping_list': "",
        'surprise_recipe_card': ""
    }
    
    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def get_current_holiday() -> Tuple[str, str]:
    """
    Determine if there's a current or upcoming holiday/special occasion
    
    Returns:
        Tuple of (holiday_name, holiday_description)
    """
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

def extract_recipe_name(recipe_content: str) -> str:
    """
    Extract just the recipe name from the AI response

    Args:
        recipe_content: The full recipe text from AI

    Returns:
        str: Clean recipe name
    """
    lines = recipe_content.split('\n')

    # Pass 1: Look for markdown headers — most reliable title indicator
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            name = stripped.lstrip('#').strip()
            # Skip section headers like "## Ingredients"
            section_words = [
                'ingredients', 'instructions', 'directions', 'steps',
                'tips', 'notes', 'shopping', 'servings'
            ]
            if name and len(name) >= 3 and not any(
                name.lower().startswith(w) for w in section_words
            ):
                return name[:80]

    # Pass 2: Look for standalone bold lines like **Recipe Name**
    for line in lines:
        stripped = line.strip()
        match = re.match(r'^\*\*(.+?)\*\*$', stripped)
        if match:
            name = match.group(1).strip()
            section_words = [
                'ingredients', 'instructions', 'directions', 'steps',
                'tips', 'notes', 'servings', 'prep time', 'cook time',
                'total time', 'shopping'
            ]
            if len(name) >= 3 and not any(
                name.lower().startswith(w) for w in section_words
            ):
                return name[:80]

    # Pass 3: First meaningful line that looks like a title
    intro_patterns = [
        'here', 'suggest', 'perfect', 'delicious', 'enjoy',
        'this is', 'try this', 'sure!', 'absolutely', 'great choice',
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()

        # Skip intro/filler lines
        if any(p in lower for p in intro_patterns):
            continue
        # Skip metadata lines
        if any(p in lower for p in [
            'servings:', 'prep time:', 'cook time:', 'total time:',
            'ingredients:', 'instructions:', 'directions:', '---',
        ]):
            continue
        # Skip list items (ingredients / bullet points)
        if stripped.startswith('-') or stripped.startswith('•'):
            continue
        # Skip numbered instruction lines
        if re.match(r'^\d+[\.\)]\s', stripped):
            continue

        # Clean markdown formatting
        clean = stripped.replace('#', '').replace('*', '').strip()

        if 3 <= len(clean) <= 80:
            return clean

    # Fallback
    for line in lines:
        clean = line.strip().replace('#', '').replace('*', '').strip()
        if clean and len(clean) > 3:
            return clean[:80]

    return "Untitled Recipe"

def generate_shopping_list(recipe_text: str, available_ingredients: str = "") -> str:
    """
    Generate a shopping list from a recipe
    
    Args:
        recipe_text: The recipe content
        available_ingredients: Ingredients the user already has
        
    Returns:
        str: Formatted shopping list
    """
    client = get_openai_client()
    
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful shopping assistant who creates organized grocery lists from recipes."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating shopping list: {e}"

def generate_recipe_card(recipe_text: str) -> str:
    """
    Generate a print-friendly recipe card from recipe text
    
    Args:
        recipe_text: The recipe content
        
    Returns:
        str: Formatted recipe card in markdown
    """
    client = get_openai_client()
    
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who creates beautifully formatted, print-friendly recipe cards. Always use sequential numbering (1. 2. 3. 4.) for instructions, never repeat '1.' for each step."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating recipe card: {e}"

def generate_weekly_shopping_list(combined_recipe_text: str) -> str:
    """
    Generate a combined shopping list from multiple recipes for a week's meal plan.

    Args:
        combined_recipe_text: Concatenated text of all recipes for the week

    Returns:
        str: Formatted combined shopping list with deduplication
    """
    client = get_openai_client()

    try:
        prompt = f"""
        I have the following recipes planned for the week:

        {combined_recipe_text}

        Please create a COMBINED, DEDUPLICATED shopping list by:
        1. Extracting all ingredients from ALL recipes above
        2. Combining duplicate ingredients and summing their quantities
           (e.g., if two recipes need 1 cup of rice each, list "Rice (2 cups)")
        3. Organizing by grocery store sections (Produce, Meat/Seafood, Dairy, Pantry, etc.)
        4. Noting which recipe(s) each ingredient is used in

        Format as:
        **WEEKLY SHOPPING LIST**

        **Produce:**
        - item (total quantity) - used in: Recipe A, Recipe B

        **Meat/Seafood:**
        - item (total quantity) - used in: Recipe A

        **Dairy:**
        - item (total quantity) - used in: Recipe B

        **Pantry/Dry Goods:**
        - item (total quantity) - used in: Recipe A, Recipe C

        **Other:**
        - item (total quantity) - used in: Recipe B

        Be smart about combining similar items. Skip very common pantry staples
        like salt, pepper, and cooking oil unless large quantities are needed.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful shopping assistant who creates organized, deduplicated grocery lists from multiple recipes for weekly meal planning."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating weekly shopping list: {e}"

def create_recipe_card_html(recipe_card_content: str) -> str:
    """
    Convert markdown recipe card to HTML for printing
    
    Args:
        recipe_card_content: Markdown formatted recipe card
        
    Returns:
        str: Complete HTML document for printing
    """
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


def generate_nutritional_info(recipe_text: str) -> str:
    """
    Generate estimated nutritional information for a recipe.

    Args:
        recipe_text: The recipe content

    Returns:
        str: Formatted nutritional estimates per serving
    """
    client = get_openai_client()
    try:
        prompt = f"""Based on this recipe, provide estimated nutritional information per serving:

{recipe_text}

Format as:
**Estimated Nutrition Per Serving:**
- Calories: ~XXX kcal
- Protein: ~XXg
- Carbohydrates: ~XXg
- Fat: ~XXg
- Fiber: ~XXg
- Sodium: ~XXXmg

Note: These are rough estimates based on typical ingredient quantities."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a nutritionist who provides estimated nutritional information for recipes. Give reasonable estimates based on typical serving sizes and ingredient quantities."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating nutritional info: {e}"


def generate_substitutions(recipe_text: str, ingredient: str) -> str:
    """
    Generate ingredient substitution suggestions for a recipe.

    Args:
        recipe_text: The recipe content
        ingredient: The ingredient to find substitutes for

    Returns:
        str: Formatted substitution suggestions
    """
    client = get_openai_client()
    try:
        prompt = f"""For this recipe:

{recipe_text}

What are good substitutions for "{ingredient}"? Consider:
1. Common pantry alternatives
2. Dietary alternatives (vegan, gluten-free, etc.)
3. How each substitute affects the dish
4. Quantity adjustments needed

List 3-5 practical options."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful chef who suggests ingredient substitutions. Be practical and consider flavor, texture, and cooking properties."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating substitutions: {e}"


def scale_recipe(recipe_text: str, target_servings: int) -> str:
    """
    Rescale a recipe to a different number of servings.

    Args:
        recipe_text: The original recipe content
        target_servings: The desired number of servings

    Returns:
        str: The rescaled recipe with adjusted quantities
    """
    client = get_openai_client()
    try:
        prompt = f"""Please rescale this recipe to serve exactly {target_servings} people.

Original recipe:
{recipe_text}

Adjust ALL ingredient quantities proportionally. Keep the instructions the same but update any references to quantities. Format the complete rescaled recipe with adjusted ingredients and instructions."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful chef who rescales recipes accurately. Always show the complete rescaled recipe with adjusted quantities."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error scaling recipe: {e}"


def generate_ics_calendar(meals: list) -> str:
    """
    Generate an .ics calendar file from meal plan entries.

    Args:
        meals: List of meal plan dictionaries with recipe_name, planned_date, meal_slot, notes

    Returns:
        str: ICS calendar file content
    """
    slot_times = {
        "Breakfast": ("0800", "0900"),
        "Lunch":     ("1200", "1300"),
        "Dinner":    ("1800", "1930"),
        "Snack":     ("1500", "1530"),
    }

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Dinner Recipe Maker//Meal Planner//EN",
    ]

    for meal in meals:
        name = meal.get("recipe_name", "Meal")
        planned_date = meal.get("planned_date", "")
        slot = meal.get("meal_slot", "Dinner")
        notes = meal.get("notes", "") or ""

        start_time, end_time = slot_times.get(slot, ("1800", "1930"))
        date_clean = planned_date.replace("-", "")

        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART:{date_clean}T{start_time}00",
            f"DTEND:{date_clean}T{end_time}00",
            f"SUMMARY:{slot}: {name}",
            f"DESCRIPTION:{notes.replace(chr(10), ' ')}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
