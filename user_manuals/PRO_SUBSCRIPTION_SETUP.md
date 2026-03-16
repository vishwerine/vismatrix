# Pro Subscription Feature - Complete Setup Guide

## Overview

VisMatrix now includes a Pro subscription system that allows users to upgrade to premium features for $20/month. The system is powered by Stripe for secure payment processing.

## Features Implemented

### 1. Subscription Plans
- **Free Plan** - Basic features, forever free
- **Pro Plan** - $20/month with advanced features

### 2. Payment Integration
- Stripe Checkout for secure payments
- Automatic subscription management
- Payment history tracking
- Webhook integration for real-time updates

### 3. User Experience
- Subscription selection during/after signup
- Upgrade/downgrade functionality
- Cancel anytime with access until period end
- Stripe Customer Portal for self-service

### 4. Developer Tools
- `@pro_required()` decorator for protecting premium features
- Context processor for subscription status in all templates
- Admin interface for subscription management

## Files Created/Modified

### New Files
1. `/tracker/subscription_views.py` - All subscription and payment views
2. `/tracker/templates/tracker/subscription_plans.html` - Pricing page
3. `/tracker/templates/tracker/payment_history.html` - Payment records

### Modified Files
1. `/tracker/models.py` - Added `Subscription` and `PaymentHistory` models
2. `/tracker/decorators.py` - Added `@pro_required()` decorator
3. `/tracker/context_processors.py` - Added subscription context
4. `/tracker/urls.py` - Added subscription routes
5. `/tracker/admin.py` - Registered new models
6. `/tracker/templates/tracker/base.html` - Added subscription link in nav
7. `/progress_tracker/settings.py` - Added Stripe configuration
8. `/requirements.txt` - Added `stripe` package

### Database Migrations
- Migration `0027_subscription_paymenthistory_and_more.py` created

## Configuration Required

### 1. Stripe Account Setup

1. **Create Stripe Account**
   - Go to https://stripe.com and sign up
   - Complete business verification

2. **Get API Keys**
   - Navigate to Developers → API keys
   - Copy your Publishable key and Secret key
   - For testing: use test mode keys (start with `pk_test_` and `sk_test_`)

3. **Setup Webhook**
   - Go to Developers → Webhooks
   - Click "Add endpoint"
   - URL: `https://yourdomain.com/webhooks/stripe/`
   - Events to select:
     - `checkout.session.completed`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
   - Copy the Signing secret

### 2. Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
```

**Important Security Notes:**
- Never commit API keys to version control
- Use test keys for development
- Use live keys only in production
- Rotate keys if compromised

### 3. Django Settings

Already configured in `settings.py`:

```python
# Stripe Payment Configuration
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')
PRO_SUBSCRIPTION_PRICE = 20.00  # USD per month
```

### 4. Context Processor

Already added to `settings.py`:

```python
'tracker.context_processors.user_subscription',
```

This makes `user_subscription` available in all templates.

## Usage

### For Users

#### Viewing Plans
```
Navigate to: /subscription/
```

#### Upgrading to Pro
1. Click "Upgrade to Pro" button
2. Redirected to Stripe Checkout
3. Enter payment information
4. Confirm purchase
5. Redirected back with Pro access

#### Managing Subscription
1. Go to Profile dropdown → Subscription
2. Click "Manage Subscription" (Pro users)
3. Opens Stripe Customer Portal
4. Can update payment method, view invoices, cancel

#### Canceling Subscription
- Click "Cancel Subscription" on plans page
- Access continues until end of billing period
- No future charges

### For Developers

#### Protecting Pro Features

Use the `@pro_required()` decorator:

```python
from django.contrib.auth.decorators import login_required
from tracker.decorators import pro_required

@login_required
@pro_required()
def advanced_analytics(request):
    """This view is only accessible to Pro users."""
    # Your pro feature code here
    return render(request, 'tracker/advanced_analytics.html')
```

#### Checking Subscription in Templates

```django
{% if user_subscription.is_pro %}
  <!-- Pro feature content -->
  <div class="pro-feature">
    Advanced analytics available!
  </div>
{% else %}
  <!-- Upgrade prompt -->
  <div class="upgrade-prompt">
    <a href="{% url 'subscription_plans' %}">Upgrade to Pro</a>
  </div>
{% endif %}
```

#### Checking Subscription in Views

```python
def my_view(request):
    if request.user.subscription.is_pro:
        # Pro logic
        pass
    else:
        # Free logic
        pass
```

## URL Routes

```
/subscription/                    - View plans (GET)
/subscription/checkout/create/    - Create checkout session (POST)
/subscription/success/            - Post-payment success page (GET)
/subscription/cancel/             - Cancel subscription (POST)
/subscription/portal/             - Stripe customer portal (GET)
/subscription/payments/           - View payment history (GET)
/webhooks/stripe/                 - Stripe webhook endpoint (POST)
```

## Database Models

### Subscription Model

```python
class Subscription(models.Model):
    user = OneToOneField(User)
    plan = CharField(choices=['free', 'pro'])
    status = CharField(choices=['active', 'canceled', 'past_due', 'trialing', 'incomplete'])
    stripe_customer_id = CharField()
    stripe_subscription_id = CharField()
    current_period_start = DateTimeField()
    current_period_end = DateTimeField()
    # ... more fields
```

### PaymentHistory Model

```python
class PaymentHistory(models.Model):
    user = ForeignKey(User)
    subscription = ForeignKey(Subscription)
    amount = DecimalField()
    currency = CharField(default='USD')
    status = CharField(choices=['succeeded', 'pending', 'failed', 'refunded'])
    stripe_payment_intent_id = CharField()
    # ... more fields
```

## Webhook Events

The system handles these Stripe events automatically:

1. **checkout.session.completed** - Initial subscription creation
2. **invoice.payment_succeeded** - Successful recurring payment
3. **invoice.payment_failed** - Failed payment (updates status to past_due)
4. **customer.subscription.updated** - Subscription changes
5. **customer.subscription.deleted** - Subscription cancelled

## Testing

### Test Mode (Development)

1. Use Stripe test keys (start with `pk_test_` and `sk_test_`)
2. Use test card numbers:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
   - Requires 3D Secure: `4000 0027 6000 3184`
3. Use any future expiry date
4. Use any 3-digit CVC

### Testing Webhooks Locally

Use Stripe CLI:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/webhooks/stripe/

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger invoice.payment_succeeded
```

### Testing the Flow

1. **Sign up as a new user**
2. **Navigate to subscription page**
3. **Click "Upgrade to Pro"**
4. **Use test card: 4242 4242 4242 4242**
5. **Complete checkout**
6. **Verify Pro badge in navigation**
7. **Check subscription status in profile**

## Production Deployment

### Before Going Live

1. ✅ Switch to live Stripe keys
2. ✅ Update webhook endpoint to production URL
3. ✅ Test webhook delivery in Stripe dashboard
4. ✅ Enable HTTPS (required for Stripe)
5. ✅ Review Stripe settings (branding, emails, etc.)
6. ✅ Setup proper error monitoring
7. ✅ Configure backup payment methods
8. ✅ Test all subscription flows end-to-end

### Security Checklist

- [ ] API keys stored in environment variables (not in code)
- [ ] Webhook signature verification enabled
- [ ] HTTPS enforced for all payment pages
- [ ] CSRF protection enabled
- [ ] PCI compliance reviewed (Stripe handles this)
- [ ] Rate limiting on payment endpoints
- [ ] Proper error handling (don't expose sensitive data)

## Admin Management

### Viewing Subscriptions

```
Django Admin → Tracker → Subscriptions
```

Features:
- Filter by plan, status, creation date
- Search by username, email, Stripe IDs
- View subscription periods and dates
- Manual status updates (use carefully)

### Viewing Payments

```
Django Admin → Tracker → Payment Histories
```

Features:
- Filter by status, currency, date
- Search by user, Stripe IDs
- View payment details and failures
- Track refunds

## Troubleshooting

### Webhook Not Working

1. Check webhook secret is correct in `.env`
2. Verify webhook endpoint URL in Stripe dashboard
3. Check server logs for errors
4. Test with Stripe CLI locally
5. Ensure CSRF exemption on webhook view

### Payment Not Completing

1. Check Stripe logs in dashboard
2. Verify API keys are correct
3. Check for JavaScript errors in browser console
4. Ensure Stripe.js is loaded
5. Test with different card numbers

### Subscription Status Not Updating

1. Check webhook delivery in Stripe dashboard
2. Verify webhook secret matches
3. Check Django logs for webhook processing errors
4. Manually trigger webhook events for testing

### User Shows Free But Paid

1. Check Subscription table in database
2. Verify webhook was delivered
3. Check for errors in webhook processing
4. Manually sync from Stripe if needed

## Support & Resources

### Stripe Documentation
- Checkout: https://stripe.com/docs/payments/checkout
- Subscriptions: https://stripe.com/docs/billing/subscriptions/overview
- Webhooks: https://stripe.com/docs/webhooks
- Testing: https://stripe.com/docs/testing

### Internal Resources
- Code: `/tracker/subscription_views.py`
- Models: `/tracker/models.py` (lines 1108-1225)
- Templates: `/tracker/templates/tracker/subscription_plans.html`
- Admin: Django Admin → Tracker section

### Getting Help
- Stripe Support: https://support.stripe.com
- Stripe Community: https://github.com/stripe
- Internal: Contact development team

## Roadmap / Future Enhancements

Potential features to add:

- [ ] Annual plan with discount
- [ ] Team/organization plans
- [ ] Usage-based billing
- [ ] Free trial period (7-14 days)
- [ ] Promo codes and discounts
- [ ] Lifetime access option
- [ ] Gifting subscriptions
- [ ] Referral program
- [ ] Enterprise plans
- [ ] Multi-currency support
- [ ] Alternative payment methods (PayPal, etc.)
- [ ] Subscription analytics dashboard
- [ ] Churn reduction features
- [ ] Automated dunning (retry failed payments)

---

**Last Updated:** January 22, 2026  
**Version:** 1.0  
**Maintained By:** VisMatrix Development Team
