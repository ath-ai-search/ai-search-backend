/* =====================================================================
 * ⚡ MEGA MENU SCRIPTS (Search History Dropdown)
 * =====================================================================
 * This JavaScript powers:
 *   1. Search history dropdown (shows when user focuses empty search bar)
 *   2. Saving searches to server when user clicks search
 *   3. Deleting individual history items (X button)
 *   4. Hiding dropdown when user clicks elsewhere
 * 
 * NOTE: Uses XMLHttpRequest for broader browser compatibility
 * Purple color (#802A8F) matches Amazon-style history UI
 * ===================================================================== */

(function() {
       'use strict';
   
       // =================================================================
       // 💾 SAVE SEARCH HISTORY (server-side Redis)
       // =================================================================
       window.saveSearchHistory = function(query) {
           if (!query || query.trim().length < 2) return;
           
           try {
               fetch('/search/history', {
                   method: 'POST',
                   headers: { 'Content-Type': 'application/json' },
                   body: JSON.stringify({ query: query.trim() })
               }).catch(err => console.warn('History save failed:', err));
           } catch (e) {
               console.warn('History save error:', e);
           }
       };
   
       // =================================================================
       // 🗑️ REMOVE SINGLE HISTORY ITEM
       // =================================================================
       window.removeHistoryItem = function(query, event) {
           event.stopPropagation();  // Prevent triggering row click
           
           try {
               fetch('/search/history', {
                   method: 'DELETE',
                   headers: { 'Content-Type': 'application/json' },
                   body: JSON.stringify({ query: query })
               }).then(() => {
                   // Remove the row visually
                   event.target.closest('.bclouds-history-row')?.remove();
                   
                   // If last item was removed, close dropdown
                   const dropdown = document.getElementById('venue-history-dropdown');
                   if (dropdown && dropdown.children.length === 0) {
                       dropdown.remove();
                   }
               });
           } catch (e) {
               console.warn('History delete error:', e);
           }
       };
   
       // =================================================================
       // 📋 SHOW HISTORY DROPDOWN
       // =================================================================
       window.showHistoryDropdown = async function() {
           // Remove any existing dropdown first
           document.getElementById('venue-history-dropdown')?.remove();
           
           // Fetch history from server
           let history = [];
           try {
               const response = await fetch('/search/history');
               const data = await response.json();
               history = data.history || [];
           } catch (e) {
               console.warn('Failed to fetch history:', e);
               return;
           }
           
           // No history? Don't show empty dropdown
           if (!history.length) return;
           
           const input = document.getElementById('search_query');
           if (!input) return;
           
           // Position dropdown below the search bar
           const rect = input.getBoundingClientRect();
           const dropdown = document.createElement('div');
           dropdown.id = 'venue-history-dropdown';
           dropdown.style.cssText = `
               position: fixed;
               top: ${rect.bottom}px;
               left: ${rect.left}px;
               width: ${rect.width}px;
               background: #ffffff;
               border: 1px solid #ccc;
               border-top: none;
               box-shadow: 0 4px 6px rgba(0,0,0,0.1);
               z-index: 99999;
               font-family: inherit;
               padding: 4px 0;
           `;
   
           // Build one row per history item
           history.forEach(query => {
               const row = document.createElement('div');
               row.className = 'bclouds-history-row';
               row.style.cssText = `
                   display: flex;
                   align-items: center;
                   justify-content: space-between;
                   padding: 8px 12px;
                   cursor: pointer;
                   background: #ffffff;
               `;
               
               // Amazon-style gray hover state
               row.onmouseover = () => row.style.background = '#f3f3f3';
               row.onmouseout = () => row.style.background = '#ffffff';
               
               // Click → fill search bar + trigger search
               row.onclick = () => {
                   input.value = query;
                   document.getElementById('venue-history-dropdown')?.remove();
                   window.saveSearchHistory(query);
                   const btn = document.getElementById('searchBtn');
                   if (btn) btn.click();
               };
   
               // Text (purple color like Amazon)
               const left = document.createElement('div');
               left.style.cssText = 'color: #802A8F; font-weight: 600; font-size: 14px;';
               left.innerText = query;
   
               // X close button
               const closeBtn = document.createElement('span');
               closeBtn.innerHTML = '&#10005;';  // ✕ character
               closeBtn.style.cssText = 'font-size: 14px; color: #111; cursor: pointer; padding: 0 5px; font-weight: bold;';
               closeBtn.onclick = (e) => window.removeHistoryItem(query, e);
   
               row.appendChild(left);
               row.appendChild(closeBtn);
               dropdown.appendChild(row);
           });
   
           document.body.appendChild(dropdown);
       };
   
       // =================================================================
       // 🎯 ATTACH EVENT LISTENERS TO SEARCH BAR
       // =================================================================
       const input = document.getElementById('search_query');
       const searchBtn = document.getElementById('searchBtn');
       
       if (input) {
           // Focus on empty search bar → show history
           input.addEventListener('focus', () => {
               if (input.value.trim() === '') window.showHistoryDropdown();
           });
           
           // Click on empty search bar → show history
           input.addEventListener('click', () => {
               if (input.value.trim() === '') window.showHistoryDropdown();
           });
   
           // Typing in search bar
           input.addEventListener('input', () => {
               document.getElementById('venue-history-dropdown')?.remove();
               const megaMenu = document.querySelector('.bclouds-mega-menu');
               
               if (input.value.trim() === '') {
                   // Empty again → show history
                   window.showHistoryDropdown();
               } else {
                   // Has text → restore AI suggestions
                   if (megaMenu) megaMenu.style.display = 'flex';
               }
           });
   
           // Click search button → save history
           if (searchBtn) {
               searchBtn.addEventListener('click', () => window.saveSearchHistory(input.value));
           }
   
           // Press Enter → save history
           input.addEventListener('keydown', (e) => {
               if (e.key === 'Enter') window.saveSearchHistory(input.value);
           });
   
           // Click outside → close dropdown
           document.addEventListener('click', (e) => {
               if (!e.target.closest('#venue-history-dropdown') && e.target !== input) {
                   document.getElementById('venue-history-dropdown')?.remove();
               }
           });
       }
   })();