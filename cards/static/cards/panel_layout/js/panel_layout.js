/**
 * PanelLayout - Vanilla JS resize and collapse handler for CSS Grid panel layouts.
 * Persists panel sizes and collapse state to localStorage.
 */
var PanelLayout = (function() {
    'use strict';

    var _layoutId;
    var _persist = true;

    function init(layoutId, options) {
        var layout = document.getElementById(layoutId);
        if (!layout) return;
        _layoutId = layoutId;
        _persist = (options && options.persist !== undefined) ? options.persist : true;
        if (layout.getAttribute('data-full-height') === 'true') {
            _setFullHeight(layout);
            window.addEventListener('resize', function() { _setFullHeight(layout); });
            // Again once the page has finished loading, and once more after that: the
            // breadcrumb and footer below the layout are part of the measurement, and their
            // heights are still settling while fonts load and a wrapped toolbar reflows.
            window.addEventListener('load', function() {
                _setFullHeight(layout);
                window.setTimeout(function() { _setFullHeight(layout); }, 150);
            });
        }
        if (_persist) {
            _restoreState(layout);
        }
        _initSplitters(layout);
        _initCollapseButtons(layout);
        _initTabMenus(layout);
        _initTabScroll(layout);
    }

    function _setFullHeight(layout) {
        layout.style.height = '';
        var rect = layout.getBoundingClientRect();
        var minHeight = parseInt(layout.getAttribute('data-min-height'), 10) || 400;
        // Everything between the layout's bottom edge and the page's: the margins and padding
        // of its own ancestors, and whatever comes after it -- a breadcrumb, a footer. Both
        // measurements are taken and the larger wins, so a page with nothing below the layout
        // is sized exactly as it was, and a page with a footer stops giving the layout the
        // room the footer needs and pushing it past the bottom of the window.
        var bottom = Math.max(_getBottomSpacing(layout), _getSpaceBelow(rect));
        var height = window.innerHeight - rect.top - bottom;
        if (height < minHeight) height = minHeight;
        layout.style.height = height + 'px';
    }

    // The height of the page below the layout. Read from the body's own box rather than from
    // documentElement.scrollHeight, which reports the viewport height when the page is shorter
    // than the window -- that would count the dead space this is here to remove as though it
    // were content. Re-measuring cannot drift: moving the layout's bottom edge moves the
    // body's with it, leaving the distance between them unchanged.
    function _getSpaceBelow(rect) {
        if (!document.body) return 0;
        var below = document.body.getBoundingClientRect().bottom - rect.bottom;
        return below > 0 ? below : 0;
    }

    function _getBottomSpacing(el) {
        var spacing = 0;
        var node = el;
        while (node && node !== document.body) {
            var style = window.getComputedStyle(node);
            spacing += parseFloat(style.marginBottom) || 0;
            spacing += parseFloat(style.paddingBottom) || 0;
            node = node.parentElement;
        }
        return spacing;
    }

    // ---- localStorage helpers ----

    function _storageKey() {
        return 'panelLayout_' + window.location.pathname + '_' + _layoutId;
    }

    function _loadState() {
        try {
            var raw = localStorage.getItem(_storageKey());
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function _saveState(layout) {
        if (!_persist) return;
        var state = { splits: [], collapsed: [] };

        // Walk every split container and record its current grid template
        var splits = layout.querySelectorAll('.panel-split');
        for (var i = 0; i < splits.length; i++) {
            var split = splits[i];
            var dir = split.getAttribute('data-direction');
            var template = dir === 'horizontal'
                ? split.style.gridTemplateColumns
                : split.style.gridTemplateRows;
            if (template) {
                state.splits.push({ index: i, direction: dir, template: template });
            }
        }

        // Record which regions are collapsed
        var regions = layout.querySelectorAll('.panel-region');
        for (var j = 0; j < regions.length; j++) {
            var region = regions[j];
            if (region.classList.contains('panel-region--collapsed')) {
                state.collapsed.push({
                    id: region.id,
                    prevSize: region.getAttribute('data-prev-size') || '250'
                });
            }
        }

        try {
            localStorage.setItem(_storageKey(), JSON.stringify(state));
        } catch (e) {
            // storage full or unavailable — silently ignore
        }
    }

    function _restoreState(layout) {
        var state = _loadState();
        if (!state.splits && !state.collapsed) return;

        // Restore collapse state first (before grid templates, so collapsed
        // regions get their class before we set sizes)
        if (state.collapsed) {
            for (var j = 0; j < state.collapsed.length; j++) {
                var info = state.collapsed[j];
                var region = document.getElementById(info.id);
                if (!region) continue;
                region.classList.add('panel-region--collapsed');
                region.setAttribute('data-prev-size', info.prevSize);
                var icon = region.querySelector('.panel-collapse-btn i');
                if (icon) {
                    var collapseDir = region.getAttribute('data-collapse-direction');
                    var dir = collapseDir || region.parentElement.getAttribute('data-direction');
                    icon.className = dir === 'horizontal'
                        ? 'fas fa-chevron-right'
                        : 'fas fa-chevron-down';
                }
            }
        }

        // Restore grid templates
        if (state.splits) {
            var splits = layout.querySelectorAll('.panel-split');
            for (var i = 0; i < state.splits.length; i++) {
                var saved = state.splits[i];
                var split = splits[saved.index];
                if (!split) continue;
                if (saved.direction === 'horizontal') {
                    split.style.gridTemplateColumns = saved.template;
                } else {
                    split.style.gridTemplateRows = saved.template;
                }
            }
        }
    }

    // ---- splitter drag logic ----

    function _initSplitters(layout) {
        var splitters = layout.querySelectorAll('.panel-splitter');
        for (var i = 0; i < splitters.length; i++) {
            _attachSplitter(layout, splitters[i]);
        }
    }

    function _attachSplitter(layout, splitter) {
        var direction = splitter.getAttribute('data-direction');
        var isHorizontal = direction === 'horizontal';

        splitter.addEventListener('mousedown', function(e) {
            e.preventDefault();
            var splitContainer = splitter.parentElement;
            var children = _getSplitChildren(splitContainer);
            var splitterIndex = _getSplitterPosition(splitContainer, splitter);

            // Get the two panels on either side of this splitter
            var prevPanel = children[splitterIndex - 1];
            var nextPanel = children[splitterIndex];
            if (!prevPanel || !nextPanel) return;

            var startPos = isHorizontal ? e.clientX : e.clientY;
            var prevSize = isHorizontal ? prevPanel.offsetWidth : prevPanel.offsetHeight;
            var nextSize = isHorizontal ? nextPanel.offsetWidth : nextPanel.offsetHeight;

            var prevMin = _parseMinSize(prevPanel, isHorizontal);
            var nextMin = _parseMinSize(nextPanel, isHorizontal);

            splitter.classList.add('panel-splitter--active');
            layout.classList.add(isHorizontal ? 'panel-layout--resizing' : 'panel-layout--resizing-v');

            function _expandIfCollapsed(panel, iconHorizontal) {
                if (panel && panel.classList.contains('panel-region--collapsed')) {
                    panel.classList.remove('panel-region--collapsed');
                    var icon = panel.querySelector('.panel-collapse-btn i');
                    if (icon) {
                        var collapseDir = panel.getAttribute('data-collapse-direction');
                        var iconDir = collapseDir ? (collapseDir === 'horizontal') : iconHorizontal;
                        icon.className = iconDir ? 'fas fa-chevron-left' : 'fas fa-chevron-up';
                    }
                }
            }

            function onMouseMove(e) {
                var delta = (isHorizontal ? e.clientX : e.clientY) - startPos;
                var newPrev = Math.max(prevMin, prevSize + delta);
                var newNext = Math.max(nextMin, nextSize - delta);

                // Clamp so we don't exceed total available space
                var total = prevSize + nextSize;
                if (newPrev + newNext > total) {
                    if (delta > 0) {
                        newNext = total - newPrev;
                    } else {
                        newPrev = total - newNext;
                    }
                }

                // Auto-expand collapsed panels when dragged open
                if (delta < 0 && nextPanel.classList.contains('panel-region--collapsed')) {
                    _expandIfCollapsed(nextPanel, isHorizontal);
                } else if (delta > 0 && prevPanel.classList.contains('panel-region--collapsed')) {
                    _expandIfCollapsed(prevPanel, isHorizontal);
                }

                _setSplitSizes(splitContainer, splitterIndex, newPrev, newNext, isHorizontal);
            }

            function onMouseUp() {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                splitter.classList.remove('panel-splitter--active');
                layout.classList.remove('panel-layout--resizing');
                layout.classList.remove('panel-layout--resizing-v');

                _saveState(layout);
                window.dispatchEvent(new Event('resize'));
                _adjustDatatables(layout);
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    function _getSplitChildren(splitContainer) {
        var children = [];
        for (var i = 0; i < splitContainer.children.length; i++) {
            var child = splitContainer.children[i];
            if (!child.classList.contains('panel-splitter')) {
                children.push(child);
            }
        }
        return children;
    }

    function _getSplitterPosition(splitContainer, splitter) {
        var count = 0;
        for (var i = 0; i < splitContainer.children.length; i++) {
            var child = splitContainer.children[i];
            if (child === splitter) return count;
            if (!child.classList.contains('panel-splitter')) {
                count++;
            }
        }
        return count;
    }

    function _setSplitSizes(splitContainer, splitterIndex, prevSize, nextSize, isHorizontal) {
        var children = _getSplitChildren(splitContainer);
        var sizes = [];

        // Find the last non-splitter, non-collapsed region index
        var lastRegionIndex = -1;
        for (var k = children.length - 1; k >= 0; k--) {
            if (!children[k].classList.contains('panel-splitter') &&
                !children[k].classList.contains('panel-region--collapsed')) {
                lastRegionIndex = k;
                break;
            }
        }

        for (var i = 0; i < children.length; i++) {
            if (i === splitterIndex - 1) {
                sizes.push(prevSize + 'px');
            } else if (i === splitterIndex) {
                sizes.push(nextSize + 'px');
            } else {
                var current = isHorizontal ? children[i].offsetWidth : children[i].offsetHeight;
                sizes.push(current + 'px');
            }
        }

        // Make last non-collapsed region use 1fr so the grid always fills available space
        if (lastRegionIndex >= 0 && lastRegionIndex !== splitterIndex - 1 && lastRegionIndex !== splitterIndex) {
            sizes[lastRegionIndex] = '1fr';
        }

        var tracks = [];
        for (var j = 0; j < sizes.length; j++) {
            if (j > 0) {
                tracks.push('auto');
            }
            tracks.push(sizes[j]);
        }

        if (isHorizontal) {
            splitContainer.style.gridTemplateColumns = tracks.join(' ');
        } else {
            splitContainer.style.gridTemplateRows = tracks.join(' ');
        }
    }

    function _parseMinSize(panel, isHorizontal) {
        var attr = panel.getAttribute('data-min-size');
        if (attr) {
            var val = parseInt(attr, 10);
            if (!isNaN(val)) return val;
        }
        return 50;
    }

    // ---- datatable adjust ----

    function _adjustDatatables(layout) {
        // DataTables itself may still require jQuery, but we only touch its API here.
        if (typeof django_datatables === 'undefined' || !django_datatables.DataTables) {
            if (typeof window.jQuery === 'undefined' || !window.jQuery.fn || !window.jQuery.fn.dataTable) return;
            var $tables = window.jQuery(layout).find('table.dataTable');
            $tables.each(function() {
                window.jQuery(this).DataTable().columns.adjust();
            });
            return;
        }
        var tables = layout.querySelectorAll('table.dataTable');
        for (var i = 0; i < tables.length; i++) {
            var tableId = tables[i].id;
            var dt = tableId && django_datatables.DataTables[tableId];
            if (dt && dt.table && dt.table.api) {
                dt.table.api().columns.adjust();
            } else if (typeof window.jQuery !== 'undefined' && window.jQuery.fn && window.jQuery.fn.dataTable) {
                window.jQuery(tables[i]).DataTable().columns.adjust();
            }
        }
    }

    // ---- collapse / expand ----

    function _initCollapseButtons(layout) {
        var buttons = layout.querySelectorAll('.panel-collapse-btn');
        for (var i = 0; i < buttons.length; i++) {
            _attachCollapseButton(layout, buttons[i]);
        }
    }

    function _attachCollapseButton(layout, button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var targetId = button.getAttribute('data-target');
            var region = document.getElementById(targetId);
            if (!region) return;

            var splitContainer = region.parentElement;
            var isHorizontal = splitContainer.getAttribute('data-direction') === 'horizontal';
            var collapseDir = region.getAttribute('data-collapse-direction');
            var iconHorizontal = collapseDir ? (collapseDir === 'horizontal') : isHorizontal;
            var isCollapsed = region.classList.contains('panel-region--collapsed');

            if (isCollapsed) {
                _expandRegion(region, splitContainer, isHorizontal, iconHorizontal);
            } else {
                _collapseRegion(region, splitContainer, isHorizontal, iconHorizontal);
            }

            _saveState(layout);
            window.dispatchEvent(new Event('resize'));
            _adjustDatatables(layout);
        });
    }

    function _collapseRegion(region, splitContainer, isHorizontal, iconHorizontal) {
        var currentSize = isHorizontal ? region.offsetWidth : region.offsetHeight;
        region.setAttribute('data-prev-size', currentSize);
        region.classList.add('panel-region--collapsed');

        var icon = region.querySelector('.panel-collapse-btn i');
        if (icon) {
            icon.className = iconHorizontal ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
        }

        _rebuildGridAfterCollapse(splitContainer, isHorizontal);
    }

    function _expandRegion(region, splitContainer, isHorizontal, iconHorizontal) {
        var prevSize = region.getAttribute('data-prev-size') || '250';
        region.classList.remove('panel-region--collapsed');

        var icon = region.querySelector('.panel-collapse-btn i');
        if (icon) {
            icon.className = iconHorizontal ? 'fas fa-chevron-left' : 'fas fa-chevron-up';
        }

        _rebuildGridAfterExpand(splitContainer, region, parseInt(prevSize, 10), isHorizontal);
    }

    function _rebuildGridAfterCollapse(splitContainer, isHorizontal) {
        var children = _getSplitChildren(splitContainer);
        var sizes = [];

        for (var i = 0; i < children.length; i++) {
            if (children[i].classList.contains('panel-region--collapsed')) {
                sizes.push('36px');
            } else {
                sizes.push('1fr');
            }
        }

        var tracks = [];
        for (var j = 0; j < sizes.length; j++) {
            if (j > 0) tracks.push('auto');
            tracks.push(sizes[j]);
        }

        if (isHorizontal) {
            splitContainer.style.gridTemplateColumns = tracks.join(' ');
        } else {
            splitContainer.style.gridTemplateRows = tracks.join(' ');
        }
    }

    function _rebuildGridAfterExpand(splitContainer, region, restoreSize, isHorizontal) {
        var children = _getSplitChildren(splitContainer);
        var sizes = [];

        for (var i = 0; i < children.length; i++) {
            if (children[i].classList.contains('panel-region--collapsed')) {
                sizes.push('36px');
            } else if (children[i] === region) {
                sizes.push(restoreSize + 'px');
            } else {
                sizes.push('1fr');
            }
        }

        var tracks = [];
        for (var j = 0; j < sizes.length; j++) {
            if (j > 0) tracks.push('auto');
            tracks.push(sizes[j]);
        }

        if (isHorizontal) {
            splitContainer.style.gridTemplateColumns = tracks.join(' ');
        } else {
            splitContainer.style.gridTemplateRows = tracks.join(' ');
        }
    }

    // ---- tab menu switching ----

    function _initTabMenus(layout) {
        var tabLinks = layout.querySelectorAll('.panel-region__tabs a[data-toggle="tab"], .panel-region__tabs a[data-bs-toggle="tab"]');
        for (var i = 0; i < tabLinks.length; i++) {
            tabLinks[i].addEventListener('click', function() {
                var tabbar = this.closest('.panel-region__tabbar');
                if (!tabbar) return;
                // Hide all tab menus in this tabbar
                var menus = tabbar.querySelectorAll('.panel-region__tabmenu');
                for (var j = 0; j < menus.length; j++) {
                    menus[j].classList.remove('panel-region__tabmenu--active');
                }
                // Show the menu for the clicked tab
                var menuId = this.getAttribute('data-tab-menu');
                if (menuId) {
                    var menu = document.getElementById(menuId);
                    if (menu) {
                        menu.classList.add('panel-region__tabmenu--active');
                    }
                }
            });
        }
    }

    // ---- tab scroll buttons ----

    function _initTabScroll(layout) {
        var tabbars = layout.querySelectorAll('.panel-region__tabbar');
        for (var i = 0; i < tabbars.length; i++) {
            _initTabbarScroll(tabbars[i]);
        }
    }

    function _initTabbarScroll(tabbar) {
        var wrapper = tabbar.querySelector('.panel-region__tabs-wrapper');
        var tabs = tabbar.querySelector('.panel-region__tabs');
        var btnLeft = tabbar.querySelector('.panel-tabs-scroll-btn--left');
        var btnRight = tabbar.querySelector('.panel-tabs-scroll-btn--right');
        if (!wrapper || !tabs || !btnLeft || !btnRight) return;

        function updateButtons() {
            var overflowing = tabs.scrollWidth > tabs.clientWidth + 1;
            var atStart = tabs.scrollLeft <= 0;
            var atEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 1;
            btnLeft.classList.toggle('panel-tabs-scroll-btn--visible', overflowing && !atStart);
            btnRight.classList.toggle('panel-tabs-scroll-btn--visible', overflowing && !atEnd);
        }

        btnLeft.addEventListener('click', function() {
            tabs.scrollBy({ left: -120, behavior: 'smooth' });
        });
        btnRight.addEventListener('click', function() {
            tabs.scrollBy({ left: 120, behavior: 'smooth' });
        });
        tabs.addEventListener('scroll', updateButtons);

        if (window.ResizeObserver) {
            new ResizeObserver(updateButtons).observe(wrapper);
        }

        // Scroll active tab into view on click
        var tabLinks = tabs.querySelectorAll('a[data-toggle="tab"], a[data-bs-toggle="tab"]');
        for (var i = 0; i < tabLinks.length; i++) {
            tabLinks[i].addEventListener('click', function() {
                var link = this;
                setTimeout(function() {
                    link.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
                    updateButtons();
                }, 0);
            });
        }

        // Initial state
        var activeLink = tabs.querySelector('.nav-link.active');
        if (activeLink) {
            activeLink.scrollIntoView({ behavior: 'auto', block: 'nearest', inline: 'nearest' });
        }
        updateButtons();
    }

    return {
        init: init
    };
})();
