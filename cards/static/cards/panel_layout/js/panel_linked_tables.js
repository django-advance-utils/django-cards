/**
 * PanelLinkedTables - Links datatables across panel regions so clicking a row
 * in one table filters the next table in the chain.
 * Optionally loads detail cards for selected rows.
 *
 * Usage:
 *   PanelLinkedTables.init('layout_id', [
 *       {table_id: 'categories', detail_card: 'cat_detail', detail_model: 'CompanyCategory'},
 *       {table_id: 'companies', linked_field: 'company_category_id',
 *        detail_card: 'comp_detail', detail_model: 'Company'},
 *   ]);
 */
var PanelLinkedTables = (function() {
    'use strict';

    function formEncode(data) {
        var parts = [];
        for (var key in data) {
            if (!Object.prototype.hasOwnProperty.call(data, key)) continue;
            parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(data[key] == null ? '' : data[key]));
        }
        return parts.join('&');
    }

    // The auto-select poll for each layout on the page, so a re-init can stop the one the
    // previous render started.
    var polls = {};

    function init(layoutId, tableConfigs) {
        var layout = document.getElementById(layoutId);
        if (!layout) return;

        // Add selected-row style
        var style = document.createElement('style');
        style.textContent = '.linked-datatable-row-selected { background-color: #d4edfa !important; }';
        document.head.appendChild(style);

        // Track selected IDs per table
        for (var i = 0; i < tableConfigs.length; i++) {
            tableConfigs[i].index = i;
            tableConfigs[i].selectedId = null;
        }

        function clearDetailCard(config) {
            if (config.detail_card) {
                var el = document.getElementById(config.detail_card + '_body');
                if (el) {
                    el.innerHTML = '<p class="text-muted p-2 mb-0" style="font-size:0.85rem">Select a row to view details</p>';
                }
            }
        }

        function loadDetailCard(config, rowId) {
            if (!config.detail_card || !config.detail_model) return;
            ajax_helpers.post_json({data: {
                button: 'load_detail',
                detail_card: config.detail_card,
                model: config.detail_model,
                row_id: rowId
            }});
        }

        function clearDownstream(fromIndex) {
            for (var i = fromIndex + 1; i < tableConfigs.length; i++) {
                var config = tableConfigs[i];
                config.selectedId = null;
                var dt = django_datatables.DataTables[config.table_id];
                if (dt) {
                    dt.table.api().clear().draw();
                }
                clearDetailCard(config);
            }
        }

        function loadTable(index, filterField, filterValue) {
            var config = tableConfigs[index];
            var dt = django_datatables.DataTables[config.table_id];
            if (!dt) return;

            var tableEl = document.getElementById(config.table_id);
            var url = tableEl ? (tableEl.getAttribute('data-url') || window.location.pathname) : window.location.pathname;
            var csrf = ajax_helpers.getCookie('csrftoken');

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-CSRFToken': csrf
                },
                body: formEncode({
                    csrfmiddlewaretoken: csrf,
                    table_id: config.table_id,
                    datatable_data: true,
                    linked_filter_field: filterField,
                    linked_filter_value: filterValue
                }),
                credentials: 'same-origin'
            }).then(function(response) {
                if (!response.ok) throw new Error('request failed');
                return response.json();
            }).then(function(response) {
                dt.table.api().clear();
                if (response.data && response.data.length > 0) {
                    dt.table.api().rows.add(response.data);
                }
                dt.table.api().draw();

                // Auto-select first row if not the last table
                if (index < tableConfigs.length - 1 && response.data && response.data.length > 0) {
                    setTimeout(function() {
                        var firstRow = document.querySelector('#' + config.table_id + ' tbody tr');
                        if (firstRow) {
                            selectRow(index, firstRow);
                        }
                    }, 50);
                }
            }).catch(function() {
                // Keep UI usable if a linked load fails.
            });
        }

        function selectRow(panelIndex, row, toggle) {
            var config = tableConfigs[panelIndex];
            var dt = django_datatables.DataTables[config.table_id];
            if (!dt) return;

            var rowData = dt.table.api().row(row).data();
            if (!rowData) return;

            var rowId = rowData[0];

            // Toggle if clicking same row
            if (toggle && config.selectedId === rowId) {
                config.selectedId = null;
                row.classList.remove('linked-datatable-row-selected');
                clearDetailCard(config);
                clearDownstream(panelIndex);
                return;
            }

            // Highlight
            var selected = document.querySelectorAll('#' + config.table_id + ' tbody tr.linked-datatable-row-selected');
            for (var s = 0; s < selected.length; s++) {
                selected[s].classList.remove('linked-datatable-row-selected');
            }
            row.classList.add('linked-datatable-row-selected');
            config.selectedId = rowId;

            // Load detail card
            loadDetailCard(config, rowId);

            // Clear and load downstream
            clearDownstream(panelIndex);

            var nextIndex = panelIndex + 1;
            if (nextIndex < tableConfigs.length && tableConfigs[nextIndex].linked_field) {
                loadTable(nextIndex, tableConfigs[nextIndex].linked_field, rowId);
            }
        }

        // Bind click handlers using delegated events on the layout container
        layout.addEventListener('click', function(e) {
            var row = e.target.closest('tbody tr');
            if (!row || !layout.contains(row)) return;
            var table = row.closest('table');
            if (!table || !table.id) return;
            for (var idx = 0; idx < tableConfigs.length; idx++) {
                if (tableConfigs[idx].table_id === table.id) {
                    selectRow(idx, row, true);
                    break;
                }
            }
        });

        // Auto-select first row of first table
        function autoSelectFirst() {
            var firstConfig = tableConfigs[0];
            var dt = django_datatables.DataTables[firstConfig.table_id];
            if (dt && dt.table.api().rows().count() > 0) {
                var firstRow = document.querySelector('#' + firstConfig.table_id + ' tbody tr');
                if (firstRow) {
                    selectRow(0, firstRow);
                    return true;
                }
            }
            return false;
        }

        if (tableConfigs.length > 0) {
            // Cancel the poll left running by a previous init of this layout before doing
            // anything else, or it would auto-select the new tables as well and load the
            // detail twice. Above the autoSelectFirst() below on purpose: an init that
            // finds rows already there returns without starting a poll of its own, and
            // would otherwise never reach this.
            // Keyed on the layout id rather than held on the element: a re-render replaces
            // the element, so the outgoing timer has to be findable without it.
            if (polls[layoutId]) {
                clearInterval(polls[layoutId]);
                polls[layoutId] = null;
            }
            if (!autoSelectFirst()) {
                var tries = 0;
                var timer = setInterval(function() {
                    tries += 1;
                    if (autoSelectFirst() || tries > 100) {
                        clearInterval(timer);
                    }
                }, 50);
                polls[layoutId] = timer;
            }
        }
    }

    return {
        init: init
    };
})();
