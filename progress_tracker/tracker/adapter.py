"""
Custom allauth adapter to handle Pro subscription during signup.
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse


class ProSubscriptionAdapter(DefaultAccountAdapter):
    """Custom adapter that redirects to Stripe checkout if user selected Pro during signup."""
    
    def get_signup_redirect_url(self, request):
        """
        After successful signup, check if user wanted Pro subscription.
        If yes, redirect to Stripe checkout instead of default redirect.
        """
        # Check if user selected Pro subscription during signup
        subscribe_to_pro = request.POST.get('subscribe_to_pro') == 'on'
        
        if subscribe_to_pro:
            # Store in session that this is a post-signup Pro upgrade
            request.session['post_signup_pro'] = True
            # Redirect to subscription plans page
            return reverse('subscription_plans')
        
        # Default behavior - redirect to dashboard or next URL
        return super().get_signup_redirect_url(request)
