from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def google_ad(slot_name, ad_format='auto', full_width_responsive=True):
    """
    Render a Google AdSense ad unit.
    
    Usage:
        {% load ad_tags %}
        {% google_ad 'header_banner' %}
        {% google_ad 'sidebar' ad_format='rectangle' %}
    
    Args:
        slot_name: Key from settings.GOOGLE_ADS_SLOTS dict
        ad_format: 'auto', 'rectangle', 'vertical', 'horizontal'
        full_width_responsive: Boolean for responsive ads
    """
    # Check if ads are enabled
    if not getattr(settings, 'GOOGLE_ADSENSE_ENABLED', False):
        return ''
    
    # Get client ID
    client_id = getattr(settings, 'GOOGLE_ADSENSE_CLIENT_ID', '')
    if not client_id:
        return '<!-- AdSense client ID not configured -->'
    
    # Get ad slots
    ad_slots = getattr(settings, 'GOOGLE_ADS_SLOTS', {})
    ad_slot = ad_slots.get(slot_name, '')
    
    if not ad_slot:
        return f'<!-- AdSense slot "{slot_name}" not configured -->'
    
    # Build responsive attribute
    responsive_attr = 'true' if full_width_responsive else 'false'
    
    # Generate ad HTML
    ad_html = f'''
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="{client_id}"
         data-ad-slot="{ad_slot}"
         data-ad-format="{ad_format}"
         data-full-width-responsive="{responsive_attr}"></ins>
    <script>
         (adsbygoogle = window.adsbygoogle || []).push({{}});
    </script>
    '''
    
    return mark_safe(ad_html)


@register.simple_tag
def adsense_script():
    """
    Render the main AdSense script tag for the <head> section.
    
    Usage:
        {% load ad_tags %}
        {% adsense_script %}
    """
    if not getattr(settings, 'GOOGLE_ADSENSE_ENABLED', False):
        return ''
    
    client_id = getattr(settings, 'GOOGLE_ADSENSE_CLIENT_ID', '')
    if not client_id:
        return '<!-- AdSense not configured -->'
    
    script = f'''
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client_id}"
            crossorigin="anonymous"></script>
    '''
    
    return mark_safe(script)


@register.simple_tag
def ad_container(slot_name, container_class='my-4'):
    """
    Render an ad with a container div for better styling.
    
    Usage:
        {% load ad_tags %}
        {% ad_container 'header_banner' 'my-6 mx-auto max-w-4xl' %}
    """
    if not getattr(settings, 'GOOGLE_ADSENSE_ENABLED', False):
        return ''
    
    ad_code = google_ad(slot_name)
    if not ad_code or '<!--' in ad_code:
        return ''
    
    html = f'''
    <div class="{container_class} text-center">
        <div class="text-xs text-base-content/50 mb-2">Advertisement</div>
        {ad_code}
    </div>
    '''
    
    return mark_safe(html)
