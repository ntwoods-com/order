# ================================
# api.py - REST API Endpoints
# ================================
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import jwt
import os
from db_utils import connect as db_connect, init_schema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.getenv('DATABASE_FILE', os.path.join(BASE_DIR, 'order_counter.db'))

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# JWT Secret
JWT_SECRET = os.getenv('JWT_SECRET', os.getenv('SECRET_KEY', 'default-secret'))

def get_db_connection():
    return db_connect(default_sqlite_db_file=DATABASE_FILE)


# ==================== JWT Authentication ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'success': False, 'error': 'Token is missing', 'code': 'AUTH_REQUIRED'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token expired', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token', 'code': 'INVALID_TOKEN'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated


def session_or_token_required(f):
    """Allow either session-based or token-based authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # First check session
        if 'user' in session:
            return f(session['user'], *args, **kwargs)
        
        # Then check JWT token
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if token:
            try:
                data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                return f(data['username'], *args, **kwargs)
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass
        
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
    return decorated


# ==================== Dashboard Stats API ====================
@api_bp.route('/dashboard/stats', methods=['GET'])
@session_or_token_required
def get_dashboard_stats(current_user):
    """Get comprehensive dashboard statistics"""
    try:
        conn = get_db_connection()
        
        # Total orders
        total_orders = conn.execute("SELECT COUNT(*) as count FROM sale_orders").fetchone()['count']
        
        # User's orders
        user_orders = conn.execute(
            "SELECT COUNT(*) as count FROM sale_orders WHERE username = ?", 
            (current_user,)
        ).fetchone()['count']
        
        # Today's orders
        today = datetime.now().strftime('%Y-%m-%d')
        today_orders = conn.execute(
            "SELECT COUNT(*) as count FROM sale_orders WHERE generated_at LIKE ?",
            (f"{today}%",)
        ).fetchone()['count']
        
        # This month's orders
        current_month = datetime.now().strftime('%Y-%m')
        month_orders = conn.execute(
            "SELECT COUNT(*) as count FROM sale_orders WHERE generated_at LIKE ?",
            (f"{current_month}%",)
        ).fetchone()['count']
        
        # Top dealers (all time)
        top_dealers = conn.execute("""
            SELECT dealer_name, city, COUNT(*) as order_count 
            FROM sale_orders 
            GROUP BY dealer_name, city 
            ORDER BY order_count DESC 
            LIMIT 10
        """).fetchall()
        
        # Top cities
        top_cities = conn.execute("""
            SELECT city, COUNT(*) as order_count 
            FROM sale_orders 
            GROUP BY city 
            ORDER BY order_count DESC 
            LIMIT 10
        """).fetchall()
        
        # Orders by month (last 12 months)
        monthly_orders = conn.execute("""
            SELECT 
                substr(generated_at, 1, 7) as month,
                COUNT(*) as count
            FROM sale_orders 
            WHERE generated_at >= date('now', '-12 months')
            GROUP BY month 
            ORDER BY month ASC
        """).fetchall()
        
        # Orders by user
        orders_by_user = conn.execute("""
            SELECT username, COUNT(*) as count 
            FROM sale_orders 
            GROUP BY username 
            ORDER BY count DESC
        """).fetchall()
        
        # Recent activity
        recent_orders = conn.execute("""
            SELECT order_id, dealer_name, city, username, generated_at 
            FROM sale_orders 
            ORDER BY generated_at DESC 
            LIMIT 20
        """).fetchall()
        
        # Issued order IDs count
        issued_ids = conn.execute("SELECT COUNT(*) as count FROM issued_order_ids").fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'overview': {
                    'total_orders': total_orders,
                    'user_orders': user_orders,
                    'today_orders': today_orders,
                    'month_orders': month_orders,
                    'issued_ids': issued_ids
                },
                'top_dealers': [dict(d) for d in top_dealers],
                'top_cities': [dict(c) for c in top_cities],
                'monthly_orders': [dict(m) for m in monthly_orders],
                'orders_by_user': [dict(u) for u in orders_by_user],
                'recent_orders': [dict(o) for o in recent_orders]
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/dashboard/chart-data', methods=['GET'])
@session_or_token_required
def get_chart_data(current_user):
    """Get chart-specific data for dashboard"""
    try:
        conn = get_db_connection()
        chart_type = request.args.get('type', 'monthly')
        
        if chart_type == 'monthly':
            # Orders per month
            data = conn.execute("""
                SELECT 
                    substr(generated_at, 1, 7) as label,
                    COUNT(*) as value
                FROM sale_orders 
                WHERE generated_at >= date('now', '-12 months')
                GROUP BY label 
                ORDER BY label ASC
            """).fetchall()
        elif chart_type == 'daily':
            # Orders per day (last 30 days)
            data = conn.execute("""
                SELECT 
                    substr(generated_at, 1, 10) as label,
                    COUNT(*) as value
                FROM sale_orders 
                WHERE generated_at >= date('now', '-30 days')
                GROUP BY label 
                ORDER BY label ASC
            """).fetchall()
        elif chart_type == 'city':
            # Orders by city
            data = conn.execute("""
                SELECT city as label, COUNT(*) as value 
                FROM sale_orders 
                GROUP BY city 
                ORDER BY value DESC 
                LIMIT 10
            """).fetchall()
        elif chart_type == 'user':
            # Orders by user
            data = conn.execute("""
                SELECT username as label, COUNT(*) as value 
                FROM sale_orders 
                GROUP BY username 
                ORDER BY value DESC
            """).fetchall()
        else:
            data = []
        
        conn.close()
        
        return jsonify({
            'success': True,
            'chart_type': chart_type,
            'labels': [d['label'] for d in data],
            'values': [d['value'] for d in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Order History API ====================
@api_bp.route('/orders', methods=['GET'])
@session_or_token_required
def get_orders(current_user):
    """Get orders with filtering and pagination"""
    try:
        conn = get_db_connection()
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        # Filters
        dealer_name = request.args.get('dealer_name', '')
        city = request.args.get('city', '')
        order_id = request.args.get('order_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        username = request.args.get('username', '')
        only_mine = request.args.get('only_mine', 'false').lower() == 'true'
        
        # Build query
        conditions = []
        params = []
        
        if only_mine:
            conditions.append("username = ?")
            params.append(current_user)
        elif username:
            conditions.append("username LIKE ?")
            params.append(f"%{username}%")
        
        if dealer_name:
            conditions.append("dealer_name LIKE ?")
            params.append(f"%{dealer_name}%")
        
        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city}%")
        
        if order_id:
            conditions.append("order_id LIKE ?")
            params.append(f"%{order_id}%")
        
        if date_from:
            conditions.append("generated_at >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("generated_at <= ?")
            params.append(f"{date_to} 23:59:59")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM sale_orders WHERE {where_clause}"
        total = conn.execute(count_query, tuple(params)).fetchone()['total']
        
        # Get paginated results
        query = f"""
            SELECT id, username, dealer_name, city, order_id, report_name, generated_at 
            FROM sale_orders 
            WHERE {where_clause}
            ORDER BY generated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])
        orders = conn.execute(query, tuple(params)).fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'orders': [dict(o) for o in orders],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/orders/<int:order_id>', methods=['GET'])
@session_or_token_required
def get_order_detail(current_user, order_id):
    """Get single order details"""
    try:
        conn = get_db_connection()
        order = conn.execute(
            "SELECT * FROM sale_orders WHERE id = ?", 
            (order_id,)
        ).fetchone()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        return jsonify({'success': True, 'data': dict(order)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/orders/search', methods=['GET'])
@session_or_token_required
def search_orders(current_user):
    """Full-text search across orders"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({'success': False, 'error': 'Query must be at least 2 characters'}), 400
        
        conn = get_db_connection()
        
        results = conn.execute("""
            SELECT id, username, dealer_name, city, order_id, report_name, generated_at 
            FROM sale_orders 
            WHERE dealer_name LIKE ? OR city LIKE ? OR order_id LIKE ? OR username LIKE ?
            ORDER BY generated_at DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'query': query,
            'results': [dict(r) for r in results],
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Export API ====================
@api_bp.route('/orders/export', methods=['GET'])
@session_or_token_required
def export_orders(current_user):
    """Export orders data as JSON (can be converted to Excel client-side)"""
    try:
        conn = get_db_connection()
        
        # Same filters as get_orders
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        only_mine = request.args.get('only_mine', 'false').lower() == 'true'
        
        conditions = []
        params = []
        
        if only_mine:
            conditions.append("username = ?")
            params.append(current_user)
        
        if date_from:
            conditions.append("generated_at >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("generated_at <= ?")
            params.append(f"{date_to} 23:59:59")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        orders = conn.execute(f"""
            SELECT order_id, dealer_name, city, username, generated_at 
            FROM sale_orders 
            WHERE {where_clause}
            ORDER BY generated_at DESC
        """, tuple(params)).fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [dict(o) for o in orders],
            'count': len(orders),
            'exported_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Issued Order IDs API ====================
@api_bp.route('/issued-ids', methods=['GET'])
@session_or_token_required
def get_issued_ids(current_user):
    """Get issued order IDs with pagination"""
    try:
        conn = get_db_connection()
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        total = conn.execute("SELECT COUNT(*) as count FROM issued_order_ids").fetchone()['count']
        
        issued = conn.execute("""
            SELECT * FROM issued_order_ids 
            ORDER BY given_at DESC 
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'issued_ids': [dict(i) for i in issued],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Health Check ====================
@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })
