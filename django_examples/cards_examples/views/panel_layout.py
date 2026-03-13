from cards_examples.models import Company, CompanyCategory, Person, Payment
from cards_examples.views.base import MainMenu
from django.views.generic import TemplateView
from django_menus.menu import MenuItem, AjaxButtonMenuItem

from cards.base import CARD_TYPE_DATATABLE
from cards.standard import CardMixin


class PanelLayoutSidebarExample(MainMenu, CardMixin, TemplateView):
    """Classic sidebar + main content layout with collapsible nav panel."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        layout = self.add_panel_layout(min_height='500px')
        root = layout.root

        sidebar_menu = [
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-plus', css_classes='btn btn-sm btn-outline-secondary'),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-sync', css_classes='btn btn-sm btn-outline-secondary'),
        ]

        main_menu = [
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-edit', css_classes='btn btn-sm btn-outline-primary'),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-cog', css_classes='btn btn-sm btn-outline-secondary'),
        ]

        sidebar = root.add_region('sidebar', size='280px', collapsible=True, min_size=150,
                                  title='Navigation', menu=sidebar_menu)
        main_region = root.add_region('main', size='1fr', min_size=200,
                                      collapsible=True, title='Dashboard', menu=main_menu)

        # Sidebar navigation card
        nav_card = self.add_card(title='Navigation')
        nav_card.add_rows(
            {'label': 'Dashboard', 'value': 'Overview of all data'},
            {'label': 'Companies', 'value': 'Manage company records'},
            {'label': 'People', 'value': 'Employee directory'},
            {'label': 'Reports', 'value': 'Monthly summaries'},
            {'label': 'Settings', 'value': 'System configuration'},
        )
        sidebar.add_card(nav_card)

        # Main content card
        main_card = self.add_card(title='Dashboard')
        main_card.add_rows(
            {'label': 'Total Companies', 'value': str(Company.objects.count())},
            {'label': 'Total People', 'value': str(Person.objects.count())},
            {'label': 'Info', 'value': 'Drag the splitter bar to resize panels'},
            {'label': 'Tip', 'value': 'Hover the sidebar to see the collapse button'},
        )
        main_region.add_card(main_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutThreeColumnExample(MainMenu, CardMixin, TemplateView):
    """Three-column layout: tree nav, main editor area, properties panel."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        layout = self.add_panel_layout(min_height='500px')
        root = layout.root

        left = root.add_region('left', size='220px', collapsible=True, min_size=120)
        centre = root.add_region('centre', size='1fr', min_size=250)
        right = root.add_region('right', size='280px', collapsible=True, min_size=150)

        # Left panel - tree-like nav
        tree_card = self.add_card(title='Explorer')
        tree_card.add_rows(
            {'label': 'Folder', 'value': 'Documents'},
            {'label': 'Folder', 'value': 'Images'},
            {'label': 'Folder', 'value': 'Reports'},
            {'label': 'File', 'value': 'notes.txt'},
            {'label': 'File', 'value': 'summary.pdf'},
        )
        left.add_card(tree_card)

        # Centre panel - main content
        content_card = self.add_card(title='Editor')
        content_card.add_rows(
            {'label': 'Document', 'value': 'Select an item from the left panel'},
            {'label': 'Status', 'value': 'Ready'},
            {'label': 'Modified', 'value': 'Today'},
        )
        centre.add_card(content_card)

        # Right panel - properties
        props_card = self.add_card(title='Properties')
        props_card.add_rows(
            {'label': 'Name', 'value': 'notes.txt'},
            {'label': 'Size', 'value': '2.4 KB'},
            {'label': 'Type', 'value': 'Text Document'},
            {'label': 'Created', 'value': '2024-01-15'},
            {'label': 'Owner', 'value': 'admin'},
        )
        right.add_card(props_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutNestedExample(MainMenu, CardMixin, TemplateView):
    """Nested layout: sidebar + right side split into top header and bottom main area."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        layout = self.add_panel_layout(min_height='550px')
        root = layout.root

        # Left sidebar
        sidebar = root.add_region('sidebar', size='250px', collapsible=True, min_size=150)

        # Right side splits vertically into top and bottom
        right = root.add_split(direction='vertical')
        top_region = right.add_region('top', size='200px', min_size=100)
        bottom_region = right.add_region('bottom', size='1fr', min_size=150)

        # Sidebar
        nav_card = self.add_card(title='Modules')
        nav_card.add_rows(
            {'label': 'CRM', 'value': 'Customer management'},
            {'label': 'HR', 'value': 'Human resources'},
            {'label': 'Finance', 'value': 'Accounts & billing'},
            {'label': 'Inventory', 'value': 'Stock control'},
        )
        sidebar.add_card(nav_card)

        # Top area - summary
        summary_card = self.add_card(title='Summary')
        summary_card.add_rows(
            {'label': 'Companies', 'value': str(Company.objects.count())},
            {'label': 'People', 'value': str(Person.objects.count())},
            {'label': 'Status', 'value': 'All systems operational'},
        )
        top_region.add_card(summary_card)

        # Bottom area - detail
        person = Person.objects.first()
        if person:
            detail_card = self.add_card(title='Person Detail', details_object=person)
            detail_card.add_rows(
                'title', 'first_name', 'surname',
                {'field': 'company__name', 'label': 'Company'},
            )
        else:
            detail_card = self.add_card(title='Person Detail')
            detail_card.add_rows({'label': 'Info', 'value': 'No people in the system'})
        bottom_region.add_card(detail_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutHolyGrailExample(MainMenu, CardMixin, TemplateView):
    """Holy grail layout: header, left sidebar, main content, right sidebar, footer."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        layout = self.add_panel_layout(min_height='600px', direction='vertical')
        root = layout.root

        header_region = root.add_region('header', size='auto')
        middle = root.add_split(direction='horizontal')
        footer_region = root.add_region('footer', size='auto')

        # Middle row splits horizontally: left, centre, right
        left = middle.add_region('left_nav', size='200px', collapsible=True, min_size=100)
        centre = middle.add_region('content', size='1fr', min_size=200)
        right_panel = middle.add_region('aside', size='220px', collapsible=True, min_size=100)

        # Header
        header_card = self.add_card(title='Application Header')
        header_card.add_rows(
            {'label': 'App', 'value': 'Django Cards Panel Layout Demo'},
            {'label': 'Version', 'value': '1.0'},
        )
        header_region.add_card(header_card)

        # Left nav
        nav_card = self.add_card(title='Menu')
        nav_card.add_rows(
            {'label': '1', 'value': 'Home'},
            {'label': '2', 'value': 'Products'},
            {'label': '3', 'value': 'Orders'},
            {'label': '4', 'value': 'Customers'},
        )
        left.add_card(nav_card)

        # Main content
        company = Company.objects.first()
        if company:
            content_card = self.add_card(title='Company Detail', details_object=company)
            content_card.add_rows('name', 'active', 'importance')
        else:
            content_card = self.add_card(title='Company Detail')
            content_card.add_rows({'label': 'Info', 'value': 'No companies in the system'})
        centre.add_card(content_card)

        # Right aside
        aside_card = self.add_card(title='Quick Stats')
        aside_card.add_rows(
            {'label': 'Online', 'value': '42'},
            {'label': 'Pending', 'value': '7'},
            {'label': 'Alerts', 'value': '3'},
        )
        right_panel.add_card(aside_card)

        # Footer
        footer_card = self.add_card(title='Status Bar')
        footer_card.add_rows(
            {'label': 'Connection', 'value': 'Connected'},
            {'label': 'Last Sync', 'value': 'Just now'},
        )
        footer_region.add_card(footer_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutWithDatatableExample(MainMenu, CardMixin, TemplateView):
    """Panel layout with a datatable card in the main region."""
    template_name = 'cards_examples/cards.html'

    def setup_datatable_cards(self):
        layout = self.add_panel_layout(min_height='550px')
        root = layout.root

        sidebar = root.add_region('sidebar', size='250px', collapsible=True, min_size=150)
        main_region = root.add_region('main', size='1fr', min_size=300)

        # Sidebar with person info
        person = Person.objects.first()
        if person:
            info_card = self.add_card(title='Selected Person', details_object=person)
            info_card.add_rows('title', 'first_name', 'surname')
        else:
            info_card = self.add_card(title='Selected Person')
            info_card.add_rows({'label': 'Info', 'value': 'No people in the system'})
        sidebar.add_card(info_card)

        # Main area with datatable
        table_card = self.add_card(
            'companies_table',
            title='Companies',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=Company,
        )
        main_region.add_card(table_card)

        self.add_card_group(layout.render(), div_css_class='col-12')

    def setup_table_companies_table(self, table, details_object):
        table.add_columns('id', 'name', 'active')


class PanelLayoutFullscreenExample(CardMixin, TemplateView):
    """Fullscreen panel layout with no menu bar — fills the entire viewport."""
    template_name = 'cards_examples/panel_fullscreen.html'

    def setup_cards(self):
        layout = self.add_panel_layout(
            card_name='fullscreen_layout',
            min_height='100vh',
            css_style='height: 100vh;',
            full_height=False,
        )
        root = layout.root

        # Left sidebar
        sidebar = root.add_region('sidebar', size='260px', collapsible=True, min_size=150)

        # Right side splits vertically
        right = root.add_split(direction='vertical')
        top_region = right.add_region('top', size='auto')
        middle = right.add_split(direction='horizontal')
        bottom_region = right.add_region('bottom', size='auto')

        # Middle splits into main + detail
        main_region = middle.add_region('main', size='1fr', min_size=200)
        detail_region = middle.add_region('detail', size='300px', collapsible=True, min_size=150)

        # Sidebar
        nav_card = self.add_card(title='Navigation')
        nav_card.add_rows(
            {'label': 'Dashboard', 'value': 'Overview'},
            {'label': 'Companies', 'value': 'Manage records'},
            {'label': 'People', 'value': 'Directory'},
            {'label': 'Reports', 'value': 'Monthly'},
            {'label': 'Settings', 'value': 'Configuration'},
            {'label': 'Help', 'value': 'Documentation'},
        )
        sidebar.add_card(nav_card)

        # Top bar
        header_card = self.add_card(title='Application')
        header_card.add_rows(
            {'label': 'Status', 'value': 'Online'},
            {'label': 'User', 'value': 'admin'},
        )
        top_region.add_card(header_card)

        # Main content
        main_card = self.add_card(title='Companies')
        main_card.add_rows(
            {'label': 'Total', 'value': str(Company.objects.count())},
            {'label': 'Active', 'value': str(Company.objects.filter(active=True).count())},
        )
        company = Company.objects.first()
        if company:
            main_card.add_rows(
                {'label': 'First', 'value': company.name},
            )
        main_region.add_card(main_card)

        # Detail panel
        person = Person.objects.first()
        if person:
            detail_card = self.add_card(title='Person Detail', details_object=person)
            detail_card.add_rows('title', 'first_name', 'surname')
        else:
            detail_card = self.add_card(title='Person Detail')
            detail_card.add_rows({'label': 'Info', 'value': 'No people in the system'})
        detail_region.add_card(detail_card)

        # Bottom bar
        footer_card = self.add_card(title='Status')
        footer_card.add_rows(
            {'label': 'Connection', 'value': 'Connected'},
            {'label': 'Last Sync', 'value': 'Just now'},
        )
        bottom_region.add_card(footer_card)

        self.add_card_group(layout.render())


class PanelLayoutAccordionExample(MainMenu, CardMixin, TemplateView):
    """Panel layout with an accordion in the sidebar and detail cards in the main area."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_card('acc_panel_companies',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company)

    def setup_table_acc_panel_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'active')

    def setup_cards(self):
        layout = self.add_panel_layout(card_name='accordion_layout', min_height='550px')
        root = layout.root

        sidebar = root.add_region('sidebar', size='350px', min_size=200)
        main_region = root.add_region('main', size='1fr', min_size=300)

        # Accordion in the sidebar
        summary_card = self.add_card(title='Summary')
        summary_card.add_entry(label='Companies', value=Company.objects.count())
        summary_card.add_entry(label='Categories', value=CompanyCategory.objects.count())
        summary_card.add_entry(label='People', value=Person.objects.count())

        companies_card = self.cards['acc_panel_companies']

        notes_card = self.add_card(title='Notes')
        notes_card.add_entry(label='Tip', value='The accordion sits inside a resizable panel.')
        notes_card.add_entry(label='Info', value='Drag the splitter to give it more room.')

        accordion = self.add_accordion_card(
            card_name='sidebar_accordion',
            multi_open=False,
            full_height=True,
            panels=[
                {'title': 'Overview', 'card': summary_card, 'icon': 'fas fa-chart-bar',
                 'expanded': True},
                {'title': 'Companies', 'card': companies_card, 'icon': 'fas fa-building'},
                {'title': 'Notes', 'card': notes_card, 'icon': 'fas fa-sticky-note'},
            ]
        )
        sidebar.add_card(accordion)

        # Main area - detail cards
        right_split = root.add_split(direction='vertical')
        right_split.children.clear()
        right_split.sizes.clear()

        # Actually, just put cards directly in main_region
        company = Company.objects.first()
        if company:
            detail_card = self.add_card(title='Company Detail', details_object=company,
                                        show_created_modified_dates=True)
            detail_card.add_rows('name', 'active', 'importance')
            detail_card.add_entry(field='sectors')
        else:
            detail_card = self.add_card(title='Company Detail')
            detail_card.add_rows({'label': 'Info', 'value': 'No companies in the system'})
        main_region.add_card(detail_card)

        person = Person.objects.first()
        if person:
            person_card = self.add_card(title='Person Detail', details_object=person)
            person_card.add_rows('title', 'first_name', 'surname')
        else:
            person_card = self.add_card(title='Person Detail')
            person_card.add_rows({'label': 'Info', 'value': 'No people in the system'})
        main_region.add_card(person_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutIframeExample(MainMenu, CardMixin, TemplateView):
    """Panel layout with iframe cards — demonstrates embedding interactive content."""
    template_name = 'cards_examples/cards.html'

    THREEJS_DEMO = '''<!DOCTYPE html>
<html>
<head>
<style>body { margin: 0; overflow: hidden; }</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
<script>
var scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);
var camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
var renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

var geometry = new THREE.BoxGeometry();
var material = new THREE.MeshPhongMaterial({ color: 0x3498db });
var cube = new THREE.Mesh(geometry, material);
scene.add(cube);

var edges = new THREE.EdgesGeometry(geometry);
var line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x2c3e50 }));
cube.add(line);

var light = new THREE.DirectionalLight(0xffffff, 0.8);
light.position.set(1, 1, 1);
scene.add(light);
scene.add(new THREE.AmbientLight(0x404040));

camera.position.z = 3;

function animate() {
    requestAnimationFrame(animate);
    cube.rotation.x += 0.01;
    cube.rotation.y += 0.01;
    renderer.render(scene, camera);
}
animate();

window.addEventListener("resize", function() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body>
</html>'''

    CANVAS_DEMO = '''<!DOCTYPE html>
<html>
<head><style>body { margin: 0; overflow: hidden; background: #1a1a2e; }</style></head>
<body>
<canvas id="c"></canvas>
<script>
var c = document.getElementById("c");
var ctx = c.getContext("2d");
c.width = window.innerWidth;
c.height = window.innerHeight;

var particles = [];
for (var i = 0; i < 80; i++) {
    particles.push({
        x: Math.random() * c.width,
        y: Math.random() * c.height,
        vx: (Math.random() - 0.5) * 1.5,
        vy: (Math.random() - 0.5) * 1.5,
        r: Math.random() * 3 + 1
    });
}

function draw() {
    ctx.fillStyle = "rgba(26, 26, 46, 0.15)";
    ctx.fillRect(0, 0, c.width, c.height);
    for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > c.width) p.vx *= -1;
        if (p.y < 0 || p.y > c.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(100, 200, 255, 0.8)";
        ctx.fill();
        for (var j = i + 1; j < particles.length; j++) {
            var q = particles[j];
            var dx = p.x - q.x, dy = p.y - q.y;
            var dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 120) {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(q.x, q.y);
                ctx.strokeStyle = "rgba(100, 200, 255," + (1 - dist / 120) * 0.4 + ")";
                ctx.stroke();
            }
        }
    }
    requestAnimationFrame(draw);
}
draw();

window.addEventListener("resize", function() {
    c.width = window.innerWidth;
    c.height = window.innerHeight;
});
</script>
</body>
</html>'''

    def setup_cards(self):
        layout = self.add_panel_layout(card_name='iframe_layout', min_height='550px')
        root = layout.root

        sidebar = root.add_region('sidebar', size='280px', collapsible=True, min_size=150)
        right = root.add_split(direction='vertical')
        top_region = right.add_region('top', size='1fr', min_size=200)
        bottom_region = right.add_region('bottom', size='1fr', min_size=200)

        # Sidebar with info
        info_card = self.add_card(title='Embedded Content')
        info_card.add_rows(
            {'label': 'Top', 'value': 'Three.js rotating cube'},
            {'label': 'Bottom', 'value': 'Canvas particle network'},
            {'label': 'Tip', 'value': 'Resize panels to see iframes adapt'},
            {'label': 'Note', 'value': 'Uses srcdoc for inline HTML'},
        )
        sidebar.add_card(info_card)

        # Three.js iframe in top panel
        threejs_card = self.add_iframe_card(
            card_name='threejs',
            title='Three.js Demo',
            iframe_srcdoc=self.THREEJS_DEMO,
            iframe_height='100%',
        )
        top_region.add_card(threejs_card)

        # Canvas iframe in bottom panel
        canvas_card = self.add_iframe_card(
            card_name='canvas',
            title='Canvas Particles',
            iframe_srcdoc=self.CANVAS_DEMO,
            iframe_height='100%',
        )
        bottom_region.add_card(canvas_card)

        self.add_card_group(layout.render(), div_css_class='col-12')


class PanelLayoutLinkedDatatablesExample(MainMenu, CardMixin, TemplateView):
    """Linked datatables in a panel layout — each table in its own resizable region."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        layout = self.add_panel_layout(card_name='linked_dt_layout', min_height='550px')
        root = layout.root

        menu_categories = [
            AjaxButtonMenuItem(button_name='add_category', menu_display='',
                               font_awesome='fas fa-plus',
                               css_classes='btn btn-sm btn-outline-success'),
        ]
        menu_companies = [
            AjaxButtonMenuItem(button_name='add_company', menu_display='',
                               font_awesome='fas fa-plus',
                               css_classes='btn btn-sm btn-outline-success'),
        ]
        menu_people = [
            AjaxButtonMenuItem(button_name='add_person', menu_display='',
                               font_awesome='fas fa-plus',
                               css_classes='btn btn-sm btn-outline-success'),
        ]

        cat_region = root.add_region('categories', size='1fr', min_size=200,
                                     title='Categories', menu=menu_categories)
        comp_region = root.add_region('companies', size='1fr', min_size=200,
                                      title='Companies', menu=menu_companies)
        people_region = root.add_region('people', size='1fr', min_size=200,
                                        title='People', menu=menu_people)

        cat_card = self.add_card(
            'pl_categories',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=CompanyCategory,
        )
        cat_region.add_card(cat_card)

        comp_card = self.add_card(
            'pl_companies',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=Company,
        )
        comp_region.add_card(comp_card)

        people_card = self.add_card(
            'pl_people',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=Person,
        )
        people_region.add_card(people_card)

        layout.linked_tables = [
            {'table_id': 'pl_categories'},
            {'table_id': 'pl_companies', 'linked_field': 'company_category_id'},
            {'table_id': 'pl_people', 'linked_field': 'company_id'},
        ]

        self.add_card_group(layout.render(), div_css_class='col-12')

    def button_add_category(self, **kwargs):
        return self.command_response('message', text='Add Category clicked')

    def button_add_company(self, **kwargs):
        return self.command_response('message', text='Add Company clicked')

    def button_add_person(self, **kwargs):
        return self.command_response('message', text='Add Person clicked')

    def setup_table_pl_categories(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')

    def setup_table_pl_companies(self, table, details_object):
        table.ajax_data = False
        table.table_data = []
        table.add_columns('id', 'name', 'importance')

    def setup_table_pl_people(self, table, details_object):
        table.ajax_data = False
        table.table_data = []
        table.add_columns('id', 'first_name', 'surname')


class PanelLayoutTabsExample(MainMenu, CardMixin, TemplateView):
    """Panel layout with tabs inside a region."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        self.add_card('tab_companies',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Company)
        self.add_card('tab_people',
                      group_type=CARD_TYPE_DATATABLE,
                      datatable_model=Person)

    def setup_table_tab_companies(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name', 'active', 'importance')

    def setup_table_tab_people(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'first_name', 'surname')

    def setup_cards(self):
        layout = self.add_panel_layout(card_name='tabs_layout', min_height='550px')
        root = layout.root

        sidebar_toolbar = [
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-plus', css_classes='btn btn-sm btn-outline-success'),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-search', css_classes='btn btn-sm btn-outline-secondary'),
            MenuItem('cards_examples:hello_modal', menu_display='',
                     font_awesome='fas fa-filter', css_classes='btn btn-sm btn-outline-secondary'),
        ]
        sidebar = root.add_region('sidebar', size='280px', collapsible=True, min_size=150,
                                  title='Navigation', toolbar=sidebar_toolbar)

        main_region = root.add_region('main', size='1fr', min_size=300, title='Data')

        # Sidebar content
        nav_card = self.add_card(title='Explorer')
        nav_card.add_rows(
            {'label': 'Section', 'value': 'Companies & People'},
            {'label': 'Records', 'value': f'{Company.objects.count()} companies'},
            {'label': 'Records', 'value': f'{Person.objects.count()} people'},
        )
        sidebar.add_card(nav_card)

        # Add tabs to the main region — each tab can have its own menu
        companies_menu = [
            AjaxButtonMenuItem(button_name='add_company', menu_display='',
                               font_awesome='fas fa-plus',
                               css_classes='btn btn-sm btn-outline-success'),
            AjaxButtonMenuItem(button_name='export_companies', menu_display='',
                               font_awesome='fas fa-download',
                               css_classes='btn btn-sm btn-outline-secondary'),
        ]
        companies_tab = main_region.add_tab('companies', title='Companies',
                                            icon='fas fa-building', active=True,
                                            menu=companies_menu)
        companies_tab.add_card(self.cards['tab_companies'])

        people_menu = [
            AjaxButtonMenuItem(button_name='add_person', menu_display='',
                               font_awesome='fas fa-plus',
                               css_classes='btn btn-sm btn-outline-success'),
        ]
        people_tab = main_region.add_tab('people', title='People',
                                         icon='fas fa-users', menu=people_menu)
        people_tab.add_card(self.cards['tab_people'])

        summary_tab = main_region.add_tab('summary', title='Summary',
                                          icon='fas fa-chart-bar')
        summary_card = self.add_card(title='Summary')
        summary_card.add_rows(
            {'label': 'Total Companies', 'value': str(Company.objects.count())},
            {'label': 'Active Companies', 'value': str(Company.objects.filter(active=True).count())},
            {'label': 'Total People', 'value': str(Person.objects.count())},
            {'label': 'Categories', 'value': str(CompanyCategory.objects.count())},
        )
        summary_tab.add_card(summary_card)

        self.add_card_group(layout.render(), div_css_class='col-12')

    def button_add_company(self, **kwargs):
        return self.command_response('message', text='Add Company clicked')

    def button_export_companies(self, **kwargs):
        return self.command_response('message', text='Export Companies clicked')

    def button_add_person(self, **kwargs):
        return self.command_response('message', text='Add Person clicked')


class PanelLayoutDetailDatatablesExample(MainMenu, CardMixin, TemplateView):
    """3x2 grid: top row has linked datatables, bottom row shows details of the selected row."""
    template_name = 'cards_examples/cards.html'

    ajax_commands = ['datatable', 'row']

    def setup_datatable_cards(self):
        layout = self.add_panel_layout(card_name='detail_dt_layout', min_height='550px',
                                       direction='horizontal', persist=False)
        root = layout.root

        # 3 columns, each a vertical split: datatable on top, collapsible detail below
        col1 = root.add_split(direction='vertical')
        col2 = root.add_split(direction='vertical')
        col3 = root.add_split(direction='vertical')

        cat_region = col1.add_region('categories', size='1fr', min_size=100,
                                     title='Categories')
        cat_detail_region = col1.add_region('cat_detail', size='200px', min_size=50,
                                            collapsible=True, title='Category Detail')

        comp_region = col2.add_region('companies', size='1fr', min_size=100,
                                      title='Companies')
        comp_detail_region = col2.add_region('comp_detail', size='200px', min_size=50,
                                             collapsible=True, collapsed=True,
                                             title='Company Detail')

        people_region = col3.add_region('people', size='1fr', min_size=100,
                                        title='People')
        people_detail_region = col3.add_region('people_detail', size='200px', min_size=50,
                                               collapsible=True, title='Person Detail')

        cat_card = self.add_card(
            'pd_categories',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=CompanyCategory,
        )
        cat_region.add_card(cat_card)

        comp_card = self.add_card(
            'pd_companies',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=Company,
        )
        comp_region.add_card(comp_card)

        people_card = self.add_card(
            'pd_people',
            group_type=CARD_TYPE_DATATABLE,
            datatable_model=Person,
        )
        people_region.add_card(people_card)

        cat_detail = self.add_card('pd_cat_detail')
        cat_detail.add_entry(label='Select a category', value='')
        cat_detail_region.add_card(cat_detail)

        comp_detail = self.add_card('pd_comp_detail')
        comp_detail.add_entry(label='Select a company', value='')
        comp_detail_region.add_card(comp_detail)

        people_detail = self.add_card('pd_people_detail')
        people_detail.add_entry(label='Select a person', value='')
        people_detail_region.add_card(people_detail)

        layout.linked_tables = [
            {'table_id': 'pd_categories', 'detail_card': 'pd_cat_detail',
             'detail_model': 'CompanyCategory'},
            {'table_id': 'pd_companies', 'linked_field': 'company_category_id',
             'detail_card': 'pd_comp_detail', 'detail_model': 'Company'},
            {'table_id': 'pd_people', 'linked_field': 'company_id',
             'detail_card': 'pd_people_detail', 'detail_model': 'Person'},
        ]

        self.add_card_group(layout.render(), div_css_class='col-12')

    def setup_table_pd_categories(self, table, details_object):
        table.ajax_data = True
        table.add_columns('id', 'name')

    def setup_table_pd_companies(self, table, details_object):
        table.ajax_data = False
        table.table_data = []
        table.add_columns('id', 'name', 'importance')

    def setup_table_pd_people(self, table, details_object):
        table.ajax_data = False
        table.table_data = []
        table.add_columns('id', 'first_name', 'surname')

    def button_load_detail(self, **kwargs):
        """AJAX handler to load detail card content for a selected row."""
        detail_card_code = kwargs.get('detail_card')
        model_name = kwargs.get('model')
        row_id = kwargs.get('row_id')

        model_map = {
            'CompanyCategory': CompanyCategory,
            'Company': Company,
            'Person': Person,
        }
        model_cls = model_map.get(model_name)
        if not model_cls or not row_id:
            return self.command_response('null')

        try:
            obj = model_cls.objects.get(pk=row_id)
        except model_cls.DoesNotExist:
            return self.command_response('null')

        rows = []
        if model_name == 'CompanyCategory':
            rows = [
                ('Name', obj.name),
                ('Companies', obj.company_set.count()),
            ]
        elif model_name == 'Company':
            rows = [
                ('Name', obj.name),
                ('Active', 'Yes' if obj.active else 'No'),
                ('Importance', obj.importance),
                ('Number', obj.number or '-'),
                ('People', obj.person_set.count()),
            ]
        elif model_name == 'Person':
            rows = [
                ('Name', f'{obj.first_name} {obj.surname}'),
                ('Title', obj.get_title_display() if obj.title is not None else '-'),
                ('Company', str(obj.company) if obj.company else '-'),
                ('Age', obj.age or '-'),
                ('Active', 'Yes' if obj.is_active else 'No'),
            ]

        html = '<table class="table table-sm table-borderless mb-0">'
        for label, value in rows:
            html += f'<tr><th class="text-muted" style="width:40%;font-size:0.85rem">{label}</th>'
            html += f'<td style="font-size:0.85rem">{value}</td></tr>'
        html += '</table>'

        return self.command_response('html',
                                     selector=f'#{detail_card_code}_body',
                                     html=html)
