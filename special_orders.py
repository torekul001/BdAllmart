"""Homepage special requests, compatible with the original OrderNow table."""
import hmac
import re
from flask import Blueprint, request, session, redirect, url_for, flash, abort, send_from_directory
from db import fetch_all, fetch_one, execute
from market_routes import csrf, upload, asset_directory

special_orders = Blueprint('special_orders', __name__)

def service_types():
    return fetch_all("SELECT DISTINCT Services FROM ServicesType WHERE ISNULL(Services,'')<>'' ORDER BY Services")

@special_orders.route('/special-order', methods=['POST'])
def place():
    request.max_content_length=22*1024*1024
    token=session.get('market_csrf','')
    if not token or not hmac.compare_digest(token,request.form.get('csrf_token','')):
        abort(400)
    saved=[]
    try:
        details=request.form.get('details','').strip()
        email=request.form.get('email','').strip()
        service=request.form.get('service_type','').strip()
        if not details or len(details)>10000:
            raise ValueError('Describe your order in 1 to 10,000 characters.')
        if len(email)>50 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
            raise ValueError('Enter a valid contact email (maximum 50 characters).')
        if service not in {r['Services'] for r in service_types()} or len(service)>50:
            raise ValueError('Choose a valid service type.')
        for field in ('image','asset'):
            identity=upload(field)
            saved.append(identity)
        paths=['/sf/'+value if value else '' for value in saved]
        # Short UUID paths fit the legacy NVARCHAR(50) columns.
        execute("INSERT INTO OrderNow (email,OrderDetails,Image1,FileName1,FileType,FilesDetails,Comment) VALUES (?,?,?,?,?,?,?)",
                [email,details,paths[0],paths[1],saved[1].rsplit('.',1)[-1] if saved[1] else '',service,'New Order'])
    except ValueError as error:
        for identity in request.environ.get('market_uploads',[]):
            (asset_directory()/identity).unlink(missing_ok=True)
        flash(str(error),'error')
        return redirect(url_for('login')+'#jobs')
    except Exception:
        for identity in request.environ.get('market_uploads',[]):
            (asset_directory()/identity).unlink(missing_ok=True)
        raise
    flash('Your special order has been submitted. Our team will review your requirements and contact you.','success')
    return redirect(url_for('login')+'#jobs')

@special_orders.route('/sf/<identity>')
def attachment(identity):
    if not re.fullmatch(r'[0-9a-f-]{36}\.(zip|pdf|jpg|jpeg|png|webp|ai)',identity):
        abort(404)
    if not session.get('user_id'):
        abort(403)
    account=fetch_one('SELECT Email,UserCatagory,Active,Status FROM Users WHERE UserId=?',[session['user_id']])
    if not account or str(account['Active']).lower() not in {'1','true'} or str(account['Status'] or '').lower() not in {'','true'}:
        abort(403)
    path='/sf/'+identity
    order=fetch_one('SELECT TOP 1 email FROM OrderNow WHERE Image1=? OR FileName1=?',[path,path])
    if not order or (str(account['UserCatagory']).lower()!='admin' and str(account['Email']).lower()!=str(order['email']).lower()):
        abort(403)
    return send_from_directory(asset_directory(),identity,as_attachment=True)
