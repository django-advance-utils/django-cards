from ajax_helpers.utils import random_string
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class PanelTab:
    """
    A tab pane within a PanelRegion.

    Each tab has a title, optional icon and menu, and holds one or more cards.
    The first tab is active by default unless another is explicitly set.

    Args:
        name (str): Unique identifier for the tab within the region.
        title (str): Display label shown on the tab.
        icon (str, optional): Font Awesome class for an icon before the title
            (e.g. ``'fas fa-building'``).
        active (bool, optional): Whether this tab is initially selected.
            Defaults to ``False``. If no tab is marked active, the first tab
            added to the region becomes active automatically.
        menu (list, optional): Menu items (e.g. ``MenuItem`` or
            ``AjaxButtonMenuItem``) shown to the right of the tab bar when
            this tab is active. The menu swaps automatically on tab switch.

    Example::

        tab = region.add_tab('companies', title='Companies',
                             icon='fas fa-building',
                             menu=[AjaxButtonMenuItem(button_name='add',
                                                      menu_display='',
                                                      font_awesome='fas fa-plus',
                                                      css_classes='btn btn-sm btn-outline-success')])
        tab.add_card(companies_card)
    """

    def __init__(self, name, title, icon=None, active=False, menu=None):
        self.name = name
        self.title = title
        self.icon = icon
        self.active = active
        self.menu = menu
        self.cards = []

    def add_card(self, card):
        """Add a card to this tab pane."""
        self.cards.append(card)
        return self


class PanelRegion:
    """
    A named region within a PanelLayout that can hold cards, tabs, or nested
    layouts.

    Regions are the leaf containers of a panel layout. Each region occupies a
    cell in its parent ``PanelSplit`` grid and can display:

    - **Cards** directly via :meth:`add_card`.
    - **Tabbed content** via :meth:`add_tab`, where each tab holds its own
      cards and optional per-tab menu.

    Regions support an optional **header toolbar** (``title`` / ``menu``),
    a separate **menu bar** (``toolbar``) rendered below the header, and
    collapsible behaviour.

    Args:
        name (str): Unique identifier used for the region's DOM id
            (``panel_region_<name>``).
        min_size (int, optional): Minimum size in pixels when resizing.
        max_size (int, optional): Maximum size in pixels when resizing.
        collapsible (bool, optional): Whether the region can be collapsed.
            Defaults to ``False``.
        collapsed (bool, optional): Whether the region starts collapsed.
            Defaults to ``False``. Only meaningful when ``collapsible=True``.
        collapse_direction (str, optional): Override chevron direction
            independently of the parent split direction. Use ``'horizontal'``
            for left/right chevrons or ``'vertical'`` for up/down. Defaults to
            the parent split's direction.
        overflow (str, optional): CSS overflow value. Defaults to ``'auto'``.
        menu (list, optional): Menu items shown in the header toolbar
            (to the right of the title by default). Accepts a list of
            ``MenuItem`` / ``AjaxButtonMenuItem`` objects.
        title (str, optional): Title displayed in the header toolbar.
        menu_align (str, optional): Alignment of the ``menu`` within the
            header toolbar — ``'right'`` (default) or ``'left'``.
        toolbar (list, optional): Menu items for a **separate menu bar**
            rendered below the header toolbar. Items are left-aligned.
            Useful for action buttons, filters, or tools that belong to the
            region but should be visually distinct from the title bar.

    Example — region with header, toolbar, and tabs::

        region = root.add_region(
            'main', size='1fr',
            title='Documents',
            menu=[MenuItem(...)],           # right side of title bar
            toolbar=[MenuItem(...)],        # separate bar below title
        )

        # Add tabbed content
        tab1 = region.add_tab('all', title='All', icon='fas fa-list')
        tab1.add_card(all_docs_card)

        tab2 = region.add_tab('recent', title='Recent', icon='fas fa-clock',
                              menu=[AjaxButtonMenuItem(...)])
        tab2.add_card(recent_docs_card)

    Example — region with just a left-aligned menu bar (no title)::

        region = root.add_region(
            'tools', size='1fr',
            toolbar=[
                MenuItem(..., font_awesome='fas fa-plus'),
                MenuItem(..., font_awesome='fas fa-filter'),
            ],
        )
        region.add_card(content_card)
    """

    def __init__(self, name, min_size=None, max_size=None, collapsible=False,
                 collapsed=False, collapse_direction=None, overflow='auto',
                 menu=None, title=None, menu_align='right', toolbar=None):
        self.name = name
        self.min_size = min_size
        self.max_size = max_size
        self.collapsible = collapsible
        self.collapsed = collapsed
        self.collapse_direction = collapse_direction
        self.overflow = overflow
        self.menu = menu
        self.title = title
        self.menu_align = menu_align
        self.toolbar = toolbar
        self.cards = []
        self.tabs = []

    def add_card(self, card):
        """
        Add a card directly to the region.

        When the region has a ``title`` or ``menu``, the card's own header is
        hidden to avoid duplication (the region toolbar acts as the header).
        """
        self.cards.append(card)
        return self

    def add_tab(self, name, title, icon=None, active=False, menu=None):
        """
        Add a tab pane to the region.

        When tabs are present, the region renders a tab bar (below the header
        toolbar if one exists) and each tab's cards are shown in switchable
        panes.

        Args:
            name (str): Unique identifier for the tab.
            title (str): Display label on the tab.
            icon (str, optional): Font Awesome class for a tab icon.
            active (bool, optional): Whether this tab is initially selected.
                The first tab is active by default if none is specified.
            menu (list, optional): Per-tab menu items shown to the right of the
                tab bar when this tab is active.

        Returns:
            PanelTab: The created tab, use ``.add_card()`` to populate it.
        """
        tab = PanelTab(name=name, title=title, icon=icon, active=active, menu=menu)
        self.tabs.append(tab)
        # First tab is active by default if none specified
        if not any(t.active for t in self.tabs):
            self.tabs[0].active = True
        return tab


class PanelSplit:
    """
    A split container that arranges child items (regions or nested splits)
    either horizontally or vertically using CSS Grid.

    Splits can be nested to create complex layouts. Each child gets a grid
    track size (e.g. ``'1fr'``, ``'250px'``, ``'auto'``).

    Args:
        direction (str, optional): ``'horizontal'`` (columns, default) or
            ``'vertical'`` (rows).
        sizes (list, optional): Explicit list of CSS grid track sizes.
            Normally populated automatically by :meth:`add_region` /
            :meth:`add_split`.
        resizable (bool, optional): Whether splitter bars are shown between
            children. Defaults to ``True``.
        name (str, optional): Identifier for the split (required if
            ``collapsible=True``).
        collapsible (bool, optional): Whether the entire split can be
            collapsed as a unit. Wraps the split in a region-like container
            with a collapse button.
        collapsed (bool, optional): Whether the split starts collapsed.
        title (str, optional): Title shown in the collapse toolbar (only
            used when ``collapsible=True``).

    Example::

        root = layout.root  # horizontal split

        sidebar = root.add_region('sidebar', size='250px')

        # Nested vertical split on the right
        right = root.add_split(direction='vertical')
        top = right.add_region('top', size='200px')
        bottom = right.add_region('bottom', size='1fr')
    """
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'

    def __init__(self, direction=HORIZONTAL, sizes=None, resizable=True,
                 name=None, collapsible=False, collapsed=False, title=None):
        self.direction = direction
        self.sizes = sizes or []
        self.resizable = resizable
        self.children = []
        self.name = name
        self.collapsible = collapsible
        self.collapsed = collapsed
        self.title = title

    def add_region(self, name, size='1fr', min_size=None, max_size=None,
                   collapsible=False, collapsed=False, collapse_direction=None,
                   overflow='auto', menu=None, title=None, menu_align='right',
                   toolbar=None):
        """
        Add a region to this split.

        Args:
            name (str): Unique region identifier.
            size (str, optional): CSS grid track size. Defaults to ``'1fr'``.
                Common values: ``'250px'``, ``'1fr'``, ``'auto'``.
            min_size (int, optional): Minimum pixel size during drag resize.
            max_size (int, optional): Maximum pixel size during drag resize.
            collapsible (bool, optional): Allow collapsing. Defaults to ``False``.
            collapsed (bool, optional): Start collapsed. Defaults to ``False``.
            collapse_direction (str, optional): Override chevron direction
                (``'horizontal'`` or ``'vertical'``).
            overflow (str, optional): CSS overflow. Defaults to ``'auto'``.
            menu (list, optional): Menu items in the header toolbar.
            title (str, optional): Title in the header toolbar.
            menu_align (str, optional): ``'right'`` (default) or ``'left'``.
            toolbar (list, optional): Menu items for a separate left-aligned
                menu bar below the header toolbar.

        Returns:
            PanelRegion: The created region.
        """
        region = PanelRegion(
            name=name,
            min_size=min_size,
            max_size=max_size,
            collapsible=collapsible,
            collapsed=collapsed,
            collapse_direction=collapse_direction,
            overflow=overflow,
            menu=menu,
            title=title,
            menu_align=menu_align,
            toolbar=toolbar,
        )
        self.children.append(region)
        self.sizes.append(size)
        return region

    def add_split(self, direction=None, sizes=None, resizable=True,
                  name=None, collapsible=False, collapsed=False, title=None):
        """
        Add a nested split inside this split.

        The default direction alternates: a horizontal parent creates vertical
        children and vice versa.

        Args:
            direction (str, optional): ``'horizontal'`` or ``'vertical'``.
                Defaults to the opposite of the parent.
            sizes (list, optional): Explicit grid track sizes.
            resizable (bool, optional): Show splitter bars. Defaults to ``True``.
            name (str, optional): Identifier (required if collapsible).
            collapsible (bool, optional): Allow collapsing the whole split.
            collapsed (bool, optional): Start collapsed.
            title (str, optional): Title for the collapse toolbar.

        Returns:
            PanelSplit: The created child split.
        """
        if direction is None:
            direction = (self.VERTICAL if self.direction == self.HORIZONTAL
                         else self.HORIZONTAL)
        split = PanelSplit(direction=direction, sizes=sizes, resizable=resizable,
                           name=name, collapsible=collapsible, collapsed=collapsed,
                           title=title)
        self.children.append(split)
        if not sizes:
            self.sizes.append('1fr')
        return split

    def _build_context(self):
        children_ctx = []
        for i, child in enumerate(self.children):
            size = self.sizes[i] if i < len(self.sizes) else '1fr'
            if isinstance(child, PanelRegion):
                region_ctx = {
                    'type': 'region',
                    'name': child.name,
                    'size': size,
                    'min_size': child.min_size,
                    'max_size': child.max_size,
                    'collapsible': child.collapsible,
                    'collapsed': child.collapsed,
                    'collapse_direction': child.collapse_direction,
                    'overflow': child.overflow,
                    'menu': child.menu,
                    'title': child.title,
                    'menu_align': child.menu_align,
                    'toolbar': child.toolbar,
                    'cards': child.cards,
                }
                if child.tabs:
                    region_ctx['tabs'] = [
                        {
                            'name': tab.name,
                            'title': tab.title,
                            'icon': tab.icon,
                            'active': tab.active,
                            'menu': tab.menu,
                            'cards': tab.cards,
                        }
                        for tab in child.tabs
                    ]
                children_ctx.append(region_ctx)
            elif isinstance(child, PanelSplit):
                ctx = {
                    'type': 'split',
                    'size': size,
                    'split': child._build_context(),
                }
                if child.name:
                    ctx['name'] = child.name
                    ctx['collapsible'] = child.collapsible
                    ctx['collapsed'] = child.collapsed
                    ctx['title'] = child.title
                children_ctx.append(ctx)
        return {
            'direction': self.direction,
            'resizable': self.resizable,
            'children': children_ctx,
        }


class PanelLayout:
    """
    A CSS Grid-based panel layout system for django-cards.

    Provides resizable and collapsible panel regions arranged via horizontal
    and vertical splits — similar in concept to IDE-style layouts but
    implemented purely with CSS Grid and vanilla JS.

    **Features:**

    - Drag-resizable splitter bars between regions
    - Collapsible regions with animated chevron icons
    - Tabbed content within regions (with per-tab menus)
    - Header toolbars and separate menu bars on regions
    - Linked datatables across regions
    - Accordion cards that fill region height
    - Nested splits for complex multi-pane layouts
    - Full-height mode (fills viewport minus surrounding content)
    - Persistent state via localStorage (sizes + collapse state)

    **Visual structure of a region:**

    A region can display up to four layers stacked vertically::

        ┌─────────────────────────────────────┐
        │ Header toolbar  (title + menu)      │  ← title/menu params
        ├─────────────────────────────────────┤
        │ Menu bar  (left-aligned buttons)    │  ← toolbar param
        ├─────────────────────────────────────┤
        │ Tab bar  (tabs + per-tab menu)      │  ← add_tab()
        ├─────────────────────────────────────┤
        │                                     │
        │ Content area  (cards)               │  ← add_card() / tab.add_card()
        │                                     │
        └─────────────────────────────────────┘

    All layers are optional. A region with just ``add_card()`` has only the
    content area.

    Args:
        view: The parent view instance.
        card_name (str, optional): Unique name for the layout card.
            Defaults to ``'panel_layout'``.
        layout_id (str, optional): DOM id for the layout container.
            Defaults to ``'panel_layout_<card_name>'``.
        direction (str, optional): Root split direction — ``'horizontal'``
            (default) or ``'vertical'``.
        resizable (bool, optional): Enable splitter bars. Defaults to ``True``.
        full_height (bool, optional): Automatically size the layout to fill
            the viewport height (minus surrounding content). Defaults to
            ``True``.
        min_height (str, optional): CSS min-height value. Defaults to
            ``'400px'``.
        css_class (str, optional): Extra CSS classes on the layout container.
        css_style (str, optional): Extra inline styles on the layout container.
        persist (bool, optional): Save/restore panel sizes and collapse state
            to localStorage. Defaults to ``True``. Set to ``False`` for layouts
            where saved state could cause issues (e.g. dynamic content).

    Basic usage::

        layout = self.add_panel_layout()
        root = layout.root

        sidebar = root.add_region('sidebar', size='250px', collapsible=True)
        right = root.add_split(direction='vertical')
        header = right.add_region('header', size='auto')
        main = right.add_region('main', size='1fr')

        sidebar.add_card(nav_card)
        main.add_card(content_card)

        self.add_card_group(layout.render(), div_css_class='col-12')

    Region with header toolbar and menu bar::

        region = root.add_region(
            'editor', size='1fr',
            title='Editor',
            menu=[MenuItem(...)],           # right side of title bar
            toolbar=[                       # separate bar below title
                MenuItem(..., font_awesome='fas fa-bold'),
                MenuItem(..., font_awesome='fas fa-italic'),
            ],
        )

    Region with tabs and per-tab menus::

        region = root.add_region('main', size='1fr', title='Data')

        tab1 = region.add_tab('companies', title='Companies',
                              icon='fas fa-building',
                              menu=[AjaxButtonMenuItem(...)])
        tab1.add_card(companies_datatable)

        tab2 = region.add_tab('people', title='People',
                              icon='fas fa-users')
        tab2.add_card(people_datatable)

    Linked datatables::

        layout.linked_tables = [
            {'table_id': 'categories'},
            {'table_id': 'companies', 'linked_field': 'company_category_id'},
            {'table_id': 'people', 'linked_field': 'company_id'},
        ]
    """

    def __init__(self, view=None, card_name='panel_layout', layout_id=None,
                 direction=PanelSplit.HORIZONTAL,
                 resizable=True, full_height=True, min_height='400px',
                 css_class='', css_style='', persist=True):
        self.view = view
        self.card_name = card_name
        self.layout_id = layout_id or f'panel_layout_{card_name}'
        self.root = PanelSplit(direction=direction, resizable=resizable)
        self.full_height = full_height
        self.min_height = min_height
        self.css_class = css_class
        self.css_style = css_style
        self.linked_tables = None
        self.persist = persist

    def get_region(self, name):
        """Look up a region by name (searches the full tree)."""
        return self._find_region(self.root, name)

    def _find_region(self, node, name):
        if isinstance(node, PanelRegion):
            if node.name == name:
                return node
            return None
        for child in node.children:
            result = self._find_region(child, name)
            if result:
                return result
        return None

    def _process_menus(self, node):
        """Convert menu lists to HtmlMenu objects throughout the tree."""
        from django_menus.menu import HtmlMenu
        if isinstance(node, PanelRegion):
            request = getattr(self.view, 'request', None)
            if node.menu and isinstance(node.menu, (list, tuple)):
                node.menu = HtmlMenu(request, 'button_group').add_items(*node.menu)
            if node.toolbar and isinstance(node.toolbar, (list, tuple)):
                node.toolbar = HtmlMenu(request, 'button_group').add_items(*node.toolbar)
            for tab in node.tabs:
                if tab.menu and isinstance(tab.menu, (list, tuple)):
                    tab.menu = HtmlMenu(request, 'button_group').add_items(*tab.menu)
        elif isinstance(node, PanelSplit):
            for child in node.children:
                self._process_menus(child)

    def _render_html(self):
        import json
        self._process_menus(self.root)
        context = {
            'layout_id': self.layout_id,
            'root': self.root._build_context(),
            'full_height': self.full_height,
            'min_height': self.min_height,
            'css_class': self.css_class,
            'css_style': self.css_style,
            'panel_card_context': {'card_css_class': 'card panel-card'},
            'panel_no_header_context': {'card_css_class': 'card panel-card panel-card--no-header', 'show_header': False},
            'linked_tables_json': mark_safe(json.dumps(self.linked_tables)) if self.linked_tables else None,
            'persist': self.persist,
        }
        return mark_safe(render_to_string('cards/standard/panel_layout.html', context))

    def render(self):
        """Render the layout and return a card ready for add_card_group()."""
        from cards.base import CARD_TYPE_PANEL_LAYOUT
        html = self._render_html()
        return self.view.add_card(
            card_name=self.card_name,
            group_type=CARD_TYPE_PANEL_LAYOUT,
            html=html,
            show_header=False,
        )
