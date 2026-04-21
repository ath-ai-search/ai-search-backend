"""
=====================================================================================
📄 PAGINATION HTML BUILDER
=====================================================================================
This file builds the pagination buttons you see at the bottom of search results.

EXAMPLE OUTPUT:
  [1] 2 3 4 5 ... 20      (when on page 1)
  1 ... 4 [5] 6 7 ... 20  (when on page 5)
  1 ... 16 17 18 19 [20]  (when on last page)

HOW IT WORKS:
- Shows 5 page buttons at a time (like: 3 4 [5] 6 7)
- Adds "..." when pages are hidden
- Highlights the current page with 'active' CSS class
- Returns raw HTML string that frontend injects into the page
=====================================================================================
"""

from app.core.constants import PAGINATION_VISIBLE_PAGES


def build_pagination_html(total_pages: int, current_page: int) -> str:
    """
    Builds HTML pagination buttons for search results.
    
    ARGS:
        total_pages: Total number of pages available (like 20)
        current_page: Which page the user is currently on (like 5)
    
    RETURNS:
        str: HTML string with pagination buttons
             Returns empty string "" if only 1 page (no pagination needed)
    
    EXAMPLE:
        build_pagination_html(total_pages=20, current_page=5)
        →  "<button>1</button>...<button class='active'>5</button>..."
    """
    
    # =====================================================================
    # EDGE CASE: Only 1 page? No pagination needed
    # =====================================================================
    if total_pages <= 1:
        return ""
    
    # =====================================================================
    # CALCULATE THE VISIBLE PAGE RANGE
    # =====================================================================
    # We show 5 pages at a time, centered around current page
    # Example: current=5 → show [3, 4, 5, 6, 7]
    #          current=1 → show [1, 2, 3, 4, 5]
    #          current=20 (last) → show [16, 17, 18, 19, 20]
    
    # Start page = current - 2 (but never less than 1)
    start = max(1, current_page - 2)
    
    # End page = start + 4 (so total 5 pages shown), but never more than total
    end = min(total_pages, start + 4)
    
    # EDGE CASE: if we're near the end, shift start back
    # Example: total=20, current=19 → start would be 17, end would be 20 (only 4 pages)
    # So we shift start back to 16 to show 5 pages: [16, 17, 18, 19, 20]
    if end - start < 4:
        start = max(1, end - 4)
    
    # =====================================================================
    # BUILD THE HTML STRING
    # =====================================================================
    html = ""
    
    # ---------------------------------------------------------------------
    # LEFT SIDE: Show "1 ..." if start is not at page 1
    # ---------------------------------------------------------------------
    # Example: if showing [5, 6, 7, 8, 9], add "1 ..." before it
    if start > 1:
        html += '<button class="page-btn" data-page="1">1</button>'
        html += '<span style="align-self:center;">...</span>'
    
    # ---------------------------------------------------------------------
    # MIDDLE: Show the actual page number buttons
    # ---------------------------------------------------------------------
    for i in range(start, end + 1):
        # If this is the current page, add 'active' CSS class for highlighting
        active_class = "active" if i == current_page else ""
        html += f'<button class="page-btn {active_class}" data-page="{i}">{i}</button>'
    
    # ---------------------------------------------------------------------
    # RIGHT SIDE: Show "... LAST" if end is not at total_pages
    # ---------------------------------------------------------------------
    # Example: if showing [5, 6, 7, 8, 9] and total=20, add "... 20" at end
    if end < total_pages:
        html += '<span style="align-self:center;">...</span>'
        html += f'<button class="page-btn" data-page="{total_pages}">{total_pages}</button>'
    
    return html