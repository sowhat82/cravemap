"""
Stripe Webhook Handler for CraveMap
Flask server to handle Stripe webhook events for subscription management.

Deploy this as a separate service (e.g., on Railway, Render, or Heroku)
and configure the webhook URL in your Stripe Dashboard.
"""

import os
import json
import stripe
from flask import Flask, request, jsonify
from datetime import datetime
from functools import wraps

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_LIVE_SECRET_KEY') or os.getenv('STRIPE_TEST_SECRET_KEY')
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Database configuration
POSTGRES_CONNECTION_STRING = os.getenv('POSTGRES_CONNECTION_STRING')


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        import psycopg2
        if POSTGRES_CONNECTION_STRING:
            return psycopg2.connect(POSTGRES_CONNECTION_STRING)
    except ImportError:
        print("psycopg2 not installed, trying sqlite fallback")
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")

    # Fallback to SQLite
    try:
        import sqlite3
        conn = sqlite3.connect('cravemap.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"SQLite connection failed: {e}")
        return None


def update_user_subscription(email, is_premium, subscription_id=None, customer_id=None):
    """Update user subscription status in database"""
    conn = get_db_connection()
    if not conn:
        print(f"Failed to connect to database")
        return False

    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Check if using PostgreSQL or SQLite
        is_postgres = hasattr(conn, 'info')  # PostgreSQL connections have 'info' attribute

        if is_postgres:
            # PostgreSQL - update users table
            cursor.execute("""
                UPDATE users
                SET is_premium = %s,
                    updated_at = %s
                WHERE email = %s
            """, (is_premium, datetime.now(), email))

            if cursor.rowcount == 0:
                print(f"No user found with email: {email}")
        else:
            # SQLite - need to handle differently due to schema
            # First check if user exists by email
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                user_id = user[0] if isinstance(user, tuple) else user['user_id']

                # Build update based on available columns
                cursor.execute("""
                    UPDATE users
                    SET is_premium = ?,
                        payment_completed = ?,
                        stripe_customer_id = COALESCE(?, stripe_customer_id),
                        last_updated = ?
                    WHERE email = ?
                """, (is_premium, is_premium, customer_id, now, email))
            else:
                print(f"No user found with email: {email}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"Updated subscription for {email}: is_premium={is_premium}")
        return True

    except Exception as e:
        print(f"Error updating subscription: {e}")
        if conn:
            conn.close()
        return False


def get_customer_email(customer_id):
    """Retrieve customer email from Stripe"""
    try:
        customer = stripe.Customer.retrieve(customer_id)
        return customer.email
    except Exception as e:
        print(f"Error retrieving customer: {e}")
        return None


def log_webhook_event(event_type, event_id, status, details=None):
    """Log webhook events for debugging"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'event_id': event_id,
        'status': status,
        'details': details
    }
    print(f"[WEBHOOK] {json.dumps(log_entry)}")

    # Optionally save to file for debugging
    try:
        with open('webhook_logs.json', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'cravemap-stripe-webhook',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events

    Configure this URL in Stripe Dashboard:
    https://your-domain.com/webhook/stripe

    Events to subscribe to:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    # Verify webhook signature
    if WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, WEBHOOK_SECRET
            )
        except ValueError as e:
            log_webhook_event('unknown', 'none', 'error', f'Invalid payload: {e}')
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError as e:
            log_webhook_event('unknown', 'none', 'error', f'Invalid signature: {e}')
            return jsonify({'error': 'Invalid signature'}), 400
    else:
        # No webhook secret configured - parse payload directly (not recommended for production)
        try:
            event = json.loads(payload)
            print("WARNING: No webhook secret configured. Signature verification skipped.")
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON'}), 400

    event_type = event.get('type', event.get('event', {}).get('type', 'unknown'))
    event_id = event.get('id', 'unknown')

    log_webhook_event(event_type, event_id, 'received')

    try:
        # Handle different event types
        if event_type == 'customer.subscription.created':
            handle_subscription_created(event)

        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(event)

        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(event)

        elif event_type == 'invoice.payment_succeeded':
            handle_payment_succeeded(event)

        elif event_type == 'invoice.payment_failed':
            handle_payment_failed(event)

        elif event_type == 'checkout.session.completed':
            handle_checkout_completed(event)

        else:
            log_webhook_event(event_type, event_id, 'ignored', 'Unhandled event type')

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        log_webhook_event(event_type, event_id, 'error', str(e))
        return jsonify({'error': str(e)}), 500


def handle_subscription_created(event):
    """Handle new subscription creation"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('id')
    status = data.get('status')

    email = get_customer_email(customer_id)
    if email:
        is_active = status in ['active', 'trialing']
        update_user_subscription(email, is_active, subscription_id, customer_id)
        log_webhook_event('subscription.created', event.get('id'), 'processed',
                         f'Email: {email}, Status: {status}')


def handle_subscription_updated(event):
    """Handle subscription updates (upgrades, downgrades, status changes)"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('id')
    status = data.get('status')

    email = get_customer_email(customer_id)
    if email:
        is_active = status in ['active', 'trialing']
        update_user_subscription(email, is_active, subscription_id, customer_id)
        log_webhook_event('subscription.updated', event.get('id'), 'processed',
                         f'Email: {email}, Status: {status}')


def handle_subscription_deleted(event):
    """Handle subscription cancellation"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('id')

    email = get_customer_email(customer_id)
    if email:
        update_user_subscription(email, False, subscription_id, customer_id)
        log_webhook_event('subscription.deleted', event.get('id'), 'processed',
                         f'Email: {email}, Premium revoked')


def handle_payment_succeeded(event):
    """Handle successful payment (subscription renewal)"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('subscription')

    # Only process if this is a subscription payment
    if subscription_id:
        email = get_customer_email(customer_id)
        if email:
            update_user_subscription(email, True, subscription_id, customer_id)
            log_webhook_event('payment.succeeded', event.get('id'), 'processed',
                             f'Email: {email}, Subscription renewed')


def handle_payment_failed(event):
    """Handle failed payment"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('subscription')

    email = get_customer_email(customer_id)
    if email:
        # Log the failure but don't immediately revoke access
        # Stripe will retry and eventually cancel if payment continues to fail
        log_webhook_event('payment.failed', event.get('id'), 'processed',
                         f'Email: {email}, Payment failed - awaiting retry')


def handle_checkout_completed(event):
    """Handle completed checkout session"""
    data = event.get('data', {}).get('object', {})
    customer_id = data.get('customer')
    subscription_id = data.get('subscription')
    customer_email = data.get('customer_email') or data.get('customer_details', {}).get('email')

    # Get email from customer if not in checkout data
    if not customer_email and customer_id:
        customer_email = get_customer_email(customer_id)

    if customer_email and subscription_id:
        update_user_subscription(customer_email, True, subscription_id, customer_id)
        log_webhook_event('checkout.completed', event.get('id'), 'processed',
                         f'Email: {customer_email}, Premium activated')


# For local development
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"""
    ===================================
    CraveMap Stripe Webhook Server
    ===================================

    Webhook URL: http://localhost:{port}/webhook/stripe
    Health Check: http://localhost:{port}/health

    For production, deploy this service and configure:
    https://your-domain.com/webhook/stripe

    In Stripe Dashboard, subscribe to these events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    - checkout.session.completed
    ===================================
    """)

    app.run(host='0.0.0.0', port=port, debug=debug)
