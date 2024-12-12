import os
import json
from bs4 import BeautifulSoup
from bs4 import Tag
import re

# initialize
json_data = []

all_unlogged = {}
def log_unhandled_sections(soup, processed_sections, ignored_sections, page_title):
    # Find all <h2> tags for potential sections
    for header in soup.find_all("h2"):
        # Extract the section title
        section_title_tag = header.find("span", class_="mw-headline")
        section_title = section_title_tag.get_text(strip=True) if section_title_tag else "Unknown Section"

        # Skip ignored or already processed sections
        if section_title in processed_sections or section_title in ignored_sections:
            continue

        if section_title != "Unknown Section": 
            # Log the unhandled section title
            print(f"[INFO] Unhandled section found: {section_title} in {page_title}")
            if section_title in all_unlogged:
                all_unlogged[section_title] += 1
            else:
                all_unlogged[section_title] = 1


def process_general_info(soup, page_title):
    general_info_chunks = []
    
    # locate the main content within <div class="mw-parser-output">
    main_content = soup.find('div', class_='mw-parser-output')
    if not main_content:
        return general_info_chunks
    
    # Flag to identify if we are still within the relevant section
    collecting_content = True
    
    # locate all elements within the main content area (typically <p> and <ul> before 'Contents' or any <h2>)
    for element in main_content.find_all(['p', 'ul', 'h2'], recursive=False):
        # Check if any new section marked by an <h2> has started
        if element.name == 'h2':
            collecting_content = False  # Stop collecting content once we reach any <h2>
            break
        
        if collecting_content and element.name in ['p', 'ul']:
            # Extract the text content from the <p> and <ul> tags
            text_content = element.get_text(separator=" ", strip=True)
            if text_content:
                general_info_chunks.append({
                    "text": text_content,
                    "metadata": {
                        "page_title": page_title,
                        "section_title": "General Information"
                    }
                })
    
    return general_info_chunks

def process_infoboxes(soup, page_title):
    infoboxes = soup.find_all("div", class_="infobox item")  # get "infobox item"
    infobox_chunks = []
    
    for infobox in infoboxes:
        # extract title
        title = infobox.find("div", class_="title").get_text(strip=True) if infobox.find("div", class_="title") else "Unknown Title"

        # extract statistics
        values = {
            'type': None,
            'rarity': None,
            'buy': None,
            'sell': None,
            'tooltip': None,
            'body_slot': None,
            'research': None,
            'set_bonus': None,
            'consumable': None,
            'defense': None,
            'damage': None,
            'knockback': None,
            'critical_chance': None,
            'use_time': None,
            'velocity': None,
            'mana': None,
            'healsmana': None,
            'healshealth': None,
            'max_stack': None,
            'basevelocity': None,
            'velocity_multiplier': None,
            'tool_speed': None,
            'baitpower': None,
            'placeable': None,
            'bonus': None,
            'usesammo': None
        }
        
        unprocessed_fields = []  # list to hold unhandled keys
        stat_table = infobox.find("table", class_="stat")
        
        if stat_table:
            for row in stat_table.find_all("tr"):
                key = row.find("th").get_text(strip=True) if row.find("th") else "Unknown Key"
                value_tag = row.find("td")
                value = value_tag.get_text(separator=" ", strip=True) if value_tag else "Unknown Value"
                
                # Handle specific keys
                normalized_key = re.sub(r'[^a-zA-Z0-9_]', '_', key.lower())
                # print(normalized_key)
                
                if key.lower() == "set bonus":
                    # Process set bonus: split by ':' and format each effect
                    effects = [effect.strip() for effect in value.split(':') if effect.strip()]
                    values["set_bonus"] = "and ".join(effects)  # Combine into a readable sentence
                elif key.lower() == "buy" and value_tag and value_tag.find("span", class_="coin"):
                    coin_span = value_tag.find("span", class_="coin")
                    coin_title = coin_span.get("title", "")
                    if coin_title:
                        values['buy'] = coin_title  # Extract full description
                elif key.lower() == "sell" and value_tag and value_tag.find("span", class_="coin"):
                    coin_span = value_tag.find("span", class_="coin")
                    coin_title = coin_span.get("title", "")
                    if coin_title:
                        values['sell'] = coin_title  # Extract full description
                elif key.lower() == "rarity" and value_tag and value_tag.find("span", class_="rarity"):
                    rarity_sortkey = value_tag.find("s", class_="sortkey")
                    if rarity_sortkey:
                        values['rarity'] = re.sub(r'[^0-9]', '', rarity_sortkey.get_text())
                elif normalized_key in values:
                    values[normalized_key] = value
                else:
                    # log unprocessed fields
                    unprocessed_fields.append(f"Key: '{key}', Value: '{value}'")
                    

        # print any unprocessed fields to standard output
        if unprocessed_fields:
            print(f"[INFO] Unhandled fields in '{title}' from infobox:")
            for field in unprocessed_fields:
                print(f"  - {field}")

        text_content = f""
        
        # general
        if values['type']:
            text_content += f"'{title}' is a {values['type'].lower()}. "
        else: 
            text_content += f"The item is '{title}'. "

        if values['consumable']:
            text_content += f"It is consumable. "
        if values['placeable']:
            text_content += f"It is placeable. "
        if values['rarity']:
            text_content += f"It has a rarity level of {values['rarity']}. "
        if values['buy']:
            text_content += f"It can be bought for {values['buy']}. "
        if values['sell']:
            text_content += f"It can be sold for {values['sell']}. "
        if values['research']:
            research_number = re.sub(r'[^0-9]', '', values['research']) if values['research'] else 'unknown'
            text_content += f"In journey mode, it requires {research_number} research. "
            
            
        # misc
        if values['tooltip']:
            text_content += f"The tooltip reads: \"{values['tooltip']}\". "
        if values['bonus']:
            text_content += f"It provides a bonus of \"{values['bonus']}\". "
            
        # armor and equipable things
        if values['body_slot']:
            text_content += f"It is equipped in the {values['body_slot']}. "
        if values['set_bonus']:
            text_content += f"When worn as a whole armor set, it provides the bonus of {values['set_bonus']}. "
        if values['defense']:
            text_content += f"It provides a defense rating of {values['defense']}. "
            
        # weapon
        if values['damage']:
            text_content += f"It deals {values['damage']} damage. "
        if values['knockback']:
            text_content += f"It has a knockback rating of {values['knockback']}. "
        if values['critical_chance']:
            text_content += f"It has a critical chance of {values['critical_chance']}. "
        if values['velocity']:
            text_content += f"It has a velocity of {values['velocity']}. "
        if values['mana']:
            text_content += f"It has a mana cost of {values['mana']}. "
        if values['healsmana']:
            text_content += f"It heals mana by {values['healsmana']}. "
        if values['healshealth']:
            text_content += f"It heals health by {values['healshealth']}. "
            
            
        # projectiles
        if values['usesammo']:
            text_content += f"Its uses {values['usesammo']} as ammo. "
        if values['basevelocity']:
            text_content += f"Its base velocity is {values['basevelocity']}. "
        if values['velocity_multiplier']:
            text_content += f"It has a velocity multiplier of {values['velocity_multiplier']}. "
            
        # using
        if values['use_time']:
            text_content += f"It has a use time of {values['use_time']}. "
        if values['tool_speed']:
            text_content += f"It has a tool speed of {values['tool_speed']}. "
            
        # bait
        if values['baitpower']:
            text_content += f"When used as bait, it has a bait power of {values['baitpower']}. "
        
        # blocks
        if values['max_stack']:
            text_content += f"The max amount it can be stacked in one slot is {values['max_stack']}. "
        
        # chunk for the infobox
        infobox_chunks.append({
            "text": text_content.strip(),
            "metadata": {
                "page_title": page_title,
                "section_title": "Infobox"
            }
        })
    
    return infobox_chunks

def process_drop_infoboxes(soup, page_title):
    drop_infoboxes = soup.find_all("div", class_="drop infobox modesbox c-normal mw-collapsible")
    drop_chunks = []
    
    for drop_infobox in drop_infoboxes:
        # Extract title (ignore images, get only text)
        title_tag = drop_infobox.find("div", class_="title")
        title_text = title_tag.get_text(separator=" ", strip=True) if title_tag else "Unknown Item"

        # Extract mode-specific tables
        unprocessed_items = []  # Track unhandled items

        # Locate the associated drop table for this mode
        drop_table = drop_infobox.find("table", class_="drop-noncustom sortable")
        
        entities = []
        if drop_table:
            for row in drop_table.find_all("tr")[1:]:  # Skip the header row
                columns = row.find_all("td")
                if len(columns) == 3:
                    try:
                        # Extract entity name, avoiding duplicates from <span class="i -w entity-img"> and <span class="entity-name">
                        entity_name_tag = columns[0]
                        
                        # Remove child spans with class 'i -w entity-img' and 'entity-name' before extracting the text
                        for span in entity_name_tag.find_all("span", class_=["i -w entity-img", "entity-name"]):
                            span.decompose()
                        
                        entity_name = entity_name_tag.get_text(separator=" ", strip=True)
                        

                        def extract_ranges(text):
                            # Pattern to match ranges with version details
                            pattern_with_versions = re.compile(r"(\d+\s*[-–]\s*\d+)\s*\((.*?)\)(?:\s*/\s*(\d+\s*[-–]\s*\d+)\s*\((.*?)\))?")
                            # Pattern to match simple ranges and single numbers
                            pattern_simple_range = re.compile(r"(\d+\s*[-–]\s*\d+|\d+|\[\d+\]|\[\d+-\d+\])")
                            
                            results = []
                            
                            # Extract ranges with version details
                            for match in pattern_with_versions.finditer(text):
                                range1, version1, range2, version2 = match.groups()
                                entry = []
                                if range1 and version1:
                                    entry.append((range1.replace("\u2013", "-"), f'({version1})'))  # Replace en-dash with hyphen
                                if range2 and version2:
                                    entry.append((range2.replace("\u2013", "-"), f'({version2})'))  # Replace en-dash with hyphen
                                results.append(entry)
                            
                            # Remove the matched portions from the text to avoid duplicate matches
                            cleaned_text = pattern_with_versions.sub("", text)
                            
                            # Extract simple ranges (without version details) from the remaining text
                            for match in pattern_simple_range.finditer(cleaned_text):
                                entry = [(match.group(1).replace("\u2013", "-"), '')]  # Replace en-dash with hyphen
                                results.append(entry)
                            
                            return results

                        # Extract and process quantity
                        quantity_raw = columns[1].get_text(separator=" ", strip=True)
                        
                        extracted_quantities = extract_ranges(quantity_raw)
    
                        # Format the extracted quantities into the required output format
                        formatted_quantities = []
                        for i, quantity_group in enumerate(extracted_quantities):
                            for (rate, version) in (quantity_group):
                                if version:
                                    formatted_quantities.append(f"{rate} {page_title} in {version.strip()[1:-1]}")
                                elif len(extracted_quantities) > 1 and i == 0:
                                    formatted_quantities.append(f"{rate} {page_title} in Classic")
                                elif len(extracted_quantities) == 2 and i == 1:
                                    formatted_quantities.append(f"{rate} {page_title} in Expert and Master")
                                elif len(extracted_quantities) == 3 and i == 1:
                                    formatted_quantities.append(f"{rate} {page_title} in Expert")
                                elif len(extracted_quantities) == 3 and i == 2:
                                    formatted_quantities.append(f"{rate} {page_title} in Master")
                                else:
                                    formatted_quantities.append(f"{rate} {page_title}")
                                    
                        # Join the formatted quantities with ' / ' separator
                        quantity_text = " and ".join(formatted_quantities) if formatted_quantities else "Unknown drop rate"
                        
                        # Extract drop rate, handle multiple drop rates in the same cell
                        drop_rate_raw = columns[2].get_text(separator=" ", strip=True)
                        
                        # Extract drop rates and versions using a regex to match percentage patterns with optional version info
                        drop_rates_with_versions = re.findall(r'(\d+\.?\d*%)\s*(\([^)]*\))?', drop_rate_raw)
                        
                        # Format drop rates to include version info
                        formatted_drop_rates = []
                        for i, (rate, version) in enumerate(drop_rates_with_versions):
                            if version:
                                formatted_drop_rates.append(f"{rate} in {version.strip()[1:-1]}")
                            elif len(drop_rates_with_versions) > 1 and i == 0:
                                formatted_drop_rates.append(f"{rate} in Classic")
                            elif len(drop_rates_with_versions) == 2 and i == 1:
                                formatted_drop_rates.append(f"{rate} in Expert and Master")
                            elif len(drop_rates_with_versions) == 3 and i == 1:
                                formatted_drop_rates.append(f"{rate} in Expert")
                            elif len(drop_rates_with_versions) == 3 and i == 2:
                                formatted_drop_rates.append(f"{rate} in Master")
                            else:
                                formatted_drop_rates.append(rate)
                        
                        drop_rate_text = " and ".join(formatted_drop_rates) if formatted_drop_rates else "Unknown drop rate"
                        
                    except Exception as e:
                        # Log any exceptions or unhandled cases
                        unprocessed_items.append(f"Unhandled row in: {columns}")
                        continue

                    # Form full entity description with multiple drop rates and version info
                    full_entity_description = (
                        f"{entity_name} has a {drop_rate_text} chance to drop {quantity_text}."
                    )
                    
                    entities.append(full_entity_description)
                else:
                    # Log unhandled row structure
                    unprocessed_items.append(f"Unexpected row format in: {row}")

        # Print any unprocessed items
        if unprocessed_items:
            print(f"[INFO] Unhandled cases in '{title_text}':")
            for item in unprocessed_items:
                print(f"  - {item}")

        # Construct text content
        for entity in entities:
            text_content = f"{entity}"
            
            # Create a chunk for the drop infobox
            drop_chunks.append({
                "text": text_content.strip(),
                "metadata": {
                    "page_title": page_title,
                    "section_title": "Drop Infobox"
                }
            })

    return drop_chunks

def process_crafting_section(soup, page_title):
    crafting_chunks = []

    # Locate the "Crafting" section header
    crafting_header = soup.find("span", {"id": "Crafting"})
    if not crafting_header:
        return crafting_chunks  # No crafting section found

    # Process each subsection under "Crafting"
    for subsection_id, section_title in [("Recipes", "Recipes"), ("Used_in", "Used in")]:
        subsection_header = crafting_header.find_next("span", {"id": subsection_id})
        if not subsection_header:
            continue  # Skip if the subsection is not found

        # Find the corresponding table
        crafting_table = subsection_header.find_next("table", class_="recipes")
        if not crafting_table:
            continue  # Skip if no table is found

        # Parse the crafting table rows
        rows = crafting_table.find_all("tr")[1:]  # Skip the header row
        current_result = "Unknown Result"
        current_station = "Unknown Station"

        for row in rows:
            # Extract result, update only if present in the current row
            result_cell = row.find("td", class_="result")
            if result_cell:
                current_result = result_cell.get_text(strip=True)
                # Insert space before any version info enclosed in parentheses
                current_result = re.sub(r"(\S)(\(.*?\))", r"\1 \2", current_result)
                current_result = re.sub(r"InternalItem ID: \d+", "", current_result)  # Remove 'InternalItem ID: <digits>'
                current_result = re.sub(r"\bonly:\b", "", current_result)  # Remove the word 'only'


            # Extract ingredients
            ingredients_cell = row.find("td", class_="ingredients")
            ingredients = []
            if ingredients_cell:
                for li in ingredients_cell.find_all("li"):
                    # Extract quantity and name in "X item_name" format
                    amount_tag = li.find("span", class_="am")
                    quantity = amount_tag.get_text(strip=True) if amount_tag else "1"
                    item_name = li.get_text(separator=" ", strip=True).replace(quantity, "").strip()
                    ingredients.append(f"{quantity} {item_name}")

            # Extract crafting station, update only if present in the current row
            station_cell = row.find("td", class_="station")
            if station_cell:
                current_station = station_cell.get_text(separator=" ", strip=True)

            if section_title == "Recipes":
                # Check if the result has a quantity at the end (e.g., 'Nebula Brick 10')
                match = re.match(r"(.*?)(\d+)$", current_result)
                if match:
                    item_name = match.group(1).strip()
                    quantity = match.group(2)
                    crafting_chunks.append({
                        "text": f"{quantity} {item_name} can be crafted using {', '.join(ingredients)} at the {current_station}.",
                        "metadata": {
                            "page_title": page_title,
                            "section_title": "Crafting - Recipes"
                        }
                    })
                else:
                    crafting_chunks.append({
                        "text": f"{current_result} can be crafted using {', '.join(ingredients)} at the {current_station}.",
                        "metadata": {
                            "page_title": page_title,
                            "section_title": "Crafting - Recipes"
                        }
                    })
            elif section_title == "Used in":
                match = re.match(r"(.*?)(\d+)$", current_result)
                if match:
                    item_name = match.group(1).strip()
                    quantity = match.group(2)
                    crafting_chunks.append({
                        "text": f"{quantity} {item_name} can be crafted using {', '.join(ingredients)} at the {current_station}.",
                        "metadata": {
                            "page_title": page_title,
                            "section_title": "Crafting - Used in"
                        }
                    })
                else:
                    crafting_chunks.append({
                        "text": f"{current_result} can be crafted using {', '.join(ingredients)} at the {current_station}.",
                        "metadata": {
                            "page_title": page_title,
                            "section_title": "Crafting - Used in"
                        }
                    })

    return crafting_chunks

def process_set_section(soup, page_title):
    set_section = soup.find("span", {"id": "Set"})
    set_chunks = []

    if set_section:
        # Locate the parent <h2> tag to find associated content
        set_header = set_section.find_parent("h2")
        set_content = set_header.find_next_sibling("div")

        if set_content:
            # Find all infoboxes within the "Set" section
            infoboxes = set_content.find_all("div", class_="infobox item")
            for infobox in infoboxes:
                # Extract item title
                title = infobox.find("div", class_="title").get_text(strip=True) if infobox.find("div", class_="title") else "Unknown Item"

                # Extract statistics
                type_value = None
                body_slot = None
                rarity_value = None
                buy_value = None
                sell_value = None
                research_value = None
                tooltip = None
                defense = None
                unprocessed_fields = []  # Track unhandled fields

                stat_table = infobox.find("table", class_="stat")
                if stat_table:
                    for row in stat_table.find_all("tr"):
                        key = row.find("th").get_text(strip=True) if row.find("th") else "Unknown Key"
                        value_tag = row.find("td")
                        value = value_tag.get_text(separator=" ", strip=True) if value_tag else "Unknown Value"
                        
                        # Handle specific keys
                        if key.lower() == "type":
                            type_value = value.lower()
                        elif key.lower() == "body slot":
                            body_slot = value
                        elif key.lower() == "rarity":
                            rarity_sortkey = value_tag.find("s", class_="sortkey")
                            if rarity_sortkey:
                               rarity_value = re.sub(r'[^0-9]', '', rarity_sortkey.get_text())
                        elif key.lower() == "buy":
                            # Handle Defender Medals and other formats
                            if "Defender Medals" in value:
                                buy_value = value_tag.get("title", value)
                            elif value_tag.find("span", class_="coins"):
                                buy_value = value_tag.find("span", class_="coins").get("title", value)
                            else:
                                buy_value = value
                        elif key.lower() == "sell":
                            if value.lower() == "no value":
                                sell_value = "No value"
                            else:
                                coin_span = value_tag.find("span", class_="coin")
                                sell_value = coin_span.get("title", "") if coin_span else value
                        elif key.lower() == "tooltip":
                            tooltip = value.strip("'")
                        elif key.lower() == "research":
                            research_value = value
                        elif key.lower() == "defense":
                            defense = value
                        else:
                            # Log unprocessed field
                            unprocessed_fields.append(f"Key: '{key}', Value: '{value}'")

                # Print unprocessed fields
                if unprocessed_fields:
                    print(f"[INFO] Unhandled fields in '{title}', set:")
                    for field in unprocessed_fields:
                        print(f"  - {field}")

                # Construct text content for the item
                text_content = (
                    f"The item '{title}' is part of the {page_title + (' set' if not page_title.lower().endswith('set') else '')} and is of type {type_value}."
                    f"It is equipped in the {body_slot} slot. "
                    f"It has a rarity level of {rarity_value}. "
                )
                if buy_value:
                    text_content += f"It can be bought for {buy_value}. "
                if sell_value:
                    text_content += f"It can be sold for {sell_value}. "
                if tooltip:
                    text_content += f"The tooltip reads: \"{tooltip}\". "
                if research_value:
                    text_content += f"It requires {research_value} for research purposes. "
                if defense:
                    text_content += f"It provides {defense} defense."

                # Create a chunk for the item
                set_chunks.append({
                    "text": text_content.strip(),
                    "metadata": {
                        "page_title": page_title,
                        "section_title": "Set"
                    }
                })

    return set_chunks

def process_achievements_section(soup, page_title):
    # Find all achievement containers
    achievement_containers = soup.find_all("div", class_="achievement")
    achievement_chunks = []
    
    for achievement_container in achievement_containers:
        try:
            # Extract achievement title
            title_tag = achievement_container.find("b")
            achievement_title = title_tag.get_text(separator=" ", strip=True) if title_tag else "Unknown Achievement"
            
            # Extract achievement description (italicized text within the container)
            description_tag = achievement_container.find("i")
            achievement_description = description_tag.get_text(separator=" ", strip=True) if description_tag else "No description available"
            
            # Extract the criteria (look for the first div after the description and exclude specific known classes and tags)
            criteria_div = achievement_container.find("div")
            achievement_criteria = "Unknown criteria"
            if criteria_div:
                for child_div in criteria_div.find_all("div", recursive=False):
                    achievement_criteria = child_div.get_text(separator=" ", strip=True)
                    # print(achievement_criteria)
                    break
                    
            # Extract applicable game versions (like Desktop, Console, etc.)
            version_tag = achievement_container.find("span", class_="eico")
            applicable_versions = "All versions"
            if version_tag and version_tag.find("span"):
                applicable_versions = version_tag.find("span").get_text(separator=" ", strip=True).strip("()")
            
            # Extract achievement category (usually in the note-text small div with the category image)
            category_div = achievement_container.find("div", class_="note-text small")
            achievement_category = "Uncategorized"
            if category_div and category_div.get_text():
                category_text_match = re.search(r'Category:\s*(.*)', category_div.get_text(separator=" ", strip=True))
                achievement_category = category_text_match.group(1) if category_text_match else "Uncategorized"
            
            # Compile all information into a single descriptive text
            full_achievement_description = (
                f"The achievement '{achievement_title}' is described as: '{achievement_description}'. "
                f"To unlock this achievement, you must: {achievement_criteria}. "
                f"This achievement is categorized under '{achievement_category}' and is available in {applicable_versions}."
            )
            
            # Add the formatted achievement to the list of chunks
            achievement_chunks.append({
                "text": full_achievement_description.strip(),
                "metadata": {
                    "page_title": page_title,
                    "section_title": "Achievement"
                }
            })
            
        except Exception as e:
            # Log any exceptions or unhandled cases
            print(f"[INFO] Unhandled achievement in '{page_title}': {e}")
            continue
    
    return achievement_chunks

def process_achievementss_section(soup, page_title):
    achievement_containers = soup.find_all("div", class_="achievement")
    achievement_chunks = []

    for achievement_container in achievement_containers:
        # Extract achievement title
        title_tag = achievement_container.find("b")
        achievement_title = title_tag.get_text(separator=" ", strip=True) if title_tag else "Unknown Achievement"
        
        # Extract achievement description (italicized text within the container)
        description_tag = achievement_container.find("i")
        achievement_description = description_tag.get_text(separator=" ", strip=True) if description_tag else "No description available"
        
        # Extract the criteria (look for the first div after the description and exclude specific known classes and tags)
        criteria_div = achievement_container.find("div")
        achievement_criteria = "Unknown criteria"
        if criteria_div:
            for child_div in criteria_div.find_all("div", recursive=False):
                if not child_div.get("class") or 'note-text' not in child_div.get("class"):
                    achievement_criteria = child_div.get_text(separator=" ", strip=True)
                    break
        
        # Extract applicable game versions (like Desktop, Console, etc.)
        version_tag = achievement_container.find("span", class_="eico")
        applicable_versions = "All versions"
        if version_tag and version_tag.find("span"):
            applicable_versions = version_tag.find("span").get_text(separator=" ", strip=True).strip("()")
        
        # Extract achievement category (usually in the note-text small div with the category image)
        category_div = achievement_container.find("div", class_="note-text small")
        achievement_category = "Uncategorized"
        if category_div and category_div.get_text():
            category_text_match = re.search(r'Category:\s*(.*)', category_div.get_text(separator=" ", strip=True))
            achievement_category = category_text_match.group(1) if category_text_match else "Uncategorized"
        
        # Compile all information into a single descriptive text
        full_achievement_description = (
            f"The achievement '{achievement_title}' is described as: '{achievement_description}'. "
            f"To unlock this achievement, you must: {achievement_criteria}. "
            f"This achievement is categorized under '{achievement_category}' and is available in {applicable_versions}."
        )
        
        # Add the formatted achievement to the list of chunks
        achievement_chunks.append({
            "text": full_achievement_description.strip(),
            "metadata": {
                "page_title": "Achievements",  # Example page title
                "section_title": "Achievement"
            }
        })

    return achievement_chunks

def process_variants_section2(soup, page_title):
    npcs = []
    
    # Extract the section title (if available)
    section_title_tag = soup.find('span', class_='mw-headline')
    section_title = section_title_tag.text if section_title_tag else 'Unknown Section'
    
    # Extract the NPC rows from the table
    npc_rows = soup.select('table.terraria tbody tr')
    
    for row in npc_rows[1:]:  # Skip header row
        columns = row.find_all('td')
        if len(columns) < 7:
            continue
        
        # Extract NPC name and variant (if any)
        npc_name_tag = columns[2].find('span', title=True)
        npc_name = npc_name_tag['title'] if npc_name_tag else 'Unknown NPC'
        
        variant_note_tag = columns[2].find('span', class_='note')
        variant = variant_note_tag.text.strip('()') if variant_note_tag else ''
        if variant: 
            npc_name += f' ({variant})'
        
        health_raw = columns[3].text.strip()
        damage_raw = columns[4].text.strip()
        defense_raw = columns[5].text.strip()
        kb_resist_raw = columns[6].text.strip()
        coins_raw = columns[7].text.strip() if len(columns) > 7 else ''
        
        health_values = extract_values(health_raw)
        damage_values = extract_values(damage_raw)
        defense_values = extract_values(defense_raw)
        kb_resist_values = extract_values(kb_resist_raw)
        coin_drop = extract_coin_values(coins_raw)
        
        # Build NPC data for each mode
        modes = ["Classic", "Expert", "Master"]
        health_by_mode = zip(modes, health_values)
        damage_by_mode = zip(modes, damage_values)
        defense_by_mode = zip(modes, defense_values)
        kb_resist_by_mode = zip(modes, kb_resist_values)
        
        for mode, health in health_by_mode:
            damage = next(damage_by_mode, (mode, 0))[1]
            defense = next(defense_by_mode, (mode, 0))[1]
            kb_resist = next(kb_resist_by_mode, (mode, '0%'))[1]
            coins = coin_drop.get(mode, '')
            if not coins and mode == 'Master':
                coins = coin_drop.get('Expert', '')  # Default Master coin drop to Expert mode value if not specified
            coin_text = f" Upon death, it drops {coins}." if coins else ''
            
            npc_data = {
                "text": f"In {mode} mode, '{npc_name}' has {health} health, {defense} defense, and {kb_resist} knockback resistance. It does {damage} damage.{coin_text}",
                "metadata": {
                    "page_title": page_title,
                    "section_title": section_title
                }
            }
            npcs.append(npc_data)
    
    return npcs

    def extract_values(raw_text):
        values = []
        numbers = re.findall(r'\d+(?:\.\d+)?%', raw_text)  # Extract percentages
        if numbers:
            return numbers
        
        values = re.findall(r'\d+', raw_text)  # Extract numeric values
        if len(values) == 1:  # If only one value, apply it to all modes
            values = [values[0]] * 3
        elif len(values) == 2:  # If two values, assume Pre-Hardmode and Hardmode
            values.append(values[-1])
        elif len(values) > 3:  # Sometimes there may be more values than needed, limit to 3
            values = values[:3]
        
        return values

    def extract_coin_values(raw_text):
        """Extract coin values from the raw text and return a dictionary with mode-specific coin values."""
        coin_pattern = re.compile(r'(\d+)\s*SC')  # Match Silver Coins
        copper_pattern = re.compile(r'(\d+)\s*CC')  # Match Copper Coins
        
        modes = ["Classic", "Expert", "Master"]
        coin_values = {}
        
        sc_values = coin_pattern.findall(raw_text)
        cc_values = copper_pattern.findall(raw_text)
        
        if sc_values or cc_values:
            for i, mode in enumerate(modes):
                sc = sc_values[i] if i < len(sc_values) else ''
                cc = cc_values[i] if i < len(cc_values) else ''
                coin_string = []
                if sc:
                    coin_string.append(f"{sc} Silver Coin{'s' if int(sc) > 1 else ''}")
                if cc:
                    coin_string.append(f"{cc} Copper Coin{'s' if int(cc) > 1 else ''}")
                coin_values[mode] = ' and '.join(coin_string)
        
        return coin_values

def process_variants_section(soup, page_title):
    variant_chunks = []

    # Locate the "Variants" section header
    variants_header = soup.find("span", {"id": "Variants"})
    if not variants_header:
        return variant_chunks  # No variants section found

    # Locate the variants table
    variants_table = variants_header.find_next("table", class_="terraria")
    if not variants_table:
        return variant_chunks  # No table found in the variants section

    # Parse the table rows
    rows = variants_table.find_all("tr")[1:]  # Skip the header row
    for row in rows:
        cells = row.find_all("td")

        if not cells:
            continue  # Skip rows without cells

        # Determine the modes
        row_class = row.get("class", [])
        if "m-expert-master" in row_class:
            modes = ["Expert", "Master"]
        else:
            modes = ["Classic", "Expert", "Master"]

        # Extract NPC ID
        npc_id = cells[0].get_text(strip=True) if len(cells) > 0 else "Unknown ID"

        # Extract NPC Name
        name_cell = cells[2] if len(cells) > 2 else None
        npc_name = (
            name_cell.find("span", title=True).get("title") if name_cell and name_cell.find("span", title=True) else "Unknown Name"
        )

        # Extract stats for Classic Mode (`m-normal`)
        if "Classic" in modes: 
            health = row.find("span", class_="m-normal").get_text(" ", strip=True) if row.find("span", class_="m-normal") else "Unknown Health"
            damage = row.find("span", class_="m-normal").get_text(" ", strip=True) if row.find("span", class_="m-normal") else "Unknown Damage"
            defense = row.find("span", class_="m-normal").get_text(" ", strip=True) if row.find("span", class_="m-normal") else "Unknown Defense"
            kb_resist = row.find("span", class_="m-normal").get_text(" ", strip=True) if row.find("span", class_="m-normal") else "Unknown KB Resist"

            # Extract Coins for Classic Mode
            coins_cell = cells[7] if len(cells) > 7 else None
            classic_coins = "Unknown Coins"

            if coins_cell:
                # Find the 'm-normal' span first
                classic_span = coins_cell.find("span", class_="m-normal")
                if classic_span:
                    # Then find the nested 'coin' span inside 'm-normal'
                    coin_span = classic_span.find("span", class_="coin")
                    if coin_span and coin_span.has_attr("title"):
                        classic_coins = coin_span["title"]

            # Create a chunk for Classic mode
            chunk_text = (
                f"In Classic mode, '{npc_name}' has {health} health, {defense} defense, and {kb_resist} knockback resistance. It does {damage} damage."
            )
            if coins_cell:
                chunk_text += f" Upon death, it drops {classic_coins}."
            variant_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "page_title": page_title,
                    "section_title": "Variants"
                }
            })
            
        # now handle expert
        def extract_values_from_row(row):
            # Function to extract and process values for a given class
            def parse_stat(class_names):
                for class_name in class_names:
                    stat_span = row.find("span", class_=class_name)
                    if stat_span:
                        # Find all spans with the 's' class inside the parent span
                        value_spans = stat_span.find_all("span", class_="s")

                        # Extract title and value, ignoring separators
                        results = [
                            [span["title"], span.get_text(strip=True)]
                            for span in value_spans if span.has_attr("title")
                        ]
                        if results:
                            return results
                return None

            # Classes to look for in priority order
            class_names = ["m-expert", "m-expert-master"]

            # Extract values for each stat using parse_stat
            health = parse_stat(class_names)
            damage = parse_stat(class_names)
            defense = parse_stat(class_names)
            kb_resist = parse_stat(class_names)

            # Return a dictionary of stats
            return {
                "health": health,
                "damage": damage,
                "defense": defense,
                "kb_resist": kb_resist,
            }


        stats = extract_values_from_row(row) 

        # Extract Coins for Classic Mode
        coins_cell = cells[7] if len(cells) > 7 else None
        classic_coins = []

        if coins_cell:
            # Search for either 'm-expert' or 'm-expert-master' span
            classic_span = (
                coins_cell.find("span", class_="m-expert") or
                coins_cell.find("span", class_="m-expert-master")
            )
            if classic_span:
                # Find all spans with the 's' class inside the found span
                coin_modes = classic_span.find_all("span", class_="s")
                for mode in coin_modes:
                    if mode and mode.has_attr("title"):
                        # Extract mode title and coin value
                        mode_title = mode["title"]  # e.g., "Pre-Hardmode"
                        coin_span = mode.find("span", class_="coin")
                        if coin_span and coin_span.has_attr("title"):
                            coin_value = coin_span["title"]  # e.g., "1 Silver 50 Copper Coins"
                            classic_coins.append(f"{coin_value} in {mode_title}")


        # Create a chunk for Expert mode
        chunk_text = f"In Expert mode, '{npc_name}' "

        # Add health information if available
        if stats.get("health"):
            health_info = ", ".join([f"{health[1]} health in {health[0]}" for health in stats["health"] if health])
            chunk_text += f"has {health_info}. "

        # Add defense information if available
        if stats.get("defense"):
            defense_info = ", ".join([f"{defense[1]} defense in {defense[0]}" for defense in stats["defense"] if defense])
            chunk_text += f"It has {defense_info}. "

        # Add knockback resistance information if available
        if stats.get("kb_resist"):
            kb_resist_info = ", ".join([f"{kb_resist[1]} knockback resistance in {kb_resist[0]}" for kb_resist in stats["kb_resist"] if kb_resist])
            chunk_text += f"It has {kb_resist_info}. "

        # Add damage information if available
        if stats.get("damage"):
            damage_info = ", ".join([f"{damage[1]} damage in {damage[0]}" for damage in stats["damage"] if damage])
            chunk_text += f"It does {damage_info}."

        
        if classic_coins:
            coin_info = ", ".join(classic_coins)
            chunk_text += f" Upon death, it drops {coin_info}."
            
        variant_chunks.append({
            "text": chunk_text,
            "metadata": {
                "page_title": page_title,
                "section_title": "Variants"
            }
        }) 
        
        # now handle master
        def extract_values_from_row(row):
            # Function to extract and process values for a given class
            def parse_stat(class_names):
                for class_name in class_names:
                    stat_span = row.find("span", class_=class_name)
                    if stat_span:
                        # Find all spans with the 's' class inside the parent span
                        value_spans = stat_span.find_all("span", class_="s")

                        # Extract title and value, ignoring separators
                        results = [
                            [span["title"], span.get_text(strip=True)]
                            for span in value_spans if span.has_attr("title")
                        ]
                        if results:
                            return results
                return None

            # Classes to look for in priority order
            class_names = ["m-master", "m-expert-master"]

            # Extract values for each stat using parse_stat
            health = parse_stat(class_names)
            damage = parse_stat(class_names)
            defense = parse_stat(class_names)
            kb_resist = parse_stat(class_names)

            # Return a dictionary of stats
            return {
                "health": health,
                "damage": damage,
                "defense": defense,
                "kb_resist": kb_resist,
            }


        stats = extract_values_from_row(row) 

        # Extract Coins for Classic Mode
        coins_cell = cells[7] if len(cells) > 7 else None
        classic_coins = []

        if coins_cell:
            # Search for either 'm-expert' or 'm-expert-master' span
            classic_span = (
                coins_cell.find("span", class_="m-master") or
                coins_cell.find("span", class_="m-expert-master")
            )
            if classic_span:
                # Find all spans with the 's' class inside the found span
                coin_modes = classic_span.find_all("span", class_="s")
                for mode in coin_modes:
                    if mode and mode.has_attr("title"):
                        # Extract mode title and coin value
                        mode_title = mode["title"]  # e.g., "Pre-Hardmode"
                        coin_span = mode.find("span", class_="coin")
                        if coin_span and coin_span.has_attr("title"):
                            coin_value = coin_span["title"]  # e.g., "1 Silver 50 Copper Coins"
                            classic_coins.append(f"{coin_value} in {mode_title}")


        # Create a chunk for Expert mode
        chunk_text = f"In Master mode, '{npc_name}' "

        # Add health information if available
        if stats.get("health"):
            health_info = ", ".join([f"{health[1]} health in {health[0]}" for health in stats["health"] if health])
            chunk_text += f"has {health_info}. "

        # Add defense information if available
        if stats.get("defense"):
            defense_info = ", ".join([f"{defense[1]} defense in {defense[0]}" for defense in stats["defense"] if defense])
            chunk_text += f"It has {defense_info}. "

        # Add knockback resistance information if available
        if stats.get("kb_resist"):
            kb_resist_info = ", ".join([f"{kb_resist[1]} knockback resistance in {kb_resist[0]}" for kb_resist in stats["kb_resist"] if kb_resist])
            chunk_text += f"It has {kb_resist_info}. "

        # Add damage information if available
        if stats.get("damage"):
            damage_info = ", ".join([f"{damage[1]} damage in {damage[0]}" for damage in stats["damage"] if damage])
            chunk_text += f"It does {damage_info}."

        
        if classic_coins:
            coin_info = ", ".join(classic_coins)
            chunk_text += f" Upon death, it drops {coin_info}."
        
        variant_chunks.append({
            "text": chunk_text,
            "metadata": {
                "page_title": page_title,
                "section_title": "Variants"
            }
        }) 

    return variant_chunks

def process_tiers_section(soup, page_title):
    set_section = soup.find("span", {"id": "Tiers"})
    set_chunks = []

    if set_section:
        # Locate the parent <h2> tag to find associated content
        set_header = set_section.find_parent("h2")
        set_content = set_header.find_next_sibling("div")

        if set_content:
            # Find all infoboxes within the "Set" section
            infoboxes = set_content.find_all("div", class_="infobox item")
            for infobox in infoboxes:
                # Extract item title
                title = infobox.find("div", class_="title").get_text(strip=True) if infobox.find("div", class_="title") else "Unknown Item"

                # Extract statistics
                type_value = None
                rarity_value = None
                buy_value = None
                sell_value = None
                research_value = None
                tooltip = None
                defense = None
                damage = None
                knockback = None
                mana = None
                use_time = None
                velocity = None
                unprocessed_fields = []  # Track unhandled fields

                stat_table = infobox.find("table", class_="stat")
                if stat_table:
                    for row in stat_table.find_all("tr"):
                        key = row.find("th").get_text(strip=True) if row.find("th") else "Unknown Key"
                        value_tag = row.find("td")
                        value = value_tag.get_text(separator=" ", strip=True) if value_tag else "Unknown Value"
                        
                        # Handle specific keys
                        if key.lower() == "type":
                            print(value)
                            type_value = value.lower()
                        elif key.lower() == "rarity":
                            rarity_sortkey = value_tag.find("s", class_="sortkey")
                            if rarity_sortkey:
                               rarity_value = re.sub(r'[^0-9]', '', rarity_sortkey.get_text())
                        elif key.lower() == "buy":
                            # Handle Defender Medals and other formats
                            if "Defender Medals" in value:
                                buy_value = value_tag.get("title", value)
                            elif value_tag.find("span", class_="coins"):
                                buy_value = value_tag.find("span", class_="coins").get("title", value)
                            else:
                                buy_value = value
                        elif key.lower() == "sell":
                            if value.lower() == "no value":
                                sell_value = "No value"
                            else:
                                coin_span = value_tag.find("span", class_="coin")
                                sell_value = coin_span.get("title", "") if coin_span else value
                        elif key.lower() == "tooltip":
                            tooltip = value.strip("'")
                        elif key.lower() == "research":
                            research_value = value
                        elif key.lower() == "defense":
                            defense = value
                        elif key.lower() == "damage":
                            damage = value
                        elif key.lower() == "knockback":
                            knockback = value
                        elif key.lower() == "mana":
                            mana = value
                        elif key.lower() == "use time":
                            use_time = value
                        elif key.lower() == "velocity":
                            velocity = value
                        else:
                            # Log unprocessed field
                            unprocessed_fields.append(f"Key: '{key}', Value: '{value}'")

                # Print unprocessed fields
                if unprocessed_fields:
                    print(f"[INFO] Unhandled fields in '{title}', set:")
                    for field in unprocessed_fields:
                        print(f"  - {field}")

                # Construct text content for the item
                text_content = (
                    f"The item '{title}' is part of the set. "
                    f"It is of type {type_value}. "
                    f"It has a rarity level of {rarity_value}. "
                )
                if buy_value:
                    text_content += f"It can be bought for {buy_value}. "
                if sell_value:
                    text_content += f"It can be sold for {sell_value}. "
                if tooltip:
                    text_content += f"The tooltip reads: \"{tooltip}\". "
                if research_value:
                    text_content += f"It requires {research_value} for research purposes. "
                if defense:
                    text_content += f"It provides {defense} defense. "
                if damage:
                    text_content += f"It deals {damage}. "
                if knockback:
                    text_content += f"It has a knockback rating of {knockback}. "
                if mana:
                    text_content += f"It consumes {mana} mana per use. "
                if use_time:
                    text_content += f"It has a use time of {use_time}. "
                if velocity:
                    text_content += f"It has a velocity of {velocity}."

                # Create a chunk for the item
                set_chunks.append({
                    "text": text_content.strip(),
                    "metadata": {
                        "page_title": page_title,
                        "section_title": "Tiers"
                    }
                })

    return set_chunks

def process_list_sections(soup, page_title):
    list_chunks = []

    # Find all <h2> tags to locate section headers
    section_headers = soup.find_all("h2")
    for header in section_headers:
        # Extract the section title
        section_title_tag = header.find("span", class_="mw-headline")
        section_title = section_title_tag.get_text(strip=True) if section_title_tag else "Unknown Section"

        # Only process explicitly supported sections
        if section_title in ["Trivia", "Tips", "Notes", "Note"]:
            # Check for <ul> or <ol> following the header
            current_element = header.find_next_sibling()
            while current_element and current_element.name != "h2":
                if current_element.name in ["ul", "ol"]:
                    # Extract each list item and create its own chunk
                    for li in current_element.find_all("li", recursive=False):  # Only consider direct children
                        parent_item_text = li.get_text(separator=" ", strip=True)

                        # Check for nested lists within the current list item
                        nested_list = li.find(["ul", "ol"])
                        if nested_list:
                            nested_items = nested_list.find_all("li")
                            nested_texts = [nested_item.get_text(separator=" ", strip=True) for nested_item in nested_items]
                            # Combine parent text with nested text
                            combined_text = f"{parent_item_text} {' '.join(nested_texts)}"
                            list_chunks.append({
                                "text": combined_text,
                                "metadata": {
                                    "page_title": page_title,
                                    "section_title": section_title
                                }
                            })
                        else:
                            # If no nested list, treat the parent item as its own chunk
                            if parent_item_text:
                                list_chunks.append({
                                    "text": parent_item_text,
                                    "metadata": {
                                        "page_title": page_title,
                                        "section_title": section_title
                                    }
                                })
                    break  # Stop after processing the list
                current_element = current_element.find_next_sibling()

    return list_chunks


# main function that calls all the other splitters
def process_html_file(file_path, file_name):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # use file name as page title (strip the .html extension)
        page_title = os.path.splitext(file_name)[0]
        
        # keep track of processed sections
        processed_sections = []
        ignored_sections = ["References", "See also", "History", "Gallery", "Quotes", "Footnotes"]  
        
        # general information
        # json_data.extend(process_general_info(soup, page_title))
        processed_sections.append("General Information")
        
        # infoboxes
        # json_data.extend(process_infoboxes(soup, page_title))
        processed_sections.append("Infobox")
        
        # drop infobox
        # json_data.extend(process_drop_infoboxes(soup, page_title))
        processed_sections.append("Drop Infobox")
        
        # crafting
        # json_data.extend(process_crafting_section(soup, page_title))
        processed_sections.append("Crafting")
        
        # set
        # json_data.extend(process_set_section(soup, page_title))
        processed_sections.append("Set")
        
        # achievements
        # json_data.extend(process_achievements_section(soup, page_title))
        processed_sections.append("Achievement")
        # json_data.extend(process_achievementss_section(soup, page_title))
        processed_sections.append("Achievements")
        
        # variants
        # json_data.extend(process_variants_section(soup, page_title))  # needed two because the variations seem to be not happy with me
        # json_data.extend(process_variants_section2(soup, page_title))
        processed_sections.append("Variants")
        
        # tiers
        # json_data.extend(process_tiers_section(soup, page_title))
        processed_sections.append("Tiers")
        
        # general stuff
        json_data.extend(process_list_sections(soup, page_title))
        processed_sections.append("Trivia")
        processed_sections.append("Tips")
        processed_sections.append("Notes")
        processed_sections.append("Note")
        
        log_unhandled_sections(soup, processed_sections, ignored_sections, page_title)
        
        
        



# main function to process all htmls the input folder
def process_input_folder(input_folder, output_file):
    for root, _, files in os.walk(input_folder):
        for file_name in files:
            if file_name.endswith(".html"):
                file_path = os.path.join(root, file_name)
                process_html_file(file_path, file_name)
    
        
    sorted_dict = dict(sorted(all_unlogged.items(), key=lambda item: item[1], reverse=True))
    print(sorted_dict)

    # write the output JSON
    with open(output_file, "w", encoding="utf-8") as output:
        json.dump(json_data, output, indent=4, ensure_ascii=False)

# Entry point
if __name__ == "__main__":
    input_folder = "terraria_wiki_pages"
    output_file = "preprocessing/terraria_preprocessed_chunks_misc.json"
    process_input_folder(input_folder, output_file)


