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
        }
        if (_persist) {
            _restoreState(layout);
        }
        _initSplitters(layout);
        _initCollapseButtons(layout);
        _initTabMenus(layout);
    }

    function _setFullHeight(layout) {
        layout.style.height = '';
        var rect = layout.getBoundingClientRect();
        var minHeight = parseInt(layout.getAttribute('data-min-height'), 10) || 400;
        var bottom = _getBottomSpacing(layout);
        var height = window.innerHeight - rect.top - bottom;
        if (height < minHeight) height = minHeight;
        layout.style.height = height + 'px';
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
        if (typeof $ !== 'undefined' && $.fn.dataTable) {
            $(layout).find('table.dataTable').each(function() {
                $(this).DataTable().columns.adjust();
            });
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
        var tabLinks = layout.querySelectorAll('.panel-region__tabs a[data-toggle="tab"]');
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

    return {
        init: init
    };
})();
