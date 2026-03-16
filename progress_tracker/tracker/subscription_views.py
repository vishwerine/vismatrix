"""
Subscription and payment views for Pro features.
"""
import stripe
import logging
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse

from .models import Subscription, PaymentHistory, User

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def subscription_plans(request):
    """Display subscription plans and current user's plan."""
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        # Create free subscription if doesn't exist
        subscription = Subscription.objects.create(
            user=request.user,
            plan='free',
            status='active'
        )
    
    # Check if this is a post-signup Pro upgrade
    post_signup_pro = request.session.pop('post_signup_pro', False)
    if post_signup_pro:
        messages.success(
            request,
            '🎉 Welcome to VisMatrix! Complete your Pro subscription to unlock all features.'
        )
    
    context = {
        'subscription': subscription,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'post_signup_pro': post_signup_pro,
        'pro_price': 2.99,  # Monthly price in USD
    }
    
    return render(request, 'tracker/subscription_plans.html', context)


@login_required
@require_http_methods(["POST"])
def create_checkout_session(request):
    """Create Stripe checkout session for Pro subscription."""
    try:
        # Get or create subscription
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            defaults={'plan': 'free', 'status': 'active'}
        )
        
        # Create or retrieve Stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.username,
                metadata={
                    'user_id': request.user.id,
                    'username': request.user.username,
                }
            )
            subscription.stripe_customer_id = customer.id
            subscription.save()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'VisMatrix Pro Subscription',
                            'description': 'Monthly subscription to VisMatrix Pro features',
                        },
                        'unit_amount': 299,  # $2.99 in cents
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.build_absolute_uri(reverse('subscription_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('subscription_plans')),
            metadata={
                'user_id': request.user.id,
            },
        )
        
        return JsonResponse({'sessionId': checkout_session.id})
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def subscription_success(request):
    """Handle successful subscription payment."""
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            # Retrieve checkout session
            session = stripe.checkout.Session.retrieve(session_id)
            logger.info(f"Processing successful payment for session: {session_id}")
            
            # Update subscription
            subscription = request.user.subscription
            
            # Retrieve the full subscription with all details
            stripe_subscription = stripe.Subscription.retrieve(
                session.subscription,
                expand=['latest_invoice', 'default_payment_method']
            )
            
            logger.info(f"Retrieved Stripe subscription: {stripe_subscription.id}")
            
            subscription.plan = 'pro'
            subscription.status = stripe_subscription.status
            subscription.stripe_subscription_id = stripe_subscription.id
            
            # Get price ID from items - safely handle the items attribute
            try:
                if stripe_subscription.get('items') and stripe_subscription.get('items', {}).get('data'):
                    subscription.stripe_price_id = stripe_subscription['items']['data'][0]['price']['id']
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Could not get price ID: {e}")
            
            # Set period dates - safely handle date fields
            try:
                from datetime import datetime, timezone as dt_timezone
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_subscription.get('current_period_start', timezone.now().timestamp()), 
                    tz=dt_timezone.utc
                )
            except (TypeError, ValueError):
                subscription.current_period_start = timezone.now()
                
            try:
                from datetime import datetime, timezone as dt_timezone
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_subscription.get('current_period_end', 
                        (timezone.now() + timezone.timedelta(days=30)).timestamp()), 
                    tz=dt_timezone.utc
                )
            except (TypeError, ValueError):
                subscription.current_period_end = timezone.now() + timezone.timedelta(days=30)
            
            subscription.save()
            
            logger.info(f"Updated subscription for user {request.user.username} to Pro")
            
            # Create payment history record
            payment_intent_id = None
            try:
                payment_intent_id = session.get('payment_intent')
            except (AttributeError, TypeError):
                pass
                
            PaymentHistory.objects.create(
                user=request.user,
                subscription=subscription,
                amount=Decimal('2.99'),
                currency='USD',
                status='succeeded',
                stripe_payment_intent_id=payment_intent_id,
                description='Pro subscription - Monthly',
            )
            
            logger.info(f"Created payment history record for user {request.user.username}")
            
            messages.success(
                request,
                '🎉 Welcome to VisMatrix Pro! You now have access to all premium features.'
            )
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {e}", exc_info=True)
            messages.error(request, 'There was an issue activating your subscription. Please contact support.')
    
    return redirect('subscription_plans')


@login_required
def subscription_cancel(request):
    """Cancel user's subscription."""
    if request.method == 'POST':
        try:
            subscription = request.user.subscription
            
            if subscription.stripe_subscription_id:
                # Cancel at period end (not immediately)
                stripe_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                
                subscription.status = 'canceled'
                subscription.canceled_at = timezone.now()
                subscription.save()
                
                messages.success(
                    request,
                    f'Your Pro subscription will remain active until {subscription.current_period_end.strftime("%B %d, %Y")}. You will not be charged again.'
                )
            else:
                messages.error(request, 'No active subscription found to cancel.')
                
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            messages.error(request, 'There was an issue canceling your subscription. Please contact support.')
    
    return redirect('subscription_plans')


@login_required
def subscription_portal(request):
    """Redirect to Stripe customer portal for subscription management."""
    try:
        subscription = request.user.subscription
        
        if not subscription.stripe_customer_id:
            messages.error(request, 'No subscription found.')
            return redirect('subscription_plans')
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=request.build_absolute_uri(reverse('subscription_plans')),
        )
        
        return redirect(portal_session.url)
        
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        messages.error(request, 'Unable to access subscription portal. Please try again.')
        return redirect('subscription_plans')


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
        
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
        
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)
        
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """Process completed checkout session."""
    try:
        user_id = session['metadata'].get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            subscription, _ = Subscription.objects.get_or_create(user=user)
            
            # Update customer ID if not set
            if not subscription.stripe_customer_id:
                subscription.stripe_customer_id = session['customer']
                subscription.save()
                
            logger.info(f"Checkout completed for user {user.username}")
    except Exception as e:
        logger.error(f"Error handling checkout session: {e}")


def handle_invoice_payment_succeeded(invoice):
    """Process successful invoice payment."""
    try:
        customer_id = invoice['customer']
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        
        # Create payment record
        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=Decimal(str(invoice['amount_paid'] / 100)),
            currency=invoice['currency'].upper(),
            status='succeeded',
            stripe_payment_intent_id=invoice.get('payment_intent'),
            stripe_invoice_id=invoice['id'],
            description=f"Invoice payment - {invoice['billing_reason']}",
        )
        
        # Update subscription status
        if subscription.status != 'active':
            subscription.status = 'active'
            subscription.save()
            
        logger.info(f"Invoice payment succeeded for user {subscription.user.username}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling invoice payment: {e}")


def handle_invoice_payment_failed(invoice):
    """Process failed invoice payment."""
    try:
        customer_id = invoice['customer']
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        
        # Create payment record
        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=Decimal(str(invoice['amount_due'] / 100)),
            currency=invoice['currency'].upper(),
            status='failed',
            stripe_invoice_id=invoice['id'],
            description=f"Invoice payment failed - {invoice['billing_reason']}",
            failure_reason=invoice.get('last_finalization_error', {}).get('message', 'Unknown error'),
        )
        
        # Update subscription status
        subscription.status = 'past_due'
        subscription.save()
        
        logger.warning(f"Invoice payment failed for user {subscription.user.username}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling failed payment: {e}")


def handle_subscription_updated(stripe_subscription):
    """Process subscription update from Stripe."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        
        subscription.status = stripe_subscription['status']
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_start'], tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_end'], tz=timezone.utc
        )
        
        # Check if subscription was canceled
        if stripe_subscription.get('cancel_at_period_end'):
            subscription.canceled_at = timezone.now()
        
        subscription.save()
        logger.info(f"Subscription updated for user {subscription.user.username}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found: {stripe_subscription['id']}")
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")


def handle_subscription_deleted(stripe_subscription):
    """Process subscription deletion from Stripe."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        
        subscription.plan = 'free'
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()
        
        logger.info(f"Subscription deleted for user {subscription.user.username}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found: {stripe_subscription['id']}")
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")


@login_required
def payment_history(request):
    """Display user's payment history."""
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'tracker/payment_history.html', context)
