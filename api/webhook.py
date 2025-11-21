"""
Stripe Webhook Handler for CraveMap - Vercel Serverless Function

Deploy to Vercel and configure webhook URL in Stripe Dashboard:
https://your-project.vercel.app/api/webhook
"""

import os
import json
import stripe
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
POSTGRES_CONNECTION_STRING = os.getenv('POSTGRES_CONNECTION_STRING')


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        import psycopg2
        if POSTGRES_CONNECTION_STRING:
            return psycopg2.connect(POSTGRES_CONNECTION_STRING)
    except Exception as e:
        print(f"Database connection failed: {e}")
    return None


def update_user_subscription(email, is_premium, subscription_id=None, customer_id=None):
    """Update user subscription status in database"""
    if not POSTGRES_CONNECTION_STRING:
        print("No database connection string configured")
        return False

    conn = get_db_connection()
    if not conn:
        print(f"Failed to connect to database")
        return False

    try:
        cursor = conn.cursor()

        # Update user's premium status
        cursor.execute("""
            UPDATE users
            SET is_premium = %s,
                stripe_customer_id = COALESCE(%s, stripe_customer_id),
                stripe_subscription_id = COALESCE(%s, stripe_subscription_id),
                updated_at = %s
            WHERE LOWER(email) = LOWER(%s)
        """, (is_premium, customer_id, subscription_id, datetime.now(), email))

        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Updated {email}: is_premium={is_premium}, rows_affected={affected}")
        return affected > 0

    except Exception as e:
        print(f"Error updating subscription: {e}")
        try:
            if conn:
                conn.close()
        except:
            pass
        return False


def get_customer_email(customer_id):
    """Retrieve customer email from Stripe"""
    if not customer_id or customer_id.startswith('cus_test'):
        return None
    try:
        customer = stripe.Customer.retrieve(customer_id)
        return customer.email
    except Exception as e:
        print(f"Error retrieving customer: {e}")
        return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            'status': 'healthy',
            'service': 'cravemap-stripe-webhook',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle Stripe webhook events"""
        try:
            content_length = int(self.headers.get('Content-Length') or 0)
            payload = self.rfile.read(content_length)
            sig_header = self.headers.get('Stripe-Signature')

            # Verify webhook signature
            if WEBHOOK_SECRET:
                try:
                    event = stripe.Webhook.construct_event(
                        payload, sig_header, WEBHOOK_SECRET
                    )
                except ValueError:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid payload'}).encode())
                    return
                except Exception as sig_err:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid signature'}).encode())
                    return
            else:
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                    return

            event_type = event.get('type', 'unknown')
            print(f"[WEBHOOK] Received: {event_type}")

            data = event.get('data', {}).get('object', {})
            customer_id = data.get('customer')
            subscription_id = data.get('subscription') or data.get('id')
            status = data.get('status', '')

            # Get customer email
            email = data.get('customer_email')
            if not email:
                customer_details = data.get('customer_details')
                if customer_details and isinstance(customer_details, dict):
                    email = customer_details.get('email')
            if not email and customer_id:
                email = get_customer_email(customer_id)

            result = {'status': 'success', 'event_type': event_type, 'email': email}

            if email:
                try:
                    if event_type in ['customer.subscription.created', 'customer.subscription.updated']:
                        is_active = status in ['active', 'trialing']
                        db_result = update_user_subscription(email, is_active, subscription_id, customer_id)
                        result['action'] = f'set_premium_{is_active}'
                        result['db_updated'] = db_result

                    elif event_type == 'customer.subscription.deleted':
                        db_result = update_user_subscription(email, False, subscription_id, customer_id)
                        result['action'] = 'revoked_premium'
                        result['db_updated'] = db_result

                    elif event_type == 'invoice.payment_succeeded':
                        if subscription_id:
                            db_result = update_user_subscription(email, True, subscription_id, customer_id)
                            result['action'] = 'renewed_premium'
                            result['db_updated'] = db_result

                    elif event_type == 'checkout.session.completed':
                        db_result = update_user_subscription(email, True, subscription_id, customer_id)
                        result['action'] = 'activated_premium'
                        result['db_updated'] = db_result
                    else:
                        result['action'] = 'unhandled_event'
                except Exception as db_error:
                    result['action'] = 'db_error'
                    result['db_error'] = str(db_error)
            else:
                result['action'] = 'no_email_found'

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[WEBHOOK] Error: {error_msg}")
            print(traceback.format_exc())
            self.send_response(200)  # Return 200 to prevent Stripe retries
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': error_msg}).encode())
