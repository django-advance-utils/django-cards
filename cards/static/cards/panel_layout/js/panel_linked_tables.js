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

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    csrfmiddlewaretoken: csrf,
                    table_id: config.table_id,
                    datatable_data: true,
                    linked_filter_field: filterField,
                    linked_filter_value: filterValue
                },
                success: function(response) {
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
                }
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
            $('#' + config.table_id + ' tbody tr').removeClass('linked-datatable-row-selected');
            $(row).addClass('linked-datatable-row-selected');
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
        for (var k = 0; k < tableConfigs.length; k++) {
            (function(idx) {
                var config = tableConfigs[idx];
                $(layout).on('click', '#' + config.table_id + ' tbody tr', function() {
                    selectRow(idx, this, true);
                });
            })(k);
        }

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
            if (!autoSelectFirst()) {
                $('#' + tableConfigs[0].table_id).on('draw.dt', function handler() {
                    if (autoSelectFirst()) {
                        $('#' + tableConfigs[0].table_id).off('draw.dt', handler);
                    }
                });
            }
        }
    }

    return {
        init: init
    };
})();
