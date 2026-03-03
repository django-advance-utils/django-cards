"""
Django Channels consumer for push-based card reloading.

Requires django-channels to be installed and configured.

Setup:
    1. Install channels: pip install channels
    2. Add to your ASGI routing:

        from django.urls import re_path
        from cards.channels import CardReloadConsumer

        websocket_urlpatterns = [
            re_path(r'ws/cards/$', CardReloadConsumer.as_asgi()),
        ]

    3. Connect from JavaScript (after page load):

        var ws = setup_card_reload_ws(
            (location.protocol === 'https:' ? 'wss://' : 'ws://') +
            location.host + '/ws/cards/'
        );

    4. To push a card reload from the server:

        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'card_updates',
            {'type': 'reload_card', 'card': 'my_card_code'}
        )

    The client will receive the message and call reload_card() automatically,
    which triggers an AJAX round-trip through button_reload_card() to fetch
    fresh HTML for that card.
"""
try:
    from asgiref.sync import async_to_sync
    from channels.generic.websocket import JsonWebsocketConsumer

    class CardReloadConsumer(JsonWebsocketConsumer):
        """WebSocket consumer that pushes card reload commands to connected clients."""

        group_name = 'card_updates'

        def connect(self):
            async_to_sync(self.channel_layer.group_add)(
                self.group_name, self.channel_name
            )
            self.accept()

        def disconnect(self, close_code):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )

        def reload_card(self, event):
            """Handle card reload messages from the channel layer."""
            self.send_json({
                'command': 'reload_card',
                'card': event['card'],
            })

except ImportError:
    pass
