"""
Utility Functions Module
Contains helper functions for the recipe app
"""

import streamlit as st
from datetime import date
from openai import OpenAI
import re
from typing import Tuple, Optional

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with API key from secrets"""
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
        'occasion_recipe_card': ""
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
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Clean up the line
        clean_line = line.strip()
        
        # Skip common non-recipe-name patterns
        skip_patterns = [
            'here', 'recipe', 'suggest', 'perfect', 'delicious', 'enjoy',
            'this is', 'try this', 'servings:', 'prep time:', 'cook time:',
            'ingredients:', 'instructions:', 'directions:', '---', '**'
        ]
        
        # Check if line contains skip patterns (case insensitive)
        if any(pattern in clean_line.lower() for pattern in skip_patterns):
            continue
        
        # Remove markdown formatting
        clean_line = clean_line.replace('#', '').replace('*', '').strip()
        
        # If line is reasonable length for a recipe name (5-80 chars) and doesn't start with a number
        if 5 <= len(clean_line) <= 80 and not clean_line[0].isdigit():
            return clean_line
    
    # Fallback: return first non-empty line, cleaned
    for line in lines:
        clean_line = line.strip().replace('#', '').replace('*', '').strip()
        if clean_line and len(clean_line) > 3:
            return clean_line[:80]  # Limit to 80 chars
    
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
