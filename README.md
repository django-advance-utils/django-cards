[![PyPI version](https://badge.fury.io/py/django-cards.svg)](https://badge.fury.io/py/django-cards)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

# django-cards

A Django library for building rich, interactive detail cards in your views — with 30+ display options, AJAX reload, search, export, datatables, and more.

---

## Overview

django-cards gives you a Python API to build Bootstrap-styled information cards directly from your Django views. Instead of writing repetitive template HTML, you declare cards and entries in Python:

- **8 card types** — standard detail, table, HTML, datatable, ordered datatable, list selection, layout/group, and message
- **30+ entry display options** — badges, icons, sparklines, ratings, progress bars, status dots, popovers, copy-to-clipboard, and more
- **Interactive features** — AJAX reload, client-side search, CSV/JSON export, collapsible cards
- **Layout system** — card groups, layout cards, and child card groups for complex page layouts
- **List & tree views** — built-in list-detail and tree-detail patterns with `CardList` and `CardTree`
- **Datatable integration** — embed [django-datatables](https://github.com/django-advance-utils/django-datatables) with drag-and-drop ordering

## Installation

```bash
pip install django-cards
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'cards',
]
```

### Dependencies

django-cards requires:
- [ajax-helpers](https://github.com/django-advance-utils/ajax-helpers)
- [django-menus](https://github.com/django-advance-utils/django-menus)
- [django-datatables](https://github.com/django-advance-utils/django-datatables) (for datatable card types)

## Quick Start

### 1. Create a view

```python
from cards.standard import CardMixin
from django.views.generic import DetailView

class CompanyDetailView(CardMixin, DetailView):
    model = Company
    template_name = 'company/detail.html'

    def setup_cards(self):
        card = self.add_card('info', title='Company Info', details_object=self.object)
        card.add_entry(field='name')
        card.add_entry(field='active')
        card.add_entry(field='importance')

        self.add_card_group('info', div_css_class='col-12')
```

### 2. Use in your template

```html
{% load django_cards_tags %}

<div class="row">
    {{ card_groups }}
</div>
```

Or render individual cards:

```html
{% load django_cards_tags %}

{% for card in cards.values %}
    {% show_card card %}
{% endfor %}
```

---

## Card Types

| Constant | Type | Description |
|---|---|---|
| `CARD_TYPE_STANDARD` (1) | Standard | Label/value detail card (default) |
| `CARD_TYPE_DATATABLE` (2) | Datatable | Embedded datatable |
| `CARD_TYPE_ORDERED_DATATABLE` (3) | Ordered Datatable | Datatable with drag-and-drop row ordering |
| `CARD_TYPE_HTML` (4) | HTML | Arbitrary HTML content |
| `CARD_TYPE_LIST_SELECTION` (5) | List Selection | Scrollable selectable list panel |
| `CARD_TYPE_CARD_GROUP` (6) | Card Group | Group of cards with a shared header |
| `CARD_TYPE_CARD_LAYOUT` (7) | Layout | Headerless nested layout container |
| `CARD_TYPE_CARD_MESSAGE` (8) | Message | Alert/warning message card |

Import constants from `cards.base`:

```python
from cards.base import CARD_TYPE_STANDARD, CARD_TYPE_DATATABLE, CARD_TYPE_HTML
```

---

## Entry Parameters Reference

The `add_entry()` method accepts 30+ parameters to control how each row is displayed.

### Core

| Parameter | Type | Default | Description |
|---|---|---|---|
| `value` | any | `None` | Direct value to display |
| `field` | str | `None` | Field name on `details_object` (supports `__` traversal, e.g. `'category__name'`) |
| `label` | str | `None` | Row label (auto-generated from `field` if omitted) |
| `default` | str | `'N/A'` | Fallback when value is None or empty |
| `hidden` | bool | `False` | Skip rendering this entry entirely |
| `hidden_if_blank_or_none` | bool | `None` | Hide row if value is blank or None |
| `hidden_if_zero` | bool | `None` | Hide row if value is 0 |

### Links & Navigation

| Parameter | Type | Default | Description |
|---|---|---|---|
| `link` | str/callable | `None` | URL — makes the entire row a hyperlink |
| `value_link` | str | `None` | URL wrapping only the value (not the label) |
| `auto_link` | bool | `False` | Auto-detect URLs and emails in text and make them clickable |

```python
card.add_entry(value='Visit https://example.com for details', label='Website', auto_link=True)
card.add_entry(value='Contact support@example.com', label='Email', auto_link=True)
```

### Display

| Parameter | Type | Default | Description |
|---|---|---|---|
| `badge` | bool/str | `None` | `True` for default badge (`bg-secondary`), or a CSS class string |
| `icon` | str | `None` | Font Awesome class (e.g. `'fas fa-envelope'`) |
| `prefix` | str | `None` | Text before the value |
| `suffix` | str | `None` | Text after the value |
| `status_dot` | str | `None` | CSS color for a dot indicator (e.g. `'green'`, `'#ff0000'`) |
| `progress_bar` | bool/str | `None` | `True` for default bar, or a CSS class (value is percentage) |
| `image` | bool/str | `None` | `True` for 40px height, or custom height string; value is image URL |
| `rating` | bool/int | `None` | `True` for 5 stars, or int for custom max; value is filled count |
| `sparkline` | bool/str | `False` | `True` for line chart, `'bar'` for bar chart; value is a list of numbers |
| `boolean_icon` | bool | `False` | Show check/cross icon for boolean values |

```python
card.add_entry(value='Active',   label='Status',  badge=True)
card.add_entry(value='Overdue',  label='Payment', badge='bg-danger')
card.add_entry(value='Premium',  label='Plan',    icon='fas fa-crown', badge='bg-warning text-dark')

card.add_entry(value='Active',   label='Server',  status_dot='green')
card.add_entry(value=75,         label='Progress', progress_bar=True)
card.add_entry(value=90,         label='Disk',    progress_bar='bg-danger')

card.add_entry(value=4,          label='Rating',   rating=True)      # 4 out of 5 stars
card.add_entry(value=7,          label='Score',    rating=10)        # 7 out of 10 stars

card.add_entry(value=[10, 25, 15, 30, 20, 35, 28], label='Trend',   sparkline=True)
card.add_entry(value=[5, 10, 3, 8, 12, 6, 9],      label='Volume',  sparkline='bar')

card.add_entry(value=True,  label='Active',   boolean_icon=True)
card.add_entry(value=False, label='Verified', boolean_icon=True)
```

### Formatting

| Parameter | Type | Default | Description |
|---|---|---|---|
| `number_format` | bool/int | `None` | `True` for comma-separated integers, int for decimal places |
| `truncate` | int | `None` | Max characters before truncation with ellipsis (full text in tooltip) |
| `timestamp` | bool | `False` | Display as "X ago" with full datetime in tooltip |
| `placeholder` | str/bool | `None` | Muted/italic placeholder when value is empty |

```python
card.add_entry(value=1234567,     label='Population', number_format=True)    # "1,234,567"
card.add_entry(value=1234567.891, label='Revenue',    number_format=2, prefix='$')  # "$1,234,567.89"
card.add_entry(value='A very long description that should be cut off', label='Desc', truncate=30)
card.add_entry(field='created_date', timestamp=True)  # "2 hours ago"
```

### Interactivity

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tooltip` | str | `None` | Bootstrap tooltip text on hover |
| `popover` | str/dict | `None` | Popover content; string or `{'title': '...', 'content': '...'}` |
| `copy_to_clipboard` | bool | `False` | Adds a copy button next to the value |
| `help_text` | str | `None` | Small muted text displayed below the value |

```python
card.add_entry(value='Hover me', label='Tooltip', tooltip='Extra information here')

card.add_entry(value='Click me', label='Popover',
               popover='Simple popover content')
card.add_entry(value='Click me', label='Rich Popover',
               popover={'title': 'Details', 'content': 'Popover with title and content'})

card.add_entry(value='sk-abc123def456ghi789', label='API Key', copy_to_clipboard=True)
card.add_entry(field='name', help_text='The primary display name')
```

### Conditional Display

| Parameter | Type | Default | Description |
|---|---|---|---|
| `show_if` | callable | `None` | `show_if(details_object) -> bool` — only show if returns True |
| `css_class_method` | callable | `None` | `css_class_method(value) -> str` — dynamic CSS class based on value |
| `default_if` | callable | `None` | Conditionally apply the default value |

```python
card.add_entry(field='name', show_if=lambda obj: obj.active)

card.add_entry(value=150, label='Balance',
               css_class_method=lambda v: 'text-success' if v >= 0 else 'text-danger')

card.add_entry(value='HIGH', label='Priority',
               css_class_method=lambda v: {'HIGH': 'text-danger fw-bold',
                                           'MEDIUM': 'text-warning',
                                           'LOW': 'text-success'}.get(v, ''))
```

### Diff / Change Indicator

| Parameter | Type | Default | Description |
|---|---|---|---|
| `old_value` | any | `None` | Shows old value as strikethrough with arrow to new value |

```python
card.add_entry(value='Active', label='Status', old_value='Pending')
card.add_entry(value=1500, label='Revenue', old_value=1200, number_format=True, prefix='$')
```

### Layout & Styling

| Parameter | Type | Default | Description |
|---|---|---|---|
| `row_style` | str | `None` | Named row style defined via `add_row_style()` |
| `separator` | bool | `False` | Render an `<hr>` separator before this entry |
| `entry_css_class` | str | `None` | CSS class for the value element |
| `css_class` | str | `None` | CSS class for the row container |
| `html_override` | str | `None` | Custom HTML — use `%1%` as value placeholder |
| `value_method` | callable | `None` | Transform the value before rendering |
| `value_type` | str | `None` | Rendering hint (`'currency'`, `'boolean'`, `'m2m'`, etc.) |

### Additional kwargs

These can be passed via `**kwargs`:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `merge` | bool | — | Join list values into a single string |
| `merge_string` | str | `' '` | Separator when merging list values |
| `m2m_field` | str | — | Attribute name on M2M related objects to display |
| `query_filter` | dict | — | Filter for M2M querysets |

---

## Card-Level Options

These are passed to `add_card()` or `CardBase.__init__()`:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `title` | str | `None` | Card heading text |
| `show_header` | bool | `True` | Whether to show the card header |
| `header_icon` | str | `None` | CSS icon class for header (e.g. `'fas fa-user'`) |
| `header_css_class` | str | `''` | CSS class for the header div |
| `footer` | str | `None` | Footer HTML content |
| `menu` | list/HtmlMenu | `None` | Action menu items in the header |
| `tab_menu` | list/HtmlMenu | `None` | Tab menu items in the header |
| `collapsed` | bool | `None` | `None`=no collapse; `False`=collapsible, open; `True`=collapsible, closed |
| `template_name` | str | `None` | Template key (`'default'`, `'table'`, `'blank'`) or custom path |
| `ajax_reload` | bool | `False` | Enable AJAX reload button |
| `reload_interval` | int | `None` | Auto-reload interval in seconds (requires `ajax_reload=True`) |
| `searchable` | bool | `False` | Adds a search input that filters card rows client-side |
| `exportable` | bool | `False` | Adds CSV/JSON export dropdown button |
| `show_created_modified_dates` | bool | `False` | Show created/modified timestamps from the details object |
| `details_object` | object | `None` | The data object for field-based entries |
| `is_empty` | bool | `False` | Render as empty state |
| `empty_message` | str | `'N/A'` | Message shown when card is empty |
| `hidden_if_blank_or_none` | list | `None` | Card-wide list of fields to hide when blank/None |
| `hidden_if_zero` | list | `None` | Card-wide list of fields to hide when zero |
| `extra_card_context` | dict | `None` | Extra context passed to the card template |

```python
card = self.add_card('profile',
                     title='User Profile',
                     details_object=user,
                     header_icon='fas fa-user',
                     header_css_class='bg-primary text-white',
                     footer='Last updated: today',
                     collapsed=False,
                     ajax_reload=True,
                     reload_interval=30,
                     searchable=True,
                     exportable=True)
```

### Table Template

Use `template_name='table'` for a table-style layout:

```python
card = self.add_card('details', title='Details', template_name='table',
                     extra_card_context={'table_css_class': 'table table-bordered'})
card.add_entry(value='Hello', label='Greeting')
```

---

## Card Groups & Layouts

### Card Groups

Arrange cards into Bootstrap grid columns:

```python
def setup_cards(self):
    self.add_card('profile', title='Profile', details_object=self.object)
    self.add_card('stats',   title='Statistics', details_object=self.object)
    self.add_card('notes',   title='Notes', details_object=self.object)

    # Two-column layout
    self.add_card_group('profile', 'stats', div_css_class='col-6 float-left')
    self.add_card_group('notes', div_css_class='col-6 float-right')
```

`add_card_group()` parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `*args` | str/CardBase | — | Card names or card objects to include |
| `div_css_class` | str | `''` | CSS class for the container div |
| `div_css` | str | `''` | Inline CSS styles |
| `div_id` | str | `''` | HTML id for the container |
| `script` | str | `''` | JavaScript to include in a `<script>` tag after the group |
| `group_title` | str | `''` | Heading displayed above the group |
| `group_code` | str | `'main'` | Group identifier |

### Layout Cards

For nesting cards inside a card (with or without a header):

```python
def setup_cards(self):
    child1 = self.add_card(title='Left Panel')
    child1.add_entry(value='Hello', label='Greeting')

    child2 = self.add_card(title='Right Panel', template_name='table')
    child2.add_entry(value='World', label='Target')

    layout = self.add_layout_card()
    layout.add_child_card_group(child1, div_css_class='col-6 float-left')
    layout.add_child_card_group(child2, div_css_class='col-6 float-left')

    self.add_card_group(layout, div_css_class='col-12')
```

Use `CARD_TYPE_CARD_GROUP` instead for a layout card **with** a header and menu:

```python
from cards.base import CARD_TYPE_CARD_GROUP

card = self.add_card('overview', title='Overview', group_type=CARD_TYPE_CARD_GROUP, menu=my_menu)
card.add_child_card_group(child1, div_css_class='col-6 float-left')
card.add_child_card_group(child2, div_css_class='col-6 float-left')
```

---

## Multi-Entry Rows

### add_row()

Place multiple entries side by side in a single row:

```python
card.add_row('first_name', 'last_name')                # Two columns
card.add_row('city', 'state', 'zip_code')               # Three columns
card.add_row('field1', 'field2', 'field3', 'field4')    # Four columns
```

Columns are automatically sized using Bootstrap grid classes (`col-sm-6` for 2, `col-sm-4` for 3, `col-sm-3` for 4).

You can also pass dicts for full control:

```python
card.add_row({'field': 'email', 'icon': 'fas fa-envelope'},
             {'field': 'phone', 'icon': 'fas fa-phone'})
```

### add_rows()

Bulk-add entries — each argument can be a string (field name), dict (entry kwargs), or list/tuple (passed to `add_row()`):

```python
card.add_rows(
    'name',                                            # Single entry
    {'field': 'email', 'icon': 'fas fa-envelope'},     # Dict entry
    ['first_name', 'last_name'],                       # Multi-column row
    [{'field': 'city', 'label': 'City'}, 'state'],    # Mixed row
)
```

---

## Custom Row Styles

Define custom HTML layouts for entries using `add_row_style()`:

```python
from ajax_helpers.html_include import HtmlDiv, HtmlElement

card.add_row_style('header_style', html=HtmlDiv([
    HtmlElement(element='span', contents=[
        HtmlElement(element='h4', contents='{label}')
    ]),
    HtmlElement(element='span', contents='{value}')
]))

card.add_entry(value='Custom layout', label='Title', row_style='header_style')
```

Set a default style for all subsequent entries:

```python
card.add_row_style('compact', html='<div class="compact">{label}: {value}</div>')
card.set_default_style('compact')

card.add_entry(value='Uses compact style', label='A')
card.add_entry(value='Also compact', label='B')
```

### HTML Entries

Insert raw HTML or rendered templates as card rows:

```python
card.add_html_entry(template_name='myapp/custom_entry.html', context={'key': 'value'}, colspan=2)
card.add_html_string_entry('<div class="custom">Raw HTML content</div>')
```

---

## CardList & CardTree

### CardList — List-Detail Pattern

A two-panel layout with a selectable list on the left and detail cards on the right:

```python
from cards.card_list import CardList
from django.views.generic import TemplateView

class CompanyListView(CardList, TemplateView):
    template_name = 'myapp/cards.html'
    list_title = 'Companies'
    model = Company

    def get_details_title(self, details_object):
        return details_object.name

    def get_details_menu(self, details_object):
        return [MenuItem('myapp:edit', menu_display='Edit', url_args=[details_object.pk])]

    def get_details_data(self, card, details_object):
        card.add_rows('name', 'active', 'importance')
        card.add_entry(field='company_category__name', label='Category')
```

Key class attributes:

| Attribute | Default | Description |
|---|---|---|
| `model` | `None` | Django model for list entries |
| `list_title` | `''` | Heading for the list panel |
| `list_class` | `'col-sm-5 col-md-4 col-lg-3 float-left'` | CSS class for list panel |
| `details_class` | `'col-sm-7 col-md-8 col-lg-9 float-left'` | CSS class for details panel |

Key methods to override:

| Method | Purpose |
|---|---|
| `get_details_data(card, details_object)` | Populate the detail card entries |
| `get_details_title(details_object)` | Return the detail card title |
| `get_details_menu(details_object)` | Return menu items for the detail card |
| `get_list_entries()` | Return the queryset for list items |
| `get_list_entry_name(entry_object)` | Return display name for a list item |
| `get_list_colour(entry_object)` | Return optional colour for a list item |

### CardTree — Tree-Detail Pattern

A two-panel layout with a jsTree navigation on the left:

```python
from cards.card_list import CardTree
from django.views.generic import TemplateView

class CategoryTreeView(CardTree, TemplateView):
    template_name = 'myapp/cards.html'
    list_title = 'Categories'

    def get_tree_data(self, selected_id):
        return [
            {'id': '1', 'parent': '#',  'text': 'Root Node'},
            {'id': '2', 'parent': '#',  'text': 'Another Root'},
            {'id': '3', 'parent': '2',  'text': 'Child Node', 'icon': 'fas fa-folder'},
            {'id': '4', 'parent': '2',  'text': 'Another Child'},
        ]

    def get_details_data(self, card, details_object):
        card.add_entry(value=details_object, label='Selected ID')
```

Override `get_tree_data(selected_id)` to return a list of node dicts with `id`, `parent` (`'#'` for root), `text`, and optionally `icon` and `state`.

---

## Datatables

### Datatable Card

Embed a django-datatables table inside a card:

```python
from cards.base import CARD_TYPE_DATATABLE

class MyView(CardMixin, TemplateView):
    ajax_commands = ['datatable', 'row', 'column']

    def setup_datatable_cards(self):
        self.add_card('companies',
                      title='Companies',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company,
                      collapsed=False)

    def setup_cards(self):
        self.add_card_group('companies', div_css_class='col-12')

    def setup_table_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'importance')
```

The `setup_table_<card_name>()` method is called automatically to configure the table.

### Ordered Datatable

Adds drag-and-drop row reordering:

```python
from cards.base import CARD_TYPE_ORDERED_DATATABLE

def setup_datatable_cards(self):
    self.add_card('statuses',
                  title='Statuses',
                  group_type=CARD_TYPE_ORDERED_DATATABLE,
                  datatable_model=Status)
```

---

## AJAX Reload

### Button Reload

Enable the reload button on a card:

```python
card = self.add_card('live_data', title='Live Data', ajax_reload=True)
```

### Auto-Reload Interval

Automatically refresh a card every N seconds:

```python
card = self.add_card('dashboard', title='Dashboard', ajax_reload=True, reload_interval=30)
```

### Programmatic Reload

Trigger a card reload from a button handler:

```python
def button_update(self, **kwargs):
    # ... perform update ...
    self.reload_card('live_data')
```

### WebSocket Push Reload

Use `CardReloadConsumer` with Django Channels for server-pushed card reloads:

```python
# routing.py
from cards.channels import CardReloadConsumer

websocket_urlpatterns = [
    path('ws/cards/', CardReloadConsumer.as_asgi()),
]
```

---

## HTML & Message Cards

### HTML Card (from template)

```python
card = self.add_html_card('myapp/chart.html', context={'data': chart_data}, title='Chart')
```

### HTML Card (from string)

```python
card = self.add_html_data_card('<div class="alert alert-info">Custom HTML</div>', title='Info')
```

### Message Card

```python
card = self.add_message_card(title='Warning', message='No data available for this period.')
```

### Link Gallery Card

Display a visual gallery of links as uniform 120px-height tiles. Supports multiple link types: images (thumbnail + lightbox), data sheets (PDF icon + new tab), product pages (web icon + new tab), and other links (link icon + new tab).

```python
links = [
    {'url': 'https://example.com/front.jpg', 'name': 'Front View', 'type': 'image'},
    {'url': 'https://example.com/side.jpg', 'name': 'Side View', 'type': 'image'},
    {'url': 'https://example.com/datasheet.pdf', 'name': 'Data Sheet', 'type': 'data_sheet'},
    {'url': 'https://example.com/product', 'name': 'Product Page', 'type': 'product_page'},
    {'url': 'https://example.com/other', 'name': 'Other Link', 'type': 'other'},
]
card = self.add_link_gallery_card(links, card_name='links', title='Links')

# Optionally show names below image thumbnails
card = self.add_link_gallery_card(links, card_name='links', title='Links', show_image_names=True)
```

`add_link_gallery_card()` parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `links` | list[dict] | — | List of dicts with `'url'`, `'type'` (required) and `'name'` (optional) keys |
| `card_name` | str | `None` | Unique card identifier |
| `title` | str | `'Links'` | Card header title |
| `show_image_names` | bool | `False` | Show name labels below image thumbnails |
| `**kwargs` | | | Additional keyword arguments passed to `add_card()` (e.g. `collapsed`, `menu`) |

Link types:

| Type | Icon | Click behaviour |
|---|---|---|
| `'image'` | Thumbnail (natural aspect ratio) | Opens lightbox modal |
| `'data_sheet'` | `fa-file-pdf` | Opens URL in new tab |
| `'product_page'` | `fa-globe` | Opens URL in new tab |
| `'other'` | `fa-link` | Opens URL in new tab |

All tiles are 120px height. Image thumbnails preserve their aspect ratio using `object-fit: contain`. Icon tiles (data sheet, product page, other) are 120x120px squares with the icon and name label.

Returns `None` if `links` is empty (no card rendered).

### Image Gallery Card

`add_image_gallery_card()` is a convenience wrapper around `add_link_gallery_card()` for image-only galleries:

```python
images = [
    {'url': 'https://example.com/front.jpg', 'name': 'Front View'},
    {'url': 'https://example.com/side.jpg', 'name': 'Side View'},
    {'url': 'https://example.com/detail.jpg'},  # name is optional
]
card = self.add_image_gallery_card(images, card_name='photos', title='Product Photos')
```

Features:
- **Thumbnails**: 120px-height tiles preserving image aspect ratio
- **Lightbox**: Click any thumbnail to open a Bootstrap modal with the full-size image
- **Navigation**: Prev/next buttons when multiple images exist
- **Multiple galleries**: Each card gets a unique ID, so multiple gallery cards on one page work independently

Full example — a product detail view with a links gallery alongside other cards:

```python
from cards.standard import CardMixin
from django.views.generic import DetailView

class ProductDetailView(CardMixin, DetailView):
    model = Product
    template_name = 'products/detail.html'

    def setup_cards(self):
        # Main details card
        card = self.add_card('details', title='Product Details', details_object=self.object)
        card.add_rows('name', 'sku', 'description', 'price')

        # Links gallery from related model
        product_links = self.object.links.all()
        links = [{'url': l.url, 'name': l.name, 'type': l.link_type} for l in product_links]
        gallery = self.add_link_gallery_card(links, card_name='links', title='Links')

        # Layout: details on the left, gallery on the right
        self.add_card_group('details', div_css_class='col-6 float-left')
        right_cards = [gallery] if gallery else []
        self.add_card_group(*right_cards, div_css_class='col-6 float-right')
```

---

## License

MIT
