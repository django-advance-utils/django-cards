from django.urls import path, register_converter
from cards.url_converters import CardListConverter
from cards_examples.views.base import HelloModal
from cards_examples.views.list import ExampleCompanyCardList, ExampleCompanyCardEmptyList, \
    ExampleCompanyCardAdvancedList
from cards_examples.views.main import ExampleIndex, ExampleCardsIndex
from cards_examples.views.tree import ExampleCompanyTree
from cards_examples.views.datatable import DatatableExample, DatatableOrderExample
from cards_examples.views.linked_datatables import (
    LinkedDatatablesExample, LinkedDatatablesPaymentExample, LinkedDatatablesFourLevelExample
)

from cards_examples.views.accordion import AccordionExample, AccordionAjaxExample, AccordionMultiExample, AccordionLayoutExample
from cards_examples.views.child_cards import ChildCardExampleIndex

from cards_examples.views.row_styles import RowStyleExampleIndex
from cards_examples.views.new_features import NewFeaturesIndex, NewFeaturesTableIndex, TooltipTestIndex, NewFeatures2Index, ImageGalleryIndex
from cards_examples.views.treegrid import (
    TreegridBasicExample, TreegridEditableExample, TreegridMultiLevelExample,
    TreegridCompactExample, TreegridPaymentsExample, TreegridExpandedExample,
    TreegridWidgetsExample, TreegridFullExample, TreegridBatchExample, TreegridColspanExample,
    TreegridStyledExample, TreegridCalculatorExample, TreegridDualExample,
    TreegridSelfDispatchExample, TreegridStaticExample, TreegridSelectExample,
    TreegridAdvancedExample,
    TreegridData,
)
from cards_examples.views.panel_layout import (
    PanelLayoutSidebarExample, PanelLayoutThreeColumnExample,
    PanelLayoutNestedExample, PanelLayoutHolyGrailExample,
    PanelLayoutWithDatatableExample, PanelLayoutFullscreenExample,
    PanelLayoutAccordionExample, PanelLayoutIframeExample,
    PanelLayoutLinkedDatatablesExample,
    PanelLayoutDetailDatatablesExample,
    PanelLayoutTabsExample,
)

app_name = 'cards_examples'


register_converter(CardListConverter, 'card_list')

urlpatterns = [
    path('', ExampleIndex.as_view(), name='index'),
    path('hello_modal/', HelloModal.as_view(), name='hello_modal'),

    path('groups/', ExampleCardsIndex.as_view(), name='groups'),

    path('list/<card_list:slug>', ExampleCompanyCardList.as_view(), name='list'),
    path('list/empty/<card_list:slug>', ExampleCompanyCardEmptyList.as_view(), name='list_empty'),
    path('list/adv/<card_list:slug>', ExampleCompanyCardAdvancedList.as_view(), name='list_adv'),

    path('tree/<card_list:slug>', ExampleCompanyTree.as_view(), name='tree'),

    path('child-cards/', ChildCardExampleIndex.as_view(), name='child_cards'),

    path('row-styles/', RowStyleExampleIndex.as_view(), name='row_styles'),

    path('datatable/', DatatableExample.as_view(), name='datatable'),
    path('datatable-order/', DatatableOrderExample.as_view(), name='datatable_order'),

    path('linked-datatables/', LinkedDatatablesExample.as_view(), name='linked_datatables'),
    path('linked-datatables-payments/', LinkedDatatablesPaymentExample.as_view(), name='linked_datatables_payments'),
    path('linked-datatables-four/', LinkedDatatablesFourLevelExample.as_view(), name='linked_datatables_four'),

    path('accordion/', AccordionExample.as_view(), name='accordion'),
    path('accordion-ajax/', AccordionAjaxExample.as_view(), name='accordion_ajax'),
    path('accordion-multi/', AccordionMultiExample.as_view(), name='accordion_multi'),
    path('accordion-layout/', AccordionLayoutExample.as_view(), name='accordion_layout'),

    path('new-features/', NewFeaturesIndex.as_view(), name='new_features'),
    path('new-features-table/', NewFeaturesTableIndex.as_view(), name='new_features_table'),

    path('tooltips/', TooltipTestIndex.as_view(), name='tooltips'),

    path('new-features-2/', NewFeatures2Index.as_view(), name='new_features_2'),
    path('image-gallery/', ImageGalleryIndex.as_view(), name='image_gallery'),

    path('treegrid/', TreegridBasicExample.as_view(), name='treegrid'),
    path('treegrid/editable/', TreegridEditableExample.as_view(), name='treegrid_editable'),
    path('treegrid/multi-level/', TreegridMultiLevelExample.as_view(), name='treegrid_multi'),
    path('treegrid/compact/', TreegridCompactExample.as_view(), name='treegrid_compact'),
    path('treegrid/payments/', TreegridPaymentsExample.as_view(), name='treegrid_payments'),
    path('treegrid/expanded/', TreegridExpandedExample.as_view(), name='treegrid_expanded'),
    path('treegrid/widgets/', TreegridWidgetsExample.as_view(), name='treegrid_widgets'),
    path('treegrid/data/', TreegridData.as_view(), name='treegrid_data'),
    path('treegrid/batch/', TreegridBatchExample.as_view(), name='treegrid_batch'),
    path('treegrid/self-dispatch/', TreegridSelfDispatchExample.as_view(), name='treegrid_self'),
    path('treegrid/select/', TreegridSelectExample.as_view(), name='treegrid_select'),
    path('treegrid/advanced/', TreegridAdvancedExample.as_view(), name='treegrid_advanced'),
    path('treegrid/static/', TreegridStaticExample.as_view(), name='treegrid_static'),
    path('treegrid/dual/', TreegridDualExample.as_view(), name='treegrid_dual'),
    path('treegrid/calculator/', TreegridCalculatorExample.as_view(), name='treegrid_calculator'),
    path('treegrid/styled/', TreegridStyledExample.as_view(), name='treegrid_styled'),
    path('treegrid/full/', TreegridFullExample.as_view(), name='treegrid_full'),
    path('treegrid/colspan/', TreegridColspanExample.as_view(), name='treegrid_colspan'),

    path('panel-layout/sidebar/', PanelLayoutSidebarExample.as_view(), name='panel_sidebar'),
    path('panel-layout/three-column/', PanelLayoutThreeColumnExample.as_view(), name='panel_three_col'),
    path('panel-layout/nested/', PanelLayoutNestedExample.as_view(), name='panel_nested'),
    path('panel-layout/holy-grail/', PanelLayoutHolyGrailExample.as_view(), name='panel_holy_grail'),
    path('panel-layout/datatable/', PanelLayoutWithDatatableExample.as_view(), name='panel_datatable'),
    path('panel-layout/fullscreen/', PanelLayoutFullscreenExample.as_view(), name='panel_fullscreen'),
    path('panel-layout/accordion/', PanelLayoutAccordionExample.as_view(), name='panel_accordion'),
    path('panel-layout/iframe/', PanelLayoutIframeExample.as_view(), name='panel_iframe'),
    path('panel-layout/linked-datatables/', PanelLayoutLinkedDatatablesExample.as_view(), name='panel_linked_dt'),
    path('panel-layout/detail-datatables/', PanelLayoutDetailDatatablesExample.as_view(), name='panel_detail_dt'),
    path('panel-layout/tabs/', PanelLayoutTabsExample.as_view(), name='panel_tabs'),
]


