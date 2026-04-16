from django.db.models import Count, Sum
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from ajax_helpers.utils import toast_commands
from cards.standard import CardMixin
from cards_examples.models import Company, CompanyCategory, Person, Payment
from cards_examples.views.base import MainMenu


# ---------------------------------------------------------------------------
# Shared data helpers (used by self-dispatch methods and kept Data classes)
# ---------------------------------------------------------------------------

def _treegrid_data_nodes(parent):
    """TreegridData logic: Category -> Company -> Person. Returns a plain list."""
    if parent:
        return _treegrid_data_children(parent)
    return _treegrid_data_root()


def _treegrid_data_root():
    categories = CompanyCategory.objects.annotate(
        company_count=Count('company')
    ).order_by('name')

    tree = []
    for cat in categories:
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {'type': 'category', 'id': cat.id},
            'childCount': cat.company_count,
        })

    uncategorised_count = Company.objects.filter(company_category__isnull=True).count()
    if uncategorised_count:
        tree.append({
            'title': '(Uncategorised)',
            'key': 'category_none',
            'folder': True,
            'lazy': True,
            'data': {'type': 'category', 'id': None},
            'childCount': uncategorised_count,
        })
    return tree


def _treegrid_data_children(parent_key):
    if parent_key.startswith('category_'):
        return _treegrid_data_companies(parent_key)
    elif parent_key.startswith('company_'):
        return _treegrid_data_people(parent_key)
    return []


def _treegrid_data_companies(cat_key):
    if cat_key == 'category_none':
        companies = Company.objects.filter(company_category__isnull=True)
    else:
        try:
            cat_id = int(cat_key.replace('category_', ''))
        except (ValueError, AttributeError):
            return []
        companies = Company.objects.filter(company_category_id=cat_id)

    companies = companies.annotate(
        people_count=Count('person')
    ).order_by('name')

    children = []
    for company in companies:
        children.append({
            'title': company.name,
            'key': f'company_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'company',
                'id': company.id,
                'category': company.company_category.name if company.company_category else '',
                'importance': company.importance or '',
                'people_count': company.people_count,
            },
            'childCount': company.people_count,
        })
    return children


def _treegrid_data_people(company_key):
    try:
        company_id = int(company_key.replace('company_', ''))
    except (ValueError, AttributeError):
        return []

    people = Person.objects.filter(
        company_id=company_id
    ).order_by('surname', 'first_name')

    children = []
    for person in people:
        children.append({
            'title': f'{person.first_name} {person.surname}',
            'key': f'person_{person.id}',
            'folder': False,
            'data': {
                'type': 'person',
                'id': person.id,
                'first_name': person.first_name,
            },
        })
    return children


def _treegrid_multi_data_nodes(parent):
    """TreegridMultiData logic: Category -> Company -> Person -> Payments."""
    if parent:
        return _treegrid_multi_data_children(parent)
    return _treegrid_multi_data_root()


def _treegrid_multi_data_root():
    categories = CompanyCategory.objects.annotate(
        company_count=Count('company')
    ).order_by('name')

    tree = []
    for cat in categories:
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'node_type': 'Category',
                'child_count': cat.company_count,
            },
        })
    return tree


def _treegrid_multi_data_children(parent_key):
    if parent_key.startswith('category_'):
        try:
            cat_id = int(parent_key.replace('category_', ''))
        except (ValueError, AttributeError):
            return []

        companies = Company.objects.filter(
            company_category_id=cat_id
        ).annotate(
            people_count=Count('person')
        ).order_by('name')

        children = []
        for company in companies:
            children.append({
                'title': company.name,
                'key': f'company_{company.id}',
                'folder': True,
                'lazy': True,
                'data': {
                    'type': 'company',
                    'node_type': 'Company',
                    'child_count': company.people_count,
                },
            })
        return children

    elif parent_key.startswith('company_'):
        try:
            company_id = int(parent_key.replace('company_', ''))
        except (ValueError, AttributeError):
            return []

        people = Person.objects.filter(
            company_id=company_id
        ).annotate(
            payment_count=Count('company__payment')
        ).order_by('surname', 'first_name')

        has_payments = Payment.objects.filter(company_id=company_id).exists()
        children = []
        for person in people:
            children.append({
                'title': f'{person.first_name} {person.surname}',
                'key': f'person_{person.id}',
                'folder': has_payments,
                'lazy': has_payments,
                'data': {
                    'type': 'person',
                    'node_type': 'Person',
                    'child_count': '',
                    'age': person.age or '',
                },
            })
        return children

    elif parent_key.startswith('person_'):
        try:
            person_id = int(parent_key.replace('person_', ''))
        except (ValueError, AttributeError):
            return []

        person = Person.objects.filter(id=person_id).first()
        if not person or not person.company_id:
            return []

        payments = Payment.objects.filter(
            company_id=person.company_id
        ).order_by('-date')[:10]

        children = []
        for payment in payments:
            children.append({
                'title': f'Payment #{payment.id}',
                'key': f'payment_{payment.id}',
                'folder': False,
                'data': {
                    'type': 'payment',
                    'node_type': 'Payment',
                    'amount': payment.amount,
                    'date': payment.date.strftime('%Y-%m-%d') if payment.date else '',
                },
            })
        return children

    return []


def _treegrid_compact_data_nodes(parent):
    """TreegridCompactData logic: Company -> People (flat, no categories)."""
    if parent:
        return _treegrid_compact_data_people(parent)
    return _treegrid_compact_data_companies()


def _treegrid_compact_data_companies():
    companies = Company.objects.annotate(
        people_count=Count('person')
    ).filter(people_count__gt=0).order_by('name')

    tree = []
    for company in companies:
        tree.append({
            'title': company.name,
            'key': f'company_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'company',
                'child_count': company.people_count,
            },
            'childCount': company.people_count,
        })
    return tree


def _treegrid_compact_data_people(parent_key):
    try:
        company_id = int(parent_key.replace('company_', ''))
    except (ValueError, AttributeError):
        return []

    title_map = dict(Person.title_choices)
    people = Person.objects.filter(
        company_id=company_id
    ).order_by('surname', 'first_name')

    children = []
    for person in people:
        children.append({
            'title': f'{person.first_name} {person.surname}',
            'key': f'person_{person.id}',
            'folder': False,
            'data': {
                'type': 'person',
                'is_active': 'Yes' if person.is_active else 'No',
                'age': person.age or '',
                'person_title': title_map.get(person.title, ''),
            },
        })
    return children


def _treegrid_payments_data_nodes(parent):
    """TreegridPaymentsData logic: Company -> Payments."""
    if parent:
        return _treegrid_payments_data_payments(parent)
    return _treegrid_payments_data_companies()


def _treegrid_payments_data_companies():
    companies = Company.objects.annotate(
        payment_count=Count('payment'),
        total_amount=Sum('payment__amount'),
    ).filter(payment_count__gt=0).order_by('name')

    tree = []
    for company in companies:
        tree.append({
            'title': company.name,
            'key': f'company_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'company',
                'amount': company.total_amount or 0,
                'quantity': '',
                'date': '',
                'received': '',
                'category': company.company_category.name if company.company_category else '',
            },
            'childCount': company.payment_count,
        })
    return tree


def _treegrid_payments_data_payments(parent_key):
    try:
        company_id = int(parent_key.replace('company_', ''))
    except (ValueError, AttributeError):
        return []

    payments = Payment.objects.filter(
        company_id=company_id
    ).order_by('-date')

    children = []
    for payment in payments:
        children.append({
            'title': f'Payment #{payment.id}',
            'key': f'payment_{payment.id}',
            'folder': False,
            'data': {
                'type': 'payment',
                'amount': payment.amount,
                'quantity': payment.quantity,
                'date': payment.date.strftime('%Y-%m-%d') if payment.date else '',
                'received': 'Yes' if payment.received else 'No',
                'category': '',
            },
        })
    return children


def _treegrid_widgets_data_nodes(parent):
    """TreegridWidgetsData logic: Company -> People with widget-friendly fields."""
    if parent:
        return _treegrid_widgets_data_people(parent)
    return _treegrid_widgets_data_companies()


def _treegrid_widgets_data_companies():
    companies = Company.objects.annotate(
        people_count=Count('person')
    ).filter(people_count__gt=0).order_by('name')[:30]

    tree = []
    for company in companies:
        tree.append({
            'title': company.name,
            'key': f'company_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'company',
                'first_name': '',
                'is_active': '',
                'person_title': '',
                'importance': str(company.importance) if company.importance else '',
                'age': '',
            },
            'childCount': company.people_count,
        })
    return tree


def _treegrid_widgets_data_people(parent_key):
    try:
        company_id = int(parent_key.replace('company_', ''))
    except (ValueError, AttributeError):
        return []

    people = Person.objects.filter(
        company_id=company_id
    ).order_by('surname', 'first_name')

    children = []
    for person in people:
        children.append({
            'title': f'{person.first_name} {person.surname}',
            'key': f'person_{person.id}',
            'folder': False,
            'data': {
                'type': 'person',
                'first_name': person.first_name,
                'is_active': person.is_active,
                'person_title': str(person.title) if person.title is not None else '',
                'importance': '',
                'age': person.age or '',
            },
        })
    return children


def _treegrid_styled_data_nodes(parent):
    """TreegridStyledData logic: Component spec tree with per-cell colours."""
    if parent:
        return _treegrid_styled_data_children(parent)
    return _treegrid_styled_data_root()


def _treegrid_styled_data_root():
    categories = CompanyCategory.objects.annotate(
        company_count=Count('company')
    ).order_by('name')

    row_colours = ['#e8e0f0', '#dce8f0', '#f0ece0', '#e0f0e4', '#f0e0e0', '#e8e8f0']

    tree = []
    for i, cat in enumerate(categories):
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'view': 'Thickness',
                'width_val': 99,
                'thickness': 68,
                'material': '',
                'supply': '',
                'comp_group': '',
                'annotate': f'_pf.{cat.name.lower().replace(" ", "_")}',
                '_row_bg': row_colours[i % len(row_colours)],
                'width_val__color': '#9b1d9b',
                'thickness__color': '#9b1d9b',
                'view__color': '#9b1d9b',
            },
        })
    return tree


def _treegrid_styled_data_children(parent_key):
    try:
        cat_id = int(parent_key.replace('category_', ''))
    except (ValueError, AttributeError):
        return []

    companies = Company.objects.filter(
        company_category_id=cat_id
    ).order_by('name')[:12]

    cat = CompanyCategory.objects.filter(id=cat_id).first()
    cat_name = cat.name if cat else ''

    children = []
    for j, company in enumerate(companies):
        imp = company.importance or 1
        thickness = 60 + (imp * 5)
        width = 90 + (imp * 3)
        is_default = (thickness == 68)

        thickness_bg = '#d4edda' if is_default else '#fff3cd'
        thickness_color = '' if is_default else '#cc0000'
        width_bg = '#d4edda' if width == 99 else '#fff3cd'

        material = f'timber:Frame' if j % 3 != 2 else f'timber:Cill'
        material_bg = '#d4edda' if 'Frame' in material else '#fce4ec'

        children.append({
            'title': company.name,
            'key': f'component_{company.id}',
            'folder': False,
            'data': {
                'type': 'component',
                'view': 'Thickness',
                'width_val': width,
                'thickness': thickness,
                'material': material,
                'supply': True,
                'comp_group': cat_name,
                'annotate': f'_pf.{company.name.lower().replace(" ", "_")[:20]}',
                'thickness__bg': thickness_bg,
                'thickness__color': thickness_color,
                'width_val__bg': width_bg,
                'material__bg': material_bg,
            },
        })
    return children


def _treegrid_full_data_nodes(parent):
    """TreegridFullData logic: Category -> Company -> Person with timestamps."""
    if parent:
        return _treegrid_full_data_children(parent)
    return _treegrid_full_data_root()


def _fmt_dt(dt):
    if not dt:
        return ''
    return dt.strftime('%b %d, %Y, %I:%M %p')


def _treegrid_full_data_root():
    categories = CompanyCategory.objects.annotate(
        company_count=Count('company')
    ).order_by('name')

    tree = []
    for cat in categories:
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'category': '',
                'is_active': '',
                'importance': '',
                'user': '',
                'created': '',
                'modified': '',
            },
        })

    uncategorised = Company.objects.filter(company_category__isnull=True).count()
    if uncategorised:
        tree.append({
            'title': '(Uncategorised)',
            'key': 'category_none',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'category': '',
                'is_active': '',
                'importance': '',
                'user': '',
                'created': '',
                'modified': '',
            },
        })
    return tree


def _treegrid_full_data_children(parent_key):
    if parent_key.startswith('category_'):
        return _treegrid_full_data_companies(parent_key)
    elif parent_key.startswith('company_'):
        return _treegrid_full_data_people(parent_key)
    return []


def _treegrid_full_data_companies(cat_key):
    if cat_key == 'category_none':
        companies = Company.objects.filter(company_category__isnull=True)
    else:
        try:
            cat_id = int(cat_key.replace('category_', ''))
        except (ValueError, AttributeError):
            return []
        companies = Company.objects.filter(company_category_id=cat_id)

    companies = companies.select_related(
        'company_category', 'user_profile'
    ).annotate(people_count=Count('person')).order_by('name')

    children = []
    for company in companies:
        children.append({
            'title': company.name,
            'key': f'company_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'company',
                'category': company.company_category.name if company.company_category else '',
                'is_active': company.active,
                'importance': str(company.importance) if company.importance else '',
                'user': company.user_profile.username if company.user_profile else '',
                'created': _fmt_dt(company.created),
                'modified': _fmt_dt(company.modified),
            },
            'childCount': company.people_count,
        })
    return children


def _treegrid_full_data_people(company_key):
    try:
        company_id = int(company_key.replace('company_', ''))
    except (ValueError, AttributeError):
        return []

    people = Person.objects.filter(
        company_id=company_id
    ).order_by('surname', 'first_name')

    children = []
    for person in people:
        children.append({
            'title': f'{person.first_name} {person.surname}',
            'key': f'person_{person.id}',
            'folder': False,
            'data': {
                'type': 'person',
                'category': '',
                'is_active': person.is_active,
                'importance': '',
                'user': '',
                'created': person.date_entered.strftime('%b %d, %Y') if person.date_entered else '',
                'modified': '',
            },
        })
    return children


def _treegrid_colspan_data_nodes(parent):
    """TreegridColspanData logic: Category -> Group -> Items."""
    if parent:
        return _treegrid_colspan_data_children(parent)
    return _treegrid_colspan_data_root()


def _treegrid_colspan_data_root():
    categories = CompanyCategory.objects.annotate(
        company_count=Count('company')
    ).order_by('name')

    tree = []
    for cat in categories:
        warning = '<i class="fas fa-exclamation-triangle text-warning"></i>' if cat.company_count > 25 else ''
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'status': warning,
                'primary': '',
                'optional': '',
                'ignore': '',
                'group_name': '',
                'category': '',
                'window_type': '',
            },
        })
    return tree


def _treegrid_colspan_data_children(parent_key):
    if parent_key.startswith('category_'):
        return _treegrid_colspan_data_groups(parent_key)
    elif parent_key.startswith('group_'):
        return _treegrid_colspan_data_items(parent_key)
    return []


def _treegrid_colspan_data_groups(cat_key):
    try:
        cat_id = int(cat_key.replace('category_', ''))
    except (ValueError, AttributeError):
        return []

    cat = CompanyCategory.objects.filter(id=cat_id).first()
    cat_name = cat.name if cat else ''

    companies = Company.objects.filter(
        company_category_id=cat_id
    ).annotate(people_count=Count('person')).order_by('name')[:10]

    children = []
    for company in companies:
        warning = '<i class="fas fa-exclamation-triangle text-warning"></i>' if company.importance and company.importance > 2 else ''
        importance_labels = {1: 'Standard', 2: 'Premium', 3: 'High Performance', 4: 'Bespoke'}
        children.append({
            'title': company.name,
            'key': f'group_{company.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'group',
                'status': warning,
                'primary': '',
                'optional': '',
                'ignore': False,
                'group_name': cat_name,
                'category': company.name,
                'window_type': importance_labels.get(company.importance, ''),
            },
            'childCount': company.people_count,
        })
    return children


def _treegrid_colspan_data_items(group_key):
    try:
        company_id = int(group_key.replace('group_', ''))
    except (ValueError, AttributeError):
        return []

    company = Company.objects.filter(id=company_id).select_related('company_category').first()
    if not company:
        return []

    people = Person.objects.filter(
        company_id=company_id
    ).order_by('surname', 'first_name')

    cat_name = company.company_category.name if company.company_category else ''
    children = []
    for person in people:
        children.append({
            'title': f'{cat_name} - {company.name} - {person.first_name} {person.surname}',
            'key': f'item_{person.id}',
            'folder': False,
            'data': {
                'type': 'item',
                'status': '',
                'primary': False,
                'optional': False,
                'ignore': '',
                'group_name': cat_name,
                'category': company.name,
                'window_type': person.get_title_display() if person.title is not None else '',
            },
        })
    return children


def _treegrid_calc_data_nodes(parent):
    """TreegridCalcData logic: Category -> Products with prices."""
    if parent:
        return _treegrid_calc_data_products(parent)
    return _treegrid_calc_data_categories()


def _treegrid_calc_data_categories():
    categories = CompanyCategory.objects.annotate(
        payment_count=Count('company__payment')
    ).filter(payment_count__gt=0).order_by('name')

    tree = []
    for cat in categories:
        tree.append({
            'title': cat.name,
            'key': f'category_{cat.id}',
            'folder': True,
            'lazy': True,
            'data': {
                'type': 'category',
                'price': '',
                'qty': '',
                'discount': '',
                'tax_rate': '',
                'subtotal': '',
                'tax': '',
                'total': '',
            },
        })
    return tree


def _treegrid_calc_data_products(parent_key):
    try:
        cat_id = int(parent_key.replace('category_', ''))
    except (ValueError, AttributeError):
        return []

    payments = Payment.objects.filter(
        company__company_category_id=cat_id
    ).select_related('company').order_by('company__name', '-date')[:15]

    children = []
    for payment in payments:
        price = payment.amount
        qty = payment.quantity
        tax_rate = 20
        subtotal = price * qty
        tax = subtotal * (tax_rate / 100)
        total = subtotal + tax

        if total >= 50000:
            total_bg = '#d4edda'
            total_color = '#28a745'
        elif total >= 10000:
            total_bg = '#fff3cd'
            total_color = '#856404'
        else:
            total_bg = '#f8d7da'
            total_color = '#dc3545'

        children.append({
            'title': f'{payment.company.name} - #{payment.id}',
            'key': f'product_{payment.id}',
            'folder': False,
            'data': {
                'type': 'product',
                'price': f'{price:.2f}',
                'qty': str(qty),
                'discount': '0',
                'tax_rate': '20',
                'subtotal': f'{subtotal:.2f}',
                'tax': f'{tax:.2f}',
                'total': f'{total:.2f}',
                'total__bg': total_bg,
                'total__color': total_color,
            },
        })
    return children


# ---------------------------------------------------------------------------
# Example views
# ---------------------------------------------------------------------------

class TreegridBasicExample(MainMenu, CardMixin, TemplateView):
    """Basic read-only treegrid with no filter bar."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='basic_tree',
            title='Organisation Tree (Basic)',
            treegrid_data_url=reverse('cards_examples:treegrid_data'),
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '60%'},
                {'title': 'Category', 'field': 'category', 'width': '20%'},
                {'title': 'People', 'field': 'people_count', 'width': '20%'},
            ],
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_show_filter=False,
        )
        self.add_card_group('basic_tree', div_css_class='col-12')


class TreegridEditableExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with inline editing enabled."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='editable_tree',
            title='Organisation Tree (Editable)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '40%', 'editable': True},
                {'title': 'Category', 'field': 'category', 'width': '20%'},
                {'title': 'Importance', 'field': 'importance', 'width': '15%'},
                {'title': 'People', 'field': 'people_count', 'width': '10%'},
                {'title': 'First Name', 'field': 'first_name', 'width': '15%', 'editable': True},
            ],
            treegrid_read_only=False,
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            footer='Double-click any highlighted column to edit inline.',
        )
        self.add_card_group('editable_tree', div_css_class='col-12')

    def get_treegrid_editable_tree_data(self, parent=None):
        return _treegrid_data_nodes(parent)

    def button_editable_tree_save(self, **kwargs):
        """Handle inline edit saves from the treegrid."""
        key = kwargs.get('key', '')
        field = kwargs.get('field')
        value = kwargs.get('value')

        if key.startswith('company_'):
            try:
                company = Company.objects.get(id=int(key.replace('company_', '')))
            except (ValueError, Company.DoesNotExist):
                return self.command_response('error', text='Company not found')
            if field == 'title':
                company.name = value
                company.save(update_fields=['name'])
            return self.command_response(toast_commands(header='Saved', text=f'{field} updated'))

        elif key.startswith('person_'):
            try:
                person = Person.objects.get(id=int(key.replace('person_', '')))
            except (ValueError, Person.DoesNotExist):
                return self.command_response('error', text='Person not found')
            if field == 'first_name':
                person.first_name = value
                person.save(update_fields=['first_name'])
            return self.command_response(toast_commands(header='Saved', text=f'{field} updated'))

        return self.command_response('error', text='Unknown node type')


class TreegridMultiLevelExample(MainMenu, CardMixin, TemplateView):
    """Four-level tree: Category -> Company -> Person -> Payments."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='multi_tree',
            title='Four-Level Drilldown',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '40%'},
                {'title': 'Type', 'field': 'node_type', 'width': '15%'},
                {'title': 'Count', 'field': 'child_count', 'width': '15%'},
                {'title': 'Amount', 'field': 'amount', 'width': '15%'},
                {'title': 'Date', 'field': 'date', 'width': '15%'},
            ],
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
                'payment': 'fas fa-money-bill',
            },
            treegrid_height='700px',
        )
        self.add_card_group('multi_tree', div_css_class='col-12')

    def get_treegrid_multi_tree_data(self, parent=None):
        return _treegrid_multi_data_nodes(parent)


class TreegridCompactExample(MainMenu, CardMixin, TemplateView):
    """Compact two-level tree: Company -> People, no filter, short height."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='compact_tree',
            title='Company People (Compact)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Active', 'field': 'is_active', 'width': '15%'},
                {'title': 'Age', 'field': 'age', 'width': '15%'},
                {'title': 'Title', 'field': 'person_title', 'width': '20%'},
            ],
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_show_filter=False,
            treegrid_height='400px',
        )
        self.add_card_group('compact_tree', div_css_class='col-12')

    def get_treegrid_compact_tree_data(self, parent=None):
        return _treegrid_compact_data_nodes(parent)


class TreegridPaymentsExample(MainMenu, CardMixin, TemplateView):
    """Treegrid showing financial data: Company -> Payments with totals."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='payments_tree',
            title='Company Payments',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '35%'},
                {'title': 'Amount', 'field': 'amount', 'width': '15%'},
                {'title': 'Quantity', 'field': 'quantity', 'width': '15%'},
                {'title': 'Date', 'field': 'date', 'width': '15%'},
                {'title': 'Received', 'field': 'received', 'width': '10%'},
                {'title': 'Category', 'field': 'category', 'width': '10%'},
            ],
            treegrid_icon_map={
                'company': 'fas fa-building',
                'payment': 'fas fa-money-bill',
            },
        )
        self.add_card_group('payments_tree', div_css_class='col-12')

    def get_treegrid_payments_tree_data(self, parent=None):
        return _treegrid_payments_data_nodes(parent)


class TreegridExpandedExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with all nodes expanded on load."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='expanded_tree',
            title='Company People (Expanded)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Active', 'field': 'is_active', 'width': '15%'},
                {'title': 'Age', 'field': 'age', 'width': '15%'},
                {'title': 'Title', 'field': 'person_title', 'width': '20%'},
            ],
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_expand_all=True,
        )
        self.add_card_group('expanded_tree', div_css_class='col-12')

    def get_treegrid_expanded_tree_data(self, parent=None):
        return _treegrid_compact_data_nodes(parent)


class TreegridWidgetsExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with checkbox and select widgets. Tree column is read-only."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='widgets_tree',
            title='Person Management (Widgets)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '30%'},
                {'title': 'First Name', 'field': 'first_name', 'width': '15%', 'editable': True},
                {'title': 'Active', 'field': 'is_active', 'width': '10%',
                 'editable': True, 'type': 'checkbox', 'inline': False},
                {'title': 'Title', 'field': 'person_title', 'width': '15%',
                 'editable': True, 'type': 'select', 'inline': False,
                 'options': [
                     {'value': '', 'label': '---'},
                     {'value': '0', 'label': 'Mr'},
                     {'value': '1', 'label': 'Mrs'},
                     {'value': '2', 'label': 'Miss'},
                 ]},
                {'title': 'Importance', 'field': 'importance', 'width': '15%',
                 'editable': True, 'type': 'select', 'inline': False,
                 'options': [
                     {'value': '', 'label': '---'},
                     {'value': '1', 'label': '1 - Low'},
                     {'value': '2', 'label': '2 - Medium'},
                     {'value': '3', 'label': '3 - High'},
                     {'value': '4', 'label': '4 - Critical'},
                 ]},
                {'title': 'Age', 'field': 'age', 'width': '15%'},
            ],
            treegrid_read_only=False,
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            footer='Double-click any cell to edit. '
                   'Changing <strong>Title</strong> updates the Name column. '
                   'Toggling <strong>Active</strong> dims the row. '
                   'Changing <strong>Importance</strong> on a company colours the row.',
        )
        self.add_card_group('widgets_tree', div_css_class='col-12')

    def get_treegrid_widgets_tree_data(self, parent=None):
        return _treegrid_widgets_data_nodes(parent)

    def button_widgets_tree_save(self, **kwargs):
        """Handle saves from the widgets treegrid.

        Demonstrates cross-cell updates:
        - Changing Title updates the Name cell with the title prefix
        - Changing Active dims/undims the row
        - Changing Importance on a company colours the row by severity
        """
        key = kwargs.get('key', '')
        field = kwargs.get('field')
        value = kwargs.get('value')

        if key.startswith('person_'):
            try:
                person = Person.objects.get(id=int(key.replace('person_', '')))
            except (ValueError, Person.DoesNotExist):
                return self.command_response('error', text='Person not found')

            title_map = {0: 'Mr', 1: 'Mrs', 2: 'Miss'}

            if field == 'first_name':
                person.first_name = value
                person.save(update_fields=['first_name'])
                # Update the tree Name column to reflect the new first name
                prefix = title_map.get(person.title, '')
                full_name = f'{prefix} {person.first_name} {person.surname}'.strip()
                self.treegrid_update_cell('widgets_tree', key, 'title', full_name)
                self.treegrid_style_cell('widgets_tree', key, 'first_name',
                                         bg='#d4edda')

            elif field == 'is_active':
                person.is_active = value in (True, 'true', 'True')
                person.save(update_fields=['is_active'])
                if person.is_active:
                    self.treegrid_style_row('widgets_tree', key, bg='', color='')
                else:
                    self.treegrid_style_row('widgets_tree', key,
                                            bg='#f8f8f8', color='#aaa')

            elif field == 'person_title':
                person.title = int(value) if value else None
                person.save(update_fields=['title'])
                # Update the Name cell with the new title prefix
                prefix = title_map.get(person.title, '')
                full_name = f'{prefix} {person.first_name} {person.surname}'.strip()
                self.treegrid_update_cell('widgets_tree', key, 'title', full_name)
                self.treegrid_style_cell('widgets_tree', key, 'title',
                                         bg='#cce5ff')

            self.add_command(toast_commands(header='Saved', text=f'{field} updated'))
            return self.command_response()

        elif key.startswith('company_'):
            try:
                company = Company.objects.get(id=int(key.replace('company_', '')))
            except (ValueError, Company.DoesNotExist):
                return self.command_response('error', text='Company not found')
            if field == 'importance':
                company.importance = int(value) if value else None
                company.save(update_fields=['importance'])
                # Colour the row by severity
                colours = {
                    1: '',
                    2: '#fff9e6',
                    3: '#fff3cd',
                    4: '#f8d7da',
                }
                bg = colours.get(company.importance, '')
                self.treegrid_style_row('widgets_tree', key, bg=bg, color='')
            self.add_command(toast_commands(header='Saved', text=f'{field} updated'))
            return self.command_response()

        return self.command_response('error', text='Unknown node type')


class TreegridStyledExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with per-cell and per-row colours from data."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='styled_tree',
            title='Component Specifications',
            treegrid_columns=[
                {'title': 'Component', 'field': 'title', 'width': '25%'},
                {'title': 'View', 'field': 'view', 'width': '10%'},
                {'title': 'Width', 'field': 'width_val', 'width': '8%'},
                {'title': 'Thickness', 'field': 'thickness', 'width': '8%'},
                {'title': 'Material', 'field': 'material', 'width': '14%'},
                {'title': 'Supply', 'field': 'supply', 'width': '8%', 'type': 'boolean'},
                {'title': 'Group', 'field': 'comp_group', 'width': '12%'},
                {'title': 'Annotate', 'field': 'annotate', 'width': '15%'},
            ],
            treegrid_icon_map={
                'category': 'fas fa-folder text-primary',
                'component': '',
            },
            treegrid_show_filter=False,
        )
        self.add_card_group('styled_tree', div_css_class='col-12')

    def get_treegrid_styled_tree_data(self, parent=None):
        return _treegrid_styled_data_nodes(parent)


class TreegridFullExample(MainMenu, CardMixin, TemplateView):
    """Full-featured treegrid: column filters, action buttons, boolean icons, toolbar."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='full_tree',
            title='Company Directory',
            treegrid_columns=[
                {'title': 'Group / Name', 'field': 'title', 'width': '30%'},
                {'title': 'Category', 'field': 'category', 'width': '12%',
                 'filter': 'select',
                 'filter_options': ['Technology', 'Finance', 'Healthcare',
                                    'Manufacturing', 'Retail', 'Services']},
                {'title': 'Active', 'field': 'is_active', 'type': 'boolean', 'width': '7%'},
                {'title': 'Importance', 'field': 'importance', 'width': '10%',
                 'editable': True, 'type': 'select',
                 'options': [
                     {'value': '', 'label': '---'},
                     {'value': '1', 'label': '1 - Low'},
                     {'value': '2', 'label': '2 - Medium'},
                     {'value': '3', 'label': '3 - High'},
                     {'value': '4', 'label': '4 - Critical'},
                 ]},
                {'title': 'User', 'field': 'user', 'width': '10%'},
                {'title': 'Created', 'field': 'created', 'width': '12%'},
                {'title': 'Modified', 'field': 'modified', 'width': '12%'},
                {'title': '', 'field': '', 'width': '7%', 'type': 'actions',
                 'actions': [
                     {'name': 'edit', 'icon': 'fas fa-pencil-alt', 'title': 'Edit'},
                     {'name': 'info', 'icon': 'fas fa-info-circle', 'title': 'Info'},
                 ]},
            ],
            treegrid_read_only=False,
            treegrid_show_column_filters=True,
            treegrid_show_filter=False,
            treegrid_icon_map={
                'category': 'fas fa-folder text-warning',
                'company': 'far fa-building',
                'person': 'fas fa-user text-muted',
            },
            treegrid_toolbar=[
                {'name': 'new_group', 'label': 'New Group', 'icon': 'fas fa-folder-plus'},
                {'name': 'new_company', 'label': 'New Company', 'icon': 'fas fa-plus'},
            ],
        )
        self.add_card_group('full_tree', div_css_class='col-12')

    def get_treegrid_full_tree_data(self, parent=None):
        return _treegrid_full_data_nodes(parent)

    def button_full_tree_save(self, **kwargs):
        key = kwargs.get('key', '')
        field = kwargs.get('field')
        value = kwargs.get('value')
        if key.startswith('company_'):
            try:
                company = Company.objects.get(id=int(key.replace('company_', '')))
            except (ValueError, Company.DoesNotExist):
                return self.command_response('error', text='Company not found')
            if field == 'importance':
                company.importance = int(value) if value else None
                company.save(update_fields=['importance'])
            return self.command_response()
        return self.command_response('error', text='Unknown node type')

    def button_full_tree_action(self, **kwargs):
        action = kwargs.get('action')
        key = kwargs.get('key', '')
        return self.command_response(toast_commands(header=f'Action: {action}', text=f'Node: {key}'))

    def button_full_tree_new_group(self, **kwargs):
        return self.command_response(toast_commands(header='New Group', text='New group dialog would open here'))

    def button_full_tree_new_company(self, **kwargs):
        return self.command_response(toast_commands(header='New Company', text='New company dialog would open here'))


class TreegridBatchExample(MainMenu, CardMixin, TemplateView):
    """Same as Widgets example but with batch save mode."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='batch_tree',
            title='Person Management (Batch Save)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '30%'},
                {'title': 'First Name', 'field': 'first_name', 'width': '15%', 'editable': True},
                {'title': 'Active', 'field': 'is_active', 'width': '10%',
                 'editable': True, 'type': 'checkbox', 'inline': False},
                {'title': 'Title', 'field': 'person_title', 'width': '15%',
                 'editable': True, 'type': 'select', 'inline': False,
                 'options': [
                     {'value': '', 'label': '---'},
                     {'value': '0', 'label': 'Mr'},
                     {'value': '1', 'label': 'Mrs'},
                     {'value': '2', 'label': 'Miss'},
                 ]},
                {'title': 'Age', 'field': 'age', 'width': '15%'},
            ],
            treegrid_read_only=False,
            treegrid_save_mode='batch',
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            footer='Changes are collected locally. Click <strong>Save</strong> to send them all at once, '
                   'or <strong>Discard</strong> to reload.',
        )
        self.add_card_group('batch_tree', div_css_class='col-12')

    def get_treegrid_batch_tree_data(self, parent=None):
        return _treegrid_widgets_data_nodes(parent)

    def button_batch_tree_batch_save(self, **kwargs):
        import json
        changes = json.loads(kwargs.get('changes', '[]'))
        count = len(changes)
        # Show details of what was received
        details = '<br>'.join(
            f'<strong>{c["key"]}</strong>.{c["field"]} = {c["value"]}'
            for c in changes
        ) if changes else 'No changes received'
        return self.command_response(toast_commands(header=f'Saved {count} change{"s" if count != 1 else ""}', text=details))


class TreegridColspanExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with multi-row headers (colspan/rowspan) and conditional checkboxes."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='colspan_tree',
            title='Product Selections',
            treegrid_columns=[
                {'title': 'Status', 'field': 'status', 'width': '5%', 'type': 'html'},
                {'title': 'Primary', 'field': 'primary', 'width': '7%',
                 'editable': True, 'type': 'checkbox', 'visible_for': ['item']},
                {'title': 'Optional', 'field': 'optional', 'width': '7%',
                 'editable': True, 'type': 'checkbox', 'visible_for': ['item']},
                {'title': 'Ignore', 'field': 'ignore', 'width': '7%',
                 'editable': True, 'type': 'checkbox', 'visible_for': ['group']},
                {'title': 'Subitem Type / Style Name', 'field': 'title', 'width': '34%'},
                {'title': 'Group', 'field': 'group_name', 'width': '15%'},
                {'title': 'Category', 'field': 'category', 'width': '15%'},
                {'title': 'Window Type', 'field': 'window_type', 'width': '10%'},
            ],
            treegrid_header_rows=[
                [
                    {'title': 'Status', 'rowspan': 2},
                    {'title': 'Selections', 'colspan': 3, 'css_class': 'text-center'},
                    {'title': 'Subitem Type / Style Name', 'rowspan': 2},
                    {'title': 'Group', 'rowspan': 2},
                    {'title': 'Option Values', 'colspan': 2, 'css_class': 'text-center'},
                ],
                [
                    {'title': 'Primary'},
                    {'title': 'Optional'},
                    {'title': 'Ignore'},
                    {'title': 'Category'},
                    {'title': 'Window Type'},
                ],
            ],
            treegrid_read_only=False,
            treegrid_show_filter=False,
            treegrid_node_column=4,
            treegrid_save_mode='batch',
            treegrid_icon_map={
                'category': 'fas fa-folder text-warning',
                'group': 'far fa-square text-primary',
                'item': '',
                'warning': 'fas fa-exclamation-triangle text-warning',
            },
        )
        self.add_card_group('colspan_tree', div_css_class='col-12')

    def get_treegrid_colspan_tree_data(self, parent=None):
        return _treegrid_colspan_data_nodes(parent)

    def button_colspan_tree_batch_save(self, **kwargs):
        import json
        changes = json.loads(kwargs.get('changes', '[]'))
        count = len(changes)
        details = '<br>'.join(
            f'<strong>{c["key"]}</strong>.{c["field"]} = {c["value"]}'
            for c in changes
        ) if changes else 'No changes received'
        return self.command_response(toast_commands(header=f'Saved {count} change{"s" if count != 1 else ""}', text=details))


class TreegridCalculatorExample(MainMenu, CardMixin, TemplateView):
    """Calculator treegrid: edit Price/Qty/Discount, server computes Total and colours it."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='calc_tree',
            title='Order Calculator',
            treegrid_columns=[
                {'title': 'Item', 'field': 'title', 'width': '25%'},
                {'title': 'Unit Price', 'field': 'price', 'width': '12%',
                 'editable': True, 'inline': False},
                {'title': 'Quantity', 'field': 'qty', 'width': '10%',
                 'editable': True, 'inline': False},
                {'title': 'Discount %', 'field': 'discount', 'width': '10%',
                 'editable': True, 'inline': False},
                {'title': 'Tax %', 'field': 'tax_rate', 'width': '10%',
                 'editable': True, 'type': 'select', 'inline': False,
                 'options': [
                     {'value': '0', 'label': '0%'},
                     {'value': '5', 'label': '5%'},
                     {'value': '10', 'label': '10%'},
                     {'value': '20', 'label': '20%'},
                 ]},
                {'title': 'Subtotal', 'field': 'subtotal', 'width': '11%'},
                {'title': 'Tax', 'field': 'tax', 'width': '10%'},
                {'title': 'Total', 'field': 'total', 'width': '12%'},
            ],
            treegrid_read_only=False,
            treegrid_show_filter=False,
            treegrid_icon_map={
                'category': 'fas fa-folder text-primary',
                'product': 'fas fa-box',
            },
            footer='Double-click <strong>Price</strong>, <strong>Quantity</strong>, '
                   '<strong>Discount</strong>, or <strong>Tax</strong> to edit. '
                   'The server recalculates and colours the Total: '
                   '<span style="color:#28a745">green</span> &ge; &pound;50k, '
                   '<span style="color:#856404">amber</span> &pound;10k&ndash;50k, '
                   '<span style="color:#dc3545">red</span> &lt; &pound;10k.',
        )
        self.add_card_group('calc_tree', div_css_class='col-12')

    def get_treegrid_calc_tree_data(self, parent=None):
        return _treegrid_calc_data_nodes(parent)

    def button_calc_tree_save(self, **kwargs):
        key = kwargs.get('key', '')
        field = kwargs.get('field')
        value = kwargs.get('value')

        if not key.startswith('product_'):
            return self.command_response()

        # All current row values are sent as row_* keys
        price = float(kwargs.get('row_price', 0))
        qty = int(float(kwargs.get('row_qty', 0)))
        discount = float(kwargs.get('row_discount', 0))
        tax_rate = float(kwargs.get('row_tax_rate', 20))

        # Apply the just-changed value (overrides the row_ value)
        if field == 'price':
            price = float(value) if value else 0
        elif field == 'qty':
            qty = int(float(value)) if value else 0
        elif field == 'discount':
            discount = float(value) if value else 0
        elif field == 'tax_rate':
            tax_rate = float(value) if value else 0

        # Calculate
        subtotal = price * qty
        discount_amount = subtotal * (discount / 100)
        after_discount = subtotal - discount_amount
        tax = after_discount * (tax_rate / 100)
        total = after_discount + tax

        # Update all cells with recalculated values
        self.treegrid_update_cell('calc_tree', key, 'price', f'{price:.2f}')
        self.treegrid_update_cell('calc_tree', key, 'qty', str(qty))
        self.treegrid_update_cell('calc_tree', key, 'discount', str(int(discount)))
        self.treegrid_update_cell('calc_tree', key, 'subtotal', f'{subtotal:.2f}')
        self.treegrid_update_cell('calc_tree', key, 'tax', f'{tax:.2f}')
        self.treegrid_update_cell('calc_tree', key, 'total', f'{total:.2f}')

        # Colour the total: green >= 50k, amber 10k-50k, red < 10k
        if total >= 50000:
            self.treegrid_style_cell('calc_tree', key, 'total',
                                     bg='#d4edda', color='#28a745')
        elif total >= 10000:
            self.treegrid_style_cell('calc_tree', key, 'total',
                                     bg='#fff3cd', color='#856404')
        else:
            self.treegrid_style_cell('calc_tree', key, 'total',
                                     bg='#f8d7da', color='#dc3545')

        # Highlight discount if applied
        if discount > 0:
            self.treegrid_style_cell('calc_tree', key, 'discount',
                                     bg='#fff3cd', color='#856404')
            self.treegrid_style_cell('calc_tree', key, 'subtotal',
                                     bg='#fff3cd', color='#856404')
        else:
            self.treegrid_style_cell('calc_tree', key, 'discount', bg='', color='')
            self.treegrid_style_cell('calc_tree', key, 'subtotal', bg='', color='')

        self.add_command(toast_commands(
            header='Recalculated',
            text=f'{price:.2f} x {qty} - {discount}% + {tax_rate}% tax = <strong>{total:.2f}</strong>'
        ))
        return self.command_response()


class TreegridSelfDispatchExample(MainMenu, CardMixin, TemplateView):
    """Treegrid using self-dispatch: data comes from a method on this view, no separate URL."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='self_tree',
            title='Company Tree (Self-Dispatch)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Category', 'field': 'category', 'width': '25%'},
                {'title': 'People', 'field': 'people_count', 'width': '25%'},
            ],
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_show_filter=False,
            footer='Data loaded via self-dispatch (no separate URL). '
                   'The view\'s <code>get_treegrid_self_tree_data()</code> method provides the data.',
        )
        self.add_card_group('self_tree', div_css_class='col-12')

    def get_treegrid_self_tree_data(self, parent=None):
        """Called automatically by CardMixin.post() when treegrid requests data."""
        if parent:
            return self._get_children(parent)
        return self._get_root_nodes()

    def _get_root_nodes(self):
        categories = CompanyCategory.objects.annotate(
            company_count=Count('company')
        ).order_by('name')
        return [
            {
                'title': cat.name,
                'key': f'category_{cat.id}',
                'folder': True,
                'lazy': True,
                'data': {'type': 'category', 'category': '', 'people_count': ''},
            }
            for cat in categories
        ]

    def _get_children(self, parent_key):
        if parent_key.startswith('category_'):
            try:
                cat_id = int(parent_key.replace('category_', ''))
            except (ValueError, AttributeError):
                return []
            companies = Company.objects.filter(
                company_category_id=cat_id
            ).select_related('company_category').annotate(
                people_count=Count('person')
            ).order_by('name')
            return [
                {
                    'title': c.name,
                    'key': f'company_{c.id}',
                    'folder': True,
                    'lazy': True,
                    'data': {
                        'type': 'company',
                        'category': c.company_category.name if c.company_category else '',
                        'people_count': c.people_count,
                    },
                }
                for c in companies
            ]
        elif parent_key.startswith('company_'):
            try:
                company_id = int(parent_key.replace('company_', ''))
            except (ValueError, AttributeError):
                return []
            people = Person.objects.filter(
                company_id=company_id
            ).order_by('surname', 'first_name')
            return [
                {
                    'title': f'{p.first_name} {p.surname}',
                    'key': f'person_{p.id}',
                    'folder': False,
                    'data': {'type': 'person', 'category': '', 'people_count': ''},
                }
                for p in people
            ]
        return []


class TreegridSelectExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with row selection checkboxes and Select All toggle."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='select_tree',
            title='Select Companies',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '35%'},
                {'title': 'Category', 'field': 'category', 'width': '20%'},
                {'title': 'Importance', 'field': 'importance', 'width': '15%'},
                {'title': 'People', 'field': 'people_count', 'width': '15%'},
                {'title': 'Active', 'field': 'is_active', 'width': '15%', 'type': 'boolean'},
            ],
            treegrid_checkbox=True,
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_show_filter=True,
            footer='Tick rows to select them. Use <strong>Select All</strong> / '
                   '<strong>Deselect All</strong> to toggle. '
                   'Click <strong>Submit Selected</strong> to post the selected keys back.',
        )
        self.add_card_group('select_tree', div_css_class='col-12')

    def get_treegrid_select_tree_data(self, parent=None):
        if parent:
            return self._get_children(parent)
        return self._get_root()

    def _get_root(self):
        categories = CompanyCategory.objects.annotate(
            company_count=Count('company')
        ).order_by('name')
        return [
            {
                'title': cat.name,
                'key': f'category_{cat.id}',
                'folder': True,
                'lazy': True,
                'data': {
                    'type': 'category',
                    'category': '',
                    'importance': '',
                    'people_count': cat.company_count,
                    'is_active': '',
                },
            }
            for cat in categories
        ]

    def _get_children(self, parent_key):
        if parent_key.startswith('category_'):
            try:
                cat_id = int(parent_key.replace('category_', ''))
            except (ValueError, AttributeError):
                return []
            companies = Company.objects.filter(
                company_category_id=cat_id
            ).select_related('company_category').annotate(
                people_count=Count('person')
            ).order_by('name')
            return [
                {
                    'title': c.name,
                    'key': f'company_{c.id}',
                    'folder': True,
                    'lazy': True,
                    'data': {
                        'type': 'company',
                        'category': c.company_category.name if c.company_category else '',
                        'importance': c.importance or '',
                        'people_count': c.people_count,
                        'is_active': c.active,
                    },
                }
                for c in companies
            ]
        elif parent_key.startswith('company_'):
            try:
                company_id = int(parent_key.replace('company_', ''))
            except (ValueError, AttributeError):
                return []
            people = Person.objects.filter(
                company_id=company_id
            ).order_by('surname', 'first_name')
            return [
                {
                    'title': f'{p.first_name} {p.surname}',
                    'key': f'person_{p.id}',
                    'folder': False,
                    'data': {
                        'type': 'person',
                        'category': '',
                        'importance': '',
                        'people_count': '',
                        'is_active': p.is_active,
                    },
                }
                for p in people
            ]
        return []

    def button_select_tree_selected(self, **kwargs):
        import json
        keys = json.loads(kwargs.get('selected_keys', '[]'))
        count = len(keys)
        details = ', '.join(keys[:10])
        if count > 10:
            details += f' ... and {count - 10} more'
        self.add_command(toast_commands(
            header=f'{count} item{"s" if count != 1 else ""} selected',
            text=details))
        return self.command_response()


class TreegridAdvancedExample(MainMenu, CardMixin, TemplateView):
    """Context menu with MenuItems, resizable columns, and dynamic add/remove nodes."""
    template_name = 'cards_examples/cards.html'

    _node_counter = 0

    def setup_cards(self):
        from django_menus.menu import MenuItem, DividerItem

        self.add_treegrid_card(
            card_name='adv_tree',
            title='Advanced Features',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '40%'},
                {'title': 'Category', 'field': 'category', 'width': '20%'},
                {'title': 'People', 'field': 'people_count', 'width': '20%'},
                {'title': 'Active', 'field': 'is_active', 'width': '20%', 'type': 'boolean'},
            ],
            treegrid_icon_map={
                'category': 'fas fa-layer-group',
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_context_menu=[
                MenuItem(url='/?node=__node_key__', menu_display='View Details',
                         font_awesome='fas fa-external-link-alt', link_type=MenuItem.HREF),
                MenuItem(url='cards_examples:hello_modal', menu_display='Hello Modal',
                         font_awesome='fas fa-comment', link_type=MenuItem.AJAX_GET_URL_NAME),
                DividerItem(),
                {'name': 'add_child', 'label': 'Add Child', 'icon': 'fas fa-plus'},
                {'name': 'add_sibling', 'label': 'Add Sibling', 'icon': 'fas fa-plus-circle'},
                DividerItem(),
                {'name': 'delete', 'label': 'Delete', 'icon': 'fas fa-trash text-danger'},
            ],
            treegrid_resizable=True,
            treegrid_toolbar=[
                {'name': 'add_root', 'label': 'Add Root Node', 'icon': 'fas fa-plus'},
            ],
            treegrid_show_filter=True,
            footer='Right-click a row for context menu (uses MenuItems for Home and Hello Modal, '
                   'dicts for Add/Delete). Drag column borders to resize.',
        )
        self.add_card_group('adv_tree', div_css_class='col-12')

    def get_treegrid_adv_tree_data(self, parent=None):
        if parent:
            return self._get_children(parent)
        return self._get_root()

    def _get_root(self):
        categories = CompanyCategory.objects.annotate(
            company_count=Count('company')
        ).order_by('name')
        return [
            {
                'title': cat.name,
                'key': f'category_{cat.id}',
                'folder': True,
                'lazy': True,
                'data': {
                    'type': 'category', 'category': '',
                    'people_count': cat.company_count, 'is_active': '',
                },
            }
            for cat in categories
        ]

    def _get_children(self, parent_key):
        if parent_key.startswith('category_'):
            try:
                cat_id = int(parent_key.replace('category_', ''))
            except (ValueError, AttributeError):
                return []
            companies = Company.objects.filter(
                company_category_id=cat_id
            ).select_related('company_category').annotate(
                people_count=Count('person')
            ).order_by('name')[:15]
            return [
                {
                    'title': c.name,
                    'key': f'company_{c.id}',
                    'folder': False,
                    'data': {
                        'type': 'company',
                        'category': c.company_category.name if c.company_category else '',
                        'people_count': c.people_count,
                        'is_active': c.active,
                    },
                }
                for c in companies
            ]
        return []

    def button_adv_tree_context(self, **kwargs):
        import random
        key = kwargs.get('key', '')
        action = kwargs.get('action', '')

        if action == 'delete':
            self.treegrid_remove_node('adv_tree', key)
            self.add_command(toast_commands(
                header='Deleted', text=f'Removed node {key}'))

        elif action == 'add_child':
            new_key = f'new_{random.randint(1000, 9999)}'
            self.treegrid_add_node('adv_tree', parent_key=key, node_data={
                'title': f'New Child ({new_key})',
                'key': new_key,
                'folder': False,
                'data': {
                    'type': 'company', 'category': 'New',
                    'people_count': 0, 'is_active': True,
                },
            })
            self.treegrid_style_row('adv_tree', new_key, bg='#d4edda')
            self.add_command(toast_commands(
                header='Added', text=f'New child under {key}'))

        elif action == 'add_sibling':
            new_key = f'new_{random.randint(1000, 9999)}'
            self.treegrid_add_node('adv_tree', parent_key=key, mode='after', node_data={
                'title': f'New Sibling ({new_key})',
                'key': new_key,
                'folder': False,
                'data': {
                    'type': 'company', 'category': 'New',
                    'people_count': 0, 'is_active': True,
                },
            })
            self.treegrid_style_row('adv_tree', new_key, bg='#cce5ff')
            self.add_command(toast_commands(
                header='Added', text=f'New sibling after {key}'))

        return self.command_response()

    def button_adv_tree_add_root(self, **kwargs):
        import random
        new_key = f'root_{random.randint(1000, 9999)}'
        self.treegrid_add_node('adv_tree', parent_key=None, node_data={
            'title': f'New Root ({new_key})',
            'key': new_key,
            'folder': True,
            'data': {
                'type': 'category', 'category': '',
                'people_count': 0, 'is_active': '',
            },
        })
        self.treegrid_style_row('adv_tree', new_key, bg='#d4edda')
        self.add_command(toast_commands(
            header='Added', text='New root node'))
        return self.command_response()


class TreegridStaticExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with static inline data - no AJAX at all."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        # Build data inline in Python
        data = [
            {
                'title': 'Fruits',
                'key': 'fruits',
                'folder': True,
                'children': [
                    {'title': 'Apple', 'key': 'apple', 'data': {'type': 'item', 'price': '1.20', 'stock': '150', 'origin': 'UK'}},
                    {'title': 'Banana', 'key': 'banana', 'data': {'type': 'item', 'price': '0.80', 'stock': '200', 'origin': 'Ecuador'}},
                    {'title': 'Cherry', 'key': 'cherry', 'data': {'type': 'item', 'price': '3.50', 'stock': '45', 'stock__color': '#dc3545', 'origin': 'Turkey'}},
                    {'title': 'Mango', 'key': 'mango', 'data': {'type': 'item', 'price': '2.00', 'stock': '80', 'origin': 'India'}},
                ],
                'data': {'type': 'group', 'price': '', 'stock': '', 'origin': ''},
            },
            {
                'title': 'Vegetables',
                'key': 'veg',
                'folder': True,
                'children': [
                    {'title': 'Carrot', 'key': 'carrot', 'data': {'type': 'item', 'price': '0.60', 'stock': '300', 'origin': 'UK'}},
                    {'title': 'Broccoli', 'key': 'broccoli', 'data': {'type': 'item', 'price': '1.10', 'stock': '90', 'origin': 'Spain'}},
                    {'title': 'Pepper', 'key': 'pepper', 'data': {'type': 'item', 'price': '1.50', 'stock': '12', 'stock__bg': '#f8d7da', 'stock__color': '#dc3545', 'origin': 'Netherlands'}},
                ],
                'data': {'type': 'group', 'price': '', 'stock': '', 'origin': ''},
            },
            {
                'title': 'Dairy',
                'key': 'dairy',
                'folder': True,
                'children': [
                    {'title': 'Milk', 'key': 'milk', 'data': {'type': 'item', 'price': '1.00', 'stock': '500', 'origin': 'UK'}},
                    {'title': 'Cheese', 'key': 'cheese', 'data': {'type': 'item', 'price': '4.50', 'stock': '60', 'origin': 'France'}},
                    {'title': 'Butter', 'key': 'butter', 'data': {'type': 'item', 'price': '2.20', 'stock': '110', 'origin': 'Denmark'}},
                ],
                'data': {'type': 'group', 'price': '', 'stock': '', 'origin': ''},
            },
        ]

        self.add_treegrid_card(
            card_name='static_tree',
            title='Product Catalogue (Static Data)',
            treegrid_static_data=data,
            treegrid_columns=[
                {'title': 'Product', 'field': 'title', 'width': '35%'},
                {'title': 'Price', 'field': 'price', 'width': '15%'},
                {'title': 'Stock', 'field': 'stock', 'width': '15%'},
                {'title': 'Origin', 'field': 'origin', 'width': '20%'},
            ],
            treegrid_icon_map={
                'group': 'fas fa-folder text-warning',
                'item': 'fas fa-box',
            },
            treegrid_expand_all=True,
            treegrid_show_filter=False,
            footer='Data is embedded directly in the page. No AJAX calls. '
                   'Cherry has low stock (red text), Pepper has critical stock (red cell).',
        )
        self.add_card_group('static_tree', div_css_class='col-12')


class TreegridDualExample(MainMenu, CardMixin, TemplateView):
    """Two treegrids on the same page, each with independent editing and save."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        # First treegrid: companies with inline editing
        self.add_treegrid_card(
            card_name='left_tree',
            title='Companies',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Active', 'field': 'is_active', 'width': '20%',
                 'editable': True, 'type': 'checkbox', 'inline': False},
                {'title': 'Age', 'field': 'age', 'width': '15%'},
                {'title': 'Title', 'field': 'person_title', 'width': '15%'},
            ],
            treegrid_read_only=False,
            treegrid_save_mode='batch',
            treegrid_height='400px',
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
        )

        # Second treegrid: payments with calculator
        self.add_treegrid_card(
            card_name='right_tree',
            title='Payments',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '30%'},
                {'title': 'Amount', 'field': 'amount', 'width': '15%',
                 'editable': True, 'inline': False},
                {'title': 'Quantity', 'field': 'quantity', 'width': '15%'},
                {'title': 'Date', 'field': 'date', 'width': '15%'},
                {'title': 'Received', 'field': 'received', 'width': '10%',
                 'type': 'boolean'},
                {'title': 'Category', 'field': 'category', 'width': '15%'},
            ],
            treegrid_read_only=False,
            treegrid_height='400px',
            treegrid_icon_map={
                'company': 'fas fa-building',
                'payment': 'fas fa-money-bill',
            },
        )

        self.add_card_group('left_tree', div_css_class='col-6 float-left')
        self.add_card_group('right_tree', div_css_class='col-6 float-left')

    def get_treegrid_left_tree_data(self, parent=None):
        return _treegrid_compact_data_nodes(parent)

    def get_treegrid_right_tree_data(self, parent=None):
        return _treegrid_payments_data_nodes(parent)

    def button_left_tree_batch_save(self, **kwargs):
        import json
        changes = json.loads(kwargs.get('changes', '[]'))
        details = '<br>'.join(
            f'<strong>{c["key"]}</strong>.{c["field"]} = {c["value"]}'
            for c in changes
        )
        self.add_command(toast_commands(
            header=f'Left tree: {len(changes)} saved', text=details))
        return self.command_response()

    def button_right_tree_save(self, **kwargs):
        key = kwargs.get('key', '')
        field = kwargs.get('field')
        value = kwargs.get('value')
        self.add_command(toast_commands(
            header='Right tree saved',
            text=f'{key}.{field} = {value}'))
        return self.command_response()


class TreegridPaginationExample(MainMenu, CardMixin, TemplateView):
    """Treegrid with client-side pagination. All root nodes load once, paged in the browser."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='paginated_tree',
            title='Company Tree (Paginated)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Category', 'field': 'category', 'width': '25%'},
                {'title': 'People', 'field': 'people_count', 'width': '25%'},
            ],
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_checkbox=True,
            treegrid_pagination=True,
            treegrid_page_size=5,
            column_search=True,
            footer='All root nodes load in one request; the browser pages through them. '
                   'Children still lazy-load normally.',
        )
        self.add_card_group('paginated_tree', div_css_class='col-12')

    def get_treegrid_paginated_tree_data(self, parent=None):
        if parent is not None:
            return self._get_people(parent)
        companies = (
            Company.objects.annotate(people_count=Count('person'))
            .filter(people_count__gt=0)
            .select_related('company_category')
            .order_by('name')
        )
        return self._companies_to_nodes(companies)

    @staticmethod
    def _companies_to_nodes(companies):
        return [
            {
                'title': company.name,
                'key': f'company_{company.id}',
                'folder': company.people_count > 0,
                'lazy': company.people_count > 0,
                'data': {
                    'type': 'company',
                    'category': company.company_category.name if company.company_category else '',
                    'people_count': company.people_count,
                },
            }
            for company in companies
        ]

    @staticmethod
    def _get_people(parent_key):
        try:
            company_id = int(parent_key.replace('company_', ''))
        except (ValueError, AttributeError):
            return []
        people = Person.objects.filter(
            company_id=company_id
        ).order_by('surname', 'first_name')
        return [
            {
                'title': f'{p.first_name} {p.surname}',
                'key': f'person_{p.id}',
                'folder': False,
                'data': {'type': 'person', 'category': '', 'people_count': ''},
            }
            for p in people
        ]


    def button_paginated_tree_selected(self, **kwargs):
        import json
        keys = json.loads(kwargs.get('selected_keys', '[]'))
        count = len(keys)
        details = ', '.join(keys[:10])
        if count > 10:
            details += f' ... and {count - 10} more'
        self.add_command(toast_commands(
            header=f'{count} item{"s" if count != 1 else ""} selected',
            text=details))
        return self.command_response()


class ColumnSearchTreegridExample(MainMenu, CardMixin, TemplateView):
    """Treegrid demonstrating per-column header search (non-paginated)."""
    template_name = 'cards_examples/cards.html'

    def setup_cards(self):
        self.add_treegrid_card(
            card_name='col_search_tree',
            title='Company Tree (Column Search)',
            treegrid_columns=[
                {'title': 'Name', 'field': 'title', 'width': '50%'},
                {'title': 'Category', 'field': 'category', 'width': '30%'},
                {'title': 'People', 'field': 'people_count', 'width': '20%'},
            ],
            treegrid_icon_map={
                'company': 'fas fa-building',
                'person': 'fas fa-user',
            },
            treegrid_expand_all=True,
            column_search=True,
        )
        self.add_card_group('col_search_tree', div_css_class='col-12')

    def get_treegrid_col_search_tree_data(self, parent=None):
        if parent is not None:
            try:
                company_id = int(parent.replace('company_', ''))
            except (ValueError, AttributeError):
                return []
            people = Person.objects.filter(company_id=company_id).order_by('surname', 'first_name')
            return [
                {
                    'title': f'{p.first_name} {p.surname}',
                    'key': f'person_{p.id}',
                    'folder': False,
                    'data': {'type': 'person', 'category': '', 'people_count': ''},
                }
                for p in people
            ]
        companies = (
            Company.objects.annotate(people_count=Count('person'))
            .filter(people_count__gt=0)
            .select_related('company_category')
            .order_by('name')
        )
        return [
            {
                'title': company.name,
                'key': f'company_{company.id}',
                'folder': True,
                'lazy': True,
                'data': {
                    'type': 'company',
                    'category': company.company_category.name if company.company_category else '',
                    'people_count': company.people_count,
                },
            }
            for company in companies
        ]


# Keep the original example for backwards compatibility
class TreegridExample(TreegridEditableExample):
    pass


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

class TreegridData(View):
    """Three-level hierarchy: Category -> Company -> Person."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_data_nodes(parent_key), safe=False)


class TreegridMultiData(View):
    """Four-level hierarchy: Category -> Company -> Person -> Payments."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_multi_data_nodes(parent_key), safe=False)


class TreegridCompactData(View):
    """Two-level hierarchy: Company -> People (flat, no categories)."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_compact_data_nodes(parent_key), safe=False)


class TreegridPaymentsData(View):
    """Two-level hierarchy: Company -> Payments."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_payments_data_nodes(parent_key), safe=False)


class TreegridWidgetsData(View):
    """Two-level hierarchy: Company -> People with widget-friendly fields."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_widgets_data_nodes(parent_key), safe=False)


class TreegridFullData(View):
    """Three-level hierarchy with timestamps: Category -> Company -> Person."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_full_data_nodes(parent_key), safe=False)


class TreegridColspanData(View):
    """Simulated product selection tree: Category -> Group -> Items."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_colspan_data_nodes(parent_key), safe=False)


class TreegridStyledData(View):
    """Component spec tree with per-cell colours from data."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_styled_data_nodes(parent_key), safe=False)


class TreegridCalcData(View):
    """Order calculator data: Category -> Products with prices."""

    def get(self, request):
        parent_key = request.GET.get('parent')
        return JsonResponse(_treegrid_calc_data_nodes(parent_key), safe=False)
